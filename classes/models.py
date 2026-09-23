from django.db import models
from django.core.exceptions import ValidationError


class ClassRoom(models.Model):
    class Grade(models.TextChoices):
        DAY_CARE="Day Care", "Day Care"
        PP1 = "PP1", "PP1"
        PP2 = "PP2", "PP2"
        GRADE_1 = "Grade 1", "Grade 1"
        GRADE_2 = "Grade 2", "Grade 2"
        GRADE_3 = "Grade 3", "Grade 3"
        GRADE_4 = "Grade 4", "Grade 4"
        GRADE_5 = "Grade 5", "Grade 5"
        GRADE_6 = "Grade 6", "Grade 6"
        GRADE_7 = "Grade 7", "Grade 7"
        GRADE_8 = "Grade 8", "Grade 8"
        GRADE_9 = "Grade 9", "Grade 9"

    STREAM_CHOICES = [
        ("A", "A"),
        ("B", "B"),
        ("C", "C"),
    ]

    grade = models.CharField(
        max_length=20,
        choices=Grade.choices
    )

    stream = models.CharField(
        max_length=1,
        choices=STREAM_CHOICES
    )

    capacity = models.PositiveIntegerField(default=0)
    total_students = models.PositiveIntegerField(default=0, editable=False)

    class_teacher = models.ForeignKey(
        "accounts.TeacherProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="classrooms"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["grade", "stream"],
                name="unique_grade_stream",
            )
        ]
        ordering = ["grade", "stream"]

    def clean(self):
        """
        Prevent one teacher from being assigned
        to more than one classroom.
        """
        if self.class_teacher:
            exists = ClassRoom.objects.filter(
                class_teacher=self.class_teacher
            ).exclude(pk=self.pk).exists()

            if exists:
                raise ValidationError({
                    "class_teacher":
                    "This teacher is already assigned as a class teacher."
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.grade} {self.stream}"