"""
Results permissions.

Role checks are re-exported from `core.permissions` (single source of
truth). The object-level "is this teacher actually assigned to this
classroom+subject?" logic stays here, because it is domain logic rather
than a role check.

BEHAVIOUR CHANGE - READ THIS
----------------------------
The old results.IsTeacher and results.IsAcademicCoordinator EXCLUDED
SUPER_ADMIN, while the identically-named classes in dashboard/ and
reports/ INCLUDED it. Super Admin is now admitted consistently. The
practical effect is that a Super Admin can submit/approve results,
which the surrounding code already assumed (every IsAssignedTeacher*
class below already had an explicit `is_super_admin(...) -> True`
fast path).
"""

from rest_framework.permissions import BasePermission

from core.permissions import (  # noqa: F401
    IsAccountant,
    IsCoordinator,
    IsCoordinator as IsAcademicCoordinator,
    IsCoordinator as IsAdminOrAcademicCoordinator,
    IsCoordinatorOrTeacher as IsTeacherOrAcademicCoordinator,
    IsSuperAdmin,
    IsTeacher,
    is_coordinator,
    is_super_admin,
    is_teacher,
)

# Legacy aliases used elsewhere in this app.
is_academic_coordinator = is_coordinator


def is_admin_or_coordinator_or_teacher(user):
    return is_coordinator(user) or is_teacher(user)


# ============================================================
# OBJECT-LEVEL: teacher assignment checks
# ============================================================

def _teacher_is_assigned(user, classroom, subject):
    """
    True if `user` is a teacher with an ACTIVE assignment to this
    classroom + subject.

    FIXED: the previous version omitted `is_active=True`, so a teacher
    whose assignment had been ended (is_active=False) could still edit
    marks for a class they no longer teach.
    """
    if classroom is None or subject is None:
        return False

    from assignments.models import TeacherAssignment

    return TeacherAssignment.objects.filter(
        teacher__user=user,
        classroom=classroom,
        subject=subject,
        is_active=True,
    ).exists()


def _teacher_is_assigned_to_result(user, result):
    """Resolve a Result -> its assessment -> classroom/subject."""
    assessment = getattr(getattr(result, "submission", None), "assessment", None)
    if assessment is None:
        return False
    return _teacher_is_assigned(user, assessment.classroom, assessment.subject)


class _AssignedTeacherBase(BasePermission):
    """
    Shared shape for the four assignment-scoped permissions:
    coordinators and Super Admin pass unconditionally; teachers must
    hold an active assignment for the object.
    """

    message = "You are not assigned to this classroom and subject."

    def has_permission(self, request, view):
        return is_admin_or_coordinator_or_teacher(request.user)

    def _object_allowed(self, user, obj):
        raise NotImplementedError

    def has_object_permission(self, request, view, obj):
        if is_coordinator(request.user):
            return True
        if not is_teacher(request.user):
            return False
        return self._object_allowed(request.user, obj)


class IsAssignedTeacher(_AssignedTeacherBase):
    def _object_allowed(self, user, result):
        return _teacher_is_assigned_to_result(user, result)


class IsAssignedTeacherObject(IsAssignedTeacher):
    """Alias kept for existing imports."""


class IsAssignedTeacherAssessment(_AssignedTeacherBase):
    def _object_allowed(self, user, assessment):
        return _teacher_is_assigned(user, assessment.classroom, assessment.subject)


class IsAssignedTeacherSubmission(_AssignedTeacherBase):
    def _object_allowed(self, user, submission):
        assessment = getattr(submission, "assessment", None)
        if assessment is None:
            return False
        return _teacher_is_assigned(user, assessment.classroom, assessment.subject)
