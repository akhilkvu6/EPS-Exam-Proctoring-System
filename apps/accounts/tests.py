"""
Automated tests for Phase 2: Identity, Custom User Model, Roles & Authentication.
Compliant with Section 7 and Section 25.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from .models import User, UserRole, UserStatus
from .decorators import admin_required, teacher_required, student_required, active_user_required


class UserModelTests(TestCase):
    def test_create_student_user(self):
        """Verify student creation without mandatory email or phone per Section 7."""
        user = User.objects.create_user(
            username="student1",
            password="StrongPassword123!",
            role=UserRole.STUDENT,
        )
        self.assertEqual(user.username, "student1")
        self.assertEqual(user.role, UserRole.STUDENT)
        self.assertEqual(user.status, UserStatus.ACTIVE)
        self.assertTrue(user.is_student_user)
        self.assertFalse(user.is_teacher_user)
        self.assertFalse(user.is_admin_user)
        self.assertFalse(user.email)
        self.assertIsNone(user.phone)

    def test_create_teacher_user(self):
        """Verify teacher user creation with official ID."""
        teacher = User.objects.create_user(
            username="prof_smith",
            password="StrongPassword123!",
            role=UserRole.TEACHER,
            first_name="John",
            last_name="Smith",
            official_id="FAC-9081",
        )
        self.assertTrue(teacher.is_teacher_user)
        self.assertEqual(teacher.official_id, "FAC-9081")
        self.assertEqual(str(teacher), "John Smith (Teacher / Invigilator)")

    def test_create_superuser_admin(self):
        """Verify superuser creation defaults to admin capabilities."""
        admin_user = User.objects.create_superuser(
            username="sysadmin",
            password="SuperPassword123!",
            role=UserRole.ADMIN,
        )
        self.assertTrue(admin_user.is_admin_user)
        self.assertTrue(admin_user.is_superuser)
        self.assertTrue(admin_user.is_staff)


class AuthenticationViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = User.objects.create_user(
            username="stud_alice",
            password="PasswordAlice123!",
            role=UserRole.STUDENT,
        )
        self.teacher = User.objects.create_user(
            username="prof_bob",
            password="PasswordBob123!",
            role=UserRole.TEACHER,
        )
        self.admin = User.objects.create_user(
            username="admin_carol",
            password="PasswordCarol123!",
            role=UserRole.ADMIN,
        )
        self.suspended_user = User.objects.create_user(
            username="stud_suspended",
            password="PasswordSuspended123!",
            role=UserRole.STUDENT,
            status=UserStatus.SUSPENDED,
        )

    def test_login_page_renders_with_role_tabs(self):
        """Verify unified login page renders with Student, Teacher, and Admin options."""
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign In to EPS Phoenix")
        self.assertContains(response, "Student")
        self.assertContains(response, "Teacher")
        self.assertContains(response, "Admin")

    def test_student_login_successful_redirect(self):
        """Student login redirects toward student workspace."""
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "stud_alice",
                "password": "PasswordAlice123!",
                "intended_role": "STUDENT",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/student/dashboard/")

    def test_teacher_login_successful_redirect(self):
        """Teacher login redirects toward teacher workspace."""
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "prof_bob",
                "password": "PasswordBob123!",
                "intended_role": "TEACHER",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/teacher/dashboard/")

    def test_admin_login_successful_redirect(self):
        """Admin login redirects toward admin workspace."""
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "admin_carol",
                "password": "PasswordCarol123!",
                "intended_role": "ADMIN",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/administration/dashboard/")

    def test_invalid_password_shows_error(self):
        """Invalid credentials show user-friendly error message."""
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "stud_alice",
                "password": "WrongPassword!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid username or password")

    def test_suspended_user_blocked(self):
        """Suspended accounts cannot log in."""
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "stud_suspended",
                "password": "PasswordSuspended123!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "administratively suspended")

    def test_role_mismatch_rejected(self):
        """Attempting to log in as Teacher using Student credentials fails validation."""
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "stud_alice",
                "password": "PasswordAlice123!",
                "intended_role": "TEACHER",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "you are not registered as TEACHER")

    def test_logout_terminates_session(self):
        """Logout terminates authenticated session."""
        self.client.login(username="stud_alice", password="PasswordAlice123!")
        response = self.client.get(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("accounts:login"))


class RoleDecoratorsTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username="stud_dan", password="Password123!", role=UserRole.STUDENT
        )
        self.teacher = User.objects.create_user(
            username="teach_eve", password="Password123!", role=UserRole.TEACHER
        )
        self.admin = User.objects.create_user(
            username="admin_frank", password="Password123!", role=UserRole.ADMIN
        )

    def test_admin_required_decorator(self):
        @admin_required
        def dummy_admin_view(request):
            return HttpResponse("admin_ok")

        from django.test import RequestFactory
        factory = RequestFactory()

        # Admin user allowed
        req = factory.get("/")
        req.user = self.admin
        res = dummy_admin_view(req)
        self.assertEqual(res.content.decode(), "admin_ok")

        # Student user blocked
        req.user = self.student
        with self.assertRaises(PermissionDenied):
            dummy_admin_view(req)

        # Teacher user blocked from admin
        req.user = self.teacher
        with self.assertRaises(PermissionDenied):
            dummy_admin_view(req)

    def test_teacher_required_decorator(self):
        @teacher_required
        def dummy_teacher_view(request):
            return HttpResponse("teacher_ok")

        from django.test import RequestFactory
        factory = RequestFactory()

        # Teacher user allowed
        req = factory.get("/")
        req.user = self.teacher
        res = dummy_teacher_view(req)
        self.assertEqual(res.content.decode(), "teacher_ok")

        # Student user blocked
        req.user = self.student
        with self.assertRaises(PermissionDenied):
            dummy_teacher_view(req)
