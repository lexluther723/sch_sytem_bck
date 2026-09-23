from datetime import date

from django.db import models

from accounts.models import TeacherProfile
from classes.models import ClassRoom
from subjects.models import Subject


# =====================================================
# CURRENT ACADEMIC YEAR
# =====================================================

def current_academic_year():
    year = date.today().year
    return f"{year}/{year + 1}"


# =====================================================
# TEACHER ASSIGNMENT
# =====================================================

class TeacherAssignment(models.Model):

    class Term(models.TextChoices):

        TERM_1 = "Term 1", "Term 1"
        TERM_2 = "Term 2", "Term 2"
        TERM_3 = "Term 3", "Term 3"

    # =================================================
    # TEACHER
    # =================================================

    teacher = models.ForeignKey(
        TeacherProfile,
        on_delete=models.CASCADE,
        related_name="assignments",
    )

    # =================================================
    # CLASSROOM
    # =================================================

    classroom = models.ForeignKey(
        ClassRoom,
        on_delete=models.CASCADE,
        related_name="teacher_assignments",
    )

    # =================================================
    # SUBJECT
    # =================================================

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="teacher_assignments",
    )

    # =================================================
    # ACADEMIC YEAR
    # =================================================

    academic_year = models.CharField(
        max_length=9,
        default=current_academic_year,
    )

    # =================================================
    # TERM
    # =================================================

    term = models.CharField(
        max_length=10,
        choices=Term.choices,
    )

    # =================================================
    # STATUS
    # =================================================

    is_active = models.BooleanField(
        default=True
    )

    # =================================================
    # CLASS TEACHER
    # =================================================

    is_class_teacher = models.BooleanField(
        default=False
    )

    # =================================================
    # DATES
    # =================================================

    assigned_date = models.DateField(
        auto_now_add=True
    )

    end_date = models.DateField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    # =================================================
    # META
    # =================================================

    class Meta:

        ordering = [
            "academic_year",
            "term",
            "classroom",
        ]

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "teacher",
                    "classroom",
                    "subject",
                    "academic_year",
                    "term",
                ],
                name="unique_teacher_class_subject_term",
            ),

        ]

        indexes = [

            models.Index(
                fields=[
                    "teacher",
                    "academic_year",
                    "term",
                ]
            ),

            models.Index(
                fields=[
                    "classroom",
                    "academic_year",
                    "term",
                ]
            ),

            models.Index(
                fields=[
                    "subject",
                    "academic_year",
                    "term",
                ]
            ),

        ]

    # =================================================
    # STRING
    # =================================================

    def __str__(self):

        teacher_name = (
            self.teacher.user.get_full_name()
            if self.teacher and self.teacher.user
            else "Unknown Teacher"
        )

        return (
            f"{teacher_name} - "
            f"{self.subject.name} - "
            f"{self.classroom}"
        )