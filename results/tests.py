from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal

from accounts.models import User, Department, ClassGroup, StudentProfile, TeacherProfile, Notification
from exams.models import Subject, Question, AnswerOption, Exam, ExamQuestion, ExamAttempt, StudentAnswer
from results.models import Result


class ResultsEvaluationAndReportingTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Department & Class
        self.dept = Department.objects.create(name='Computer Science', code='CS')
        self.cls_grp = ClassGroup.objects.create(department=self.dept, name='BCA', semester='3')

        # Teacher
        self.teacher = User.objects.create_user(
            username='prof_evaluator',
            password='TeacherPassword123!',
            role='teacher'
        )
        self.teacher_profile = TeacherProfile.objects.create(
            user=self.teacher,
            employee_id='EMP555',
            department='Computer Science',
            verification_status='approved'
        )

        # Student
        self.student = User.objects.create_user(
            username='student_marks_user',
            password='StudentPassword123!',
            role='student'
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student,
            full_name='Vikram Seth',
            roll_number='BCA202655',
            department='Computer Science',
            semester='3',
            class_group=self.cls_grp,
            verification_status='approved'
        )

        # Subject
        self.subject = Subject.objects.create(
            name='Software Engineering',
            code='BCA304',
            department=self.dept,
            created_by=self.teacher
        )

        # Objective & Descriptive Questions
        self.q_mcq = Question.objects.create(
            subject=self.subject,
            question_text='What model is also known as classic life cycle?',
            question_type='mcq',
            marks=5.0
        )
        self.opt_waterfall = AnswerOption.objects.create(question=self.q_mcq, option_text='Waterfall Model', is_correct=True, order=1)
        self.opt_spiral = AnswerOption.objects.create(question=self.q_mcq, option_text='Spiral Model', is_correct=False, order=2)

        self.q_desc = Question.objects.create(
            subject=self.subject,
            question_text='Explain agile methodology principles.',
            question_type='descriptive',
            marks=10.0,
            correct_text_answer='Individuals and interactions, working software, customer collaboration.'
        )

        # Exam
        self.exam = Exam.objects.create(
            title='Software Engineering Midterm',
            subject=self.subject,
            created_by=self.teacher,
            start_time=timezone.now() - timezone.timedelta(hours=1),
            end_time=timezone.now() + timezone.timedelta(hours=2),
            duration_minutes=60,
            total_marks=15.0,
            passing_marks=8.0,
            status='published'
        )
        self.exam.assigned_classes.add(self.cls_grp)
        ExamQuestion.objects.create(exam=self.exam, question=self.q_mcq, order=1, marks=5.0)
        ExamQuestion.objects.create(exam=self.exam, question=self.q_desc, order=2, marks=10.0)

        # Attempt
        self.attempt = ExamAttempt.objects.create(
            exam=self.exam,
            student=self.student,
            attempt_number=1,
            started_at=timezone.now() - timezone.timedelta(minutes=30),
            server_deadline=timezone.now() + timezone.timedelta(minutes=30),
            status='in_progress',
            shuffled_question_ids=[self.q_mcq.id, self.q_desc.id]
        )
        self.ans_mcq = StudentAnswer.objects.create(
            attempt=self.attempt,
            question=self.q_mcq,
            selected_option=self.opt_waterfall
        )
        self.ans_desc = StudentAnswer.objects.create(
            attempt=self.attempt,
            question=self.q_desc,
            text_answer='Agile focuses on iterative cycles and client feedback.'
        )

    def test_result_auto_created_and_evaluated_on_submit(self):
        """Submitting an attempt auto-evaluates objective questions and creates Result."""
        self.client.force_login(self.student)
        resp = self.client.post(reverse('submit_exam', args=[self.attempt.id]))
        self.assertEqual(resp.status_code, 302)

        result = Result.objects.get(attempt=self.attempt)
        self.assertEqual(float(result.total_marks_obtained), 5.0)
        self.assertEqual(result.grading_status, 'pending_manual')
        self.assertFalse(result.is_published)

    def test_unpublished_results_hidden_from_students(self):
        """Unpublished results are protected from student access."""
        result = Result.objects.create(
            attempt=self.attempt,
            exam=self.exam,
            student=self.student,
            total_marks_obtained=12.0,
            maximum_marks=15.0,
            is_passed=True,
            is_published=False
        )

        self.client.force_login(self.student)

        # List view does not show unpublished result
        resp = self.client.get(reverse('student_results'))
        self.assertNotContains(resp, 'Software Engineering Midterm')

        # Direct detail access returns 404
        resp_detail = self.client.get(reverse('student_result_detail', args=[result.id]))
        self.assertEqual(resp_detail.status_code, 404)

    def test_publish_results_workflow(self):
        """Teacher publishing results notifies students in-app and unblocks student scorecard."""
        result = Result.objects.create(
            attempt=self.attempt,
            exam=self.exam,
            student=self.student,
            total_marks_obtained=10.0,
            maximum_marks=15.0,
            is_passed=True,
            is_published=False
        )

        self.client.force_login(self.teacher)
        resp = self.client.post(reverse('toggle_result_publication', args=[self.exam.id]), {'action': 'publish'})
        self.assertEqual(resp.status_code, 302)

        result.refresh_from_db()
        self.assertTrue(result.is_published)

        # In-app notification received
        self.assertTrue(Notification.objects.filter(recipient=self.student, notification_type='result').exists())

        # Student can now view result scorecard
        self.client.force_login(self.student)
        resp = self.client.get(reverse('student_results'))
        self.assertContains(resp, 'Software Engineering Midterm')

        resp_detail = self.client.get(reverse('student_result_detail', args=[result.id]))
        self.assertEqual(resp_detail.status_code, 200)
        self.assertContains(resp_detail, '10.0')

    def test_manual_grading_of_descriptive_responses(self):
        """Teacher can manually evaluate descriptive responses and recalculate total score."""
        self.ans_mcq.marks_awarded = Decimal('5.0')
        self.ans_mcq.is_evaluated = True
        self.ans_mcq.save()

        result = Result.objects.create(
            attempt=self.attempt,
            exam=self.exam,
            student=self.student,
            total_marks_obtained=5.0,
            maximum_marks=15.0,
            is_published=False
        )

        self.client.force_login(self.teacher)

        # Submit manual score for descriptive answer (8.0 out of 10.0)
        resp = self.client.post(reverse('grade_attempt', args=[self.attempt.id]), {
            f'marks_{self.ans_desc.id}': '8.0',
            f'feedback_{self.ans_desc.id}': 'Good explanation of iterative development.'
        })
        self.assertEqual(resp.status_code, 302)

        self.ans_desc.refresh_from_db()
        self.assertEqual(float(self.ans_desc.marks_awarded), 8.0)
        self.assertTrue(self.ans_desc.is_evaluated)

        result.refresh_from_db()
        # 5.0 (MCQ) + 8.0 (Descriptive) = 13.0
        self.assertEqual(float(result.total_marks_obtained), 13.0)
        self.assertTrue(result.is_passed)  # 13.0 >= 8.0 passing marks
        self.assertEqual(result.grading_status, 'fully_graded')

    def test_export_results_csv(self):
        """Teacher can export a CSV performance ledger for an exam."""
        Result.objects.create(
            attempt=self.attempt,
            exam=self.exam,
            student=self.student,
            total_marks_obtained=11.0,
            maximum_marks=15.0,
            percentage=73.33,
            is_passed=True,
            is_published=True
        )

        self.client.force_login(self.teacher)
        resp = self.client.get(reverse('export_results_csv', args=[self.exam.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/csv')
        self.assertContains(resp, 'BCA202655')
        self.assertContains(resp, 'Vikram Seth')
        self.assertContains(resp, 'PASS')

    def test_cross_teacher_results_access_denied(self):
        """Teacher from an unrelated department cannot access, grade, publish, or export results for another teacher's exam."""
        other_dept = Department.objects.create(name='Civil Engineering', code='CE')
        other_teacher = User.objects.create_user(
            username='prof_civil',
            password='CivilPassword123!',
            role='teacher'
        )
        TeacherProfile.objects.create(
            user=other_teacher,
            employee_id='CE-101',
            department='Civil Engineering',
            verification_status='approved'
        )

        self.client.force_login(other_teacher)

        # 1. View results
        resp = self.client.get(reverse('teacher_exam_results', args=[self.exam.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse('manage_exams'))

        # 2. Grade attempt
        resp = self.client.get(reverse('grade_attempt', args=[self.attempt.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse('manage_exams'))

        # 3. Toggle publication
        resp = self.client.post(reverse('toggle_result_publication', args=[self.exam.id]), {'action': 'publish'})
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse('manage_exams'))

        # 4. Export CSV
        resp = self.client.get(reverse('export_results_csv', args=[self.exam.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertRedirects(resp, reverse('manage_exams'))
