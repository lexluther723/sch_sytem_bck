#!/usr/bin/env bash
# ============================================================
# School Management System - verification script
#
# Run this from the project root with your virtualenv active.
# It runs, in order, every check that could not be run in the
# environment where these changes were written.
# ============================================================
set -e

echo "==> 1. Python dependencies"
pip install -r requirements.txt

echo
echo "==> 2. Environment file"
if [ ! -f .env ]; then
  cp .env.example .env
  python - <<'PY'
import secrets, string, pathlib
alphabet = string.ascii_letters + string.digits + "!@#$%^&*(-_=+)"
key = "".join(secrets.choice(alphabet) for _ in range(50))
p = pathlib.Path(".env")
p.write_text(p.read_text().replace(
    "change-me-generate-with-get_random_secret_key", key))
print("Created .env with a generated SECRET_KEY")
PY
else
  echo ".env already exists - leaving it alone"
fi

echo
echo "==> 3. Django system check"
python manage.py check

echo
echo "==> 4. Deployment check (informational; expected to warn while DEBUG=True)"
python manage.py check --deploy || true

echo
echo "==> 5. Generate migrations"
# Every app now has a migrations/ package, so this produces one
# consistent initial migration per app in a single pass.
python manage.py makemigrations

echo
echo "==> 6. Confirm no model changes are left unmigrated"
python manage.py makemigrations --check --dry-run

echo
echo "==> 7. Apply migrations"
python manage.py migrate

echo
echo "==> 8. Migration status"
python manage.py showmigrations

echo
echo "==> 9. Validate every URL resolves to an importable view"
python - <<'PY'
import django, os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "school_management_system.settings")
django.setup()
from django.urls import get_resolver
resolver = get_resolver()

def walk(patterns, prefix=""):
    count = 0
    for p in patterns:
        if hasattr(p, "url_patterns"):
            count += walk(p.url_patterns, prefix + str(p.pattern))
        else:
            count += 1
    return count

print(f"{walk(resolver.url_patterns)} routes resolved successfully")
PY

echo
echo "==> 10. Test suite"
python manage.py test -v 2

echo
echo "==> 11. OpenAPI schema generation"
python manage.py spectacular --file schema.yml
echo "Wrote schema.yml"

echo
echo "============================================"
echo "All checks passed."
echo "Next: python manage.py createsuperuser"
echo "      python manage.py runserver"
echo "============================================"
