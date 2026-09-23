"""
Dashboard permissions.

CONSOLIDATED: the real definitions now live in `core.permissions`, which
is the single source of truth for role checks across the whole project.
This module re-exports them so every existing import path keeps working
and no view had to be edited.

Behaviour unchanged: dashboard's definitions already included
SUPER_ADMIN in every combined class.
"""

from core.permissions import (  # noqa: F401
    HasRole as HasRolePermission,
    IsSuperAdmin,
    IsCoordinator as IsAcademicCoordinator,
    IsAccountant,
    IsTeacher,
    IsParent,
    IsCoordinator as IsAdminOrAcademicCoordinator,
    IsAccountant as IsAdminOrAccountant,
    IsTeacher as IsAdminOrTeacher,
    IsStaff as IsDashboardUser,
)
