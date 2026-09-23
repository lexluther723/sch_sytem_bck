from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    GradeScaleViewSet,
    AssessmentTypeViewSet,
    AssessmentViewSet,
    LearningOutcomeViewSet,
    ResultSubmissionViewSet,
    ResultViewSet,
    StudentResultViewSet,
    StudentTermResultViewSet,
    ReportCommentViewSet,
    StudentReportCardAPIView,
)


# =====================================================
# API ROUTER
# =====================================================

router = DefaultRouter()


# -----------------------------------------------------
# Grade Scales
# -----------------------------------------------------

router.register(
    r"grade-scales",
    GradeScaleViewSet,
    basename="grade-scale",
)


# -----------------------------------------------------
# Assessment Types
# -----------------------------------------------------

router.register(
    r"assessment-types",
    AssessmentTypeViewSet,
    basename="assessment-type",
)


# -----------------------------------------------------
# Assessments
# -----------------------------------------------------

router.register(
    r"assessments",
    AssessmentViewSet,
    basename="assessment",
)


# -----------------------------------------------------
# Learning Outcomes
# -----------------------------------------------------

router.register(
    r"learning-outcomes",
    LearningOutcomeViewSet,
    basename="learning-outcome",
)


# -----------------------------------------------------
# Result Submissions
# -----------------------------------------------------

router.register(
    r"result-submissions",
    ResultSubmissionViewSet,
    basename="result-submission",
)


# -----------------------------------------------------
# Individual Results
# -----------------------------------------------------

router.register(
    r"results",
    ResultViewSet,
    basename="result",
)


# -----------------------------------------------------
# Final Student Subject Results
# -----------------------------------------------------

router.register(
    r"student-results",
    StudentResultViewSet,
    basename="student-result",
)


# -----------------------------------------------------
# Final Student Term Results
# -----------------------------------------------------

router.register(
    r"student-term-results",
    StudentTermResultViewSet,
    basename="student-term-result",
)


# -----------------------------------------------------
# Report Comments
# -----------------------------------------------------

router.register(
    r"report-comments",
    ReportCommentViewSet,
    basename="report-comment",
)


# =====================================================
# URL PATTERNS
# =====================================================

urlpatterns = [

    # -----------------------------------------------
    # All ViewSet APIs
    # -----------------------------------------------

    path(
        "",
        include(router.urls)
    ),


    # -----------------------------------------------
    # Student Report Card
    #
    # Example:
    #
    # /api/results/report-card/12/2026/Term%201/
    #
    # -----------------------------------------------

    path(
        "report-card/<int:student_id>/<str:academic_year>/<str:term>/",
        StudentReportCardAPIView.as_view(),
        name="student-report-card",
    ),
]