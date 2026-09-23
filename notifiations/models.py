from django.db import models
from django.conf import settings


class Notification(models.Model):

    class NotificationType(models.TextChoices):
        ATTENDANCE = "Attendance", "Attendance"
        FEES = "Fees", "Fees"
        RESULTS = "Results", "Results"
        ANNOUNCEMENT = "Announcement", "Announcement"
        GENERAL = "General", "General"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="triggered_notifications",
    )

    attendance = models.ForeignKey(
        "attendance.Attendance",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )

    notification_type = models.CharField(
        max_length=40,
        choices=NotificationType.choices,
    )

    title = models.CharField(max_length=200)

    message = models.TextField()

    is_read = models.BooleanField(
        default=False
    )

    read_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.recipient.username} - "
            f"{self.title}"
        )