from django.db import models

from accounts.models import CustomUser
from students.models import Student, ClassRoom
from subjects.models import Subject


# =====================================================
# TERM CHOICES
# =====================================================

TERM_CHOICES = [
    ("Term 1", "Term 1"),
    ("Term 2", "Term 2"),
    ("Term 3", "Term 3"),
]


# =====================================================
# CBC GRADE SCALE
# =====================================================

class GradeScale(models.Model):

    level = models.CharField(
        max_length=5,
        unique=True,
    )

    description = models.CharField(
        max_length=100,
    )

    minimum_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
    )

    maximum_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
    )

    remarks = models.CharField(
        max_length=255,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-minimum_score"]

    def __str__(self):
        return (
            f"{self.level} "
            f"({self.minimum_score}-{self.maximum_score})"
        )


# =====================================================
# LEARNING OUTCOME
# =====================================================

class LearningOutcome(models.Model):

    classroom = models.ForeignKey(
        ClassRoom,
        on_delete=models.CASCADE,
        related_name="learning_outcomes",
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="learning_outcomes",
    )

    name = models.CharField(
        max_length=200,
    )

    description = models.TextField(
        blank=True,
    )

    maximum_marks = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=20,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "classroom",
                    "subject",
                    "name",
                ],
                name="unique_learning_outcome_per_class_subject",
            ),
        ]

        ordering = [
            "classroom",
            "subject",
            "name",
        ]

    def __str__(self):
        return (
            f"{self.classroom} - "
            f"{self.subject} - "
            f"{self.name}"
        )


# =====================================================
# ASSESSMENT TYPE
#
# Examples:
# CAT
# Project
# Practical
# Mid Term
# End Term
#
# NOTE:
# This model is descriptive only.
#
# We DO NOT use a percentage here.
#
# Assessment marks are calculated from the
# Assessment.total_marks instead.
# =====================================================

class AssessmentType(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return self.name


# =====================================================
# ASSESSMENT
# =====================================================

class Assessment(models.Model):

    classroom = models.ForeignKey(
        ClassRoom,
        on_delete=models.CASCADE,
        related_name="assessments",
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="assessments",
    )

    # -------------------------------------------------
    # Assessment type
    #
    # Examples:
    # "CAT 1"
    # "CAT 2"
    # "Project"
    # "Practical"
    # "End Term"
    #
    # This remains a CharField intentionally.
    # There is NO percentage calculation attached to it.
    # -------------------------------------------------

    assessment_type = models.CharField(
        max_length=100,
    )

    academic_year = models.CharField(
        max_length=20,
    )

    term = models.CharField(
        max_length=20,
        choices=TERM_CHOICES,
    )

    # -------------------------------------------------
    # Maximum marks for this particular assessment
    #
    # Examples:
    #
    # CAT 1 = 30
    # CAT 2 = 40
    # Project = 20
    # End Term = 100
    #
    # The entered student's marks are calculated
    # against THIS value.
    # -------------------------------------------------

    total_marks = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100,
    )

    assessment_date = models.DateField()

    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_assessments",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-assessment_date",
            "-created_at",
        ]

    def __str__(self):
        return (
            f"{self.subject} - "
            f"{self.assessment_type}"
        )


# =====================================================
# RESULT SUBMISSION
# =====================================================

class ResultSubmission(models.Model):

    class ApprovalStatus(models.TextChoices):

        DRAFT = (
            "Draft",
            "Draft",
        )

        PENDING = (
            "Pending",
            "Pending",
        )

        APPROVED = (
            "Approved",
            "Approved",
        )

        RETURNED = (
            "Returned",
            "Returned",
        )

    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        related_name="result_submissions",
        null=True,
        blank=True,
    )

    submitted_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_results",
    )

    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.DRAFT,
    )

    approved_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_results",
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    coordinator_comments = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):

        assessment = (
            str(self.assessment)
            if self.assessment
            else "No Assessment"
        )

        return (
            f"{assessment} "
            f"({self.approval_status})"
        )


# =====================================================
# STUDENT MARKS / RAW RESULT
# =====================================================

class Result(models.Model):

    class ResultStatus(models.TextChoices):

        PENDING = (
            "Pending",
            "Pending",
        )

        PRESENT = (
            "Present",
            "Present",
        )

        ABSENT = (
            "Absent",
            "Absent",
        )

        EXCUSED = (
            "Excused",
            "Excused",
        )

        EXEMPTED = (
            "Exempted",
            "Exempted",
        )

    submission = models.ForeignKey(
        ResultSubmission,
        on_delete=models.CASCADE,
        related_name="results",
    )

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="results",
    )

    # -------------------------------------------------
    # Student assessment status
    # -------------------------------------------------

    status = models.CharField(
        max_length=20,
        choices=ResultStatus.choices,
        default=ResultStatus.PENDING,
    )

    # -------------------------------------------------
    # Raw marks entered by teacher
    #
    # Example:
    #
    # Assessment total = 50
    # Student marks = 42
    #
    # The system calculates:
    #
    # 42 / 50 × 100 = 84%
    # -------------------------------------------------

    marks = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # -------------------------------------------------
    # Automatically calculated percentage
    #
    # Example:
    #
    # marks = 42
    # total_marks = 50
    # percentage = 84
    # -------------------------------------------------

    weighted_marks = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
    )

    # -------------------------------------------------
    # Automatically assigned GradeScale
    # -------------------------------------------------

    grade = models.ForeignKey(
        GradeScale,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    # -------------------------------------------------
    # CBC result
    # -------------------------------------------------

    cbc_code = models.CharField(
        max_length=5,
        blank=True,
    )

    cbc_description = models.CharField(
        max_length=100,
        blank=True,
    )

    # -------------------------------------------------
    # Teacher remarks
    # -------------------------------------------------

    remarks = models.CharField(
        max_length=255,
        blank=True,
    )

    # -------------------------------------------------
    # User who originally entered the result
    # -------------------------------------------------

    entered_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entered_marks",
    )

    # -------------------------------------------------
    # User who last modified the result
    # -------------------------------------------------

    last_modified_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="modified_results",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        unique_together = (
            "submission",
            "student",
        )

        ordering = [
            "student",
        ]

    def __str__(self):

        if self.status == self.ResultStatus.PRESENT:
            return (
                f"{self.student} - "
                f"{self.marks}"
            )

        return (
            f"{self.student} - "
            f"{self.status}"
        )


