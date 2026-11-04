"""
Automated tests for Phase 7: Academic Management & Scoping.
Compliant with Section 9 (Academic Hierarchy, Enrollments, and Teacher Scoping).
"""

from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import User, UserRole, UserStatus
from apps.student.models import StudentProfile, AdmissionApplicationStatus
from apps.academics.models import (
    Department,
    Course,
    AcademicBatch,
    Semester,
    Subject,
    TeacherAssignment,
    StudentEnrollment,
)
from apps.academics.services.scoping import (
    get_teacher_assigned_subjects,
    get_teacher_assigned_batches,
    is_student_in_teacher_scope,
    promote_student_semester,
)


class AcademicManagementTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Admin User
        self.admin = User.objects.create_user(
            username="admin_arthur",
            password="ArthurPassword123!",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            is_staff=True,
            is_superuser=True,
        )

        # Faculty Member
        self.teacher = User.objects.create_user(
            username="prof_lupin",
            password="LupinPassword123!",
            role=UserRole.TEACHER,
            status=UserStatus.ACTIVE,
        )

        # Department & Course
        self.dept = Department.objects.create(code="CSE", name="Computer Science and Engineering")
        self.course = Course.objects.create(
            department=self.dept,
            code="BT-CSE",
            name="B.Tech Computer Science",
            duration_years=4,
            total_semesters=8,
        )

        # Batch & Subject
        self.batch = AcademicBatch.objects.create(
            course=self.course,
            name="2024-2028",
            start_year=2024,
            end_year=2028,
            current_semester=1,
        )
        self.subject = Subject.objects.create(
            course=self.course,
            code="CS101",
            name="Introduction to Computing",
            semester_number=1,
            credits=4,
        )

        # Another batch in another course
        self.course_ee = Course.objects.create(
            department=self.dept,
            code="BT-EE",
            name="B.Tech Electrical",
            duration_years=4,
            total_semesters=8,
        )
        self.batch_unassigned = AcademicBatch.objects.create(
            course=self.course_ee,
            name="2024-2028-EE",
            start_year=2024,
            end_year=2028,
            current_semester=1,
        )

        # Scoping Assignment
        TeacherAssignment.objects.create(
            teacher=self.teacher,
            subject=self.subject,
            batch=self.batch,
            academic_year=2026,
        )

        # Students & Enrollments
        self.student_user = User.objects.create_user(
            username="stud_colin",
            password="ColinPassword123!",
            role=UserRole.STUDENT,
            status=UserStatus.ACTIVE,
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            registration_number="APP-COLIN-01",
            roll_number="CS-2026-0081",
            admission_status=AdmissionApplicationStatus.APPROVED,
        )
        self.enrollment = StudentEnrollment.objects.create(
            student=self.student_profile,
            batch=self.batch,
            current_semester=1,
        )

        # Unassigned Student
        self.student_unassigned_user = User.objects.create_user(
            username="stud_dennis",
            password="DennisPassword123!",
            role=UserRole.STUDENT,
            status=UserStatus.ACTIVE,
        )
        self.student_unassigned_profile = StudentProfile.objects.create(
            user=self.student_unassigned_user,
            registration_number="APP-DENNIS-01",
            roll_number="EE-2026-0005",
            admission_status=AdmissionApplicationStatus.APPROVED,
        )
        self.enrollment_unassigned = StudentEnrollment.objects.create(
            student=self.student_unassigned_profile,
            batch=self.batch_unassigned,
            current_semester=1,
        )

    def test_academic_hierarchy_relationships(self):
        """Verify Department -> Course -> Batch -> Subject relational integrity."""
        self.assertEqual(self.course.department, self.dept)
        self.assertEqual(self.batch.course, self.course)
        self.assertEqual(self.subject.course, self.course)
        self.assertEqual(self.batch.semesters.count(), 0)

    def test_teacher_scoping_queries(self):
        """Teacher can only retrieve assigned subjects and batches."""
        assigned_subjects = get_teacher_assigned_subjects(self.teacher)
        self.assertEqual(assigned_subjects.count(), 1)
        self.assertEqual(assigned_subjects.first(), self.subject)

        assigned_batches = get_teacher_assigned_batches(self.teacher)
        self.assertEqual(assigned_batches.count(), 1)
        self.assertEqual(assigned_batches.first(), self.batch)

    def test_student_in_teacher_scope_verification(self):
        """Candidate in assigned batch is in scope; candidate in unassigned batch is blocked."""
        # Enrolled in teacher's batch -> True
        self.assertTrue(is_student_in_teacher_scope(self.teacher, self.student_profile))
        # Enrolled in unassigned batch -> False
        self.assertFalse(is_student_in_teacher_scope(self.teacher, self.student_unassigned_profile))
        # Admin has institution-wide scope -> True for both
        self.assertTrue(is_student_in_teacher_scope(self.admin, self.student_profile))
        self.assertTrue(is_student_in_teacher_scope(self.admin, self.student_unassigned_profile))

    def test_student_semester_promotion(self):
        """Semester promotion increments semester level and respects total semester boundary."""
        # Promote from semester 1 to 2
        next_sem = promote_student_semester(self.student_profile)
        self.assertEqual(next_sem, 2)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.current_semester, 2)
        self.assertEqual(self.enrollment.status, StudentEnrollment.EnrollmentStatus.PROMOTED)

        # Promote to max (8) then beyond -> status becomes GRADUATED
        promote_student_semester(self.student_profile, target_semester=8)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.current_semester, 8)

        # Beyond max total_semesters (8)
        promote_student_semester(self.student_profile, target_semester=9)
        self.enrollment.refresh_from_db()
        self.assertEqual(self.enrollment.status, StudentEnrollment.EnrollmentStatus.GRADUATED)

    def test_departments_list_view_accessible_to_faculty(self):
        """Faculty member can inspect departments list."""
        self.client.login(username="prof_lupin", password="LupinPassword123!")
        response = self.client.get(reverse("academics:departments_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Computer Science and Engineering")

    def test_teacher_assignments_endpoint_restricted_to_admin(self):
        """Only Admin can manage teacher academic scoping assignments."""
        # Admin allowed
        self.client.login(username="admin_arthur", password="ArthurPassword123!")
        response = self.client.get(reverse("academics:teacher_assignments"))
        self.assertEqual(response.status_code, 200)

        # Faculty blocked with 403 Forbidden
        self.client.login(username="prof_lupin", password="LupinPassword123!")
        response = self.client.get(reverse("academics:teacher_assignments"))
        self.assertEqual(response.status_code, 403)
