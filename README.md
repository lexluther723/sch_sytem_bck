# School Management System

A REST API backend for running a school: accounts and roles, students,
classes, subjects, teacher assignments, timetable, attendance, exams and
results, fees with M-Pesa payments, announcements, notifications,
dashboards and reports.

> **Status:** in development, not yet launched.
> See `CHANGELOG_FIXES.md` for what was recently repaired, and run
> `./verify.sh` before trusting anything.

## Quick start

```bash
git clone <repo> && cd school-main
python -m venv .venv && source .venv/bin/activate
./verify.sh                      # installs deps, creates .env, migrates, tests
python manage.py createsuperuser
python manage.py runserver
```

API docs once running: <http://localhost:8000/api/docs/>

## Technology

| Layer | Choice |
|---|---|
| Framework | Django 4.2 + Django REST Framework |
| Auth | JWT (`djangorestframework-simplejwt`) with refresh rotation |
| Database | MySQL in production, SQLite for local dev |
| Docs | OpenAPI 3 via `drf-spectacular` |
| Cache | LocMemCache in dev, Redis in production (set `REDIS_URL`) |
| Payments | Safaricom Daraja (M-Pesa STK push) |

## Roles

| Role | Can see | Can change |
|---|---|---|
| `SUPER_ADMIN` | everything | everything, incl. creating user accounts |
| `ACADEMIC_COORDINATOR` | all academic data | classes, subjects, exams, timetable, assignments; approves results |
| `ACCOUNTANT` | fees and financial reports | fee structures, payments |
| `TEACHER` | their assigned classes only | attendance and marks for those classes |
| `PARENT` | their own children only | nothing |
| `STUDENT` | their own record only | nothing |

Authorization is enforced **on the backend**, in `core/permissions.py`
plus per-view `get_queryset()` scoping. Frontend restrictions are
presentation only.

## Authentication

```http
POST /api/auth/login/            {"username": "...", "password": "..."}
  -> {"access": "...", "refresh": "...", "user": {...}}

POST /api/auth/token/refresh/    {"refresh": "..."}
  -> {"access": "...", "refresh": "..."}     # rotation: store the new one

POST /api/auth/logout/           {"refresh": "..."}   # blacklists it
```

Send `Authorization: Bearer <access>` on every other request.

Access tokens last 60 minutes and refresh tokens 7 days, both
configurable via `.env`. Refresh rotation is on, so **each refresh
returns a new refresh token and invalidates the old one** — the client
must store the new value.

`/api/accounts/...` remains available as an alias for `/api/auth/...`.

## Environment

Copy `.env.example` to `.env` and fill it in. Nothing sensitive is
hardcoded; the app will refuse to start without `SECRET_KEY`.

## Project layout

```
school_management_system/   settings, root urls, wsgi/asgi
core/                       shared: permissions, pagination, caching,
                            throttling, error envelope, mixins
accounts/                   CustomUser + the five role profiles, auth
students/  parents/         student records, transfers, guardians
classes/   subjects/        classrooms, subjects
assignments/ timetable/     teacher-to-class-and-subject, schedule
attendance/                 daily attendance submissions
exams/  results/            exams, assessments, marks, report cards
fees/                       fee structures, payments, M-Pesa
anouncements/ notifiations/ broadcast + per-user messaging
                            (labels are misspelt; renaming them would
                            rewrite DB table names, so the URLs carry
                            correctly-spelled aliases instead)
dashboard/  reports/        aggregated read-only views
```

## Pagination, filtering, searching

Every DRF generic view and ViewSet paginates by default:

```
?page=2&page_size=50
```

`page_size` is capped at 100 (500 on export-style endpoints), so no
client can request an entire table. Responses carry `count`,
`total_pages`, `current_page`, `page_size`, `next`, `previous`,
`results`.

Filtering, searching and ordering all happen **server-side** via
`django-filter` + DRF's `SearchFilter` / `OrderingFilter`:

```
GET /api/students/?classroom=3&status=Active&search=otieno&ordering=-created_at
```

## Error format

Every failure returns:

```json
{
  "success": false,
  "message": "Student not found.",
  "errors": {}
}
```

`detail` and `error` are also populated with the same message, for
backward compatibility with existing frontend code.

## Caching

| What | TTL | Invalidated by |
|---|---|---|
| Admin dashboard summary | `CACHE_TTL_DASHBOARD_SUMMARY` (60s) | any `FeePayment` save |
| Top outstanding students | 60s | any `FeePayment` save |

Use Redis in production (`REDIS_URL`): `LocMemCache` is per-process, so
with multiple workers each has its own copy and invalidation only
reaches the worker that handled the write.

## Testing

```bash
python manage.py test
```

> The test suite is **not yet written** — all `tests.py` files are
> currently empty. This is the highest-priority outstanding task; see
> `CHANGELOG_FIXES.md`.

## Migrations

```bash
python manage.py makemigrations
python manage.py makemigrations --check --dry-run   # proves none are missing
python manage.py migrate
python manage.py showmigrations
```

Migrations were reset to a clean slate because eight apps had none at
all. Do not run `makemigrations` against a database holding data you
care about without reading `CHANGELOG_FIXES.md` first.

## Deployment

1. `DEBUG=False` — this alone enables SSL redirect, secure cookies,
   HSTS, nosniff and referrer policy.
2. Set `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`.
3. Set `REDIS_URL`.
4. Point `DB_*` at MySQL.
5. `python manage.py collectstatic`, then serve `/media/` and `/static/`
   from the web server (Django does not serve them when `DEBUG=False`).
6. Behind a TLS-terminating proxy, `SECURE_PROXY_SSL_HEADER` is already
   configured — make sure the proxy sets `X-Forwarded-Proto`.
7. `python manage.py check --deploy` should be clean.

## Troubleshooting

| Symptom | Cause |
|---|---|
| `ModuleNotFoundError` on startup | `pip install -r requirements.txt` not run, or stale venv |
| `SECRET_KEY` undefined | no `.env` — run `./verify.sh` |
| Infinite redirect in production | proxy not sending `X-Forwarded-Proto` |
| 401 after an hour | frontend not calling `/api/auth/token/refresh/` — see Authentication |
| Dashboard numbers look stale | `LocMemCache` with multiple workers; set `REDIS_URL` |
| Uploads 404 | `collectstatic` not run, or `/media/` not served by the web server |

## Outstanding work

Tests, README endpoint reference, endpoint consolidation, remaining
pagination, `reports/` caching, and the `StudentProfile` vs `Student`
duality. All tracked in `CHANGELOG_FIXES.md`.
