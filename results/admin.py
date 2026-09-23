from django.contrib import admin

from .models import (
    GradeScale,
    LearningOutcome,
    AssessmentType,
    Assessment,
    ResultSubmission,
    Result,
    StudentResult,
    StudentTermResult,
    ReportComment,
)


# =====================================================
# GRADE SCALE
# =====================================================

@admin.register(GradeScale)
class GradeScaleAdmin(admin.ModelAdmin):

    list_display = (
        "level",
        "description",
        "minimum_score",
        "maximum_score",
        "remarks",
        "created_at",
    )

    search_fields = (
        "level",
        "description",
    )

    ordering = (
        "-minimum_score",
    )


# =====================================================
# LEARNING OUTCOME
# =====================================================

@admin.register(LearningOutcome)
class LearningOutcomeAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "subject",
        "maximum_marks",
        "is_active",
        "created_at",
    )

    list_filter = (
        "subject",
        "is_active",
    )

    search_fields = (
        "name",
        "description",
        "subject__name",
    )

    ordering = (
        "subject",
        "name",
    )


# =====================================================
# ASSESSMENT TYPE
# =====================================================

@admin.register(AssessmentType)
class AssessmentTypeAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "name",
    )

    ordering = (
        "name",
    )


# =====================================================
# ASSESSMENT
# =====================================================

@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):

    list_display = (
        "assessment_type",
        "subject",
        "classroom",
        "academic_year",
        "term",
        "total_marks",
        "assessment_date",
        "created_by",
        "created_at",
    )

    list_filter = (
        "academic_year",
        "term",
        "subject",
        "classroom",
        "assessment_date",
    )

    search_fields = (
        "assessment_type",
        "subject__name",
        "classroom__name",
        "academic_year",
    )

    ordering = (
        "-assessment_date",
        "-created_at",
    )


# =====================================================
# RESULT SUBMISSION
# =====================================================

@admin.register(ResultSubmission)
class ResultSubmissionAdmin(admin.ModelAdmin):

    list_display = (
        "assessment",
        "submitted_by",
        "approval_status",
        "submitted_at",
        "approved_by",
        "approved_at",
        "created_at",
    )

    list_filter = (
        "approval_status",
        "submitted_at",
        "approved_at",
    )

    search_fields = (
        "assessment__assessment_type",
        "assessment__subject__name",
        "submitted_by__username",
        "approved_by__username",
    )

    ordering = (
        "-created_at",
    )


# =====================================================
# RESULT
# =====================================================

@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):

    list_display = (
        "student",
        "submission",
        "status",
        "marks",
        "weighted_marks",
        "grade",
        "cbc_code",
        "entered_by",
        "updated_at",
    )

    list_filter = (
        "status",
        "grade",
        "cbc_code",
    )

    search_fields = (
        "student__first_name",
        "student__last_name",
        "student__admission_number",
        "cbc_code",
        "cbc_description",
    )

    ordering = (
        "student__first_name",
        "student__last_name",
    )


# =====================================================
# STUDENT RESULT
# =====================================================

@admin.register(StudentResult)
class StudentResultAdmin(admin.ModelAdmin):

    list_display = (
        "student",
        "classroom",
        "subject",
        "academic_year",
        "term",
        "total_score",
        "average_score",
        "grade",
        "subject_position",
        "class_average",
        "learners_assessed",
    )

    list_filter = (
        "academic_year",
        "term",
        "subject",
        "classroom",
        "grade",
    )

    search_fields = (
        "student__first_name",
        "student__last_name",
        "student__admission_number",
        "subject__name",
    )

    ordering = (
        "academic_year",
        "term",
        "subject",
        "subject_position",
    )


# =====================================================
# STUDENT TERM RESULT
# =====================================================

@admin.register(StudentTermResult)
class StudentTermResultAdmin(admin.ModelAdmin):

    list_display = (
        "student",
        "classroom",
        "academic_year",
        "term",
        "total_marks",
        "average_marks",
        "overall_grade",
        "position",
        "total_subjects",
        "attendance_percentage",
        "generated_at",
    )

    list_filter = (
        "academic_year",
        "term",
        "classroom",
        "overall_grade",
    )

    search_fields = (
        "student__first_name",
        "student__last_name",
        "student__admission_number",
    )

    ordering = (
        "academic_year",
        "term",
        "position",
    )


# =====================================================
# REPORT COMMENTS
# =====================================================

@admin.register(ReportComment)
class ReportCommentAdmin(admin.ModelAdmin):

    list_display = (
        "grade",
        "comment",
    )

    list_filter = (
        "grade",
    )

    search_fields = (
        "grade__level",
        "comment",
    )