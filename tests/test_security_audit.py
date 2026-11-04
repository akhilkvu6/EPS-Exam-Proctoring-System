"""
Comprehensive Security Hardening and IDOR Audit Test Suite for EPS Phoenix.
Tests access boundaries, IDOR prevention, server-authoritative time enforcement,
inactive account isolation, and role permissions.
"""

from decimal import Decimal
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import UserRole
from apps.student.models import StudentProfile, AdmissionApplicationStatus
from apps.teacher.models import TeacherProfile
from apps.academics.models import (
    Department,
    Course,
    AcademicBatch,
    Semester,
    Subject,
    TeacherAssignment,
    StudentEnrollment,
)
from apps.question_bank.models import Question, QuestionType, QuestionDifficulty
from apps.question_bank.services.snapshot import create_or_get_question_snapshot
from apps.examinations.models import (
    Examination,
    ExamSection,
    ExamQuestion,
    ExamStatus,
    CandidateAssignment,
)
from apps.exam_engine.models import ExamAttempt, AttemptStatus
from apps.exam_engine.services.delivery import start_or_resume_attempt
from apps.exam_engine.services.autosave import process_batch_answer_sync
from apps.results.models import ExaminationResult

User = get_user_model()


class SecurityAuditTestCase(TestCase):
    def setUp(self):
        # 1. Admin & Faculty
        self.admin = User.objects.create_user(
            username="sec_admin",
            email="admin@test.edu",
            password="AdminPassword123!",
            role=UserRole.ADMIN,
        )
        self.teacher_cs = User.objects.create_user(
            username="teacher_cs",
            email="cs@faculty.edu",
            password="FacultyPassword123!",
            role=UserRole.TEACHER,
        )
        self.teacher_ee = User.objects.create_user(
            username="teacher_ee",
            email="ee@faculty.edu",
            password="FacultyPassword123!",
            role=UserRole.TEACHER,
        )
        TeacherProfile.objects.create(
            user=self.teacher_cs,
            staff_id="FAC-CS-01",
            designation="Professor",
        )
        TeacherProfile.objects.create(
            user=self.teacher_ee,
            staff_id="FAC-EE-01",
            designation="Professor",
        )

        # 2. Students (Alice & Bob)
        self.student_alice = User.objects.create_user(
            username="alice",
            email="alice@student.edu",
            password="StudentPassword123!",
            role=UserRole.STUDENT,
        )
        self.student_bob = User.objects.create_user(
            username="bob",
            email="bob@student.edu",
            password="StudentPassword123!",
            role=UserRole.STUDENT,
        )
        self.profile_alice = StudentProfile.objects.create(
            user=self.student_alice,
            registration_number="REG-ALICE",
            admission_status=AdmissionApplicationStatus.APPROVED,
            roll_number="CSE-2026-0001",
        )
        self.profile_bob = StudentProfile.objects.create(
            user=self.student_bob,
            registration_number="REG-BOB",
            admission_status=AdmissionApplicationStatus.APPROVED,
            roll_number="CSE-2026-0002",
        )

        # 3. Academic Structure
        self.dept = Department.objects.create(code="CSE", name="Computer Science")
        self.course = Course.objects.create(department=self.dept, code="CS-DEG", name="CS Degree")
        self.batch = AcademicBatch.objects.create(course=self.course, name="2026-2030", start_year=2026, end_year=2030)
        self.subject = Subject.objects.create(course=self.course, code="CS300", name="Cybersecurity")
        TeacherAssignment.objects.create(
            teacher=self.teacher_cs,
            subject=self.subject,
            batch=self.batch,
            academic_year=2026,
        )
        StudentEnrollment.objects.create(student=self.profile_alice, batch=self.batch, status="ENROLLED")
        StudentEnrollment.objects.create(student=self.profile_bob, batch=self.batch, status="ENROLLED")

        # 4. Examination Setup
        now = timezone.now()
        self.exam = Examination.objects.create(
            subject=self.subject,
            batch=self.batch,
            created_by=self.teacher_cs,
            title="Cybersecurity Security Audit Exam",
            code="EXAM-CYBER-01",
            start_window=now - timedelta(minutes=2),
            end_window=now + timedelta(hours=3),
            duration_minutes=60,
            allow_late_join_minutes=60,
            total_marks=Decimal("20.00"),
            pass_percentage=Decimal("40.00"),
            status=ExamStatus.ACTIVE,
        )
        self.section = ExamSection.objects.create(examination=self.exam, title="Section 1", order=1)
        self.q = Question.objects.create(
            subject=self.subject,
            author=self.teacher_cs,
            question_type=QuestionType.MCQ_SINGLE,
            difficulty=QuestionDifficulty.MEDIUM,
            title="CSRF Token",
            content="What prevents Cross-Site Request Forgery?",
        )
        self.snapshot = create_or_get_question_snapshot(self.q)
        ExamQuestion.objects.create(
            section=self.section,
            question=self.q,
            snapshot=self.snapshot,
            order=1,
            marks=Decimal("20.00"),
        )
        CandidateAssignment.objects.create(examination=self.exam, student=self.student_alice, is_eligible=True)
        CandidateAssignment.objects.create(examination=self.exam, student=self.student_bob, is_eligible=True)

        # Alice begins her attempt
        self.attempt_alice = start_or_resume_attempt(self.exam, self.student_alice)

    def test_idor_student_cannot_access_other_students_exam_room(self):
        """Student Bob attempting to view Student Alice's exam room must be blocked (HTTP 403)."""
        self.client.force_login(self.student_bob)
        url = reverse("exam_engine:exam_room", kwargs={"attempt_id": self.attempt_alice.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_idor_student_cannot_sync_answers_to_other_students_attempt(self):
        """Student Bob attempting to post answers to Student Alice's attempt must be blocked (HTTP 403 or 404)."""
        self.client.force_login(self.student_bob)
        url = reverse("exam_engine:api_batch_sync", kwargs={"attempt_id": self.attempt_alice.id})
        payload = {"updates": [{"question_id": "fake", "answer": {}}]}
        response = self.client.post(url, data=payload, content_type="application/json")
        self.assertIn(response.status_code, [403, 404])

    def test_idor_student_cannot_download_other_students_scorecard(self):
        """Student Bob cannot download Student Alice's private transcript/scorecard."""
        result = ExaminationResult.objects.create(
            attempt=self.attempt_alice,
            examination=self.exam,
            student=self.student_alice,
            total_score=Decimal("18.00"),
            maximum_score=Decimal("20.00"),
            percentage=Decimal("90.00"),
            grade_letter="O",
            is_passed=True,
            is_published=True,
            verification_hash="abc123hash",
        )
        self.client.force_login(self.student_bob)
        url = reverse("results:download_pdf", kwargs={"result_id": result.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_role_boundary_student_blocked_from_admin_and_teacher(self):
        """Students attempting to access administrative or teacher portals are denied (HTTP 403)."""
        self.client.force_login(self.student_alice)
        res_admin = self.client.get("/administration/dashboard/")
        self.assertEqual(res_admin.status_code, 403)

        res_teacher = self.client.get("/teacher/dashboard/")
        self.assertEqual(res_teacher.status_code, 403)

    def test_role_boundary_teacher_blocked_from_admin(self):
        """Faculty attempting to access institutional governance routes are denied (HTTP 403)."""
        self.client.force_login(self.teacher_cs)
        response = self.client.get("/administration/dashboard/")
        self.assertEqual(response.status_code, 403)

    def test_server_authoritative_timer_expired_autosave_rejection(self):
        """Server-authoritative timer rejects answer persistence after expires_at has elapsed."""
        # Force attempt expiry
        self.attempt_alice.expires_at = timezone.now() - timedelta(minutes=5)
        self.attempt_alice.save(update_fields=["expires_at"])

        att_q = self.attempt_alice.attempt_questions.first()
        payload = [
            {
                "question_id": str(att_q.id),
                "answer": {"text": "Tampered Late Answer"},
                "time_spent_seconds": 10,
            }
        ]
        ok, res, msg = process_batch_answer_sync(self.attempt_alice, payload)
        self.assertFalse(ok)
        self.assertIn("expired", msg.lower())

        self.attempt_alice.refresh_from_db()
        self.assertEqual(self.attempt_alice.status, AttemptStatus.AUTO_SUBMITTED)

    def test_inactive_suspended_user_is_blocked(self):
        """Users suspended/deactivated by administration cannot interact with protected views."""
        self.student_alice.is_active = False
        self.student_alice.save(update_fields=["is_active"])

        self.client.force_login(self.student_alice)
        url = reverse("student:dashboard")
        response = self.client.get(url)
        # Should redirect to login or return 403/302
        self.assertIn(response.status_code, [302, 403])
