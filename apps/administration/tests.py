"""
Automated tests for Phase 5: Admin Workspace Module.
Compliant with Section 6.2, Section 7, Section 8.4, and Section 25.
"""

from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import User, UserRole, UserStatus
from apps.student.models import StudentProfile, AdmissionApplicationStatus
from apps.teacher.models import TeacherProfile
from apps.administration.models import InstitutionSetting, SystemAuditLog


class AdminWorkspaceTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Institutional Admin
        self.admin_user = User.objects.create_user(
            username="admin_albus",
            password="AlbusPassword123!",
            first_name="Albus",
            last_name="Dumbledore",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            is_staff=True,
            is_superuser=True,
        )

        # Faculty Member
        self.teacher_user = User.objects.create_user(
            username="prof_flitwick",
            password="FlitwickPassword123!",
            role=UserRole.TEACHER,
            status=UserStatus.ACTIVE,
        )

        # Student User
        self.student_user = User.objects.create_user(
            username="stud_neville",
            password="NevillePassword123!",
            role=UserRole.STUDENT,
            status=UserStatus.ACTIVE,
        )

        # Escalated Applicant
        self.escalated_user = User.objects.create_user(
            username="candidate_luna",
            password="LunaPassword123!",
            role=UserRole.STUDENT,
            status=UserStatus.PENDING_APPROVAL,
        )
        self.escalated_profile = StudentProfile.objects.create(
            user=self.escalated_user,
            registration_number="APP-LUNA-777",
            department_name="Department of Magical Creatures",
            course_name="B.Sc Zoology",
            batch_name="2024-2027",
            admission_status=AdmissionApplicationStatus.ESCALATED_ADMIN,
        )

    def test_admin_dashboard_accessible_to_admin(self):
        """Admin user can view administrative governance console."""
        self.client.login(username="admin_albus", password="AlbusPassword123!")
        response = self.client.get(reverse("administration:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Central Administration Console")
        self.assertContains(response, "Total Students")

    def test_teacher_blocked_from_admin_dashboard(self):
        """Faculty member cannot access institutional admin console."""
        self.client.login(username="prof_flitwick", password="FlitwickPassword123!")
        response = self.client.get(reverse("administration:dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_student_blocked_from_admin_dashboard(self):
        """Student cannot access institutional admin console."""
        self.client.login(username="stud_neville", password="NevillePassword123!")
        response = self.client.get(reverse("administration:dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_escalated_admissions_view_shows_escalated_cases(self):
        """Admin can view escalated applications queue."""
        self.client.login(username="admin_albus", password="AlbusPassword123!")
        response = self.client.get(reverse("administration:escalated_admissions"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "APP-LUNA-777")
        self.assertContains(response, "candidate_luna")

    def test_admin_approve_escalated_application(self):
        """Admin approves escalated admission, allocates roll number with prefix, writes audit log."""
        self.client.login(username="admin_albus", password="AlbusPassword123!")
        response = self.client.post(
            reverse("administration:escalation_detail", kwargs={"application_id": self.escalated_profile.id}),
            {
                "action": "APPROVE",
                "roll_number": "EP-SPECIAL-001",
                "remarks": "Special institutional admission exemption approved by Chancellor.",
            },
        )
        self.assertEqual(response.status_code, 302)

        self.escalated_profile.refresh_from_db()
        self.escalated_user.refresh_from_db()

        self.assertEqual(self.escalated_profile.admission_status, AdmissionApplicationStatus.APPROVED)
        self.assertEqual(self.escalated_profile.roll_number, "EP-SPECIAL-001")
        self.assertEqual(self.escalated_user.status, UserStatus.ACTIVE)

        # Verify audit log created
        audit = SystemAuditLog.objects.filter(action_type="ESCALATION_APPROVED").first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.actor, self.admin_user)
        self.assertIn("EP-SPECIAL-001", audit.details)

    def test_admin_return_escalation_to_teacher(self):
        """Admin returns application back to faculty queue with instructions."""
        self.client.login(username="admin_albus", password="AlbusPassword123!")
        response = self.client.post(
            reverse("administration:escalation_detail", kwargs={"application_id": self.escalated_profile.id}),
            {
                "action": "RETURN",
                "remarks": "Please ask candidate for translated transcripts first.",
            },
        )
        self.assertEqual(response.status_code, 302)

        self.escalated_profile.refresh_from_db()
        self.assertEqual(self.escalated_profile.admission_status, AdmissionApplicationStatus.PENDING_TEACHER)

        audit = SystemAuditLog.objects.filter(action_type="ESCALATION_RETURNED").first()
        self.assertIsNotNone(audit)

    def test_user_status_toggle_suspend(self):
        """Admin can administratively suspend a student account."""
        self.client.login(username="admin_albus", password="AlbusPassword123!")
        response = self.client.post(
            reverse("administration:user_status_toggle", kwargs={"user_id": self.student_user.id}),
            {
                "new_status": UserStatus.SUSPENDED,
                "reason": "Security violation investigation",
            },
        )
        self.assertEqual(response.status_code, 302)

        self.student_user.refresh_from_db()
        self.assertEqual(self.student_user.status, UserStatus.SUSPENDED)

        audit = SystemAuditLog.objects.filter(action_type="USER_STATUS_CHANGE").first()
        self.assertIsNotNone(audit)
        self.assertIn("SUSPENDED", audit.details)

    def test_admin_self_suspension_prevented(self):
        """Admin cannot suspend their own account."""
        self.client.login(username="admin_albus", password="AlbusPassword123!")
        response = self.client.post(
            reverse("administration:user_status_toggle", kwargs={"user_id": self.admin_user.id}),
            {
                "new_status": UserStatus.SUSPENDED,
            },
        )
        self.assertEqual(response.status_code, 302)

        self.admin_user.refresh_from_db()
        self.assertEqual(self.admin_user.status, UserStatus.ACTIVE)

    def test_provision_faculty_account(self):
        """Admin can provision a new faculty account."""
        self.client.login(username="admin_albus", password="AlbusPassword123!")
        response = self.client.post(
            reverse("administration:teachers_management"),
            {
                "username": "prof_sprout",
                "first_name": "Pomona",
                "last_name": "Sprout",
                "password": "SproutPassword123!",
                "staff_id": "FAC-BOT-007",
                "department_name": "Department of Botany",
                "designation": "Associate Professor",
                "office_location": "Greenhouse 3",
            },
        )
        self.assertEqual(response.status_code, 302)

        new_teacher = User.objects.get(username="prof_sprout")
        self.assertEqual(new_teacher.role, UserRole.TEACHER)
        self.assertEqual(new_teacher.status, UserStatus.ACTIVE)
        self.assertTrue(hasattr(new_teacher, "teacher_profile"))
        self.assertEqual(new_teacher.teacher_profile.staff_id, "FAC-BOT-007")

    def test_institution_settings_update(self):
        """Admin can update institutional settings and theme tokens."""
        self.client.login(username="admin_albus", password="AlbusPassword123!")
        response = self.client.post(
            reverse("administration:settings"),
            {
                "institution_name": "Hogwarts School of Technology",
                "tagline": "Draco Dormiens Nunquam Titillandus",
                "contact_email": "admin@hogwarts.edu",
                "contact_phone": "+44 1234 567890",
                "default_theme": "dark",
                "default_accent_color": "#7c3aed",
                "roll_number_prefix": "HOG",
                "allow_student_self_registration": True,
            },
        )
        self.assertEqual(response.status_code, 302)

        settings_obj = InstitutionSetting.get_settings()
        self.assertEqual(settings_obj.institution_name, "Hogwarts School of Technology")
        self.assertEqual(settings_obj.default_theme, "dark")
        self.assertEqual(settings_obj.roll_number_prefix, "HOG")
