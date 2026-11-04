from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.decorators import active_user_required
from apps.notifications.models import Notification


@login_required
@active_user_required
def notification_list_view(request):
    """Personal notifications and event activity stream."""
    notifications = Notification.objects.filter(recipient=request.user)

    filter_unread = request.GET.get("unread") == "1"
    if filter_unread:
        notifications = notifications.filter(is_read=False)

    return render(
        request,
        "notifications/notification_list.html",
        {
            "notifications": notifications,
            "filter_unread": filter_unread,
        },
    )


@login_required
@active_user_required
def mark_notification_read_view(request, notification_id):
    """Marks a notification as read and navigates to its destination."""
    notification = get_object_or_404(Notification, id=notification_id)

    if notification.recipient != request.user:
        raise PermissionDenied("Unauthorized notification access.")

    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])

    if notification.action_url:
        return redirect(notification.action_url)
    return redirect("notifications:list")


@login_required
@active_user_required
@require_POST
def mark_all_read_view(request):
    """Marks all notifications as read for current user."""
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect("notifications:list")


@login_required
@active_user_required
def api_unread_count_view(request):
    """Returns JSON unread count for real-time badge updates."""
    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({"unread_count": count})
