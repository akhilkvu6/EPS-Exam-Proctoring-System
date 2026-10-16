from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User, Department, ClassGroup, StudentProfile, TeacherProfile, Notification
from exams.models import (
    Subject, Question, AnswerOption, Exam, ExamQuestion,
    ExamAttempt, StudentAnswer, ProctoringIncident
)


class ExaminationManagementTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Department & Class
        self.dept = Department.objects.create(name='Computer Science', code='CS')
        self.cls_grp = ClassGroup.objects.create(department=self.dept, name='BCA', semester='3')

        # Teacher
        self.teacher = User.objects.create_user(
            username='prof_exam_creator',
            password='TeacherPassword123!',
            role='teacher'
        )
        self.teacher_profile = TeacherProfile.objects.create(
            user=self.teacher,
            employee_id='EMP999',
            department='Computer Science',
            verification_status='approved'
        )

        # Student
        self.student = User.objects.create_user(
            username='student_examinee',
            password='StudentPassword123!',
            role='student'
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student,
            full_name='Test Examinee',
            roll_number='BCA202688',
            department='Computer Science',
            semester='3',
            class_group=self.cls_grp,
            verification_status='approved'
        )

        # Subject
        self.subject = Subject.objects.create(
            name='Web Programming',
            code='BCA302',
            department=self.dept,
            created_by=self.teacher
        )

        # Questions
        self.q1 = Question.objects.create(
            subject=self.subject,
            question_text='What does HTML stand for?',
            question_type='mcq',
            difficulty='easy',
            marks=2.0,
            negative_marks=0.5
        )
        AnswerOption.objects.create(question=self.q1, option_text='Hyper Text Markup Language', is_correct=True, order=1)
        AnswerOption.objects.create(question=self.q1, option_text='High Tech Multi Language', is_correct=False, order=2)

        self.q2 = Question.objects.create(
            subject=self.subject,
            question_text='Django is a Python web framework.',
            question_type='true_false',
            difficulty='easy',
            marks=1.0
        )
        AnswerOption.objects.create(question=self.q2, option_text='True', is_correct=True, order=1)
        AnswerOption.objects.create(question=self.q2, option_text='False', is_correct=False, order=2)

    def test_create_draft_examination(self):
        """Teacher can create an examination in Draft status."""
        self.client.force_login(self.teacher)

        start = timezone.now() + timezone.timedelta(days=1)
        end = start + timezone.timedelta(hours=2)

        resp = self.client.post(reverse('create_exam'), {
            'title': 'BCA Midterm Web Exam',
            'subject': self.subject.id,
            'description': 'Midterm evaluation for Web Programming',
            'instructions': 'Attempt all questions. Fullscreen required.',
            'start_time': start.strftime('%Y-%m-%dT%H:%M'),
            'end_time': end.strftime('%Y-%m-%dT%H:%M'),
            'duration_minutes': 60,
            'total_marks': 50,
            'passing_marks': 20,
            'default_negative_mark': 0.25,
            'camera_required': 'required',
            'microphone_required': 'optional',
            'fullscreen_required': 'on',
            'block_tab_switch': 'on',
            'block_copy_paste': 'on',
            'screen_sharing_required': 'disabled',
            'face_detection_enabled': 'on',
            'max_warning_count': 3,
            'assigned_classes': [self.cls_grp.id],
        })
        self.assertEqual(resp.status_code, 302)

        exam = Exam.objects.get(title='BCA Midterm Web Exam')
        self.assertEqual(exam.status, 'draft')
        self.assertEqual(exam.created_by, self.teacher)
        self.assertTrue(exam.assigned_classes.filter(id=self.cls_grp.id).exists())

    def test_add_and_remove_questions_from_exam(self):
        """Teacher can attach and remove questions from a draft exam."""
        exam = Exam.objects.create(
            title='Test Exam Qs',
            subject=self.subject,
            created_by=self.teacher,
            start_time=timezone.now() + timezone.timedelta(days=1),
            end_time=timezone.now() + timezone.timedelta(days=1, hours=2),
            duration_minutes=60,
            total_marks=10,
            status='draft'
        )

        self.client.force_login(self.teacher)

        # Add Q1
        resp = self.client.post(reverse('add_question_to_exam', args=[exam.id]), {
            'question_id': self.q1.id
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(exam.exam_questions.count(), 1)

        # Add Q2
        resp = self.client.post(reverse('add_question_to_exam', args=[exam.id]), {
            'question_id': self.q2.id
        })
        self.assertEqual(exam.exam_questions.count(), 2)

        # Remove Q1
        eq1 = exam.exam_questions.get(question=self.q1)
        resp = self.client.get(reverse('remove_question_from_exam', args=[exam.id, eq1.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(exam.exam_questions.count(), 1)

    def test_publish_exam_validation_and_notifications(self):
        """Publishing requires questions and sends in-app notifications to assigned students."""
        exam = Exam.objects.create(
            title='Publish Test Exam',
            subject=self.subject,
            created_by=self.teacher,
            start_time=timezone.now() + timezone.timedelta(days=1),
            end_time=timezone.now() + timezone.timedelta(days=1, hours=2),
            duration_minutes=60,
            total_marks=10,
            status='draft'
        )
        exam.assigned_classes.add(self.cls_grp)

        self.client.force_login(self.teacher)

        # Publishing with 0 questions fails
        resp = self.client.post(reverse('publish_exam', args=[exam.id]))
        exam.refresh_from_db()
        self.assertEqual(exam.status, 'draft')

        # Add question and publish
        ExamQuestion.objects.create(exam=exam, question=self.q1, order=1)
        resp = self.client.post(reverse('publish_exam', args=[exam.id]))
        self.assertEqual(resp.status_code, 302)

        exam.refresh_from_db()
        self.assertEqual(exam.status, 'published')

        # Check student received in-app notification
        self.assertTrue(Notification.objects.filter(recipient=self.student, notification_type='exam').exists())

    def test_student_eligibility_check(self):
        """is_eligible method properly respects student approval and class assignments."""
        exam = Exam.objects.create(
            title='Eligibility Exam',
            subject=self.subject,
            created_by=self.teacher,
            start_time=timezone.now() + timezone.timedelta(days=1),
            end_time=timezone.now() + timezone.timedelta(days=1, hours=2),
            duration_minutes=60,
            status='published'
        )
        exam.assigned_classes.add(self.cls_grp)

        # Approved enrolled student is eligible
        self.assertTrue(exam.is_eligible(self.student))

        # Teacher is not eligible to take exam as examinee
        self.assertFalse(exam.is_eligible(self.teacher))

        # Unapproved student is not eligible
        unapproved_student = User.objects.create_user(username='unapp_student', password='Pass12345!', role='student')
        StudentProfile.objects.create(
            user=unapproved_student,
            roll_number='BCA0001',
            department='Computer Science',
            semester='3',
            class_group=self.cls_grp,
            verification_status='pending'
        )
        self.assertFalse(exam.is_eligible(unapproved_student))

    def test_random_question_picker(self):
        """Random question selector correctly picks unassigned questions."""
        exam = Exam.objects.create(
            title='Random Test Exam',
            subject=self.subject,
            created_by=self.teacher,
            start_time=timezone.now() + timezone.timedelta(days=1),
            end_time=timezone.now() + timezone.timedelta(days=1, hours=2),
            duration_minutes=60,
            status='draft'
        )

        self.client.force_login(self.teacher)
        resp = self.client.post(reverse('add_random_questions', args=[exam.id]), {
            'count': 2,
            'difficulty': 'any',
            'topic': ''
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(exam.exam_questions.count(), 2)


class ExaminationEngineAndProctoringTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Department & Class
        self.dept = Department.objects.create(name='Computer Science', code='CS')
        self.cls_grp = ClassGroup.objects.create(department=self.dept, name='BCA', semester='3')

        # Teacher
        self.teacher = User.objects.create_user(
            username='prof_invigilator',
            password='TeacherPassword123!',
            role='teacher'
        )
        self.teacher_profile = TeacherProfile.objects.create(
            user=self.teacher,
            employee_id='EMP777',
            department='Computer Science',
            verification_status='approved'
        )

        # Student
        self.student = User.objects.create_user(
            username='student_taker',
            password='StudentPassword123!',
            role='student'
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student,
            full_name='Aarav Sharma',
            roll_number='BCA202677',
            department='Computer Science',
            semester='3',
            class_group=self.cls_grp,
            verification_status='approved'
        )

        # Subject
        self.subject = Subject.objects.create(
            name='Computer Networks',
            code='BCA303',
            department=self.dept,
            created_by=self.teacher
        )

        # Questions
        self.q_mcq = Question.objects.create(
            subject=self.subject,
            question_text='Which layer is responsible for routing?',
            question_type='mcq',
            marks=4.0,
            negative_marks=1.0
        )
        self.opt_correct = AnswerOption.objects.create(question=self.q_mcq, option_text='Network Layer', is_correct=True, order=1)
        self.opt_wrong = AnswerOption.objects.create(question=self.q_mcq, option_text='Transport Layer', is_correct=False, order=2)

        self.q_tf = Question.objects.create(
            subject=self.subject,
            question_text='TCP is a connectionless protocol.',
            question_type='true_false',
            marks=2.0,
            negative_marks=0.5
        )
        self.opt_tf_false = AnswerOption.objects.create(question=self.q_tf, option_text='False', is_correct=True, order=1)
        self.opt_tf_true = AnswerOption.objects.create(question=self.q_tf, option_text='True', is_correct=False, order=2)

        # Active Examination
        self.now = timezone.now()
        self.exam = Exam.objects.create(
            title='Networking Midterm Proctored',
            subject=self.subject,
            created_by=self.teacher,
            start_time=self.now - timezone.timedelta(minutes=10),
            end_time=self.now + timezone.timedelta(hours=2),
            duration_minutes=60,
            total_marks=6.0,
            passing_marks=3.0,
            negative_marking=True,
            default_negative_mark=1.0,
            camera_required='required',
            fullscreen_required=True,
            block_tab_switch=True,
            max_warning_count=2,
            status='published'
        )
        self.exam.assigned_classes.add(self.cls_grp)
        ExamQuestion.objects.create(exam=self.exam, question=self.q_mcq, order=1, marks=4.0, negative_marks=1.0)
        ExamQuestion.objects.create(exam=self.exam, question=self.q_tf, order=2, marks=2.0, negative_marks=0.5)

    def test_start_exam_creates_attempt_with_strict_deadline(self):
        """Student starting an active exam initializes attempt with calculated server deadline."""
        self.client.force_login(self.student)
        resp = self.client.get(reverse('start_exam', args=[self.exam.id]))
        self.assertEqual(resp.status_code, 302)

        attempt = ExamAttempt.objects.get(exam=self.exam, student=self.student)
        self.assertEqual(attempt.status, 'in_progress')
        self.assertTrue(attempt.server_deadline > timezone.now())
        self.assertEqual(attempt.answers.count(), 2)

    def test_autosave_answer_api(self):
        """Autosave endpoint saves chosen option and marked-for-review status via JSON."""
        self.client.force_login(self.student)
        self.client.get(reverse('start_exam', args=[self.exam.id]))
        attempt = ExamAttempt.objects.get(exam=self.exam, student=self.student)

        # Autosave MCQ answer
        resp = self.client.post(
            reverse('save_answer', args=[attempt.id]),
            data={
                'question_id': self.q_mcq.id,
                'selected_option_id': self.opt_correct.id,
                'is_marked_for_review': True
            },
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        json_data = resp.json()
        self.assertEqual(json_data['status'], 'saved')

        ans = attempt.answers.get(question=self.q_mcq)
        self.assertEqual(ans.selected_option, self.opt_correct)
        self.assertTrue(ans.is_marked_for_review)

    def test_submit_exam_and_automated_grading(self):
        """Student submits exam; objective questions are auto-graded with negative marking."""
        self.client.force_login(self.student)
        self.client.get(reverse('start_exam', args=[self.exam.id]))
        attempt = ExamAttempt.objects.get(exam=self.exam, student=self.student)

        # Answer Q1 correctly (4 marks)
        ans1 = attempt.answers.get(question=self.q_mcq)
        ans1.selected_option = self.opt_correct
        ans1.save()

        # Answer Q2 incorrectly (-0.5 marks)
        ans2 = attempt.answers.get(question=self.q_tf)
        ans2.selected_option = self.opt_tf_true
        ans2.save()

        # Submit
        resp = self.client.post(reverse('submit_exam', args=[attempt.id]))
        self.assertEqual(resp.status_code, 302)

        attempt.refresh_from_db()
        self.assertEqual(attempt.status, 'submitted')
        self.assertIsNotNone(attempt.submitted_at)

        # Total score: 4.0 - 0.5 = 3.5
        self.assertEqual(float(attempt.total_score), 3.5)

    def test_proctoring_incident_logging_and_flagging(self):
        """Proctoring telemetry increments warnings and flags attempt when threshold exceeded."""
        self.client.force_login(self.student)
        self.client.get(reverse('start_exam', args=[self.exam.id]))
        attempt = ExamAttempt.objects.get(exam=self.exam, student=self.student)

        # Log incident 1: Tab switch
        resp1 = self.client.post(
            reverse('log_proctoring_event', args=[attempt.id]),
            data={'event_type': 'tab_switch', 'severity': 'high', 'details': 'Switched to browser tab'},
            content_type='application/json'
        )
        self.assertEqual(resp1.status_code, 200)
        attempt.refresh_from_db()
        self.assertEqual(attempt.warning_count, 1)
        self.assertFalse(attempt.proctoring_flagged)

        # Log incident 2: Fullscreen exit (reaches max_warning_count = 2)
        resp2 = self.client.post(
            reverse('log_proctoring_event', args=[attempt.id]),
            data={'event_type': 'fullscreen_exit', 'severity': 'medium', 'details': 'Exited fullscreen'},
            content_type='application/json'
        )
        self.assertEqual(resp2.status_code, 200)
        attempt.refresh_from_db()
        self.assertEqual(attempt.warning_count, 2)
        self.assertTrue(attempt.proctoring_flagged)

    def test_live_invigilation_dashboard(self):
        """Teacher can monitor active examination sessions and flagged examinees."""
        self.client.force_login(self.student)
        self.client.get(reverse('start_exam', args=[self.exam.id]))

        self.client.force_login(self.teacher)
        resp = self.client.get(reverse('live_invigilation', args=[self.exam.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Aarav Sharma')

    def test_cross_teacher_exam_access_denied(self):
        """Teacher from an unrelated department cannot edit, view details, publish, or invigilate another teacher's exam."""
        other_dept = Department.objects.create(name='Mechanical Engineering', code='ME')
        other_teacher = User.objects.create_user(
            username='prof_mechanical',
            password='Password123!',
            role='teacher'
        )
        TeacherProfile.objects.create(
            user=other_teacher,
            employee_id='ME-888',
            department='Mechanical Engineering',
            verification_status='approved'
        )

        self.client.force_login(other_teacher)

        # 1. Edit Exam
        resp = self.client.get(reverse('edit_exam', args=[self.exam.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse('manage_exams'))

        # 2. Exam Detail
        resp = self.client.get(reverse('exam_detail', args=[self.exam.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse('manage_exams'))

        # 3. Publish Exam
        resp = self.client.post(reverse('publish_exam', args=[self.exam.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse('manage_exams'))

        # 4. Live Invigilation
        resp = self.client.get(reverse('live_invigilation', args=[self.exam.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse('manage_exams'))

    def test_late_entry_policy_rejection(self):
        """Student cannot start an exam past the institutional late entry window."""
        now = timezone.now()
        # Set exam start time to 45 minutes in past, duration 90 minutes
        self.exam.start_time = now - timezone.timedelta(minutes=45)
        self.exam.end_time = now + timezone.timedelta(minutes=45)
        self.exam.save()

        self.client.force_login(self.student)
        resp = self.client.get(reverse('start_exam', args=[self.exam.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse('student_exam_list'))

        # Attempt should NOT be created
        self.assertFalse(ExamAttempt.objects.filter(exam=self.exam, student=self.student).exists())

    def test_save_answer_foreign_question_rejected(self):
        """Student cannot submit answers to a foreign question ID not assigned to their attempt."""
        self.client.force_login(self.student)
        self.client.get(reverse('start_exam', args=[self.exam.id]))
        attempt = ExamAttempt.objects.get(exam=self.exam, student=self.student)

        # Foreign question ID
        resp = self.client.post(
            reverse('save_answer', args=[attempt.id]),
            data={'question_id': 99999, 'selected_option_id': self.opt_correct.id},
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 400)
        json_data = resp.json()
        self.assertEqual(json_data['status'], 'error')
        self.assertIn('not part of this examination', json_data['message'])

    def test_save_answer_foreign_option_rejected(self):
        """Student cannot submit an option ID that belongs to a different question."""
        self.client.force_login(self.student)
        self.client.get(reverse('start_exam', args=[self.exam.id]))
        attempt = ExamAttempt.objects.get(exam=self.exam, student=self.student)

        # Pass q_mcq but provide opt_tf_true (from True/False question)
        resp = self.client.post(
            reverse('save_answer', args=[attempt.id]),
            data={'question_id': self.q_mcq.id, 'selected_option_id': self.opt_tf_true.id},
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 400)
        json_data = resp.json()
        self.assertEqual(json_data['status'], 'error')
        self.assertIn('does not belong to this question', json_data['message'])

    def test_multi_attempt_result_binding_safe(self):
        """Multiple attempts safely update Result record without triggering unique_together IntegrityError."""
        from results.models import Result
        # Set exam attempt limit to 2
        self.exam.attempt_limit = 2
        self.exam.save()

        # Update institutional policy to dual attempt allowance
        from accounts.policies import save_institutional_policies
        save_institutional_policies({'attempt_allowance': 'dual'})

        self.client.force_login(self.student)

        # Attempt 1
        self.client.get(reverse('start_exam', args=[self.exam.id]))
        attempt1 = ExamAttempt.objects.get(exam=self.exam, student=self.student, attempt_number=1)
        self.client.post(reverse('submit_exam', args=[attempt1.id]))

        res1 = Result.objects.get(exam=self.exam, student=self.student)
        self.assertEqual(res1.attempt, attempt1)

        # Attempt 2
        self.client.get(reverse('start_exam', args=[self.exam.id]))
        attempt2 = ExamAttempt.objects.get(exam=self.exam, student=self.student, attempt_number=2)
        self.client.post(reverse('submit_exam', args=[attempt2.id]))

        res2 = Result.objects.get(exam=self.exam, student=self.student)
        self.assertEqual(res2.attempt, attempt2)
        self.assertEqual(Result.objects.filter(exam=self.exam, student=self.student).count(), 1)


class NewFeaturesAndHardeningWorkflowsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.dept = Department.objects.create(name='Computer Science', code='CS')
        self.cls_grp = ClassGroup.objects.create(department=self.dept, name='BCA', semester='3')

        self.teacher = User.objects.create_user(
            username='prof_anita_tests',
            password='Pass12345!',
            role='teacher',
            first_name='Anita Sharma'
        )
        self.teacher_prof = TeacherProfile.objects.create(
            user=self.teacher,
            employee_id='EMP888',
            department='Computer Science',
            verification_status='approved'
        )

        self.student = User.objects.create_user(
            username='student_arun',
            password='Pass12345!',
            role='student',
            first_name='Arun Kumar'
        )
        self.student_prof = StudentProfile.objects.create(
            user=self.student,
            full_name='Arun Kumar',
            roll_number='BCA202611',
            department='Computer Science',
            semester='3',
            class_group=self.cls_grp,
            verification_status='approved'
        )

        self.subject = Subject.objects.create(
            name='Operating Systems',
            code='CS303',
            department=self.dept,
            created_by=self.teacher
        )

        now = timezone.now()
        self.exam = Exam.objects.create(
            title='Midterm OS Assessment',
            subject=self.subject,
            created_by=self.teacher,
            status='published',
            start_time=now - timezone.timedelta(minutes=10),
            end_time=now + timezone.timedelta(hours=2),
            duration_minutes=60,
            total_marks=20,
            passing_marks=8,
            attempt_limit=1,
            camera_required='required',
            microphone_required='optional'
        )
        self.exam.assigned_classes.add(self.cls_grp)

        self.q = Question.objects.create(
            subject=self.subject,
            created_by=self.teacher,
            question_text='What is a Semaphore?',
            question_type='mcq',
            difficulty='medium',
            marks=5.0,
            negative_marks=1.0
        )
        self.opt1 = AnswerOption.objects.create(question=self.q, option_text='A synchronization tool', is_correct=True, order=1)
        self.opt2 = AnswerOption.objects.create(question=self.q, option_text='A CPU scheduling algorithm', is_correct=False, order=2)
        ExamQuestion.objects.create(exam=self.exam, question=self.q, order=1)

    def test_exam_readiness_page_access_and_parameters(self):
        self.client.force_login(self.student)
        resp = self.client.get(reverse('exam_readiness', args=[self.exam.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Midterm OS Assessment')
        self.assertContains(resp, '60 Mins')
        self.assertContains(resp, 'Pre-Flight Hardware & Proctoring Diagnostic')
        self.assertContains(resp, 'Institutional Examination Honor Code Declaration')

    def test_exam_readiness_ineligible_student_blocked(self):
        other_student = User.objects.create_user(username='other_student', password='Pass123!', role='student')
        StudentProfile.objects.create(user=other_student, roll_number='MECH01', department='Mechanical Engineering', semester='1', verification_status='approved')
        self.client.force_login(other_student)

        resp = self.client.get(reverse('exam_readiness', args=[self.exam.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse('student_exam_list'))

    def test_manual_close_exam_auto_submits_attempts(self):
        # Start an attempt for the student
        self.client.force_login(self.student)
        self.client.get(reverse('start_exam', args=[self.exam.id]))
        attempt = ExamAttempt.objects.get(exam=self.exam, student=self.student)
        self.assertEqual(attempt.status, 'in_progress')

        # Teacher closes the exam
        self.client.force_login(self.teacher)
        close_resp = self.client.post(reverse('close_exam', args=[self.exam.id]))
        self.assertEqual(close_resp.status_code, 302)

        self.exam.refresh_from_db()
        attempt.refresh_from_db()
        self.assertEqual(self.exam.status, 'closed')
        self.assertEqual(attempt.status, 'auto_submitted')

    def test_edit_question_and_delete_safeguards(self):
        self.client.force_login(self.teacher)

        # 1. Edit Question
        edit_resp = self.client.post(reverse('edit_question', args=[self.q.id]), {
            'subject': self.subject.id,
            'question_type': 'mcq',
            'difficulty': 'hard',
            'topic': 'Process Synchronization',
            'question_text': 'What is a counting semaphore?',
            'marks': '6.0',
            'negative_marks': '1.5',
            'option_text[]': ['Sync Primitive', 'Storage Register'],
            'correct_option': '0',
            'explanation': 'Semaphores manage access to shared resources.',
        })
        self.assertEqual(edit_resp.status_code, 302)
        self.q.refresh_from_db()
        self.assertEqual(self.q.question_text, 'What is a counting semaphore?')
        self.assertEqual(float(self.q.marks), 6.0)

        # 2. Delete safeguard: question in published exam cannot be deleted
        del_resp = self.client.post(reverse('delete_question', args=[self.q.id]))
        self.assertEqual(del_resp.status_code, 302)
        self.assertTrue(Question.objects.filter(id=self.q.id).exists())

        # Unlink question from exam
        ExamQuestion.objects.filter(exam=self.exam, question=self.q).delete()

        # 3. Delete safeguard: attempt student answers exist
        attempt = ExamAttempt.objects.create(
            exam=self.exam,
            student=self.student,
            attempt_number=1,
            server_deadline=timezone.now() + timezone.timedelta(hours=1)
        )
        StudentAnswer.objects.create(attempt=attempt, question=self.q)
        del_attempt_resp = self.client.post(reverse('delete_question', args=[self.q.id]))
        self.assertEqual(del_attempt_resp.status_code, 302)
        self.assertTrue(Question.objects.filter(id=self.q.id).exists())

        # 4. Clean deletion when unreferenced
        clean_q = Question.objects.create(
            subject=self.subject,
            created_by=self.teacher,
            question_text='Temporary Unused Question',
            question_type='short_answer',
            marks=1.0
        )
        del_clean_resp = self.client.post(reverse('delete_question', args=[clean_q.id]))
        self.assertEqual(del_clean_resp.status_code, 302)
        self.assertFalse(Question.objects.filter(id=clean_q.id).exists())

    def test_import_questions_csv(self):
        self.client.force_login(self.teacher)
        csv_content = (
            "subject_code,question_type,question_text,marks,negative_marks,difficulty,topic,option_a,option_b,option_c,option_d,correct_option,explanation\n"
            "CS303,mcq,What is virtual memory?,2.0,0.5,medium,Memory Management,RAM extension,Hard disk,Cache,Register,A,Virtual memory maps to disk storage.\n"
            "CS303,true_false,Paging suffers from external fragmentation.,1.0,0.25,easy,Paging,True,False,,,False,Paging avoids external fragmentation.\n"
        )
        from django.core.files.uploadedfile import SimpleUploadedFile
        csv_file = SimpleUploadedFile("test_questions.csv", csv_content.encode('utf-8'), content_type="text/csv")

        resp = self.client.post(reverse('import_questions'), {
            'file': csv_file,
            'default_subject': self.subject.id,
            'mode': 'skip_errors',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Question.objects.filter(question_text='What is virtual memory?').exists())
        self.assertTrue(Question.objects.filter(question_text='Paging suffers from external fragmentation.').exists())

    def test_review_incident_flow(self):
        self.client.force_login(self.student)
        self.client.get(reverse('start_exam', args=[self.exam.id]))
        attempt = ExamAttempt.objects.get(exam=self.exam, student=self.student)

        incident = ProctoringIncident.objects.create(
            attempt=attempt,
            event_type='tab_switch',
            severity='medium',
            details='User switched tabs during question 1'
        )

        self.client.force_login(self.teacher)
        review_url = reverse('review_incident', args=[incident.id])
        get_resp = self.client.get(review_url)
        self.assertEqual(get_resp.status_code, 200)
        self.assertContains(get_resp, 'User switched tabs during question 1')

        # Submit review outcome
        post_resp = self.client.post(review_url, {
            'review_status': 'reviewed',
            'review_notes': 'Verified incidental notification popup. Cleared without penalty.',
        })
        self.assertEqual(post_resp.status_code, 302)
        incident.refresh_from_db()
        self.assertEqual(incident.review_status, 'reviewed')
        self.assertEqual(incident.reviewed_by, self.teacher)
        self.assertIn('Verified incidental notification popup', incident.review_notes)


