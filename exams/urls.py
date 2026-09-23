from django.urls import path

from .views import (
    ExamCreateView,
    ExamListView,
    ExamDetailView,
    ExamUpdateView,
    ExamDeleteView,
)

urlpatterns = [
    # =====================================
    # Create Exam
    # =====================================
    path(
        "create/",
        ExamCreateView.as_view(),
        name="exam-create",
    ),

    # =====================================
    # List Exams
    # =====================================
    path(
        "",
        ExamListView.as_view(),
        name="exam-list",
    ),

    # =====================================
    # Retrieve Exam
    # =====================================
    path(
        "<int:pk>/",
        ExamDetailView.as_view(),
        name="exam-detail",
    ),

    # =====================================
    # Update Exam
    # =====================================
    path(
        "update/<int:pk>/",
        ExamUpdateView.as_view(),
        name="exam-update",
    ),

    # =====================================
    # Delete Exam
    # =====================================
    path(
        "delete/<int:pk>/",
        ExamDeleteView.as_view(),
        name="exam-delete",
    ),
]