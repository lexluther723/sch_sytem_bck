"""
Root URL configuration for the School Management System.

BACKWARD COMPATIBILITY NOTE
---------------------------
Every pre-existing URL is preserved exactly as it was. The only
additions are:

  * /api/auth/...            - a clean alias for the auth endpoints,
                               alongside the original /api/accounts/...
                               which continues to work unchanged.
  * /api/auth/token/refresh/ - NEW. simplejwt's refresh view was never
                               routed, which is why access tokens had a
                               30-day lifetime. Now that refresh works,
                               access tokens are short-lived.
  * /api/announcements/      - correctly-spelled alias for the existing
                               (misspelt) /api/anouncements/ mount.
  * /api/notifications/      - correctly-spelled alias for the existing
                               (misspelt) /api/notifiations/ mount.

The misspelt app LABELS are deliberately left alone - renaming them
would rewrite database table names for no functional gain. Only the
public URL gets a correct spelling, with the old one kept as an alias
so the frontend can migrate whenever it likes.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView


def home(request):
    return JsonResponse(
        {
            "message": "School Management System API is running",
            "status": "success",
            "docs": "/api/docs/",
        }
    )


urlpatterns = [
    path("", home, name="api-root"),

    path("admin/", admin.site.urls),

    # ----------------------------------------------------------
    # API DOCUMENTATION
    # ----------------------------------------------------------
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),

    # ----------------------------------------------------------
    # AUTH
    #
    # NEW: token refresh + verify. Without a routed refresh view the
    # frontend had no way to renew an access token, which is why the
    # access lifetime had been pushed to 30 days.
    # ----------------------------------------------------------
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("api/auth/token/verify/", TokenVerifyView.as_view(), name="token-verify"),
    path("api/auth/", include("accounts.urls")),

    # ----------------------------------------------------------
    # ORIGINAL MOUNTS - unchanged, still authoritative
    # ----------------------------------------------------------
    path("api/accounts/", include("accounts.urls")),
    path("api/dashboard/", include("dashboard.urls")),
    path("api/students/", include("students.urls")),
    path("api/classes/", include("classes.urls")),
    path("api/subjects/", include("subjects.urls")),
    path("api/assignments/", include("assignments.urls")),
    path("api/timetable/", include("timetable.urls")),
    path("api/attendance/", include("attendance.urls")),
    path("api/exams/", include("exams.urls")),
    path("api/results/", include("results.urls")),
    path("api/reports/", include("reports.urls")),
    path("api/fees/", include("fees.urls")),
    path("api/parents/", include("parents.urls")),

    path("api/anouncements/", include("anouncements.urls")),
    path("api/notifiations/", include("notifiations.urls")),

    # Correctly-spelled aliases (additive).
    path("api/announcements/", include("anouncements.urls")),
    path("api/notifications/", include("notifiations.urls")),
]


# Serve uploaded media in development. MEDIA_URL / MEDIA_ROOT were not
# defined at all before, so profile pictures and student photos had
# nowhere to go and could never be served back.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
