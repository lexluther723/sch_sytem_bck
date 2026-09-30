from django.db.models import Count
from rest_framework import generics, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import ClassRoom
from .serializers import ClassRoomSerializer
from accounts.permisions import IsAdminOrAcademicCoordinator


class ClassRoomListView(generics.ListAPIView):
    # annotate() computes every classroom's student count in the SAME
    # query as the list itself - one query total, instead of one extra
    # COUNT per classroom in the serializer.
    queryset = ClassRoom.objects.select_related(
        "class_teacher",
        "class_teacher__user",
    ).annotate(
        student_count=Count("students", distinct=True),
    ).order_by("-created_at")

    serializer_class = ClassRoomSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = [
        "grade",
        "stream",
    ]

    search_fields = [
        "grade",
        "stream",
        "class_teacher__user__first_name",
        "class_teacher__user__last_name",
    ]

    ordering_fields = [
        "grade",
        "stream",
        "capacity",
        "created_at",
    ]


# class ClassRoomDetailView(generics.RetrieveAPIView):
#     queryset = ClassRoom.objects.select_related(
#         "class_teacher",
#         "class_teacher__user",
#     ).annotate(
#         student_count=Count("students", distinct=True),
#     )

#     serializer_class = ClassRoomSerializer
#     permission_classes = [IsAuthenticated]

class ClassRoomDetailView(generics.RetrieveUpdateAPIView):
    """
    GET/PUT/PATCH /api/classes/<id>/
    Update also available at /api/classes/update/<id>/.
    """
    queryset = ClassRoom.objects.select_related(
        "class_teacher",
        "class_teacher__user",
    ).annotate(
        student_count=Count("students", distinct=True),
    )

    serializer_class = ClassRoomSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        # Anyone authenticated can read; only admin/coordinator can update
        if self.request.method in ("PUT", "PATCH"):
            return [IsAdminOrAcademicCoordinator()]
        return [IsAuthenticated()]


class ClassRoomCreateView(generics.CreateAPIView):
    queryset = ClassRoom.objects.all()

    serializer_class = ClassRoomSerializer

    permission_classes = [
        IsAdminOrAcademicCoordinator
    ]


class ClassRoomUpdateView(generics.UpdateAPIView):
    queryset = ClassRoom.objects.select_related(
        "class_teacher",
        "class_teacher__user",
    )

    serializer_class = ClassRoomSerializer

    permission_classes = [
        IsAdminOrAcademicCoordinator
    ]

    # Allows both PUT and PATCH
    http_method_names = [
        "put",
        "patch",
        "options",
        "head",
    ]


class ClassRoomDeleteView(generics.DestroyAPIView):
    queryset = ClassRoom.objects.all()

    serializer_class = ClassRoomSerializer

    permission_classes = [
        IsAdminOrAcademicCoordinator
    ]

    http_method_names = [
        "delete",
        "options",
        "head",
    ]