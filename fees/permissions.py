"""
Fees permissions.

CONSOLIDATED into `core.permissions`.

BEHAVIOUR CHANGE - READ THIS
----------------------------
The old fees.IsAccountant and fees.IsAcademicCoordinator EXCLUDED
SUPER_ADMIN, while the identically-named classes in reports/ and
dashboard/ INCLUDED it. Super Admin could therefore open the financial
*reports* but not the equivalent fees screens.

These names now follow the project-wide rule (Super Admin is allowed
wherever a narrower staff role is allowed), which WIDENS access for
SUPER_ADMIN only. No other role gains or loses anything.

In practice nothing regresses today, because every fees view uses
IsSuperAdminOrAccountant, which already admitted Super Admin. The
narrower classes were unused.
"""

from core.permissions import (  # noqa: F401
    IsAccountant,
    IsCoordinator as IsAcademicCoordinator,
    IsCoordinatorOrAccountant as IsSuperAdminAccountantOrAcademicCoordinator,
    IsAccountant as IsSuperAdminOrAccountant,
    IsSuperAdmin,
)
