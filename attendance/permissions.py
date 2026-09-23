from rest_framework.permissions import BasePermission

from assignments.models import TeacherAssignment
from accounts.models import CustomUser


class IsAssignedClassTeacher(BasePermission):
    """
    Attendance permission.

    Allows:

    - Super Admin
    - Academic Coordinator
    - Teacher who is an active class teacher

    TeacherAssignment logic is NOT changed.
    """

    def has_permission(self, request, view):

        # ====================================================
        # AUTHENTICATION
        # ====================================================

        if not request.user.is_authenticated:
            return False

        # ====================================================
        # SUPER ADMIN
        # ====================================================

        if request.user.role == CustomUser.Role.SUPER_ADMIN:
            return True

        # ====================================================
        # ACADEMIC COORDINATOR
        # ====================================================

        if (
            request.user.role
            == CustomUser.Role.ACADEMIC_COORDINATOR
        ):
            return True

        # ====================================================
        # TEACHER ONLY
        # ====================================================

        if request.user.role != CustomUser.Role.TEACHER:
            return False

        # ====================================================
        # TEACHER PROFILE
        # ====================================================

        try:
            teacher_profile = request.user.teacher_profile
        except Exception:
            return False

        # ====================================================
        # CREATE ENDPOINT
        #
        # /attendance/create/
        #
        # receives:
        #
        # {
        #     "assignment": 3
        # }
        #
        # Object verification happens in the view.
        # ====================================================

        if view.__class__.__name__ == (
            "AttendanceSubmissionCreateView"
        ):

            return True

        # ====================================================
        # MARK ENDPOINT
        #
        # Verification happens in the view using
        # submission -> assignment -> teacher.
        # ====================================================

        if view.__class__.__name__ == (
            "MarkAttendanceView"
        ):

            return True

        # ====================================================
        # SUBMIT ENDPOINT
        #
        # Kept for backwards compatibility.
        # The application no longer needs a separate
        # submit step.
        # ====================================================

        if view.__class__.__name__ == (
            "SubmitAttendanceView"
        ):

            return True

        # ====================================================
        # HISTORY
        # ====================================================

        if view.__class__.__name__ == (
            "TeacherAttendanceHistoryView"
        ):

            return TeacherAssignment.objects.filter(
                teacher=teacher_profile,
                is_active=True,
                is_class_teacher=True,
            ).exists()

        # ====================================================
        # DEFAULT
        # ====================================================

        return True