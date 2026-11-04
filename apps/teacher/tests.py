"""
Automated tests for Phase 4: Teacher Workspace Module.
Compliant with Section 6.2, Section 7, Section 8.3, and Section 25.
"""

from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import User, UserRole, UserStatus
from apps.student.models import StudentProfile, AdmissionApplicationStatus
from apps.teacher.models import TeacherProfile, AdmissionReviewRecord, AdmissionReviewAction


class TeacherWorkspaceTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Faculty member in Computer Science
        self.teacher_user = User.objects.create_user(
            username="prof_mcgonagall",
            password="ProfPassword123!",
            first_name="Minerva",
            last_name="McGonagall",
            role=UserRole.TEACHER,
            status=UserStatus.ACTIVE,
        )
        self.teacher_profile = TeacherProfile.objects.create(
            user=self.teacher_user,
            staff_id="FAC-CS-001",
            designation="Professor & Head",
            department_name="Department of Computer Science",
            is_head_of_department=False,
        )

        # Student in Computer Science (Pending Review)
        self.student_cs_user = User.objects.create_user(
            username="stud_ron",
            password="RonPassword123!",
            first_name="Ron",
            last_name="Weasley",
            role=UserRole.STUDENT,
            status=UserStatus.PENDING_APPROVAL,
        )
        self.student_cs_profile = StudentProfile.objects.create(
            user=self.student_cs_user,
            registration_number="APP-CS-0089",
            department_name="Department of Computer Science",
            course_name="B.Tech Computer Science",
            batch_name="2024-2028",
            admission_status=AdmissionApplicationStatus.SUBMITTED,
        )

        # Student in Mechanical Engineering (Different department)
        self.student_mech_user = User.objects.create_user(
            username="stud_seamus",
            password="SeamusPassword123!",
            role=UserRole.STUDENT,
            status=UserStatus.PENDING_APPROVAL,
        )
        self.student_mech_profile = StudentProfile.objects.create(
            user=self.student_mech_user,
            registration_number="APP-MECH-0012",
            department_name="Department of Mechanical Engineering",
            course_name="B.Tech Mechanical",
            batch_name="2024-2028",
            admission_status=AdmissionApplicationStatus.SUBMITTED,
        )

    def test_teacher_dashboard_accessible_to_teacher(self):
        """Faculty can access teacher workspace dashboard."""
        self.client.login(username="prof_mcgonagall", password="ProfPassword123!")
        response = self.client.get(reverse("teacher:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Minerva McGonagall")
        self.assertContains(response, "Department of Computer Science")

    def test_student_blocked_from_teacher_dashboard(self):
        """Active student accessing faculty workspace receives 403 Forbidden."""
        active_student = User.objects.create_user(
            username="stud_active_ron",
            password="RonPassword123!",
            role=UserRole.STUDENT,
            status=UserStatus.ACTIVE,
        )
        self.client.login(username="stud_active_ron", password="RonPassword123!")
        response = self.client.get(reverse("teacher:dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_admission_queue_department_scoping(self):
        """Faculty only views applications belonging to their department jurisdiction."""
        self.client.login(username="prof_mcgonagall", password="ProfPassword123!")
        response = self.client.get(reverse("teacher:admission_queue"))
        self.assertEqual(response.status_code, 200)
        # Should contain CS applicant
        self.assertContains(response, "APP-CS-0089")
        # Should not contain Mechanical applicant
        self.assertNotContains(response, "APP-MECH-0012")

    def test_faculty_admission_approve_allocates_roll_and_activates_user(self):
        """Faculty approves applicant: sets APPROVED, allocates roll number, activates user."""
        self.client.login(username="prof_mcgonagall", password="ProfPassword123!")
        response = self.client.post(
            reverse("teacher:admission_detail", kwargs={"application_id": self.student_cs_profile.id}),
            {
                "action": AdmissionReviewAction.APPROVE,
                "roll_number": "CS-2024-0099",
                "remarks": "Academic transcripts verified. Admission granted.",
            },
        )
        self.assertEqual(response.status_code, 302)

        self.student_cs_profile.refresh_from_db()
        self.student_cs_user.refresh_from_db()

        self.assertEqual(self.student_cs_profile.admission_status, AdmissionApplicationStatus.APPROVED)
        self.assertEqual(self.student_cs_profile.roll_number, "CS-2024-0099")
        self.assertIsNotNone(self.student_cs_profile.admission_approved_at)
        self.assertEqual(self.student_cs_user.status, UserStatus.ACTIVE)
        self.assertTrue(self.student_cs_user.is_verified)

        # Verify audit record created
        audit = AdmissionReviewRecord.objects.filter(student_profile=self.student_cs_profile).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.action, AdmissionReviewAction.APPROVE)
        self.assertEqual(audit.reviewer, self.teacher_user)
        self.assertIn("verified", audit.remarks)

    def test_faculty_admission_escalate_to_admin(self):
        """Faculty escalates exception to admin."""
        self.client.login(username="prof_mcgonagall", password="ProfPassword123!")
        response = self.client.post(
            reverse("teacher:admission_detail", kwargs={"application_id": self.student_cs_profile.id}),
            {
                "action": AdmissionReviewAction.ESCALATE,
                "remarks": "Candidate requested special exemption; escalating to Admin office.",
            },
        )
        self.assertEqual(response.status_code, 302)

        self.student_cs_profile.refresh_from_db()
        self.assertEqual(self.student_cs_profile.admission_status, AdmissionApplicationStatus.ESCALATED_ADMIN)

    def test_faculty_admission_request_info(self):
        """Faculty requests additional info from applicant."""
        self.client.login(username="prof_mcgonagall", password="ProfPassword123!")
        response = self.client.post(
            reverse("teacher:admission_detail", kwargs={"application_id": self.student_cs_profile.id}),
            {
                "action": AdmissionReviewAction.REQUEST_INFO,
                "remarks": "Please provide your secondary school certificate.",
            },
        )
        self.assertEqual(response.status_code, 302)

        self.student_cs_profile.refresh_from_db()
        self.assertEqual(self.student_cs_profile.admission_status, AdmissionApplicationStatus.INFO_REQUESTED)

    def test_teacher_profile_update(self):
        """Faculty can update permitted profile fields."""
        self.client.login(username="prof_mcgonagall", password="ProfPassword123!")
        response = self.client.post(
            reverse("teacher:profile"),
            {
                "first_name": "Minerva",
                "last_name": "McGonagall",
                "designation": "Distinguished Professor",
                "office_location": "Tower Room 3B",
                "qualifications": "Ph.D. Transfiguration & Systems",
            },
        )
        self.assertEqual(response.status_code, 302)

        self.teacher_profile.refresh_from_db()
        self.assertEqual(self.teacher_profile.designation, "Distinguished Professor")
        self.assertEqual(self.teacher_profile.office_location, "Tower Room 3B")
