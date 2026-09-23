from django.db import transaction

from .models import Notification


# ============================================================
# CREATE SINGLE NOTIFICATION
# ============================================================

@transaction.atomic
def create_notification(
    recipient,
    title,
    message,
    notification_type,
    triggered_by=None,
    attendance=None,
):
    """
    Create one notification for one user.

    This is used by attendance, fees, results,
    announcements, and other parts of Luma.
    """

    if recipient is None:
        raise ValueError(
            "Recipient cannot be None."
        )

    if not title:
        raise ValueError(
            "Notification title cannot be empty."
        )

    if not message:
        raise ValueError(
            "Notification message cannot be empty."
        )

    if not notification_type:
        raise ValueError(
            "Notification type cannot be empty."
        )

    notification = Notification.objects.create(
        recipient=recipient,
        triggered_by=triggered_by,
        attendance=attendance,
        title=title,
        message=message,
        notification_type=notification_type,
    )

    return notification


# ============================================================
# CREATE BULK NOTIFICATIONS
# ============================================================

@transaction.atomic
def create_bulk_notifications(
    recipients,
    title,
    message,
    notification_type,
    triggered_by=None,
):
    """
    Create notifications for multiple users.
    """

    if not recipients:
        return []

    notifications = [
        Notification(
            recipient=user,
            triggered_by=triggered_by,
            title=title,
            message=message,
            notification_type=notification_type,
        )
        for user in recipients
        if user is not None
    ]

    if not notifications:
        return []

    return Notification.objects.bulk_create(
        notifications
    )