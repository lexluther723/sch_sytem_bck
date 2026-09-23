from django.db import models

from classes.models import ClassRoom
from subjects.models import Subject


# Create your models here
# =====================================================
# Exam
# =====================================================
class Exam(models.Model):

    class Term(models.TextChoices):
        TERM_1 = "Term 1", "Term 1"
        TERM_2 = "Term 2", "Term 2"
        TERM_3 = "Term 3", "Term 3"

    class ExamType(models.TextChoices):
        CAT_1 = "CAT 1", "CAT 1"
        CAT_2 = "CAT 2", "CAT 2"
        MIDTERM = "Midterm", "Midterm"
        ENDTERM = "End Term", "End Term"

    classroom = models.ForeignKey(
        ClassRoom,
        on_delete=models.CASCADE,
        related_name="exams"
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="exams"
    )

    exam_type = models.CharField(
        max_length=20,
        choices=ExamType.choices
    )

    term = models.CharField(
        max_length=20,
        choices=Term.choices
    )

    academic_year = models.PositiveIntegerField()

    exam_date = models.DateField()

    total_marks = models.PositiveIntegerField(
        default=100
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-academic_year", "-exam_date"]
        unique_together = (
            "classroom",
            "subject",
            "exam_type",
            "term",
            "academic_year",
        )

    def __str__(self):
        return (
            f"{self.exam_type} - "
            f"{self.subject.name} - "
            f"{self.classroom}"
        ) 