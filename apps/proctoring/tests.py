import json
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
from apps.proctoring.models import (
    ProctoringEvent,
    ProctoringSummary,
    ProctoringEventType,
    EventSeverity,
)
from apps.proctoring.services.ai_verifier import verify_and_log_ai_telemetry
from apps.proctoring.services.noise_filter import record_proctoring_event


class ProctoringEngineTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.teacher = User.objects.create_user(
            username="teacher_remus",
            email="remus@phoenix.edu",
            password="securepassword123",
            role=UserRole.TEACHER,
            status=UserStatus.ACTIVE,
        )
        self.student = User.objects.create_user(
            username="student_ron",
            email="ron@phoenix.edu",
            password="securepassword123",
            role=UserRole.STUDENT,
            status=UserStatus.ACTIVE,
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student,
            roll_number="EP-2026-0002",
        )

        self.dept = Department.objects.create(name="Defence Against Dark Arts", code="DADA")
        self.course = Course.objects.create(department=self.dept, name="B.Sc Defense", code="BSCD", duration_years=3)
        self.batch = AcademicBatch.objects.create(course=self.course, name="2026 Cohort", start_year=2026, end_year=2029)
        self.subject = Subject.objects.create(course=self.course, name="Dark Creatures", code="DADA201", credits=3)

        StudentEnrollment.objects.create(student=self.student_profile, batch=self.batch, status="ENROLLED")
        TeacherAssignment.objects.create(teacher=self.teacher, subject=self.subject, batch=self.batch, academic_year=2026)

        self.q = Question.objects.create(
            subject=self.subject,
            author=self.teacher,
            question_type=QuestionType.SHORT_ANSWER,
            title="Boggart Defense",
            content="What spell repels a boggart?",
        )

        now = timezone.now()
        self.exam = Examination.objects.create(
            title="DADA Practical Exam",
            code="EXAM-DADA-01",
            subject=self.subject,
            batch=self.batch,
            created_by=self.teacher,
            start_window=now - timedelta(minutes=5),
            end_window=now + timedelta(hours=2),
            duration_minutes=45,
            strict_proctoring=True,
        )
        sec = ExamSection.objects.create(examination=self.exam, title="Part 1", order=1)
        add_question_to_section(sec, self.q)
        publish_examination(self.exam, self.teacher)

        self.attempt = start_or_resume_attempt(self.exam, self.student)

    def test_transient_noise_filter_discards_minor_focus_jitter(self):
        """Verifies OS notification flicker under 1.5 seconds is filtered as noise without penalty."""
        event, summary = record_proctoring_event(
            attempt=self.attempt,
            event_type=ProctoringEventType.TAB_SWITCH,
            duration_seconds=0.75, # < 1.5s threshold
        )

        self.assertTrue(event.is_noise_filtered)
        self.assertEqual(event.severity, EventSeverity.INFO)
        self.assertEqual(summary.trust_score, Decimal("100.00"))
        self.assertFalse(summary.requires_human_review)

    def test_genuine_fullscreen_and_tab_departure_penalties(self):
        """Verifies departures above threshold reduce trust score and log warnings."""
        event, summary = record_proctoring_event(
            attempt=self.attempt,
            event_type=ProctoringEventType.FULLSCREEN_EXIT,
            duration_seconds=12.0,
        )

        self.assertFalse(event.is_noise_filtered)
        self.assertEqual(event.severity, EventSeverity.WARNING)
        self.assertEqual(summary.fullscreen_exit_count, 1)
        self.assertLess(summary.trust_score, Decimal("100.00"))

    def test_critical_event_and_human_review_escalation(self):
        """Tests that DevTools or critical breaches flag the candidate for faculty review."""
        event, summary = record_proctoring_event(
            attempt=self.attempt,
            event_type=ProctoringEventType.DEVTOOLS_ATTEMPT,
            metadata={"key": "F12"},
        )

        self.assertEqual(event.severity, EventSeverity.CRITICAL)
        self.assertTrue(summary.requires_human_review)
        self.assertLessEqual(summary.trust_score, Decimal("85.00"))

    def test_api_log_event_telemetry(self):
        """Tests client telemetry ingestion over HTTP endpoint."""
        self.client.force_login(self.student)
        url = reverse("proctoring:api_log_event", args=[self.attempt.id])

        payload = {
            "event_type": "CLIPBOARD_COPY",
            "duration_seconds": 0.0,
            "metadata": {"action": "copy"},
        }
        resp = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        self.assertEqual(data["status"], "recorded")
        self.assertFalse(data["is_noise_filtered"])
        self.assertEqual(data["trust_score"], 95.0)

    def test_ai_telemetry_valid_events_and_zero_video_storage(self):
        """Verifies ingestion of client edge vision metadata and stripping of binary/video payloads."""
        metadata = {
            "confidence": 0.94,
            "face_count": 0,
            "video": b"RAW_VIDEO_BYTES_PROHIBITED",
            "frame_bytes": "BASE64_BYTES",
        }
        event, summary = verify_and_log_ai_telemetry(
            attempt=self.attempt,
            anomaly_type=ProctoringEventType.AI_ABSENCE,
            duration_seconds=3.5,
            metadata=metadata,
        )

        self.assertIsNotNone(event.id)
        # Strict zero-video verification: raw video and frame bytes MUST be stripped
        self.assertNotIn("video", event.metadata)
        self.assertNotIn("frame_bytes", event.metadata)
        self.assertEqual(event.metadata["confidence"], 0.94)

        # Anomaly counter incremented
        self.assertGreaterEqual(summary.ai_anomaly_count, 1)

    def test_ai_telemetry_invalid_type_raises_error(self):
        """Verifies that unauthorized anomaly taxonomy raises validation error."""
        with self.assertRaises(ValueError):
            verify_and_log_ai_telemetry(
                attempt=self.attempt,
                anomaly_type="UNAUTHORIZED_AI_TYPE",
                duration_seconds=1.0,
            )
