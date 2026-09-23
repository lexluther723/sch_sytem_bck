from rest_framework import generics

from .models import Exam
from .serializers import ExamSerializer
from accounts.permisions import IsAdminOrAcademicCoordinator


# =====================================================
# CREATE
# =====================================================

class ExamCreateView(generics.CreateAPIView):
    queryset = Exam.objects.select_related(
        "classroom",
        "subject",
    )

    serializer_class = ExamSerializer

    permission_classes = [
        IsAdminOrAcademicCoordinator
    ]


# =====================================================
# LIST
# =====================================================

class ExamListView(generics.ListAPIView):
    queryset = Exam.objects.select_related(
        "classroom",
        "subject",
    )

    serializer_class = ExamSerializer

    permission_classes = [
        IsAdminOrAcademicCoordinator
    ]


# =====================================================
# DETAIL
# =====================================================

class ExamDetailView(generics.RetrieveAPIView):
    queryset = Exam.objects.select_related(
        "classroom",
        "subject",
    )

    serializer_class = ExamSerializer

    permission_classes = [
        IsAdminOrAcademicCoordinator
    ]


# =====================================================
# UPDATE
# =====================================================

class ExamUpdateView(generics.UpdateAPIView):
    queryset = Exam.objects.select_related(
        "classroom",
        "subject",
    )

    serializer_class = ExamSerializer

    permission_classes = [
        IsAdminOrAcademicCoordinator
    ]


# =====================================================
# DELETE
# =====================================================

class ExamDeleteView(generics.DestroyAPIView):
    queryset = Exam.objects.select_related(
        "classroom",
        "subject",
    )

    serializer_class = ExamSerializer

    permission_classes = [
        IsAdminOrAcademicCoordinator
    ]