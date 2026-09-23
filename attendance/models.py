from django.db import models
from django.utils import timezone

from assignments.models import TeacherAssignment
from accounts.models import CustomUser
from classes.models import ClassRoom
from students.models import Student


# ============================================================
# ATTENDANCE SUBMISSION
# ============================================================

class AttendanceSubmission(models.Model):

    class Status(models.TextChoices):
        DRAFT = "Draft", "Draft"
        FINAL = "Final", "Final"

    assignment = models.ForeignKey(
        TeacherAssignment,
        on_delete=models.CASCADE,
        related_name="attendance_submissions",
    )

    classroom = models.ForeignKey(
        ClassRoom,
        on_delete=models.CASCADE,
        related_name="attendance_submissions",
    )

    date = models.DateField(
        default=timezone.localdate,
        db_index=True,
    )

    submitted_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_attendance",
    )

    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # ========================================================
    # NO APPROVAL SYSTEM
    #
    # Draft = attendance session has been opened
    # Final = teacher has saved attendance
    # ========================================================

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-date", "classroom"]

        unique_together = (
            "assignment",
            "date",
        )

        verbose_name = "Attendance Submission"
        verbose_name_plural = "Attendance Submissions"

    def __str__(self):

        teacher_name = (
            self.assignment.teacher.user.get_full_name()
            if self.assignment.teacher
            and self.assignment.teacher.user
            else "Unknown Teacher"
        )

        return (
            f"{teacher_name} - "
            f"{self.classroom} - "
            f"{self.date}"
        )


# ============================================================
# ATTENDANCE RECORD
# ============================================================

class Attendance(models.Model):

    class Status(models.TextChoices):
        PRESENT = "Present", "Present"
        ABSENT = "Absent", "Absent"
        EXCUSED = "Excused", "Excused"

    submission = models.ForeignKey(
        AttendanceSubmission,
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PRESENT,
        # Indexed: attendance history/report endpoints filter by
        # status (Present/Absent/Excused) constantly, and this table
        # grows by (students × school days) rows — one of the
        # fastest-growing tables in the whole schema.
        db_index=True,
    )

    remarks = models.TextField(
        blank=True,
        null=True,
    )

    marked_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "student__admission_number",
        ]

        unique_together = (
            "submission",
            "student",
        )

        verbose_name = "Attendance Record"
        verbose_name_plural = "Attendance Records"

    def __str__(self):

        return (
            f"{self.student.admission_number} - "
            f"{self.student.first_name} "
            f"{self.student.last_name} "
            f"({self.status})"
        )