"""
Accounts permissions.

CONSOLIDATED: the real definitions now live in `core.permissions`, which
is the single source of truth for role checks across the whole project.
This module re-exports them so every existing import path keeps working
and no view had to be edited.

Behaviour unchanged: accounts.IsAdminOrAcademicCoordinator already
admitted SUPER_ADMIN + ACADEMIC_COORDINATOR.
"""

from core.permissions import (  # noqa: F401
    IsCoordinator as IsAdminOrAcademicCoordinator,
    IsCoordinator,
    IsSuperAdmin,
)
