from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.models import ParentProfile
from students.models import Student
from students.serializers import StudentSerializer


class ParentChildrenViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        user = self.request.user

        # =====================================================
        # SUPER ADMIN / ACCOUNTANT / ACADEMIC COORDINATOR
        # =====================================================

        if user.role in [
            user.Role.SUPER_ADMIN,
            user.Role.ACCOUNTANT,
            user.Role.ACADEMIC_COORDINATOR,
        ]:
            return Student.objects.select_related(
                "parent__user",
                "classroom",
            )

        # =====================================================
        # TEACHER
        # =====================================================
        # Teachers can only see students belonging to classrooms
        # they are actively assigned to.

        if user.role == user.Role.TEACHER:

            from assignments.models import TeacherAssignment

            teacher_profile = getattr(
                user,
                "teacher_profile",
                None,
            )

            if not teacher_profile:
                return Student.objects.none()

            classroom_ids = TeacherAssignment.objects.filter(
                teacher=teacher_profile,
                is_active=True,
            ).values_list(
                "classroom_id",
                flat=True,
            )

            return Student.objects.filter(
                classroom_id__in=classroom_ids
            ).select_related(
                "parent__user",
                "classroom",
            )

        # =====================================================
        # PARENT
        # =====================================================
        # Parents can ONLY see their own children.

        parent = ParentProfile.objects.filter(
            user=user
        ).first()

        if not parent:
            return Student.objects.none()

        return Student.objects.filter(
            parent=parent
        ).select_related(
            "parent__user",
            "classroom",
        )