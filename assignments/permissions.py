from rest_framework.permissions import BasePermission

from .models import TeacherAssignment


# =====================================================
# Assigned Class Teacher Permission
# =====================================================
class IsAssignedClassTeacher(BasePermission):
    """
    Allows access only to the assigned class teacher.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):

        if not hasattr(request.user, "teacher_profile"):
            return False

        return TeacherAssignment.objects.filter(
            teacher=request.user.teacher_profile,
            classroom=obj.classroom,
            is_class_teacher=True,
            is_active=True,
        ).exists()


# =====================================================
# Assigned Subject Teacher Permission
# =====================================================
class IsAssignedSubjectTeacher(BasePermission):
    """
    Allows access only to the assigned subject teacher.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):

        if not hasattr(request.user, "teacher_profile"):
            return False

        return TeacherAssignment.objects.filter(
            teacher=request.user.teacher_profile,
            classroom=obj.classroom,
            subject=obj.subject,
            is_active=True,
        ).exists()