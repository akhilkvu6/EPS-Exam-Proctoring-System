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
from apps.examinations.models import Examination, ExamSection, ExamStatus
from apps.examinations.services.scheduling import publish_examination, add_question_to_section
from apps.question_bank.models import Question, QuestionType
from apps.exam_engine.models import ExamAttempt, AttemptStatus
from apps.exam_engine.services.delivery import start_or_resume_attempt, submit_attempt
from apps.results.models import ExaminationResult, calculate_grade_letter
from apps.results.services.publisher import publish_examination_results
from apps.results.services.pdf_generator import generate_scorecard_pdf


class ResultsAndScorecardTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.teacher = User.objects.create_user(
            username="teacher_alastor",
            email="alastor@phoenix.edu",
            password="securepassword123",
            role=UserRole.TEACHER,
            status=UserStatus.ACTIVE,
        )
        self.student_cedric = User.objects.create_user(
            username="student_cedric",
            email="cedric@phoenix.edu",
            password="securepassword123",
            role=UserRole.STUDENT,
            status=UserStatus.ACTIVE,
        )
        self.student_draco = User.objects.create_user(
            username="student_draco",
            email="draco@phoenix.edu",
            password="securepassword123",
            role=UserRole.STUDENT,
            status=UserStatus.ACTIVE,
        )
        self.profile_cedric = StudentProfile.objects.create(
            user=self.student_cedric,
            roll_number="EP-2026-0005",
        )

        self.dept = Department.objects.create(name="Herbology", code="HERB")
        self.course = Course.objects.create(department=self.dept, name="B.Sc Botany", code="BSBO", duration_years=3)
        self.batch = AcademicBatch.objects.create(course=self.course, name="2026 Cohort", start_year=2026, end_year=2029)
        self.subject = Subject.objects.create(course=self.course, name="Magical Flora", code="HERB101", credits=3)

        StudentEnrollment.objects.create(student=self.profile_cedric, batch=self.batch, status="ENROLLED")
        TeacherAssignment.objects.create(teacher=self.teacher, subject=self.subject, batch=self.batch, academic_year=2026)

        self.q = Question.objects.create(
            subject=self.subject,
            author=self.teacher,
            question_type=QuestionType.SHORT_ANSWER,
            title="Mandrake Cry",
            content="What are the acoustic properties of mature Mandrake cry?",
            default_marks=Decimal("10.00"),
        )

        now = timezone.now()
        self.exam = Examination.objects.create(
            title="Flora Identification Exam",
            code="EXAM-HERB-01",
            subject=self.subject,
            batch=self.batch,
            created_by=self.teacher,
            start_window=now - timedelta(minutes=10),
            end_window=now + timedelta(hours=2),
            duration_minutes=45,
            pass_percentage=Decimal("40.00"),
        )
        sec = ExamSection.objects.create(examination=self.exam, title="Section 1", order=1)
        add_question_to_section(sec, self.q)
        publish_examination(self.exam, self.teacher)

        self.attempt = start_or_resume_attempt(self.exam, self.student_cedric)
        submit_attempt(self.attempt)
        # Manually evaluate attempt with 8.5 marks (85%)
        self.attempt.total_score = Decimal("8.50")
        self.attempt.status = AttemptStatus.EVALUATED
        self.attempt.save()

    def test_grade_letter_calculation(self):
        """Verifies grade classification boundaries."""
        self.assertEqual(calculate_grade_letter(Decimal("95.0")), "O")
        self.assertEqual(calculate_grade_letter(Decimal("82.5")), "A+")
        self.assertEqual(calculate_grade_letter(Decimal("74.0")), "A")
        self.assertEqual(calculate_grade_letter(Decimal("65.0")), "B+")
        self.assertEqual(calculate_grade_letter(Decimal("52.0")), "B")
        self.assertEqual(calculate_grade_letter(Decimal("45.0")), "C")
        self.assertEqual(calculate_grade_letter(Decimal("32.0")), "F")

    def test_publish_examination_results_service(self):
        """Tests cohort result publication, percentage computation, and SHA-256 hash stamp."""
        success, msg, count = publish_examination_results(self.exam, self.teacher)
        self.assertTrue(success)
        self.assertEqual(count, 1)

        self.exam.refresh_from_db()
        self.assertEqual(self.exam.status, ExamStatus.RESULTS_PUBLISHED)

        res = ExaminationResult.objects.filter(examination=self.exam, student=self.student_cedric).first()
        self.assertIsNotNone(res)
        self.assertEqual(res.total_score, Decimal("8.50"))
        self.assertEqual(res.percentage, Decimal("85.00"))
        self.assertEqual(res.grade_letter, "A+")
        self.assertTrue(res.is_passed)
        self.assertEqual(len(res.verification_hash), 64)

    def test_pdf_scorecard_generation_stream(self):
        """Tests ReportLab PDF generator outputting valid PDF bytes."""
        publish_examination_results(self.exam, self.teacher)
        res = ExaminationResult.objects.get(examination=self.exam, student=self.student_cedric)

        pdf_bytes = generate_scorecard_pdf(res)
        self.assertTrue(len(pdf_bytes) > 500)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

        # HTTP Download view
        self.client.force_login(self.student_cedric)
        url = reverse("results:download_pdf", args=[res.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        self.assertIn("inline", resp["Content-Disposition"])

    def test_public_cryptographic_verification_portal(self):
        """Verifies unauthenticated public verification endpoint displays authentic transcript."""
        publish_examination_results(self.exam, self.teacher)
        res = ExaminationResult.objects.get(examination=self.exam, student=self.student_cedric)

        # Anonymous client accesses public verify portal
        anon_client = Client()
        url = reverse("results:public_verify", args=[res.id])
        resp = anon_client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, res.verification_hash)
        self.assertContains(resp, "Academic Certificate Verified")

    def test_student_isolation_scorecard_access(self):
        """Ensures Student Draco cannot view or download Student Cedric's private web scorecard."""
        publish_examination_results(self.exam, self.teacher)
        res = ExaminationResult.objects.get(examination=self.exam, student=self.student_cedric)

        self.client.force_login(self.student_draco)
        url = reverse("results:scorecard", args=[res.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)
