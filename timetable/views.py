from django.shortcuts import render
from rest_framework import generics, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend  # ✅ Added

from .models import Timetable
from .serializers import TimetableSerializer
from accounts.permisions import IsAdminOrAcademicCoordinator


# List Timetable (active only, full search/filter/sort)
class TimetableListView(generics.ListAPIView):
    queryset = Timetable.objects.select_related(
        "assignment",
        "assignment__teacher",
        "assignment__teacher__user",
        "assignment__subject",
        "assignment__classroom",
    ).filter(is_active=True)  # ✅ Only active timetables

    serializer_class = TimetableSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]  # ✅ Added DjangoFilterBackend

    filterset_fields = [
        "academic_year",
        "term",
        "day",
        "assignment__teacher",
        "assignment__classroom",
        "assignment__subject",
    ]

    search_fields = [
        "assignment__teacher__user__first_name",
        "assignment__teacher__user__last_name",
        "assignment__subject__name",
        "assignment__classroom__grade",
        "assignment__classroom__stream",
        "day",
        "term",
        "academic_year",
    ]

    ordering_fields = ["day", "start_time", "end_time", "academic_year"]
    ordering = ["day", "start_time"]  # ✅ Default sensible ordering


# Retrieve single Timetable entry
class TimetableDetailView(generics.RetrieveAPIView):
    queryset = Timetable.objects.select_related(
        "assignment", "assignment__teacher", "assignment__teacher__user",
        "assignment__subject", "assignment__classroom"
    )
    serializer_class = TimetableSerializer
    permission_classes = [IsAuthenticated]


# Create Timetable (Coordinator/Admin only)
class TimetableCreateView(generics.CreateAPIView):
    queryset = Timetable.objects.all()
    serializer_class = TimetableSerializer
    permission_classes = [IsAdminOrAcademicCoordinator]


# Update Timetable (Coordinator/Admin only)
class TimetableUpdateView(generics.UpdateAPIView):
    queryset = Timetable.objects.all()
    serializer_class = TimetableSerializer
    permission_classes = [IsAdminOrAcademicCoordinator]


# Delete Timetable (Coordinator/Admin only)
class TimetableDeleteView(generics.DestroyAPIView):
    queryset = Timetable.objects.all()
    serializer_class = TimetableSerializer
    permission_classes = [IsAdminOrAcademicCoordinator]


# Teacher: Get ONLY MY Timetable
class MyTimetableView(generics.ListAPIView):
    serializer_class = TimetableSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if not hasattr(self.request.user, "teacher_profile"):
            return Timetable.objects.none()  # Non-teachers get empty list

        return Timetable.objects.select_related(
            "assignment", "assignment__teacher", "assignment__teacher__user",
            "assignment__subject", "assignment__classroom"
        ).filter(
            assignment__teacher=self.request.user.teacher_profile,
            is_active=True
        ).order_by("day", "start_time")


# Get Timetable for specific Classroom
class ClassroomTimetableView(generics.ListAPIView):
    serializer_class = TimetableSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        classroom_id = self.kwargs["classroom_id"]
        return Timetable.objects.select_related(
            "assignment", "assignment__teacher", "assignment__teacher__user",
            "assignment__subject", "assignment__classroom"
        ).filter(
            assignment__classroom_id=classroom_id,
            is_active=True
        ).order_by("day", "start_time")