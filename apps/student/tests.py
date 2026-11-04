"""
Automated tests for Phase 3: Student Workspace Module.
Compliant with Section 6.2, Section 7, and Section 25.
"""

from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import User, UserRole, UserStatus
from apps.student.models import StudentProfile, AdmissionApplicationStatus


class StudentWorkspaceTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Active student
        self.student_user = User.objects.create_user(
            username="stud_emma",
            password="EmmaPassword123!",
            first_name="Emma",
            last_name="Watson",
            role=UserRole.STUDENT,
            status=UserStatus.ACTIVE,
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            registration_number="APP-EMMA-01",
            roll_number="CS-2026-0042",
            department_name="Computer Science",
            course_name="B.Tech Computer Science",
            batch_name="2024-2028",
            current_semester=2,
            admission_status=AdmissionApplicationStatus.APPROVED,
        )

        # Teacher user to verify role boundary
        self.teacher_user = User.objects.create_user(
            username="prof_snape",
            password="SnapePassword123!",
            role=UserRole.TEACHER,
            status=UserStatus.ACTIVE,
        )

    def test_student_dashboard_accessible_to_active_student(self):
        """Active student can view student dashboard with accurate academic info."""
        self.client.login(username="stud_emma", password="EmmaPassword123!")
        response = self.client.get(reverse("student:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Emma Watson")
        self.assertContains(response, "CS-2026-0042")
        self.assertContains(response, "Semester 2")

    def test_teacher_blocked_from_student_dashboard(self):
        """Teachers cannot access student workspace (server-side role isolation)."""
        self.client.login(username="prof_snape", password="SnapePassword123!")
        response = self.client.get(reverse("student:dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_user_redirected_to_login(self):
        """Unauthenticated requests to student dashboard redirect to login."""
        response = self.client.get(reverse("student:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_student_profile_edit_and_idor_protection(self):
        """Student can update permitted contact details, but cannot manipulate roll number."""
        self.client.login(username="stud_emma", password="EmmaPassword123!")
        response = self.client.post(
            reverse("student:profile"),
            {
                "first_name": "Emma",
                "last_name": "Watson-Edited",
                "guardian_name": "Chris Watson",
                "contact_number": "+1234567890",
                "roll_number": "HACKED-ROLL-999",  # Attempted illegal tamper
            },
        )
        self.assertEqual(response.status_code, 302)

        self.student_profile.refresh_from_db()
        self.student_user.refresh_from_db()
        # Permitted fields updated
        self.assertEqual(self.student_user.last_name, "Watson-Edited")
        self.assertEqual(self.student_profile.guardian_name, "Chris Watson")
        # Critical roll number protected and unchanged
        self.assertEqual(self.student_profile.roll_number, "CS-2026-0042")

    def test_student_academics_view(self):
        """Student can access academic curriculum details."""
        self.client.login(username="stud_emma", password="EmmaPassword123!")
        response = self.client.get(reverse("student:academics"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "B.Tech Computer Science")
        self.assertContains(response, "2024-2028")

    def test_student_registration_workflow(self):
        """Public self-registration creates pending user and application."""
        response = self.client.post(
            reverse("student:register"),
            {
                "username": "candidate_harry",
                "password": "HarryPassword123!",
                "confirm_password": "HarryPassword123!",
                "first_name": "Harry",
                "last_name": "Potter",
                "department_name": "Department of Physics",
                "course_name": "B.Sc Physics",
                "batch_name": "2024-2027",
                "contact_number": "9876543210",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("student:admission_status"))

        # Verify created user is pending approval
        user = User.objects.get(username="candidate_harry")
        self.assertEqual(user.role, UserRole.STUDENT)
        self.assertEqual(user.status, UserStatus.PENDING_APPROVAL)
        self.assertTrue(hasattr(user, "student_profile"))
        self.assertEqual(user.student_profile.admission_status, AdmissionApplicationStatus.SUBMITTED)
        self.assertIsNone(user.student_profile.roll_number)

    def test_pending_applicant_can_view_admission_status(self):
        """Candidate in pending review status can view their admission progress."""
        self.client.login(username="candidate_harry", password="HarryPassword123!")
        # Let's create a pending user directly to test status view
        pending_user = User.objects.create_user(
            username="stud_pending",
            password="PendingPassword123!",
            role=UserRole.STUDENT,
            status=UserStatus.PENDING_APPROVAL,
        )
        StudentProfile.objects.create(
            user=pending_user,
            registration_number="APP-PENDING-99",
            admission_status=AdmissionApplicationStatus.SUBMITTED,
        )
        self.client.login(username="stud_pending", password="PendingPassword123!")
        response = self.client.get(reverse("student:admission_status"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "APP-PENDING-99")
        self.assertContains(response, "Admission Application Tracker")
