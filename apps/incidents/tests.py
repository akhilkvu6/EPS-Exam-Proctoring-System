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
from apps.exam_engine.services.delivery import start_or_resume_attempt
from apps.incidents.models import (
    InvigilatorIntervention,
    InterventionAction,
    IncidentReviewRecord,
    FinalDisposition,
)
from apps.incidents.services.intervention import (
    issue_warning,
    grant_time_extension,
    terminate_attempt_for_cause,
    adjudicate_incident,
)


class IncidentManagementTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.teacher_assigned = User.objects.create_user(
            username="teacher_severus",
            email="severus@phoenix.edu",
            password="securepassword123",
            role=UserRole.TEACHER,
            status=UserStatus.ACTIVE,
        )
        self.teacher_unassigned = User.objects.create_user(
            username="teacher_lockhart",
            email="lockhart@phoenix.edu",
            password="securepassword123",
            role=UserRole.TEACHER,
            status=UserStatus.ACTIVE,
        )
        self.student = User.objects.create_user(
            username="student_neville",
            email="neville@phoenix.edu",
            password="securepassword123",
            role=UserRole.STUDENT,
            status=UserStatus.ACTIVE,
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student,
            roll_number="EP-2026-0003",
        )

        self.dept = Department.objects.create(name="Potions", code="POT")
        self.course = Course.objects.create(department=self.dept, name="B.Sc Alchemy", code="BSAL", duration_years=3)
        self.batch = AcademicBatch.objects.create(course=self.course, name="2026 Cohort", start_year=2026, end_year=2029)
        self.subject = Subject.objects.create(course=self.course, name="Advanced Potion Making", code="POT301", credits=4)

        StudentEnrollment.objects.create(student=self.student_profile, batch=self.batch, status="ENROLLED")
        TeacherAssignment.objects.create(teacher=self.teacher_assigned, subject=self.subject, batch=self.batch, academic_year=2026)

        self.q = Question.objects.create(
            subject=self.subject,
            author=self.teacher_assigned,
            question_type=QuestionType.SHORT_ANSWER,
            title="Draught of Peace",
            content="Specify the key ingredient for Draught of Peace.",
        )

        now = timezone.now()
        self.exam = Examination.objects.create(
            title="Potions Practical Examination",
            code="EXAM-POT-01",
            subject=self.subject,
            batch=self.batch,
            created_by=self.teacher_assigned,
            start_window=now - timedelta(minutes=5),
            end_window=now + timedelta(hours=3),
            duration_minutes=60,
        )
        sec = ExamSection.objects.create(examination=self.exam, title="Lab Assessment", order=1)
        add_question_to_section(sec, self.q)
        publish_examination(self.exam, self.teacher_assigned)

        self.attempt = start_or_resume_attempt(self.exam, self.student)

    def test_warning_issuance_and_candidate_receipt(self):
        """Tests that teacher issues warning and student polling receives it."""
        itv = issue_warning(self.attempt, self.teacher_assigned, "Keep eyes focused on the screen.")
        self.assertEqual(itv.action_type, InterventionAction.OFFICIAL_WARNING)
        self.assertFalse(itv.is_acknowledged)

        # Student polls for alerts
        self.client.force_login(self.student)
        url = reverse("incidents:api_candidate_alerts", args=[self.attempt.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        self.assertEqual(len(data["alerts"]), 1)
        self.assertIn("Keep eyes focused", data["alerts"][0]["message"])

        # Alert should now be acknowledged
        itv.refresh_from_db()
        self.assertTrue(itv.is_acknowledged)

    def test_grant_time_extension(self):
        """Verifies extending candidate's timer atomically increases expires_at."""
        original_expiry = self.attempt.expires_at
        itv = grant_time_extension(self.attempt, self.teacher_assigned, minutes=15)

        self.attempt.refresh_from_db()
        expected_expiry = original_expiry + timedelta(minutes=15)
        self.assertEqual(self.attempt.expires_at, expected_expiry)
        self.assertEqual(itv.granted_extra_minutes, 15)

    def test_terminate_attempt_for_cause(self):
        """Verifies invigilator termination expels candidate and updates status."""
        itv = terminate_attempt_for_cause(self.attempt, self.teacher_assigned, reason="Unpermitted auxiliary device detected.")

        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.status, AttemptStatus.TERMINATED_SECURITY)
        self.assertIsNotNone(self.attempt.submitted_at)

        # Student poll reports termination
        self.client.force_login(self.student)
        url = reverse("incidents:api_candidate_alerts", args=[self.attempt.id])
        resp = self.client.get(url)
        data = resp.json()
        self.assertTrue(data["is_terminated"])

    def test_adjudicate_incident(self):
        """Tests post-exam formal adjudication record."""
        record = adjudicate_incident(
            attempt=self.attempt,
            reviewer=self.teacher_assigned,
            disposition=FinalDisposition.PENALIZED,
            penalty_percentage=Decimal("15.00"),
            findings="Two unauthorized window blur excursions exceeding 20 seconds.",
        )
        self.assertEqual(record.final_disposition, FinalDisposition.PENALIZED)
        self.assertEqual(record.penalty_percentage, Decimal("15.00"))

    def test_invigilator_scoping_permissions(self):
        """Ensures non-assigned teacher cannot access or intervene in exam."""
        # Unassigned teacher Lockhart gets 403
        self.client.force_login(self.teacher_unassigned)
        url = reverse("incidents:live_console", args=[self.exam.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)

        # Assigned teacher Severus gets 200
        self.client.force_login(self.teacher_assigned)
        resp_severus = self.client.get(url)
        self.assertEqual(resp_severus.status_code, 200)
