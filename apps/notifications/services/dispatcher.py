from typing import Iterable, List
from django.db import transaction
from apps.accounts.models import User
from apps.notifications.models import Notification, NotificationLevel


def send_notification(
    recipient: User,
    title: str,
    message: str,
    level: str = NotificationLevel.INFO,
    action_url: str = "",
) -> Notification:
    """Dispatches a single in-app notification to a user."""
    return Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        level=level,
        action_url=action_url,
    )


@transaction.atomic
def send_bulk_notifications(
    recipients: Iterable[User],
    title: str,
    message: str,
    level: str = NotificationLevel.INFO,
    action_url: str = "",
) -> int:
    """Dispatches in-app notifications in batch across multiple users."""
    items = [
        Notification(
            recipient=r,
            title=title,
            message=message,
            level=level,
            action_url=action_url,
        )
        for r in recipients
    ]
    created = Notification.objects.bulk_create(items)
    return len(created)
