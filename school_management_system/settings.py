"""
Django settings for the School Management System.

All environment-specific and secret values are read from the
environment (see .env.example). Nothing sensitive is hardcoded here.
"""

from datetime import timedelta
from pathlib import Path

from decouple import config


BASE_DIR = Path(__file__).resolve().parent.parent


def csv_env(name, default=""):
    """Read a comma-separated env var into a clean list."""
    raw = config(name, default=default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# ============================================================
# SECURITY
# ============================================================

SECRET_KEY = config("SECRET_KEY")

DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = csv_env("ALLOWED_HOSTS", default="localhost,127.0.0.1")

AUTH_USER_MODEL = "accounts.CustomUser"

# Production-only hardening. Applied automatically when DEBUG=False so
# a deploy can never accidentally ship without them.
if not DEBUG:
    SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=31536000, cast=int)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    # Required when running behind a TLS-terminating proxy (alwaysdata,
    # nginx, Heroku-style routers) or SECURE_SSL_REDIRECT loops forever.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# ============================================================
# CORS / CSRF
# ============================================================
#
# Previously hardcoded, and the two lists disagreed (one referenced
# luma-six-xi.vercel.app, the other luma-six-ix.vercel.app). Both are
# now env-driven so dev/staging/production can differ without a code
# change, and so the typo cannot silently reappear.

CORS_ALLOWED_ORIGINS = csv_env(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:5173,http://127.0.0.1:5173",
)

CSRF_TRUSTED_ORIGINS = csv_env(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost:5173,http://127.0.0.1:5173",
)

CORS_ALLOW_CREDENTIALS = True


# ============================================================
# APPLICATIONS
# ============================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "django_filters",
    "django_rest_passwordreset",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "corsheaders",

    # Local apps
    "core",             # shared pagination / caching / permissions / mixins
    "accounts",
    "students",
    "parents",
    "classes",
    "subjects",
    "assignments",
    "timetable",
    "attendance",
    "exams",
    "results",
    "fees",
    "anouncements",     # NOTE: misspelt app label kept deliberately -
    "notifiations",     # renaming would rewrite DB table names.
    "dashboard",
    "reports",
]

# REMOVED: "django_rename_app". It was listed in INSTALLED_APPS but was
# never in requirements.txt, so a clean `pip install -r requirements.txt`
# followed by any manage.py command crashed with ModuleNotFoundError.
# It is a one-off app-label renaming utility with no runtime role.


# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    # Compresses JSON payloads (~70-85% smaller). Must be outermost.
    "django.middleware.gzip.GZipMiddleware",

    "corsheaders.middleware.CorsMiddleware",

    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    # ETag + 304 Not Modified on unchanged GETs. Safe for JWT APIs:
    # the ETag hashes the response body, it is not a shared cache.
    "django.middleware.http.ConditionalGetMiddleware",
]


ROOT_URLCONF = "school_management_system.urls"

WSGI_APPLICATION = "school_management_system.wsgi.application"


# ============================================================
# TEMPLATES
# ============================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# ============================================================
# DATABASE
# ============================================================

DATABASES = {
    "default": {
        "ENGINE": config("DB_ENGINE", default="django.db.backends.mysql"),
        "NAME": config("DB_NAME", default=str(BASE_DIR / "sch")),
        "USER": config("DB_USER", default="root"),
        "PASSWORD": config("DB_PASSWORD", default=""),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="3306"),
        # Reuse connections for 60s instead of a new TCP (+TLS) handshake
        # per request. No effect on SQLite; real saving on MySQL/Postgres.migart
        "CONN_MAX_AGE": config("DB_CONN_MAX_AGE", default=60, cast=int),
    }
}


# ============================================================
# PASSWORD VALIDATION
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ============================================================
# INTERNATIONALIZATION
# ============================================================

LANGUAGE_CODE = "en-us"
TIME_ZONE = config("TIME_ZONE", default="Africa/Nairobi")
USE_I18N = True
USE_TZ = True


# ============================================================
# STATIC & MEDIA
# ============================================================

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# ADDED: the project has three ImageFields (CustomUser.profile_picture,
# Student.photo, and student uploads) but defined no MEDIA settings at
# all, so every upload was written to an undefined location and could
# never be served back.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Reject oversized uploads before they reach a view.
DATA_UPLOAD_MAX_MEMORY_SIZE = config("DATA_UPLOAD_MAX_MEMORY_SIZE", default=5 * 1024 * 1024, cast=int)
FILE_UPLOAD_MAX_MEMORY_SIZE = DATA_UPLOAD_MAX_MEMORY_SIZE

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ============================================================
# EMAIL
# ============================================================
#
# Credentials were previously hardcoded in this file. Now env-driven.
# Default backend is the console backend so local dev never needs real
# SMTP credentials and never accidentally emails a real parent.

EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config(
    "DEFAULT_FROM_EMAIL",
    default="School Management System <no-reply@example.com>",
)

DJANGO_REST_PASSWORDRESET_TOKEN_EXPIRY_TIME = 3600


# ============================================================
# DJANGO REST FRAMEWORK
# ============================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),

    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),

    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",

    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],

    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 25,

    # Uniform {success, message, errors} error envelope on every failure.
    "EXCEPTION_HANDLER": "core.exceptions.api_exception_handler",

    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],

    "DEFAULT_THROTTLE_RATES": {
        # Raised from 100/day. The old value was shared across ALL
        # anonymous traffic, so an entire school behind one NAT could
        # exhaust it, while still being far too loose to stop a
        # distributed brute-force. Real login protection is the
        # dedicated "login" scope below.
        "anon": config("THROTTLE_ANON", default="60/minute"),
        "user": config("THROTTLE_USER", default="2000/day"),

        # Named scopes for specific expensive/sensitive actions.
        "burst": "20/minute",
        "login": "10/minute",
        "password_reset": "5/hour",
        "mpesa_stk_push": "5/minute",
        "report_export": "10/minute",
    },
}


# ============================================================
# JWT
# ============================================================
#
# Previously: 30-day access tokens, and no refresh endpoint was routed
# anywhere - so the long lifetime was load-bearing. Access tokens are
# not blacklistable (only refresh tokens are), which made a leaked
# token valid for a month with no way to revoke it.
#
# Now: short access tokens + a routed /api/auth/token/refresh/ endpoint
# + rotation with blacklisting of the consumed refresh token.

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=config("ACCESS_TOKEN_LIFETIME_MINUTES", default=60, cast=int)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=config("REFRESH_TOKEN_LIFETIME_DAYS", default=7, cast=int)
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
}


# ============================================================
# CACHING
# ============================================================
#
# LocMemCache is per-process: with multiple gunicorn workers each has
# its own cache and cross-worker invalidation does not happen. Point
# CACHES at Redis in production via REDIS_URL.

REDIS_URL = config("REDIS_URL", default="")

if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "sms-default-cache",
        }
    }

CACHE_TTL_DASHBOARD_SUMMARY = config("CACHE_TTL_DASHBOARD_SUMMARY", default=60, cast=int)
CACHE_TTL_REPORTS = config("CACHE_TTL_REPORTS", default=120, cast=int)
CACHE_TTL_STATIC_LOOKUPS = config("CACHE_TTL_STATIC_LOOKUPS", default=300, cast=int)


# ============================================================
# API DOCUMENTATION (drf-spectacular)
# ============================================================

SPECTACULAR_SETTINGS = {
    "TITLE": "School Management System API",
    "DESCRIPTION": (
        "REST API for the School Management System: accounts and roles, "
        "students, classes, subjects, teacher assignments, timetable, "
        "attendance, exams, results, fees and M-Pesa payments, "
        "announcements, notifications, dashboards and reports."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/api",
    "SORT_OPERATIONS": False,
}


# ============================================================
# LOGGING
# ============================================================
#
# The project previously had no LOGGING config at all, so unhandled
# 500s were invisible outside of runserver's console.

LOG_LEVEL = config("LOG_LEVEL", default="INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "school_management_system": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}


# ============================================================
# SAFARICOM DARAJA / M-PESA
# ============================================================

MPESA_ENVIRONMENT = config("MPESA_ENVIRONMENT", default="sandbox")
MPESA_CONSUMER_KEY = config("MPESA_CONSUMER_KEY", default="")
MPESA_CONSUMER_SECRET = config("MPESA_CONSUMER_SECRET", default="")
MPESA_SHORTCODE = config("MPESA_SHORTCODE", default="")
MPESA_PASSKEY = config("MPESA_PASSKEY", default="")
MPESA_CALLBACK_URL = config("MPESA_CALLBACK_URL", default="")

# Safaricom does not sign callbacks, so the callback endpoint must stay
# AllowAny. Restrict it by source IP instead when the list is known.
MPESA_CALLBACK_ALLOWED_IPS = csv_env("MPESA_CALLBACK_ALLOWED_IPS", default="")
