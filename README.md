# EventHub

Django event discovery and registration platform with a responsive website, REST API, organizer studio, waitlists, and transactional notification outbox.

[Live preview](https://eventhub-donfitex.onrender.com/) · [Interactive API reference](https://eventhub-donfitex.onrender.com/api/docs/) · [Health check](https://eventhub-donfitex.onrender.com/health/)

The preview runs on Render with Neon PostgreSQL, Neon Better Auth, and private Neon Object Storage for uploaded images. Event notifications are queued. Scheduled delivery is pending sender setup.

## Run locally (PowerShell)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py seed_demo
.venv\Scripts\python manage.py createsuperuser
.venv\Scripts\python manage.py runserver
```

Open http://127.0.0.1:8000. A fresh checkout uses SQLite and local authentication. If you already have a .env file, check that it points to a development database before running migrations or seeding demo data. PostgreSQL is required for concurrent registration guarantees. Grant organizer access through the user administration page; public signup never grants elevated privileges. Create categories in admin before creating events.

## Verification

```powershell
.venv\Scripts\python -m pytest --cov=apps
.venv\Scripts\ruff check .
.venv\Scripts\ruff format --check .
.venv\Scripts\python manage.py check
.venv\Scripts\python manage.py spectacular --file openapi.yaml --validate --fail-on-warn
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

With a transactional sender configured, schedule `send_notifications` every minute and `send_reminders` hourly. Neither command runs automatically inside the web process.

See [development](docs/development.md), [architecture](docs/architecture.md), [API](docs/api.md), [testing](docs/testing.md), [security](docs/security.md), [deployment](docs/deployment.md), and [demo photo credits](docs/demo-photo-credits.md).
