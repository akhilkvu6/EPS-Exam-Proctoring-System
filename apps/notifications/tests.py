from django.test import TestCase, Client, RequestFactory
from django.urls import reverse

from apps.accounts.models import User, UserRole, UserStatus
from apps.notifications.models import Notification, NotificationLevel
from apps.notifications.services.dispatcher import send_notification, send_bulk_notifications
from apps.notifications.context_processors import notifications_context


class NotificationSystemTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()

        self.user_a = User.objects.create_user(
            username="user_arthur",
            email="arthur@phoenix.edu",
            password="securepassword123",
            role=UserRole.STUDENT,
            status=UserStatus.ACTIVE,
        )
        self.user_b = User.objects.create_user(
            username="user_bellatrix",
            email="bellatrix@phoenix.edu",
            password="securepassword123",
            role=UserRole.STUDENT,
            status=UserStatus.ACTIVE,
        )

    def test_single_and_bulk_dispatch(self):
        """Verifies individual and bulk notification dispatch."""
        notif = send_notification(
            recipient=self.user_a,
            title="Roll Allocated",
            message="Your official roll number is EP-2026-0099.",
            level=NotificationLevel.SUCCESS,
            action_url="/student/profile/",
        )
        self.assertIsNotNone(notif.id)
        self.assertFalse(notif.is_read)
        self.assertEqual(notif.recipient, self.user_a)

        # Bulk dispatch
        count = send_bulk_notifications(
            recipients=[self.user_a, self.user_b],
            title="System Maintenance",
            message="Platform will undergo brief maintenance on Sunday.",
            level=NotificationLevel.INFO,
        )
        self.assertEqual(count, 2)
        self.assertEqual(Notification.objects.filter(recipient=self.user_a).count(), 2)

    def test_notifications_context_processor(self):
        """Verifies context processor calculates unread counts accurately."""
        send_notification(self.user_a, "Alert 1", "Msg 1")
        send_notification(self.user_a, "Alert 2", "Msg 2")

        request = self.factory.get("/")
        request.user = self.user_a

        ctx = notifications_context(request)
        self.assertEqual(ctx["unread_notifications_count"], 2)
        self.assertEqual(len(ctx["recent_notifications"]), 2)

    def test_mark_as_read_and_navigation(self):
        """Tests individual mark read following destination URL."""
        notif = send_notification(
            recipient=self.user_a,
            title="Exam Scheduled",
            message="Exam opens tomorrow.",
            action_url="/exam/lobby/EXAM-101/",
        )

        self.client.force_login(self.user_a)
        url = reverse("notifications:mark_read", args=[notif.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/exam/lobby/EXAM-101/")

        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

    def test_mark_all_as_read(self):
        """Tests mark all as read action."""
        send_notification(self.user_a, "N1", "M1")
        send_notification(self.user_a, "N2", "M2")

        self.client.force_login(self.user_a)
        url = reverse("notifications:mark_all_read")
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)

        unread_count = Notification.objects.filter(recipient=self.user_a, is_read=False).count()
        self.assertEqual(unread_count, 0)

    def test_notification_user_isolation(self):
        """Ensures User B cannot mark User A's notification as read."""
        notif_a = send_notification(self.user_a, "Private Notice", "Confidential.")

        self.client.force_login(self.user_b)
        url = reverse("notifications:mark_read", args=[notif_a.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)
