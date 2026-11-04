from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse

from apps.accounts.models import User, UserRole, UserStatus
from apps.academics.models import (
    Department,
    Course,
    AcademicBatch,
    Semester,
    Subject,
    TeacherAssignment,
)
from apps.question_bank.models import (
    Question,
    QuestionOption,
    QuestionCategory,
    QuestionType,
    QuestionDifficulty,
    QuestionSnapshot,
)
from apps.question_bank.services.snapshot import (
    create_or_get_question_snapshot,
    get_student_safe_snapshot_data,
    serialize_question_to_dict,
)


class QuestionBankTests(TestCase):
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
        self.subject_algo = Subject.objects.create(
            course=self.course,
            name="Design and Analysis of Algorithms",
            code="CS301",
            semester_number=1,
            credits=4,
        )
        self.subject_db = Subject.objects.create(
            course=self.course,
            name="Database Systems",
            code="CS302",
            semester_number=1,
            credits=4,
        )

        # Assign Flitwick to Algorithms (CS301)
        TeacherAssignment.objects.create(
            teacher=self.teacher_flitwick,
            subject=self.subject_algo,
            batch=self.batch,
            academic_year=2026,
            is_active=True,
        )

    def test_question_models_all_eight_types(self):
        """Verifies model creation and validation across all 8 mandatory question types."""
        types_to_test = [
            QuestionType.MCQ_SINGLE,
            QuestionType.MCQ_MULTI,
            QuestionType.TRUE_FALSE,
            QuestionType.FILL_BLANKS,
            QuestionType.NUMERICAL,
            QuestionType.SHORT_ANSWER,
            QuestionType.DESCRIPTIVE,
            QuestionType.IMAGE_BASED,
        ]

        for q_type in types_to_test:
            q = Question.objects.create(
                subject=self.subject_algo,
                author=self.teacher_flitwick,
                question_type=q_type,
                difficulty=QuestionDifficulty.MEDIUM,
                title=f"Sample Question for {q_type}",
                content=f"Explain or solve problem relating to {q_type}.",
                default_marks=Decimal("2.00"),
                negative_marks=Decimal("0.50"),
                numerical_target=42.0 if q_type == QuestionType.NUMERICAL else None,
                numerical_tolerance=0.01 if q_type == QuestionType.NUMERICAL else 0.0,
            )
            self.assertIsNotNone(q.id)
            self.assertEqual(q.question_type, q_type)

    def test_question_snapshot_immutability(self):
        """Verifies that snapshots are immutable and protect against subsequent question edits."""
        q = Question.objects.create(
            subject=self.subject_algo,
            author=self.teacher_flitwick,
            question_type=QuestionType.MCQ_SINGLE,
            title="Time Complexity of MergeSort",
            content="What is the worst-case time complexity of MergeSort?",
            default_marks=Decimal("1.00"),
            version=1,
        )
        QuestionOption.objects.create(question=q, option_text="O(N log N)", is_correct=True, order=1)
        QuestionOption.objects.create(question=q, option_text="O(N^2)", is_correct=False, order=2)

        # Create v1 snapshot
        snap1 = create_or_get_question_snapshot(q)
        self.assertEqual(snap1.version, 1)
        self.assertEqual(snap1.snapshot_data["title"], "Time Complexity of MergeSort")
        self.assertEqual(len(snap1.snapshot_data["options"]), 2)

        # Teacher modifies the live question
        q.title = "Time Complexity of Modified MergeSort (Updated)"
        q.version = 2
        q.save()

        # Confirm old snapshot remains unchanged
        snap1.refresh_from_db()
        self.assertEqual(snap1.snapshot_data["title"], "Time Complexity of MergeSort")

        # Create v2 snapshot
        snap2 = create_or_get_question_snapshot(q)
        self.assertEqual(snap2.version, 2)
        self.assertEqual(snap2.snapshot_data["title"], "Time Complexity of Modified MergeSort (Updated)")

    def test_student_safe_snapshot_data_zero_leakage(self):
        """Ensures student-safe serialization strictly strips answers, solutions, and rubrics."""
        q = Question.objects.create(
            subject=self.subject_algo,
            author=self.teacher_flitwick,
            question_type=QuestionType.NUMERICAL,
            title="Dijkstra Shortest Path Length",
            content="Find the shortest path length from node A to node Z.",
            explanation="The shortest path is A->B->E->Z with sum 17.",
            rubric="Award 2 marks for exact match within tolerance.",
            numerical_target=17.0,
            numerical_tolerance=0.5,
            version=1,
        )
        opt1 = QuestionOption.objects.create(question=q, option_text="Node A", is_correct=True, order=1)
        opt2 = QuestionOption.objects.create(question=q, option_text="Node B", is_correct=False, order=2)

        snapshot = create_or_get_question_snapshot(q)
        safe_data = get_student_safe_snapshot_data(snapshot)

        # Confidential fields must be absent
        self.assertNotIn("explanation", safe_data)
        self.assertNotIn("rubric", safe_data)
        self.assertNotIn("numerical_target", safe_data)
        self.assertNotIn("numerical_tolerance", safe_data)

        # Check options for absence of is_correct
        for opt in safe_data["options"]:
            self.assertNotIn("is_correct", opt)

    def test_teacher_scoping_permissions(self):
        """Verifies that teachers can only view/edit questions for subjects they are assigned to."""
        q_algo = Question.objects.create(
            subject=self.subject_algo,
            author=self.teacher_flitwick,
            question_type=QuestionType.MCQ_SINGLE,
            title="Binary Search Invariant",
            content="Specify loop invariant.",
            version=1,
        )

        # Teacher Flitwick (assigned to CS301) can view
        self.client.force_login(self.teacher_flitwick)
        resp_flitwick = self.client.get(reverse("question_bank:question_detail", args=[q_algo.pk]))
        self.assertEqual(resp_flitwick.status_code, 200)

        # Teacher Snape (NOT assigned to CS301) gets 403 Forbidden
        self.client.force_login(self.teacher_snape)
        resp_snape = self.client.get(reverse("question_bank:question_detail", args=[q_algo.pk]))
        self.assertEqual(resp_snape.status_code, 403)

        # Student gets 403 Forbidden
        self.client.force_login(self.student_harry)
        resp_student = self.client.get(reverse("question_bank:question_detail", args=[q_algo.pk]))
        self.assertEqual(resp_student.status_code, 403)

    def test_question_duplicate_service(self):
        """Tests cloning functionality duplicating questions and option sets."""
        q = Question.objects.create(
            subject=self.subject_algo,
            author=self.teacher_flitwick,
            question_type=QuestionType.MCQ_SINGLE,
            title="Master Theorem Case 1",
            content="Solve T(n) = 2T(n/2) + n",
            version=1,
        )
        QuestionOption.objects.create(question=q, option_text="Theta(n log n)", is_correct=True, order=1)

        self.client.force_login(self.teacher_flitwick)
        resp = self.client.get(reverse("question_bank:question_duplicate", args=[q.pk]))
        self.assertEqual(resp.status_code, 302)

        cloned = Question.objects.filter(title="Master Theorem Case 1 (Copy)").first()
        self.assertIsNotNone(cloned)
        self.assertEqual(cloned.options.count(), 1)
        self.assertEqual(cloned.options.first().option_text, "Theta(n log n)")
