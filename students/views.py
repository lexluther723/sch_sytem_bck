from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404

from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework import status
from rest_framework.filters import SearchFilter, OrderingFilter

from accounts.models import CustomUser, ParentProfile, TeacherProfile
from accounts.serializers import UserSerializer

from students.models import Student, StudentTransfer
from students.serializers import (
    StudentSerializer,
    StudentListSerializer,
    StudentTransferSerializer,
)

from core.pagination import (
    StandardResultsSetPagination,
    paginate_queryset_response,
)


# =====================================================
# SECURITY
# =====================================================

class IsAdminOrCoordinatorForStudents(BasePermission):
    """
    Student records are managed by Super Admin /
    Academic Coordinator only.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in [
                CustomUser.Role.SUPER_ADMIN,
                CustomUser.Role.ACADEMIC_COORDINATOR,
            ]
        )


class IsAdminCoordinatorOrAccountant(BasePermission):
    """
    Student transfer records are viewable by Super Admin, Academic
    Coordinator, and Accountant (accountants need transfer history
    for fee-structure changes between classrooms).
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in [
                CustomUser.Role.SUPER_ADMIN,
                CustomUser.Role.ACADEMIC_COORDINATOR,
                CustomUser.Role.ACCOUNTANT,
            ]
        )


def _teacher_classroom_ids(user):
    """
    Return classroom IDs that this teacher is actively
    assigned to teach.
    """

    from assignments.models import TeacherAssignment

    try:
        teacher_profile = user.teacher_profile
    except TeacherProfile.DoesNotExist:
        return []

    return list(
        TeacherAssignment.objects.filter(
            teacher=teacher_profile,
            is_active=True,
        ).values_list(
            "classroom_id",
            flat=True,
        )
    )


# =====================================================
# STUDENT LIST
# GET /api/students/
# =====================================================

# =====================================================
# STUDENT LIST
# GET /api/students/
#
# BEFORE: a plain APIView that built the full queryset, evaluated
# it completely, and returned every matching row in one Response —
# no pagination at all, and `classroom__class_teacher__user` was
# NOT in select_related even though `StudentListSerializer` reads
# `obj.classroom.class_teacher.user` for every row (an N+1: one
# extra query per student just to resolve the class teacher's name).
#
# AFTER: a `generics.ListAPIView`, which means:
#   - Pagination is automatic (project default from settings.py) —
#     a school with 800 students now returns 25 at a time instead
#     of 800 fully-serialized rows per request.
#   - `select_related` now covers the FK chain the serializer
#     actually walks, so listing 25 students is a small constant
#     number of queries, not 25+ extra ones for class teachers.
#   - Filtering/search move to declared `filter_backends` so they
#     compose with pagination and ordering for free instead of
#     being hand-rolled per view.
# =====================================================

class StudentListView(generics.ListAPIView):

    serializer_class = StudentListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = [
        "first_name",
        "last_name",
        "admission_number",
        "assessment_number",
    ]
    ordering_fields = [
        "first_name",
        "last_name",
        "admission_number",
        "created_at",
    ]

    def get_queryset(self):
        user = self.request.user

        base_qs = Student.objects.select_related(
            "parent__user",
            "classroom",
            "classroom__class_teacher__user",
        )

        # ---------------------------------------------
        # SUPER ADMIN / ACADEMIC COORDINATOR / ACCOUNTANT
        # ---------------------------------------------
        if user.role in [
            CustomUser.Role.SUPER_ADMIN,
            CustomUser.Role.ACADEMIC_COORDINATOR,
            CustomUser.Role.ACCOUNTANT,
        ]:
            students = base_qs.all()

        # ---------------------------------------------
        # TEACHER
        # ---------------------------------------------
        elif user.role == CustomUser.Role.TEACHER:
            students = base_qs.filter(
                classroom_id__in=_teacher_classroom_ids(user)
            )

        # ---------------------------------------------
        # PARENT
        # ---------------------------------------------
        elif user.role == CustomUser.Role.PARENT:
            parent_profile = ParentProfile.objects.filter(
                user=user
            ).first()

            if parent_profile:
                students = base_qs.filter(parent=parent_profile)
            else:
                students = Student.objects.none()

        # ---------------------------------------------
        # UNKNOWN ROLE
        # ---------------------------------------------
        else:
            students = Student.objects.none()

        # =================================================
        # EXTRA FILTERS (kept as explicit query params rather
        # than DjangoFilterBackend filterset_fields, since they
        # map 1:1 onto model fields with no extra logic needed —
        # adding a FilterSet class here would be pure boilerplate)
        # =================================================
        classroom_id = self.request.query_params.get("classroom")
        status_param = self.request.query_params.get("status")
        gender_param = self.request.query_params.get("gender")

        if classroom_id:
            students = students.filter(classroom_id=classroom_id)

        if status_param:
            students = students.filter(status=status_param)

        if gender_param:
            students = students.filter(gender=gender_param)

        return students


