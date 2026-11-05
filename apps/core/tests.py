"""
Automated tests for apps.core foundation.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.conf import settings
import json


class CoreViewsTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_index_view_status_and_content(self):
        """Verify the institutional landing page renders with status 200 and expected branding."""
        response = self.client.get(reverse("core:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "EPS Phoenix")
        self.assertContains(response, "Phoenix Institute of Technology")
        self.assertContains(response, "Student Workspace")
        self.assertContains(response, "Teacher Workspace")
        self.assertContains(response, "Admin Workspace")

    def test_health_check_endpoint(self):
        """Verify the health check endpoint returns 200 and valid JSON with healthy database status."""
        response = self.client.get(reverse("core:health_check"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["database"], "connected")
        self.assertEqual(data["platform"], "EPS Phoenix")
        self.assertEqual(data["version"], "3.0.0")

    def test_context_processor_institution_branding(self):
        """Verify institution context processor supplies branding variables."""
        response = self.client.get(reverse("core:index"))
        self.assertIn("INSTITUTION_NAME", response.context)
        self.assertIn("PLATFORM_NAME", response.context)
        self.assertIn("PLATFORM_VERSION", response.context)
        self.assertEqual(response.context["PLATFORM_NAME"], "EPS Phoenix")

    def test_index_view_authenticated_roles(self):
        """Verify the landing page navbar renders correctly for all authenticated roles."""
        from apps.accounts.models import User

        for role in ["ADMIN", "TEACHER", "STUDENT"]:
            user = User.objects.create_user(
                username=f"user_{role.lower()}",
                password="password123",
                role=role,
            )
            self.client.force_login(user)
            response = self.client.get(reverse("core:index"))
            self.assertEqual(response.status_code, 200)
            self.client.logout()


class CoreSettingsTests(TestCase):
    def test_installed_apps_includes_core(self):
        """Ensure apps.core is installed in the project configuration."""
        self.assertIn("apps.core", settings.INSTALLED_APPS)

    def test_design_tokens_file_configured(self):
        """Ensure staticfiles directories include the project static folder."""
        static_dirs = [str(p) for p in settings.STATICFILES_DIRS]
        self.assertTrue(any("static" in p for p in static_dirs))
