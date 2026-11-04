# Development

Use the README setup with a local virtual environment. Development defaults to SQLite. Set `DB_HOST` and the other `DB_*` values for local PostgreSQL, or set `DATABASE_URL` to a separate development database. `DATABASE_URL` takes precedence. A fresh checkout uses local login. Configure `NEON_AUTH_BASE_URL` and `NEON_AUTH_JWKS_URL` together only when testing managed sign-in. Testing uses an isolated database and fast password hashing. Production refuses an empty/short key or missing allowed hosts and uses PostgreSQL, secure transport settings and Redis when configured. Without Redis it uses the database cache table.

Run `ruff check .`, `ruff format .`, `python manage.py makemigrations --check --dry-run`, and pytest before commits. Keep .env, database files, uploaded media and collected static files out of Git. Source assets in `static/` are versioned. Database schema changes require committed migrations.
