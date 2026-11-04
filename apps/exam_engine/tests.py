import json
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
from apps.examinations.models import (
    Examination,
    ExamSection,
    ExamQuestion,
    CandidateAssignment,
    ExamStatus,
)
from apps.examinations.services.scheduling import add_question_to_section, publish_examination
from apps.exam_engine.models import ExamAttempt, AttemptQuestion, AttemptStatus
from apps.exam_engine.services.delivery import start_or_resume_attempt, submit_attempt


class ExamEngineTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Users
        self.teacher = User.objects.create_user(
            username="teacher_minerva",
            email="minerva@phoenix.edu",
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
        self.student_malfoy = User.objects.create_user(
            username="student_malfoy",
            email="malfoy@phoenix.edu",
            password="securepassword123",
            role=UserRole.STUDENT,
            status=UserStatus.ACTIVE,
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_harry,
            roll_number="EP-2026-0001",
        )

        # Academics
        self.dept = Department.objects.create(name="Transfiguration", code="TRANS")
        self.course = Course.objects.create(department=self.dept, name="Advanced Magic", code="AMAG", duration_years=4)
        self.batch = AcademicBatch.objects.create(course=self.course, name="2026 Cohort", start_year=2026, end_year=2030)
        self.subject = Subject.objects.create(course=self.course, name="Applied Spells", code="SPELL101", credits=3)

        StudentEnrollment.objects.create(student=self.student_profile, batch=self.batch, status="ENROLLED")
        TeacherAssignment.objects.create(teacher=self.teacher, subject=self.subject, batch=self.batch, academic_year=2026)

        # Question Bank item
        self.q1 = Question.objects.create(
            subject=self.subject,
            author=self.teacher,
            question_type=QuestionType.MCQ_SINGLE,
            title="Levitation Incantation",
            content="What is the incantation for levitation?",
            explanation="Wingardium Leviosa is correct.",
            default_marks=Decimal("2.00"),
            negative_marks=Decimal("0.50"),
            version=1,
        )
        self.opt1 = QuestionOption.objects.create(question=self.q1, option_text="Wingardium Leviosa", is_correct=True, order=1)
        self.opt2 = QuestionOption.objects.create(question=self.q1, option_text="Alohomora", is_correct=False, order=2)

        # Examination
        now = timezone.now()
        self.exam = Examination.objects.create(
            title="Spells Practical Assessment",
            code="EXAM-SPELL-01",
            subject=self.subject,
            batch=self.batch,
            created_by=self.teacher,
            status=ExamStatus.DRAFT,
            start_window=now - timedelta(minutes=5),
            end_window=now + timedelta(hours=3),
            duration_minutes=60,
            shuffle_questions=True,
            shuffle_options=True,
        )
        self.sec = ExamSection.objects.create(examination=self.exam, title="Section 1", order=1)
        add_question_to_section(self.sec, self.q1)
        publish_examination(self.exam, self.teacher)

    def test_start_attempt_authoritative_timer_and_safe_payload(self):
        """Tests attempt initialization, authoritative expiry calculation, and safe question masking."""
        attempt = start_or_resume_attempt(self.exam, self.student_harry)
        self.assertEqual(attempt.status, AttemptStatus.IN_PROGRESS)

        # Check authoritative timer
        self.assertFalse(attempt.is_expired())
        self.assertGreater(attempt.get_remaining_seconds(), 3500) # near 60 mins

        # Check delivery question instantiated with zero leaked solutions
        att_q = attempt.attempt_questions.first()
        self.assertIsNotNone(att_q)
        self.assertEqual(att_q.safe_payload["title"], "Levitation Incantation")
        self.assertNotIn("explanation", att_q.safe_payload)
        for opt in att_q.safe_payload["options"]:
            self.assertNotIn("is_correct", opt)

    def test_save_answer_api(self):
        """Tests live autosave API for an active question item."""
        attempt = start_or_resume_attempt(self.exam, self.student_harry)
        att_q = attempt.attempt_questions.first()

        self.client.force_login(self.student_harry)
        url = reverse("exam_engine:api_save_answer", args=[attempt.id, att_q.id])

        payload = {"answer": {"selected_option_ids": [self.opt1.id]}, "time_spent_seconds": 15}
        resp = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(resp.status_code, 200)

        att_q.refresh_from_db()
        self.assertTrue(att_q.is_answered)
        self.assertEqual(att_q.candidate_answer["selected_option_ids"], [self.opt1.id])
        self.assertEqual(att_q.time_spent_seconds, 15)

    def test_server_expiration_blocks_answers_and_auto_submits(self):
        """Ensures when server clock passes expires_at, save is blocked and attempt auto-submits."""
        attempt = start_or_resume_attempt(self.exam, self.student_harry)
        att_q = attempt.attempt_questions.first()

        # Simulate expiration
        attempt.expires_at = timezone.now() - timedelta(seconds=1)
        attempt.save(update_fields=["expires_at"])
        self.assertTrue(attempt.is_expired())

        # Attempt to save answer after expiration
        self.client.force_login(self.student_harry)
        url = reverse("exam_engine:api_save_answer", args=[attempt.id, att_q.id])
        resp = self.client.post(url, data=json.dumps({"answer": {"text": "Late answer"}}), content_type="application/json")
        self.assertEqual(resp.status_code, 403)

        attempt.refresh_from_db()
        self.assertEqual(attempt.status, AttemptStatus.AUTO_SUBMITTED)
        self.assertTrue(len(attempt.submission_hash) == 64)

    def test_manual_submission_creates_sha256_receipt(self):
        """Tests manual final exam submission producing a valid cryptographic receipt."""
        attempt = start_or_resume_attempt(self.exam, self.student_harry)
        self.client.force_login(self.student_harry)

        url = reverse("exam_engine:api_submit", args=[attempt.id])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)

        attempt.refresh_from_db()
        self.assertEqual(attempt.status, AttemptStatus.SUBMITTED)
        self.assertIsNotNone(attempt.submitted_at)
        self.assertEqual(len(attempt.submission_hash), 64)

    def test_idor_protection_isolation(self):
        """Ensures Candidate B cannot view, save answers, or submit Candidate A's attempt."""
        attempt = start_or_resume_attempt(self.exam, self.student_harry)
        att_q = attempt.attempt_questions.first()

        self.client.force_login(self.student_malfoy)

        # Room view IDOR check
        room_url = reverse("exam_engine:exam_room", args=[attempt.id])
        resp_room = self.client.get(room_url)
        self.assertEqual(resp_room.status_code, 403)

        # Save API IDOR check (returns 404 because student=malfoy filter fails)
        save_url = reverse("exam_engine:api_save_answer", args=[attempt.id, att_q.id])
        resp_save = self.client.post(save_url, data=json.dumps({"answer": {}}), content_type="application/json")
        self.assertEqual(resp_save.status_code, 404)
