"""
Comprehensive End-to-End Lifecycle Integration Test for EPS Phoenix.
Tests the entire institutional examination pipeline from admission approval to cryptographic PDF transcript.
"""

from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from apps.accounts.models import UserRole
from apps.student.models import StudentProfile, AdmissionApplicationStatus
from apps.teacher.models import TeacherProfile
from apps.admissions.services.roll_allocator import allocate_roll_number_atomic
from apps.admissions.models import RollAllocationRecord
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
from apps.question_bank.services.snapshot import (
    create_or_get_question_snapshot,
    get_student_safe_snapshot_data,
)
from apps.examinations.models import (
    Examination,
    ExamSection,
    ExamQuestion,
    ExamStatus,
    CandidateAssignment,
)
from apps.examinations.services.scheduling import publish_examination
from apps.exam_engine.models import ExamAttempt, AttemptStatus
from apps.exam_engine.services.delivery import start_or_resume_attempt, submit_attempt
from apps.exam_engine.services.autosave import process_batch_answer_sync
from apps.proctoring.models import ProctoringEvent, ProctoringEventType, ProctoringSummary
from apps.evaluation.services.grader import evaluate_entire_exam_cohort
from apps.results.services.publisher import publish_examination_results
from apps.results.services.pdf_generator import generate_scorecard_pdf
from apps.results.models import ExaminationResult

User = get_user_model()


