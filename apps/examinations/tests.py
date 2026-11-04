from datetime import timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User, UserRole, UserStatus
from apps.student.models import StudentProfile
from apps.academics.models import (
    Department,
    Course,
    AcademicBatch,
    Semester,
    Subject,
    TeacherAssignment,
    StudentEnrollment,
)
from apps.question_bank.models import (
    Question,
    QuestionOption,
    QuestionType,
    QuestionDifficulty,
)
from apps.question_bank.services.snapshot import create_or_get_question_snapshot
from apps.examinations.models import (
    Examination,
    ExamSection,
    ExamQuestion,
    CandidateAssignment,
    ExamStatus,
)
from apps.examinations.services.scheduling import (
    add_question_to_section,
    publish_examination,
)


class ExaminationManagementTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Users
        self.admin = User.objects.create_user(
            username="admin_albus",
            email="albus@phoenix.edu",
            password="securepassword123",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        )
        self.teacher_flitwick = User.objects.create_user(
            username="teacher_flitwick",
            email="flitwick@phoenix.edu",
            password="securepassword123",
            role=UserRole.TEACHER,
            status=UserStatus.ACTIVE,
        )
        self.teacher_snape = User.objects.create_user(
            username="teacher_snape",
            email="snape@phoenix.edu",
            password="securepassword123",
            role=UserRole.TEACHER,
            status=UserStatus.ACTIVE,
        )
        self.student_harry = User.objects.create_user(
            username="student_harry",
            email="harry@phoenix.edu",
            password="securepassword123",
            role=UserRole.STUDENT,
            status=UserStatus.ACTIVE,
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_harry,
            roll_number="EP-2026-0001",
        )

        # Academics
        self.dept = Department.objects.create(name="Computer Science", code="CS")
        self.course = Course.objects.create(
            department=self.dept, name="B.Tech Computer Science", code="BTCS", duration_years=4
        )
        self.batch = AcademicBatch.objects.create(
            course=self.course, name="2026-2030 Batch", start_year=2026, end_year=2030
        )
        self.semester = Semester.objects.create(
            batch=self.batch, semester_number=1, is_current=True
        )
        self.subject = Subject.objects.create(
            course=self.course,
            name="Design and Analysis of Algorithms",
            code="CS301",
            semester_number=1,
            credits=4,
        )

        # Enroll Harry into the batch
        StudentEnrollment.objects.create(
            student=self.student_profile,
            batch=self.batch,
            status="ENROLLED",
        )

        # Assign Flitwick to Algorithms for this batch
        TeacherAssignment.objects.create(
            teacher=self.teacher_flitwick,
            subject=self.subject,
            batch=self.batch,
            academic_year=2026,
            is_active=True,
        )

        # Create Question Bank item
        self.question = Question.objects.create(
            subject=self.subject,
            author=self.teacher_flitwick,
            question_type=QuestionType.MCQ_SINGLE,
            title="Dijkstra Shortest Path",
            content="What data structure optimizes Dijkstra's algorithm?",
            default_marks=Decimal("2.00"),
            negative_marks=Decimal("0.50"),
            version=1,
        )
        QuestionOption.objects.create(question=self.question, option_text="Min-Heap", is_correct=True, order=1)
        QuestionOption.objects.create(question=self.question, option_text="Stack", is_correct=False, order=2)

    def test_exam_creation_and_section_setup(self):
        """Verifies creating an examination, adding a section, and attaching a snapshot."""
        now = timezone.now()
        exam = Examination.objects.create(
            title="Mid-Semester Algorithms Exam",
            code="EXAM-CS301-MID",
            subject=self.subject,
            batch=self.batch,
            created_by=self.teacher_flitwick,
            status=ExamStatus.DRAFT,
            start_window=now + timedelta(hours=1),
            end_window=now + timedelta(hours=5),
            duration_minutes=60,
        )

        section = ExamSection.objects.create(
            examination=exam,
            title="Section A: Algorithms Theory",
            order=1,
        )

        # Attach question via service
        exam_q = add_question_to_section(
            section=section,
            question=self.question,
            marks=Decimal("2.00"),
        )

        self.assertIsNotNone(exam_q.snapshot)
        self.assertEqual(exam_q.snapshot.version, 1)

        # Check total marks recalculated on examination
        exam.refresh_from_db()
        self.assertEqual(exam.total_marks, Decimal("2.00"))

    def test_publish_examination_auto_provisions_candidates(self):
        """Tests that publishing an exam validates requirements and auto-provisions cohort candidates."""
        now = timezone.now()
        exam = Examination.objects.create(
            title="Final Term Assessment",
            code="EXAM-CS301-FINAL",
            subject=self.subject,
            batch=self.batch,
            created_by=self.teacher_flitwick,
            status=ExamStatus.DRAFT,
            start_window=now + timedelta(days=1),
            end_window=now + timedelta(days=1, hours=3),
            duration_minutes=90,
        )

        # Cannot publish without sections
        with self.assertRaises(ValidationError):
            publish_examination(exam, self.teacher_flitwick)

        section = ExamSection.objects.create(
            examination=exam,
            title="Section 1",
            order=1,
        )

        # Cannot publish without questions
        with self.assertRaises(ValidationError):
            publish_examination(exam, self.teacher_flitwick)

        # Add question and publish
        add_question_to_section(section, self.question)
        success, msg, count = publish_examination(exam, self.teacher_flitwick)

        self.assertTrue(success)
        self.assertEqual(count, 1)
        exam.refresh_from_db()
        self.assertEqual(exam.status, ExamStatus.PUBLISHED)

        # Verify Harry is enrolled as an eligible candidate
        assignment = CandidateAssignment.objects.filter(examination=exam, student=self.student_harry).first()
        self.assertIsNotNone(assignment)
        self.assertTrue(assignment.is_eligible)

    def test_teacher_scoping_isolation(self):
        """Verifies faculty cannot manage examinations outside their assigned scope."""
        now = timezone.now()
        exam = Examination.objects.create(
            title="Algorithms Assessment",
            code="EXAM-CS301-TEST",
            subject=self.subject,
            batch=self.batch,
            created_by=self.teacher_flitwick,
            start_window=now + timedelta(hours=1),
            end_window=now + timedelta(hours=4),
        )

        # Flitwick (assigned) has access
        self.client.force_login(self.teacher_flitwick)
        resp_flitwick = self.client.get(reverse("examinations:exam_detail", args=[exam.pk]))
        self.assertEqual(resp_flitwick.status_code, 200)

        # Snape (unassigned) receives 403 Forbidden
        self.client.force_login(self.teacher_snape)
        resp_snape = self.client.get(reverse("examinations:exam_detail", args=[exam.pk]))
        self.assertEqual(resp_snape.status_code, 403)

        # Student receives 403 Forbidden
        self.client.force_login(self.student_harry)
        resp_student = self.client.get(reverse("examinations:exam_detail", args=[exam.pk]))
        self.assertEqual(resp_student.status_code, 403)

    def test_exam_window_time_check(self):
        """Tests is_currently_open() against real-time operational windows."""
        now = timezone.now()
        exam = Examination.objects.create(
            title="Time Window Exam",
            code="EXAM-WINDOW-01",
            subject=self.subject,
            batch=self.batch,
            status=ExamStatus.PUBLISHED,
            start_window=now - timedelta(minutes=10),
            end_window=now + timedelta(minutes=50),
        )
        self.assertTrue(exam.is_currently_open())

        # Future exam
        exam.start_window = now + timedelta(hours=2)
        exam.end_window = now + timedelta(hours=4)
        exam.save()
        self.assertFalse(exam.is_currently_open())
