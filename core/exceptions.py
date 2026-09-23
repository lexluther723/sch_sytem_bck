"""
Uniform API error envelope.

Registered as REST_FRAMEWORK["EXCEPTION_HANDLER"].

BEFORE: error shapes varied per view - {"error": "..."} from the
hand-written accounts/attendance views, {"detail": "..."} from DRF's
own machinery, and {"field": ["msg"]} from serializer validation. The
frontend had to branch on all three.

AFTER: every failure returns the same envelope:

    {
      "success": false,
      "message": "Student not found.",
      "errors": {}                      # field errors, when applicable
    }

BACKWARD COMPATIBILITY: the original keys are preserved alongside the
new ones ("detail" for DRF errors, "error" for the hand-written views),
so existing frontend code that reads response.data.detail or
response.data.error keeps working. Nothing breaks on day one; the
frontend can migrate to `message` at its own pace.
"""

import logging

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


DEFAULT_MESSAGES = {
    status.HTTP_400_BAD_REQUEST: "The request could not be processed.",
    status.HTTP_401_UNAUTHORIZED: "Authentication credentials were not provided or have expired.",
    status.HTTP_403_FORBIDDEN: "You do not have permission to perform this action.",
    status.HTTP_404_NOT_FOUND: "The requested resource was not found.",
    status.HTTP_405_METHOD_NOT_ALLOWED: "That method is not allowed on this endpoint.",
    status.HTTP_409_CONFLICT: "This request conflicts with the current state of the resource.",
    status.HTTP_429_TOO_MANY_REQUESTS: "Too many requests. Please slow down and try again shortly.",
}


def _extract(detail):
    """
    Split a DRF exception detail into (message, field_errors).

    Serializer validation produces {"field": ["msg", ...]}; simple
    errors produce a plain string or a list.
    """
    if isinstance(detail, dict):
        # Non-field errors are the best candidate for the headline message.
        for key in ("detail", "non_field_errors", "__all__"):
            value = detail.get(key)
            if value:
                message = value[0] if isinstance(value, (list, tuple)) else value
                return str(message), {k: v for k, v in detail.items() if k != key}
        first_field = next(iter(detail))
        first_value = detail[first_field]
        first_message = first_value[0] if isinstance(first_value, (list, tuple)) else first_value
        return f"{first_field}: {first_message}", detail

    if isinstance(detail, (list, tuple)):
        return (str(detail[0]) if detail else "Invalid input."), {}

    return str(detail), {}


def api_exception_handler(exc, context):
    # Translate Django-native exceptions into their DRF equivalents so
    # they get the same envelope rather than falling through to a 500.
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    response = drf_exception_handler(exc, context)

    if response is None:
        # Genuinely unhandled - log it with the view for triage, and
        # never leak a traceback or internal message to the client.
        view = context.get("view")
        logger.exception(
            "Unhandled exception in %s",
            view.__class__.__name__ if view else "unknown view",
        )
        return Response(
            {
                "success": False,
                "message": "An unexpected server error occurred.",
                "errors": {},
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    message, field_errors = _extract(response.data)

    payload = {
        "success": False,
        "message": message or DEFAULT_MESSAGES.get(response.status_code, "Request failed."),
        "errors": field_errors,
    }

    # --- backward-compatible aliases (see module docstring) ---
    payload["detail"] = payload["message"]
    payload["error"] = payload["message"]

    if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        retry_after = response.headers.get("Retry-After") if hasattr(response, "headers") else None
        if retry_after:
            payload["retry_after_seconds"] = retry_after

    response.data = payload
    return response
