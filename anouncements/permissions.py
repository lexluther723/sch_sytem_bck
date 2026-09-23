"""
Announcements permissions.

CONSOLIDATED into `core.permissions`. The local
IsSuperAdminOrAcademicCoordinator already admitted SUPER_ADMIN +
ACADEMIC_COORDINATOR, which is exactly core.permissions.IsCoordinator,
so behaviour is unchanged.
"""

from core.permissions import (  # noqa: F401
    IsCoordinator,
    IsCoordinator as IsSuperAdminOrAcademicCoordinator,
)
