from django.db import models
from django.conf import settings


class Announcement(models.Model):

    class Target(models.TextChoices):
        ALL_USERS = "All Users", "All Users"
        STAFF = "Staff", "Staff"
        PARENTS = "Parents", "Parents"
        TEACHERS = "Teachers", "Teachers"

    class Priority(models.TextChoices):
        LOW = "Low", "Low"
        NORMAL = "Normal", "Normal"
        HIGH = "High", "High"

    title = models.CharField(max_length=200)
    message = models.TextField()
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )
    target = models.CharField(
        max_length=20,
        choices=Target.choices,
        default=Target.ALL_USERS,
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="personal_announcements",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="announcements",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]  # ✅ Newest first — matches ViewSet ordering

    def __str__(self):
        return self.title
