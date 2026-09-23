"""
Throttling and duplicate-request protection.

Two different problems, two different tools:

1. "This client is calling us too often" -> DRF throttle classes
   (rate limiting, e.g. 100 requests/minute).

2. "This exact action was already submitted a moment ago and
   shouldn't run twice" -> `duplicate_request_guard` below (an
   idempotency lock), which a rate limit does NOT protect against —
   two rapid double-taps of a "Pay Now" button are well within any
   sane rate limit, but must never trigger two M-Pesa STK pushes or
   two attendance submissions.
"""

from rest_framework.throttling import (
    AnonRateThrottle,
    ScopedRateThrottle,
    UserRateThrottle,
)
from django.core.cache import cache
from rest_framework.response import Response
from rest_framework import status
from functools import wraps


class BurstRateThrottle(UserRateThrottle):
    """
    Tighter, short-window throttle for expensive or sensitive
    write endpoints (payments, bulk marking, report generation)
    where the default per-day user throttle is too loose to stop a
    misbehaving frontend (e.g. a retry loop) from hammering the
    server in a tight burst.

    Add to a view with:
        throttle_classes = [BurstRateThrottle]
        throttle_scope = "burst"
    and register the rate in REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"].
    """

    scope = "burst"


class SensitiveActionThrottle(ScopedRateThrottle):
    """
    Named-scope throttle for a specific sensitive action (e.g.
    `"mpesa_stk_push"`, `"login"`, `"password_reset"`). Set
    `throttle_scope = "mpesa_stk_push"` on the view and configure its
    rate in `DEFAULT_THROTTLE_RATES` — keeps rate limits declarative
    and per-action instead of scattering ad-hoc counters everywhere.
    """


def duplicate_request_guard(key_func, timeout=15):
    """
    Decorator for APIView.post()/put() methods that must not be
    allowed to run twice in quick succession for the same logical
    request (e.g. "pay this student's fee balance via M-Pesa",
    "submit today's attendance for this classroom").

    Uses `cache.add`, which is atomic at the cache-backend level
    (unlike "check then set"): only the FIRST caller within the
    `timeout` window acquires the lock and proceeds; any repeat
    call (double-tap, retried request, duplicate webhook) within
    that window gets a 409 immediately, without touching the
    database or an external API (e.g. Safaricom Daraja) at all.

    `key_func(request, *args, **kwargs)` must return a string that
    uniquely identifies the logical action being guarded, e.g.:
        lambda request, *a, **kw: f"stk-push:{request.user.id}:{request.data.get('student_id')}"

    Usage:
        class StkPushAPIView(APIView):
            @duplicate_request_guard(
                lambda request, *a, **kw: f"stk-push:{request.user.id}:{request.data.get('student_id')}",
                timeout=20,
            )
            def post(self, request):
                ...
    """

    def decorator(view_method):
        @wraps(view_method)
        def wrapper(self, request, *args, **kwargs):
            lock_key = f"dup-guard:{key_func(request, *args, **kwargs)}"
            acquired = cache.add(lock_key, "1", timeout)
            if not acquired:
                return Response(
                    {
                        "success": False,
                        "message": (
                            "This request was already submitted. "
                            "Please wait a few seconds before retrying."
                        ),
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            try:
                return view_method(self, request, *args, **kwargs)
            except Exception:
                # Don't let a failed attempt lock the user out for
                # the full timeout — release immediately on error so
                # a genuine retry after a failure isn't blocked.
                cache.delete(lock_key)
                raise

        return wrapper

    return decorator


class LoginRateThrottle(AnonRateThrottle):
    """
    Dedicated brute-force protection for the login endpoint.

    WHY THIS IS SEPARATE
    --------------------
    Login was protected only by the project-wide `anon` throttle, which
    was set to 100/day. That single number had to serve two conflicting
    jobs and did neither well:

      * Too weak as brute-force protection - 100 password guesses per
        day per IP is plenty for a targeted attack on a known username.
      * Too harsh for real users - the `anon` bucket is shared across
        ALL anonymous traffic, so an entire school behind one NAT could
        exhaust it with ordinary browsing.

    Splitting login into its own scope lets the two be tuned
    independently: `anon` is now generous (60/minute) while `login` is
    tight (10/minute), both configurable via DEFAULT_THROTTLE_RATES.
    """

    scope = "login"


class PasswordResetRateThrottle(AnonRateThrottle):
    """
    Throttles password-reset requests so the endpoint cannot be used to
    spam a real inbox, or to probe which email addresses are registered
    by timing the response.
    """

    scope = "password_reset"
