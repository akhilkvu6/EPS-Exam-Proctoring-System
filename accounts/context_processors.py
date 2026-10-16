def notifications_context(request):
    if request.user.is_authenticated:
        try:
            return {
                'unread_notification_count': request.user.notifications.filter(is_read=False).count()
            }
        except Exception:
            return {'unread_notification_count': 0}
    return {'unread_notification_count': 0}
