"""
DEPRECATED MODULE NAME (note the missing 's': "permisions").

Kept so that the existing imports in classes/, subjects/, exams/,
timetable/ and assignments/ views keep working unchanged. New code
should import from `core.permissions` instead.
"""

from accounts.permissions import (  # noqa: F401
    IsAdminOrAcademicCoordinator,
    IsCoordinator,
    IsSuperAdmin,
)