# =====================================================
# STUDENT DETAIL
# GET /api/students/<pk>/
# =====================================================

class StudentDetailView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):

        student = get_object_or_404(
            Student.objects.select_related(
                "parent__user",
                "classroom",
            ),
            pk=pk,
        )

        user = request.user

        # ---------------------------------------------
        # ADMIN / COORDINATOR / ACCOUNTANT
        # ---------------------------------------------

        allowed = user.role in [
            CustomUser.Role.SUPER_ADMIN,
            CustomUser.Role.ACADEMIC_COORDINATOR,
            CustomUser.Role.ACCOUNTANT,
        ]

        # ---------------------------------------------
        # TEACHER
        # ---------------------------------------------

        if not allowed and user.role == CustomUser.Role.TEACHER:
            allowed = (
                student.classroom_id
                in _teacher_classroom_ids(user)
            )

        # ---------------------------------------------
        # PARENT
        # ---------------------------------------------

        if not allowed and user.role == CustomUser.Role.PARENT:

            parent_profile = ParentProfile.objects.filter(
                user=user
            ).first()

            allowed = bool(
                parent_profile
                and student.parent_id == parent_profile.id
            )

        if not allowed:
            return Response(
                {
                    "error": (
                        "You do not have permission to view "
                        "this student."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = StudentSerializer(
            student,
            context={"request": request},
        )

        return Response(serializer.data)


# =====================================================
# CREATE STUDENT
# POST /api/students/create/
# =====================================================

class StudentCreateView(APIView):

    permission_classes = [
        IsAdminOrCoordinatorForStudents
    ]

    def post(self, request):

        serializer = StudentSerializer(
            data=request.data,
            context={"request": request},
        )

        serializer.is_valid(raise_exception=True)

        student = serializer.save()

        return Response(
            StudentSerializer(
                student,
                context={"request": request},
            ).data,
            status=status.HTTP_201_CREATED,
        )


# =====================================================
# UPDATE STUDENT
# PUT/PATCH /api/students/update/<pk>/
# =====================================================

class StudentUpdateView(APIView):

    permission_classes = [
        IsAdminOrCoordinatorForStudents
    ]

    def put(self, request, pk):

        student = get_object_or_404(
            Student,
            pk=pk,
        )

        serializer = StudentSerializer(
            student,
            data=request.data,
            context={"request": request},
        )

        serializer.is_valid(raise_exception=True)

        student = serializer.save()

        return Response(
            StudentSerializer(
                student,
                context={"request": request},
            ).data
        )

    def patch(self, request, pk):

        student = get_object_or_404(
            Student,
            pk=pk,
        )

        serializer = StudentSerializer(
            student,
            data=request.data,
            partial=True,
            context={"request": request},
        )

        serializer.is_valid(raise_exception=True)

        student = serializer.save()

        return Response(
            StudentSerializer(
                student,
                context={"request": request},
            ).data
        )


# =====================================================
# DELETE STUDENT
# DELETE /api/students/delete/<pk>/
# =====================================================

class StudentDeleteView(APIView):

    permission_classes = [
        IsAdminOrCoordinatorForStudents
    ]

    def delete(self, request, pk):

        student = get_object_or_404(
            Student,
            pk=pk,
        )

        student.delete()

        return Response(
            {
                "message": "Student deleted successfully."
            },
            status=status.HTTP_204_NO_CONTENT,
        )


# =====================================================
# STUDENT TRANSFER
# POST /api/students/transfer/
# =====================================================

class StudentTransferView(APIView):

    permission_classes = [
        IsAdminOrCoordinatorForStudents
    ]

    @transaction.atomic
    def post(self, request):

        serializer = StudentTransferSerializer(
            data=request.data,
            context={"request": request},
        )

        serializer.is_valid(raise_exception=True)

        transfer = serializer.save(
            transferred_by=request.user
        )

        student = transfer.student

        student.classroom = transfer.to_classroom

        student.save(
            update_fields=[
                "classroom",
                "updated_at",
            ]
        )

        return Response(
            StudentTransferSerializer(
                transfer,
                context={"request": request},
            ).data,
            status=status.HTTP_201_CREATED,
        )


# =====================================================
# TRANSFER LIST
# GET /api/students/transfers/
# =====================================================

# BEFORE: unpaginated APIView returning every transfer ever recorded.
# AFTER: paginated ListAPIView; permission check moved to a real
# permission class so it's testable/reusable instead of inlined.
class StudentTransferListView(generics.ListAPIView):

    serializer_class = StudentTransferSerializer
    permission_classes = [IsAdminCoordinatorOrAccountant]
    pagination_class = StandardResultsSetPagination
    filter_backends = [OrderingFilter]
    ordering_fields = ["transfer_date", "created_at"]

    def get_queryset(self):
        return StudentTransfer.objects.select_related(
            "student",
            "from_classroom",
            "to_classroom",
            "transferred_by",
        )


# =====================================================
# TRANSFER DETAIL
# GET /api/students/transfers/<pk>/
# =====================================================

class StudentTransferDetailView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):

        if request.user.role not in [
            CustomUser.Role.SUPER_ADMIN,
            CustomUser.Role.ACADEMIC_COORDINATOR,
            CustomUser.Role.ACCOUNTANT,
        ]:
            return Response(
                {
                    "error": (
                        "You do not have permission "
                        "to view transfers."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        transfer = get_object_or_404(
            StudentTransfer.objects.select_related(
                "student",
                "from_classroom",
                "to_classroom",
                "transferred_by",
            ),
            pk=pk,
        )

        serializer = StudentTransferSerializer(
            transfer,
            context={"request": request},
        )

        return Response(serializer.data)


# =====================================================
# PARENT CHILDREN
# GET /api/students/parent/children/
# =====================================================

class ParentChildrenView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        parent = ParentProfile.objects.filter(
            user=request.user
        ).first()

        if not parent:
            return Response(
                {
                    "children_count": 0,
                    "children": [],
                    "message": "Parent profile not found.",
                },
                status=status.HTTP_200_OK,
            )

        children = (
            Student.objects
            .filter(parent=parent)
            .select_related(
                "parent",
                "parent__user",
                "classroom",
                "classroom__class_teacher__user",
            )
            .order_by(
                "first_name",
                "last_name",
            )
        )

        # A parent typically has a handful of children, so this
        # doesn't strictly need pagination the way a school-wide
        # student list does — but we avoid the previous double
        # query (one implicit query to serialize `children`, then a
        # SEPARATE `.count()` query) by evaluating the queryset once
        # into a list and reusing that both for serialization and
        # the count.
        children = list(children)

        serializer = StudentListSerializer(
            children,
            many=True,
            context={"request": request},
        )

        return Response(
            {
                "parent_id": parent.id,
                "children_count": len(children),
                "children": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


# =====================================================
# MY STUDENT RECORD
# GET /api/students/me/
# =====================================================

class MyStudentRecordView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        user = request.user

        if user.role != CustomUser.Role.STUDENT:
            return Response(
                {
                    "error": (
                        "This endpoint is only for "
                        "student accounts."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        student = (
            Student.objects
            .select_related(
                "parent__user",
                "classroom",
                "classroom__class_teacher__user",
            )
            .filter(user=user)
            .first()
        )

        if not student:
            return Response(
                {
                    "linked": False,
                    "message": (
                        "Your login account has not been "
                        "linked to a classroom yet. Please "
                        "contact the academic coordinator."
                    ),
                },
                status=status.HTTP_200_OK,
            )

        serializer = StudentSerializer(
            student,
            context={"request": request},
        )

        data = serializer.data
        data["linked"] = True

        return Response(
            data,
            status=status.HTTP_200_OK,
        )


# =====================================================
# UNLINKED STUDENT LOGIN ACCOUNTS
# GET /api/students/unlinked-users/
# =====================================================

class UnlinkedStudentUsersView(APIView):

    permission_classes = [
        IsAdminOrCoordinatorForStudents
    ]

    def get(self, request):

        users = (
            CustomUser.objects
            .filter(
                role=CustomUser.Role.STUDENT,
                student_record__isnull=True,
            )
            # .only(): fetch exactly the columns UserSerializer
            # reads (see accounts/serializers.py) instead of every
            # column on CustomUser (password hash, last_login,
            # is_staff/is_superuser, groups, etc.) for every row.
            # Listing fewer than the serializer needs would just
            # trigger a silent extra query per missing field per
            # row when DRF accesses it — so this set must match the
            # serializer's `fields`, not be a smaller "convenient"
            # subset.
            .only(
                "id",
                "username",
                "first_name",
                "last_name",
                "email",
                "phone_number",
                "role",
                "profile_picture",
                "is_active",
                "created_at",
            )
            .order_by(
                "first_name",
                "last_name",
                "username",
            )
        )

        # Plain APIView -> not covered by the global pagination
        # setting, so we paginate explicitly. This list is usually
        # small (accounts waiting to be linked), but "usually small"
        # is exactly the kind of assumption that breaks once a
        # school does a bulk account import.
        paginated = paginate_queryset_response(
            self, users, UserSerializer
        )
        if paginated is not None:
            return paginated

        return Response(UserSerializer(users, many=True).data)