"""
Notifications permissions.

IsSuperAdmin is re-exported from `core.permissions`.
IsNotificationRecipient stays here: it is object-level ownership logic,
not a role check, so it does not belong in the shared role module.
"""

from rest_framework.permissions import BasePermission

from core.permissions import IsSuperAdmin  # noqa: F401


class IsNotificationRecipient(BasePermission):
    """A user may only act on notifications addressed to them."""

    message = "This notification does not belong to you."

    def has_object_permission(self, request, view, obj):
        return obj.recipient_id == request.user.id
