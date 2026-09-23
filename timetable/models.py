from datetime import date
from django.db import models
from assignments.models import TeacherAssignment
from django.core.exceptions import ValidationError

# create your model here
class Timetable(models.Model):

    class Day(models.TextChoices):
        MONDAY = "Monday", "Monday"
        TUESDAY = "Tuesday", "Tuesday"
        WEDNESDAY = "Wednesday", "Wednesday"
        THURSDAY = "Thursday", "Thursday"
        FRIDAY = "Friday", "Friday"
        SATURDAY = "Saturday", "Saturday"

    assignment = models.ForeignKey(
        TeacherAssignment,
        on_delete=models.CASCADE,
        related_name="timetable_entries"
    )

    def current_academic_year():
        year = date.today().year
        return f"{year}/{year + 1}"

    academic_year = models.CharField(
        max_length=9,
        default=current_academic_year
    )

    term = models.CharField(
        max_length=10,
        choices=TeacherAssignment.Term.choices
    )

    day = models.CharField(
        max_length=10,
        choices=Day.choices
    )

    start_time = models.TimeField()

    end_time = models.TimeField()

    is_break = models.BooleanField(default=False)

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    is_active = models.BooleanField(
        default=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = [
            "academic_year",
            "term",
            "day",
            "start_time",
            "assignment__classroom",
        ]

        unique_together = (
            "assignment",
            "academic_year",
            "term",
            "day",
            "start_time",
        )
    def clean(self):
        if self.end_time <= self.start_time:
            raise ValidationError(
                "End time must be later than start time."
            )    

    def __str__(self):
        return (
            f"{self.assignment.teacher.user.get_full_name()} | "
            f"{self.assignment.subject.name} | "
            f"{self.assignment.classroom} | "
            f"{self.day}"
        )