from datetime import timedelta
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User, UserRole, UserStatus
from apps.student.models import StudentProfile
from apps.academics.models import (
    Department,
    Course,
    AcademicBatch,
    Subject,
    TeacherAssignment,
    StudentEnrollment,
)
from apps.examinations.models import Examination, ExamSection, ExamQuestion, ExamStatus
from apps.examinations.services.scheduling import publish_examination, add_question_to_section
from apps.question_bank.models import Question, QuestionOption, QuestionType
from apps.exam_engine.models import ExamAttempt, AttemptQuestion, AttemptStatus
from apps.exam_engine.services.delivery import start_or_resume_attempt, submit_attempt
from apps.evaluation.services.grader import (
    grade_objective_question,
    evaluate_attempt_objective_items,
    calculate_and_finalize_attempt_score,
    evaluate_entire_exam_cohort,
)
from apps.incidents.models import IncidentReviewRecord, FinalDisposition


class EvaluationEngineTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.teacher = User.objects.create_user(
            username="teacher_filius",
            email="filius@phoenix.edu",
            password="securepassword123",
            role=UserRole.TEACHER,
            status=UserStatus.ACTIVE,
        )
        self.student = User.objects.create_user(
            username="student_luna",
            email="luna@phoenix.edu",
            password="securepassword123",
            role=UserRole.STUDENT,
            status=UserStatus.ACTIVE,
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student,
            roll_number="EP-2026-0004",
        )

        self.dept = Department.objects.create(name="Charms", code="CHRM")
        self.course = Course.objects.create(department=self.dept, name="B.Sc Charms", code="BSCH", duration_years=3)
        self.batch = AcademicBatch.objects.create(course=self.course, name="2026 Cohort", start_year=2026, end_year=2029)
        self.subject = Subject.objects.create(course=self.course, name="Theory of Charms", code="CHRM101", credits=3)

        StudentEnrollment.objects.create(student=self.student_profile, batch=self.batch, status="ENROLLED")
        TeacherAssignment.objects.create(teacher=self.teacher, subject=self.subject, batch=self.batch, academic_year=2026)

        # 1. MCQ Single
        self.q_mcq = Question.objects.create(
            subject=self.subject,
            author=self.teacher,
            question_type=QuestionType.MCQ_SINGLE,
            title="Lumos Effect",
            content="What does Lumos create?",
            default_marks=Decimal("2.00"),
            negative_marks=Decimal("0.50"),
            version=1,
        )
        self.opt_mcq_correct = QuestionOption.objects.create(question=self.q_mcq, option_text="Light", is_correct=True, order=1)
        self.opt_mcq_wrong = QuestionOption.objects.create(question=self.q_mcq, option_text="Fire", is_correct=False, order=2)

        # 2. Numerical with tolerance
        self.q_num = Question.objects.create(
            subject=self.subject,
            author=self.teacher,
            question_type=QuestionType.NUMERICAL,
            title="Wand Arc Angle",
            content="Specify wand arc angle in degrees.",
            default_marks=Decimal("3.00"),
            negative_marks=Decimal("1.00"),
            numerical_target=45.0,
            numerical_tolerance=1.5,
            version=1,
        )

        # 3. Descriptive
        self.q_desc = Question.objects.create(
            subject=self.subject,
            author=self.teacher,
            question_type=QuestionType.DESCRIPTIVE,
            title="History of Cheering Charms",
            content="Detail the historical origins and ethical boundaries.",
            rubric="Award up to 5 marks based on historical depth.",
            default_marks=Decimal("5.00"),
            version=1,
        )

        now = timezone.now()
        self.exam = Examination.objects.create(
            title="Charms Mid-Term Exam",
            code="EXAM-CHRM-01",
            subject=self.subject,
            batch=self.batch,
            created_by=self.teacher,
            start_window=now - timedelta(minutes=10),
            end_window=now + timedelta(hours=2),
            duration_minutes=60,
        )
        sec = ExamSection.objects.create(examination=self.exam, title="Section A", order=1)
        add_question_to_section(sec, self.q_mcq)
        add_question_to_section(sec, self.q_num)
        add_question_to_section(sec, self.q_desc)
        publish_examination(self.exam, self.teacher)

        self.attempt = start_or_resume_attempt(self.exam, self.student)

    def test_auto_grader_mcq_single_and_numerical(self):
        """Verifies auto-grading of single MCQ and numerical items with tolerance."""
        att_questions = {
            q.exam_question.question.question_type: q
            for q in self.attempt.attempt_questions.all()
        }

        # 1. Correct MCQ
        att_mcq = att_questions[QuestionType.MCQ_SINGLE]
        att_mcq.candidate_answer = {"selected_option_ids": [self.opt_mcq_correct.id]}
        att_mcq.is_answered = True
        att_mcq.save()

        marks, evaluated = grade_objective_question(att_mcq)
        self.assertTrue(evaluated)
        self.assertEqual(marks, Decimal("2.00"))

        # 2. Correct Numerical within tolerance window [43.5, 46.5]
        att_num = att_questions[QuestionType.NUMERICAL]
        att_num.candidate_answer = {"value": 45.8} # within 1.5 tolerance
        att_num.is_answered = True
        att_num.save()

        num_marks, num_eval = grade_objective_question(att_num)
        self.assertTrue(num_eval)
        self.assertEqual(num_marks, Decimal("3.00"))

        # 3. Descriptive item is not auto-graded
        att_desc = att_questions[QuestionType.DESCRIPTIVE]
        att_desc.candidate_answer = {"text": "Detailed essay on cheering charms."}
        att_desc.is_answered = True
        att_desc.save()

        desc_marks, desc_eval = grade_objective_question(att_desc)
        self.assertFalse(desc_eval)

    def test_negative_marking_penalty(self):
        """Ensures incorrect responses receive configured negative penalty marks."""
        att_mcq = self.attempt.attempt_questions.filter(
            exam_question__question__question_type=QuestionType.MCQ_SINGLE
        ).first()

        att_mcq.candidate_answer = {"selected_option_ids": [self.opt_mcq_wrong.id]}
        att_mcq.is_answered = True
        att_mcq.save()

        marks, evaluated = grade_objective_question(att_mcq)
        self.assertTrue(evaluated)
        self.assertEqual(marks, Decimal("-0.50"))

    def test_subjective_rubric_grading_view(self):
        """Tests faculty scoring form updating awarded marks and feedback."""
        att_desc = self.attempt.attempt_questions.filter(
            exam_question__question__question_type=QuestionType.DESCRIPTIVE
        ).first()
        att_desc.candidate_answer = {"text": "Essay answer."}
        att_desc.is_answered = True
        att_desc.save()

        self.client.force_login(self.teacher)
        url = reverse("evaluation:grade_item", args=[att_desc.id])

        resp = self.client.post(url, {
            "awarded_marks": "4.50",
            "evaluator_feedback": "Excellent historical analysis.",
        })
        self.assertEqual(resp.status_code, 302)

        att_desc.refresh_from_db()
        self.assertTrue(att_desc.is_evaluated)
        self.assertEqual(att_desc.awarded_marks, Decimal("4.50"))
        self.assertEqual(att_desc.evaluator_feedback, "Excellent historical analysis.")

    def test_score_clamping_and_disciplinary_penalty(self):
        """Verifies disciplinary deduction applies and final score is clamped >= 0."""
        # Attach disciplinary penalty 20%
        IncidentReviewRecord.objects.create(
            attempt=self.attempt,
            reviewer=self.teacher,
            final_disposition=FinalDisposition.PENALIZED,
            penalty_percentage=Decimal("20.00"),
        )

        for q in self.attempt.attempt_questions.all():
            q.awarded_marks = Decimal("2.00")
            q.is_evaluated = True
            q.save()

        # Raw total = 3 * 2.00 = 6.00. Minus 20% penalty (1.20) = 4.80
        final_score = calculate_and_finalize_attempt_score(self.attempt)
        self.assertEqual(final_score, Decimal("4.80"))