class EndToEndExaminationLifecycleTestCase(TestCase):
    def setUp(self):
        # 1. Admin & Teacher Setup
        self.admin = User.objects.create_user(
            username="admin_dean",
            email="dean@institution.edu",
            password="AdminPassword123!",
            role=UserRole.ADMIN,
        )
        self.teacher_user = User.objects.create_user(
            username="prof_alan",
            email="alan@institution.edu",
            password="TeacherPassword123!",
            role=UserRole.TEACHER,
        )
        self.teacher_profile = TeacherProfile.objects.create(
            user=self.teacher_user,
            staff_id="FAC-001",
            designation="Professor",
        )

        # 2. Student Setup
        self.student_user = User.objects.create_user(
            username="candidate_john",
            email="john@student.edu",
            password="StudentPassword123!",
            role=UserRole.STUDENT,
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            registration_number="REG-2026-9901",
            admission_status=AdmissionApplicationStatus.PENDING_TEACHER,
        )

        # 3. Academic Hierarchy
        self.dept = Department.objects.create(
            code="CSE",
            name="Computer Science & Engineering",
        )
        self.course = Course.objects.create(
            department=self.dept,
            code="BTECH-CS",
            name="B.Tech Computer Science",
            duration_years=4,
        )
        self.batch = AcademicBatch.objects.create(
            course=self.course,
            name="2026-2030",
            start_year=2026,
            end_year=2030,
        )
        self.semester = Semester.objects.create(
            batch=self.batch,
            semester_number=1,
            is_current=True,
        )
        self.subject = Subject.objects.create(
            course=self.course,
            code="CS101",
            name="Data Structures and Algorithms",
            credits=4,
        )
        TeacherAssignment.objects.create(
            teacher=self.teacher_user,
            subject=self.subject,
            batch=self.batch,
            academic_year=2026,
        )

    def test_complete_examination_lifecycle(self):
        # --- STEP 1: Admission Dossier Approval & Concurrency-Safe Roll Allocation ---
        self.student_profile.admission_status = AdmissionApplicationStatus.APPROVED
        self.student_profile.save(update_fields=["admission_status"])

        roll = allocate_roll_number_atomic(
            student_profile=self.student_profile,
            allocated_by=self.teacher_user,
            prefix_override="CSE",
        )
        self.student_profile.refresh_from_db()
        self.assertEqual(self.student_profile.roll_number, roll)
        self.assertTrue(roll.startswith("CSE-"))
        self.assertTrue(RollAllocationRecord.objects.filter(student_profile=self.student_profile).exists())

        # Enroll candidate into academic cohort
        enrollment = StudentEnrollment.objects.create(
            student=self.student_profile,
            batch=self.batch,
            status="ENROLLED",
        )
        self.assertIsNotNone(enrollment.pk)

        # --- STEP 2: Question Bank Authoring & Snapshot Immutability ---
        q1 = Question.objects.create(
            subject=self.subject,
            author=self.teacher_user,
            question_type=QuestionType.MCQ_SINGLE,
            difficulty=QuestionDifficulty.MEDIUM,
            title="BST Search Complexity",
            content="What is the average time complexity of searching in a balanced Binary Search Tree?",
            explanation="Balanced BST maintains O(log n) height.",
        )
        opt_correct = QuestionOption.objects.create(
            question=q1,
            option_text="O(log n)",
            is_correct=True,
            order=1,
        )
        opt_wrong = QuestionOption.objects.create(
            question=q1,
            option_text="O(n^2)",
            is_correct=False,
            order=2,
        )

        snapshot1 = create_or_get_question_snapshot(q1)
        self.assertEqual(snapshot1.version, 1)

        # Verify candidate-safe payload strips correct answers
        safe_data = get_student_safe_snapshot_data(snapshot1)
        for opt in safe_data["options"]:
            self.assertNotIn("is_correct", opt)
        self.assertNotIn("explanation", safe_data)

        # --- STEP 3: Examination Scheduling & Cohort Assignment ---
        now = timezone.now()
        exam = Examination.objects.create(
            subject=self.subject,
            batch=self.batch,
            created_by=self.teacher_user,
            title="CS101 Midterm Examination",
            code="EXAM-CS101-MID",
            start_window=now - timedelta(minutes=10),
            end_window=now + timedelta(hours=3),
            duration_minutes=90,
            total_marks=Decimal("10.00"),
            pass_percentage=Decimal("40.00"),
            status=ExamStatus.DRAFT,
        )
        sec = ExamSection.objects.create(
            examination=exam,
            title="Part A: Algorithms",
            order=1,
        )
        eq1 = ExamQuestion.objects.create(
            section=sec,
            question=q1,
            snapshot=snapshot1,
            order=1,
            marks=Decimal("10.00"),
            negative_marks=Decimal("0.00"),
        )

        # Publish examination and auto-populate candidate roster from cohort
        ok, msg, roster_count = publish_examination(exam, triggered_by=self.teacher_user)
        self.assertTrue(ok)
        self.assertEqual(roster_count, 1)
        exam.refresh_from_db()
        self.assertEqual(exam.status, ExamStatus.PUBLISHED)
        self.assertTrue(
            CandidateAssignment.objects.filter(examination=exam, student=self.student_user).exists()
        )

        # --- STEP 4: Timed Room Launch & Delivery Engine ---
        exam.status = ExamStatus.ACTIVE
        exam.save()

        attempt = start_or_resume_attempt(exam, self.student_user)
        self.assertEqual(attempt.status, AttemptStatus.IN_PROGRESS)
        self.assertIsNotNone(attempt.expires_at)
        self.assertGreater(attempt.expires_at, now)
        self.assertEqual(attempt.attempt_questions.count(), 1)

        att_q1 = attempt.attempt_questions.first()

        # --- STEP 5: Dual-Layer Autosave & Answer Synchronization ---
        sync_payload = [
            {
                "question_id": str(att_q1.id),
                "answer": {"selected_option_ids": [opt_correct.id]},
                "time_spent_seconds": 15,
            }
        ]
        sync_ok, results_list, msg = process_batch_answer_sync(attempt, sync_payload)
        self.assertTrue(sync_ok)
        self.assertEqual(len(results_list), 1)

        att_q1.refresh_from_db()
        self.assertTrue(att_q1.is_answered)
        self.assertEqual(att_q1.candidate_answer["selected_option_ids"], [opt_correct.id])

        # --- STEP 6: Edge AI & Browser Proctoring Telemetry Ingestion ---
        ProctoringEvent.objects.create(
            attempt=attempt,
            event_type=ProctoringEventType.FULLSCREEN_EXIT,
            metadata={"mode": "engaged"},
        )
        summary, _ = ProctoringSummary.objects.get_or_create(attempt=attempt)
        summary.trust_score = Decimal("98.50")
        summary.save()

        self.assertEqual(attempt.proctoring_events.count(), 1)
        self.assertEqual(attempt.proctoring_summary.trust_score, Decimal("98.50"))

        # --- STEP 7: Candidate Submission & Cryptographic Receipt ---
        receipt_hash = submit_attempt(attempt)
        self.assertTrue(receipt_hash)
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, AttemptStatus.SUBMITTED)
        self.assertEqual(attempt.submission_hash, receipt_hash)
        self.assertIsNotNone(attempt.submitted_at)

        # --- STEP 8: Deterministic Auto-Evaluation ---
        exam.status = ExamStatus.CLOSED
        exam.save()

        graded, pending_subj = evaluate_entire_exam_cohort(exam)
        self.assertEqual(graded, 1)
        self.assertEqual(pending_subj, 0)

        attempt.refresh_from_db()
        self.assertEqual(attempt.status, AttemptStatus.EVALUATED)
        self.assertEqual(attempt.total_score, Decimal("10.00"))

        # --- STEP 9: Cohort Result Publishing ---
        pub_ok, pub_msg, pub_count = publish_examination_results(exam, self.teacher_user)
        self.assertTrue(pub_ok)
        self.assertEqual(pub_count, 1)
        exam.refresh_from_db()
        self.assertEqual(exam.status, ExamStatus.RESULTS_PUBLISHED)

        result = ExaminationResult.objects.get(attempt=attempt)
        self.assertEqual(result.total_score, Decimal("10.00"))
        self.assertEqual(result.maximum_score, Decimal("10.00"))
        self.assertEqual(result.percentage, Decimal("100.00"))
        self.assertEqual(result.grade_letter, "O")  # Outstanding >= 90%
        self.assertTrue(result.is_passed)
        self.assertTrue(result.verification_hash)

        # --- STEP 10: Cryptographic PDF Scorecard Generation ---
        pdf_bytes = generate_scorecard_pdf(result)
        self.assertIsNotNone(pdf_bytes)
        self.assertGreater(len(pdf_bytes), 500)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
