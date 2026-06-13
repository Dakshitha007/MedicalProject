# Project Inventory: medcloud

This file lists all top-level files, Python packages, and important resources present in the repository.

## Top-level files

- manage.py
- db.sqlite3 (SQLite database file)
- PROJECT_CONTENTS.md (this file)

## Package: medcloud/

- __init__.py
- asgi.py
- settings.py
- urls.py
- wsgi.py
- __pycache__/ (compiled Python files)

## App: frontend/

Files:
- __init__.py
- admin.py
- apps.py
- models.py
- views.py
- urls.py
- tests.py

Migrations:
- migrations/__init__.py
- migrations/__pycache__/ (compiled)

Templates (frontend/templates/):
- base.html
- dashboard.html
- login.html
- reports.html
- setting.html
- upload.html

Template partials (frontend/templates/partials/):
- appointments.html
- medications.html
- pro_card.html

## Notes

- The project is a Django project with a `frontend` app and the project package `medcloud`.
- There are compiled `__pycache__` files present.
- The database is `db.sqlite3` at repository root.

If you want more detail (file sizes, last-modified times, or file contents), tell me which details to include and I will update this file accordingly.
