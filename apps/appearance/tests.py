import json
from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory
from django.urls import reverse

from apps.accounts.models import UserRole
from apps.appearance.models import UserAppearancePreference, ThemeMode, InterfaceDensity
from apps.appearance.context_processors import appearance_context

User = get_user_model()


class AppearancePreferenceModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="test_appearance_user",
            email="theme@example.com",
            password="StrongPassword123!",
            role=UserRole.STUDENT,
        )

    def test_appearance_preference_defaults(self):
        pref = UserAppearancePreference.objects.create(user=self.user)
        self.assertEqual(pref.theme_mode, ThemeMode.SYSTEM)
        self.assertEqual(pref.accent_color, "#3b82f6")
        self.assertEqual(pref.density, InterfaceDensity.COMFORTABLE)
        self.assertFalse(pref.high_contrast)
        self.assertIn("test_appearance_user", str(pref))


class AppearanceContextProcessorTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="context_user",
            email="ctx@example.com",
            password="StrongPassword123!",
            role=UserRole.STUDENT,
        )

    def test_anonymous_user_defaults_and_cookies(self):
        request = self.factory.get("/")
        request.user = None
        request.COOKIES = {
            "theme_mode": "DARK",
            "accent_color": "#10b981",
            "density": "COMPACT",
            "high_contrast": "true",
        }
        ctx = appearance_context(request)
        self.assertEqual(ctx["user_theme_mode"], "dark")
        self.assertEqual(ctx["user_accent_color"], "#10b981")
        self.assertEqual(ctx["user_density"], "compact")
        self.assertTrue(ctx["user_high_contrast"])

    def test_authenticated_user_with_preference(self):
        UserAppearancePreference.objects.create(
            user=self.user,
            theme_mode=ThemeMode.DARK,
            accent_color="#8b5cf6",
            density=InterfaceDensity.RELAXED,
            high_contrast=True,
        )
        request = self.factory.get("/")
        request.user = self.user
        request.COOKIES = {}
        ctx = appearance_context(request)
        self.assertEqual(ctx["user_theme_mode"], "dark")
        self.assertEqual(ctx["user_accent_color"], "#8b5cf6")
        self.assertEqual(ctx["user_density"], "relaxed")
        self.assertTrue(ctx["user_high_contrast"])


class AppearanceViewsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="view_user",
            email="view_user@example.com",
            password="StrongPassword123!",
            role=UserRole.STUDENT,
            is_active=True,
        )
        self.client.force_login(self.user)

    def test_get_settings_view(self):
        url = reverse("appearance:settings")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "appearance/settings.html")
        self.assertIn("pref", response.context)

    def test_post_settings_view_updates_and_sets_cookies(self):
        url = reverse("appearance:settings")
        payload = {
            "theme_mode": ThemeMode.DARK,
            "accent_color": "#10b981",
            "density": InterfaceDensity.COMPACT,
            "high_contrast": "on",
        }
        response = self.client.post(url, data=payload)
        self.assertRedirects(response, url)

        pref = UserAppearancePreference.objects.get(user=self.user)
        self.assertEqual(pref.theme_mode, ThemeMode.DARK)
        self.assertEqual(pref.accent_color, "#10b981")
        self.assertEqual(pref.density, InterfaceDensity.COMPACT)
        self.assertTrue(pref.high_contrast)

        self.assertEqual(response.cookies["theme_mode"].value, ThemeMode.DARK)
        self.assertEqual(response.cookies["accent_color"].value, "#10b981")

    def test_api_update_appearance(self):
        url = reverse("appearance:api_update")
        data = {
            "theme_mode": ThemeMode.LIGHT,
            "accent_color": "#f59e0b",
            "density": InterfaceDensity.RELAXED,
            "high_contrast": False,
        }
        response = self.client.post(
            url,
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertEqual(res_data["status"], "updated")
        self.assertEqual(res_data["theme_mode"], ThemeMode.LIGHT)

        pref = UserAppearancePreference.objects.get(user=self.user)
        self.assertEqual(pref.theme_mode, ThemeMode.LIGHT)
        self.assertEqual(pref.accent_color, "#f59e0b")
        self.assertEqual(pref.density, InterfaceDensity.RELAXED)
        self.assertFalse(pref.high_contrast)
