# EventHub

Django event discovery and registration platform with a responsive website, REST API, organizer studio, waitlists, and transactional notification outbox.

## Run locally (PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py createsuperuser
.venv\Scripts\python manage.py runserver
```

Open http://127.0.0.1:8000. SQLite is the default for local exploration. PostgreSQL is required for concurrent registration guarantees. Grant organizer access through the user administration page; public signup never grants elevated privileges. Create categories in admin before creating events.

## Verification

```powershell
.venv\Scripts\python -m pytest --cov=apps
.venv\Scripts\ruff check .
.venv\Scripts\ruff format --check .
.venv\Scripts\python manage.py check
```

## Interfaces

- `/` — event discovery
- `/dashboard/` — registration history
- `/organizer/` — organizer studio
- `/admin/` — users, categories and read-only operational records
- `/api/v1/` — REST endpoints
- `/api/schema/` — OpenAPI schema
- `/api/docs/` — interactive API documentation (requires internet for Swagger assets)
- `/health/` — database readiness

Run `python manage.py send_notifications` every minute and `python manage.py send_reminders` hourly. These commands do not run automatically inside the web process.

See [deployment](docs/deployment.md), [architecture](docs/architecture.md), [API](docs/api.md), and [release audit](docs/PROGRESS.md). Production deployment is a separate operational step requiring a hosting target, credentials, SMTP and persistent storage.
