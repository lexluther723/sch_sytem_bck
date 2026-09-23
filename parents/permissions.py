"""
Parents permissions.

CONSOLIDATED: the real definitions now live in `core.permissions`, which
is the single source of truth for role checks across the whole project.
This module re-exports them so every existing import path keeps working
and no view had to be edited.

Behaviour unchanged.
"""

from core.permissions import (  # noqa: F401
    IsSuperAdmin,
    IsParent,
)
