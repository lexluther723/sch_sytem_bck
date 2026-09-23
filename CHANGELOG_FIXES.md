# Changes applied

Baseline: the uploaded `school-main` archive. Every change below is
listed with the file it touches and why.

**Verification status:** written in an environment with no network
access, so Django could not be installed and no Django command was
executed. Everything is verified by static analysis only (AST parsing,
model-graph field resolution, import resolution). Run `./verify.sh`
to confirm.

---

## A. Repository hygiene

| # | File | Change |
|---|---|---|
| A1 | `requirements.txt` | Re-encoded UTF-16 → UTF-8. `pip install -r` could not parse the old file. |
| A2 | `requirements.txt`, `settings.py` | Removed `django_rename_app` from `INSTALLED_APPS`. It was never in requirements, so a clean install crashed with `ModuleNotFoundError`. It is a one-off rename utility with no runtime role. |
| A3 | `.gitignore` | Resolved the unresolved Git merge conflict; rewrote properly. `.env` is now reliably ignored. |
| A4 | `README.md` | Conflict markers removed (replaced in §F). |
| A5 | `db.sqlite3` | Deleted. It was corrupt (`database disk image is malformed`) and contained Django's stock `auth_user` table — it predated the custom user model entirely. |
| A6 | `.env.example` | **New.** Documents all environment variables. |
| A7 | `verify.sh` | **New.** Runs every check that could not be run here. |

## B. Project rename

| # | Change |
|---|---|
| B1 | `luma_2000_academy/` → `school_management_system/`, and all 5 referencing files updated (`manage.py`, `settings.py`, `wsgi.py`, `asgi.py`, `urls.py`). Zero references remain. |

**No app label, model name, database table or migration was renamed.** This is purely a Python package rename.

## C. Broken endpoints (were returning 500 on every call)

| # | File | Fix |
|---|---|---|
| C1 | `reports/views.py` ×4 | `Count("students")` → `Count("children")` on `ParentProfile`. The reverse accessor from `Student.parent` is `children`. Fixes `/api/reports/parents/{summary,contact,children,fees,with-outstanding-balances}/`. |
| C2 | `reports/views.py` | `prefetch_related("students__classroom")` → `"children__classroom"`. |
| C3 | `reports/views.py` `get_payment_qs()` | `select_related("student", "student__classroom")` → `"student_fee__student"...`. `FeePayment` has no `student` field. |
| C4 | `reports/views.py` `get_payment_qs()` | `payment_date__date__gte` → `payment_date__gte`. `payment_date` is a `DateField`; the `__date` lookup is `DateTimeField`-only. C3+C4 fix `/api/reports/financial/generate/` and `/export/`. |
| C5 | `reports/views.py` | Term filter `student__studentfee__fee_structure__term` → `student_fee__fee_structure__term`. |
| C6 | `results/views.py` ×2, `results/admin.py` ×3, `accounts/serializers.py` ×1 | `admission_no` → `admission_number`. Fixes 500 on `?search=` against `/api/results/student-results/` and `/student-term-results/`. |
| C7 | `dashboard/views.py` | `Result.objects.filter(assessment=...)` → `submission__assessment=...`. (Latent — the function had no callers.) |

**Guard against C1 recurring:** the blanket rename initially also hit `ClassCapacityReport`, where `Count("students")` on `ClassRoom` was *correct*. The model-graph validator caught it and it was reverted, with a comment explaining the distinction.

## D. Security

| # | File | Fix |
|---|---|---|
| D1 | `accounts/models.py` | **`CustomUser.role` no longer defaults to `SUPER_ADMIN`.** It defaults to `STUDENT` (least privilege) and is now indexed. Any code path creating a user without an explicit role previously minted an administrator. |
| D2 | `results/views.py` | `StudentResultViewSet` and `StudentTermResultViewSet` now scope by `get_queryset()`. They were `IsAuthenticated` with an unfiltered queryset — any logged-in student or parent could list every student's marks. |
| D3 | `results/views.py` | `StudentReportCardAPIView` now checks ownership before returning a report card, and returns 404 (not 403) so student ids cannot be enumerated. |
| D4 | `settings.py`, root `urls.py` | Access tokens 30 days → 60 min; refresh 60 → 7 days; rotation + blacklist-after-rotation enabled; **`/api/auth/token/refresh/` routed for the first time.** |
| D5 | `settings.py` | Email credentials moved out of source into env. Default backend is now the console backend, so dev never needs real SMTP and cannot email a real parent by accident. |
| D6 | `settings.py` | `CORS_ALLOWED_ORIGINS` / `CSRF_TRUSTED_ORIGINS` moved to env. The hardcoded lists disagreed: one had `luma-six-xi`, the other `luma-six-ix`. |
| D7 | `settings.py` | Production headers applied automatically when `DEBUG=False`: SSL redirect, secure cookies, HSTS, nosniff, referrer policy, and `SECURE_PROXY_SSL_HEADER` (required behind a TLS-terminating proxy, or SSL redirect loops). |
| D8 | `core/throttling.py`, `accounts/views.py` | Dedicated `login` (10/min) and `password_reset` (5/hr) throttle scopes. `anon` relaxed 100/day → 60/min: the old value was simultaneously too weak for brute force and too harsh for a school behind one NAT. |
| D9 | `accounts/views.py` | Login returns an identical response for a wrong password and a deactivated account. The 403-vs-401 difference confirmed which usernames exist. |
| D10 | `results/permissions.py` | Teacher assignment checks now require `is_active=True`. A teacher whose assignment had ended could still edit marks for that class. |
| D11 | `settings.py` | Upload size cap (`DATA_UPLOAD_MAX_MEMORY_SIZE`, 5 MB). |