# =====================================================
# FINAL SUBJECT RESULT
# =====================================================

class StudentResult(models.Model):

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="final_results",
    )

    classroom = models.ForeignKey(
        ClassRoom,
        on_delete=models.CASCADE,
        related_name="student_results",
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="student_results",
    )

    academic_year = models.CharField(
        max_length=20,
    )

    term = models.CharField(
        max_length=20,
        choices=TERM_CHOICES,
    )

    # -------------------------------------------------
    # Total score
    # -------------------------------------------------

    total_score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
    )

    # -------------------------------------------------
    # Average percentage
    # -------------------------------------------------

    average_score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
    )

    grade = models.ForeignKey(
        GradeScale,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    cbc_code = models.CharField(
        max_length=5,
        blank=True,
    )

    cbc_description = models.CharField(
        max_length=100,
        blank=True,
    )

    # -------------------------------------------------
    # Subject teacher comment
    # -------------------------------------------------

    teacher_comment = models.TextField(
        blank=True,
    )

    # -------------------------------------------------
    # Report-card comments
    # -------------------------------------------------

    class_teacher_comment = models.TextField(
        blank=True,
    )

    headteacher_comment = models.TextField(
        blank=True,
    )

    # -------------------------------------------------
    # Subject position
    # -------------------------------------------------

    subject_position = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    # -------------------------------------------------
    # Subject statistics
    # -------------------------------------------------

    highest_score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
    )

    lowest_score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
    )

    class_average = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
    )

    learners_assessed = models.PositiveIntegerField(
        default=0,
    )

    generated_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        unique_together = (
            "student",
            "subject",
            "term",
            "academic_year",
        )

        ordering = [
            "student",
            "subject",
        ]

    def __str__(self):
        return (
            f"{self.student} - "
            f"{self.subject}"
        )


# =====================================================
# STUDENT TERM RESULT
# =====================================================

class StudentTermResult(models.Model):

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="term_results",
    )

    classroom = models.ForeignKey(
        ClassRoom,
        on_delete=models.CASCADE,
        related_name="term_results",
    )

    academic_year = models.CharField(
        max_length=20,
    )

    term = models.CharField(
        max_length=20,
        choices=TERM_CHOICES,
    )

    # -------------------------------------------------
    # Overall term marks
    # -------------------------------------------------

    total_marks = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
    )

    average_marks = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
    )

    overall_grade = models.ForeignKey(
        GradeScale,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="overall_results",
    )

    cbc_code = models.CharField(
        max_length=5,
        blank=True,
    )

    cbc_description = models.CharField(
        max_length=100,
        blank=True,
    )

    # -------------------------------------------------
    # Class position
    # -------------------------------------------------

    position = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    # -------------------------------------------------
    # Number of subjects
    # -------------------------------------------------

    total_subjects = models.PositiveIntegerField(
        default=0,
    )

    # -------------------------------------------------
    # Attendance
    # -------------------------------------------------

    attendance_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    # -------------------------------------------------
    # Comments
    # -------------------------------------------------

    teacher_comment = models.TextField(
        blank=True,
        help_text="Subject teacher's comment",
    )

    class_teacher_comment = models.TextField(
        blank=True,
    )

    headteacher_comment = models.TextField(
        blank=True,
    )

    generated_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        unique_together = (
            "student",
            "academic_year",
            "term",
        )

        ordering = [
            "student",
        ]

    def __str__(self):
        return (
            f"{self.student} - "
            f"{self.term} "
            f"({self.academic_year})"
        )


# =====================================================
# AUTOMATIC REPORT COMMENTS
# =====================================================

class ReportComment(models.Model):

    grade = models.ForeignKey(
        GradeScale,
        on_delete=models.CASCADE,
        related_name="comments",
    )

    comment = models.TextField()

    def __str__(self):
        return self.grade.level


# =====================================================
# ASSESSMENT RUBRIC
# =====================================================

class AssessmentRubric(models.Model):

    min_score = models.PositiveIntegerField()

    max_score = models.PositiveIntegerField()

    code = models.CharField(
        max_length=5,
    )

    description = models.CharField(
        max_length=100,
    )

    order = models.PositiveIntegerField()

    class Meta:
        ordering = [
            "order",
        ]

    def __str__(self):
        return (
            f"{self.code} - "
            f"{self.description}"
        )