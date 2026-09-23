"""
Single source of truth for role-based permissions.

WHY THIS FILE EXISTS
--------------------
The same permission class names were defined independently in six
different apps, and the definitions DID NOT AGREE:

    fees.permissions.IsAccountant            -> ACCOUNTANT only
    reports.permissions.IsAccountant         -> SUPER_ADMIN + ACCOUNTANT
    results.permissions.IsTeacher            -> TEACHER only
    dashboard.permissions.IsTeacher          -> SUPER_ADMIN + TEACHER
    results.permissions.IsAcademicCoordinator      -> COORDINATOR only
    dashboard.permissions.IsAcademicCoordinator    -> SUPER_ADMIN + COORDINATOR

So whether a Super Admin could open a given screen depended on which
module the developer happened to import from. That is not a matrix
anyone can reason about, and it is not testable.

THE RULE ADOPTED HERE
---------------------
SUPER_ADMIN is the system owner and is implicitly allowed everywhere a
narrower staff role is allowed. Every class below follows that rule
consistently, and the class NAMES now state exactly who they admit, so
nobody has to open the file to know.

Names are explicit on purpose:
    IsSuperAdmin                  -> SUPER_ADMIN
    IsCoordinator                 -> SUPER_ADMIN + COORDINATOR
    IsAccountant                  -> SUPER_ADMIN + ACCOUNTANT
    IsTeacher                     -> SUPER_ADMIN + TEACHER
    IsParent                      -> PARENT              (never admin)
    IsStudent                     -> STUDENT             (never admin)
    IsCoordinatorOrTeacher        -> SUPER_ADMIN + COORDINATOR + TEACHER
    IsCoordinatorOrAccountant     -> SUPER_ADMIN + COORDINATOR + ACCOUNTANT
    IsStaff                       -> any non-parent, non-student role

IsParent / IsStudent deliberately EXCLUDE Super Admin, because they
guard "this is my own data" endpoints where an admin has a separate,
properly-scoped endpoint to use instead.
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from accounts.models import CustomUser


Role = CustomUser.Role


def role_of(user):
    """Return a user's role, or None for anonymous/roleless users."""
    if not user or not user.is_authenticated:
        return None
    return getattr(user, "role", None)


class HasRole(BasePermission):
    """
    Base class: allow the request if the user's role is in
    `allowed_roles`. Subclass and set the attribute.
    """

    allowed_roles = ()
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        return role_of(request.user) in self.allowed_roles


# ============================================================
# SINGLE ROLES
# ============================================================

class IsSuperAdmin(HasRole):
    allowed_roles = (Role.SUPER_ADMIN,)


class IsCoordinator(HasRole):
    allowed_roles = (Role.SUPER_ADMIN, Role.ACADEMIC_COORDINATOR)


class IsAccountant(HasRole):
    allowed_roles = (Role.SUPER_ADMIN, Role.ACCOUNTANT)


class IsTeacher(HasRole):
    allowed_roles = (Role.SUPER_ADMIN, Role.TEACHER)


class IsParent(HasRole):
    """Own-children endpoints only. Excludes Super Admin by design."""
    allowed_roles = (Role.PARENT,)


class IsStudent(HasRole):
    """Own-record endpoints only. Excludes Super Admin by design."""
    allowed_roles = (Role.STUDENT,)


# ============================================================
# COMBINATIONS
# ============================================================

class IsCoordinatorOrTeacher(HasRole):
    allowed_roles = (Role.SUPER_ADMIN, Role.ACADEMIC_COORDINATOR, Role.TEACHER)


class IsCoordinatorOrAccountant(HasRole):
    allowed_roles = (Role.SUPER_ADMIN, Role.ACADEMIC_COORDINATOR, Role.ACCOUNTANT)


class IsStaff(HasRole):
    """Any employee of the school. Not parents, not students."""
    allowed_roles = (
        Role.SUPER_ADMIN,
        Role.ACADEMIC_COORDINATOR,
        Role.ACCOUNTANT,
        Role.TEACHER,
    )


class IsStaffOrReadOnlyForOwner(HasRole):
    """
    Staff get full access; everyone authenticated gets read access.
    Object-level ownership must still be enforced by the view's
    get_queryset() - this class does not do that for you.
    """

    allowed_roles = (
        Role.SUPER_ADMIN,
        Role.ACADEMIC_COORDINATOR,
        Role.ACCOUNTANT,
        Role.TEACHER,
    )

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return role_of(request.user) in self.allowed_roles


# ============================================================
# HELPERS for object-level checks inside views
# ============================================================

def is_super_admin(user):
    return role_of(user) == Role.SUPER_ADMIN


def is_coordinator(user):
    return role_of(user) in (Role.SUPER_ADMIN, Role.ACADEMIC_COORDINATOR)


def is_accountant(user):
    return role_of(user) in (Role.SUPER_ADMIN, Role.ACCOUNTANT)


def is_teacher(user):
    return role_of(user) == Role.TEACHER


def is_parent(user):
    return role_of(user) == Role.PARENT


def is_student(user):
    return role_of(user) == Role.STUDENT


def parent_profile_of(user):
    """Return the user's ParentProfile, or None."""
    return getattr(user, "parent_profile", None)


def teacher_profile_of(user):
    """Return the user's TeacherProfile, or None."""
    return getattr(user, "teacher_profile", None)


def teacher_classroom_ids(user):
    """
    Classroom ids a teacher is actively assigned to. Returns an empty
    list for non-teachers, so callers can filter unconditionally.
    """
    profile = teacher_profile_of(user)
    if profile is None:
        return []

    # Imported here rather than at module level to avoid an import
    # cycle (assignments -> accounts -> core -> assignments).
    from assignments.models import TeacherAssignment

    return list(
        TeacherAssignment.objects
        .filter(teacher=profile, is_active=True)
        .values_list("classroom_id", flat=True)
        .distinct()
    )


def student_ids_visible_to(user):
    """
    The set of Student ids this user is allowed to see, as a queryset
    filter argument. Returns None when the user may see ALL students
    (so callers can skip filtering entirely).

    This is the one place that answers "whose records can you read?",
    so results/fees/attendance/dashboard all agree.
    """
    from students.models import Student

    if is_coordinator(user) or is_accountant(user):
        return None  # unrestricted

    if is_teacher(user):
        return Student.objects.filter(
            classroom_id__in=teacher_classroom_ids(user)
        ).values_list("id", flat=True)

    if is_parent(user):
        profile = parent_profile_of(user)
        if profile is None:
            return Student.objects.none().values_list("id", flat=True)
        return Student.objects.filter(parent=profile).values_list("id", flat=True)

    if is_student(user):
        return Student.objects.filter(user=user).values_list("id", flat=True)

    return Student.objects.none().values_list("id", flat=True)