## E. Correctness and performance

| # | File | Fix |
|---|---|---|
| E1 | `core/cache.py` | **Cache invalidation never fired.** Keys were registered under `"dashboard:summary"` but busted under `"dashboard"`, so `bust_cache_prefix` looked up an index key nothing ever wrote. Keys are now registered against every ancestor namespace. |
| E2 | `dashboard/views.py` | `attendance_today` aggregated over *every attendance record ever* and reported it as today's rate. Now filtered to `submission__date=today` — correct, and no longer a full scan of the largest table on every cache miss. |
| E3 | `classes/serializers.py`, `classes/views.py`, `students/Signals.py` | **`ClassRoom.total_students` was permanently 0.** The signals maintaining it were never imported (`students/apps.py` has no `ready()`; file is capital-S `Signals.py`). Replaced with an annotated `Count("students")` — correct, cannot drift, one query for the whole list. JSON key and type unchanged. |
| E4 | `reports/views.py` | `ParentFeeReport` and `ParentsWithOutstandingBalancesReport` ran one aggregate query **per parent**. Now a single query using `Sum("children__fee_accounts__...")` with `Coalesce`. 401 queries → 1 for 400 parents. |
| E5 | `reports/views.py` | `ParentsWithOutstandingBalancesReport` filters `balance__gt=0` in SQL, so parents with nothing outstanding never leave the database. |
| E6 | `accounts/views.py` | `UserList` paginates. **Opt-in**: the bare array is still returned unless `?page=` or `?page_size=` is supplied, so no frontend call breaks. |

## F. Consistency and infrastructure

| # | File | Change |
|---|---|---|
| F1 | `core/permissions.py` | **New — single source of truth for role checks.** Previously six apps defined classes with the same names and *different* meanings (`fees.IsAccountant` excluded Super Admin, `reports.IsAccountant` included it; `results.IsTeacher` excluded, `dashboard.IsTeacher` included). Whether an admin could see a screen depended on which module a developer imported from. |
| F2 | 8 `permissions.py` files + `accounts/permisions.py` | Converted to thin re-export shims. **Every existing import path still works and no view file was edited.** Verified: no previously-exported name was dropped. |
| F3 | `core/exceptions.py` | **New.** Uniform `{success, message, errors}` envelope on every error. **Backward compatible**: the original `detail` and `error` keys are still populated alongside, so existing frontend branching keeps working. |
| F4 | `settings.py` | `SPECTACULAR_SETTINGS` added — `drf_spectacular` was installed and `/api/docs/` routed, but unconfigured. Added `/api/redoc/`. |
| F5 | `settings.py` | `LOGGING` added. There was none, so unhandled 500s were invisible outside runserver. |
| F6 | `settings.py`, root `urls.py` | `MEDIA_URL` / `MEDIA_ROOT` added and served in DEBUG. Three `ImageField`s existed with no media config at all. |
| F7 | `settings.py` | Redis cache backend used automatically when `REDIS_URL` is set. `LocMemCache` is per-process, so cross-worker invalidation silently fails under gunicorn. |
| F8 | root `urls.py` | Added `/api/announcements/` and `/api/notifications/` as correctly-spelled **aliases**. The misspelt app labels are deliberately untouched — renaming them rewrites table names for no gain. |
| F9 | root `urls.py` | Added `/api/auth/` as an alias for `/api/accounts/`; removed the stray `import reports`; added an `api-root` view. |
| F10 | `settings.py` | `TIME_ZONE` `UTC` → `Africa/Nairobi` (env-overridable). Attendance and fee reports are date-bucketed, so UTC shifted day boundaries. |

---

## Migrations — read this

Eight apps that define models had **no `migrations/` directory at all**, including `accounts`, which owns `AUTH_USER_MODEL`. The five migrations that did exist depended on apps that had none.

Because you confirmed this is **development, pre-launch, with no production data**, I reset to a clean slate:

- Deleted the 6 existing migration files (all recoverable via `git checkout`).
- Created `migrations/__init__.py` for all 15 apps with models.

`./verify.sh` then runs a single `makemigrations` pass, producing one consistent initial migration per app, followed by `makemigrations --check` to prove nothing is left unmigrated.

**If any of your databases holds data you care about, stop and tell me before running step 5.**

---

## Not done yet

- Test suite (all 15 `tests.py` are still empty)
- README rewrite
- Endpoint consolidation — three "my children" endpoints, three teacher-directory endpoints, `payments/successful/` + `payments/pending/` vs `?payment_status=`
- Dashboard widget consolidation (9 admin round-trips)
- Pagination for the remaining ~17 unbounded list endpoints
- Caching for `reports/`
- The `accounts.StudentProfile` vs `students.Student` duality

---

## Frontend impact

**Nothing should break.** Every change was made additively or behind an opt-in.

One thing **does** need frontend work, and only when you choose to deploy it:

> **D4 — JWT lifetimes.** Access tokens now expire after 60 minutes instead of 30 days. The frontend must call `POST /api/auth/token/refresh/` with `{"refresh": "..."}` on a 401 and retry. Until that exists, set `ACCESS_TOKEN_LIFETIME_MINUTES=43200` in `.env` to keep the old 30-day behaviour — no code change needed.

Because rotation is on, each refresh returns a **new** refresh token; the frontend must store and use it, as the old one is blacklisted.
