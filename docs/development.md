# Development

Use the README setup with a local virtual environment. Development uses SQLite unless DB_HOST is configured. Testing uses an isolated database and fast password hashing. Production refuses an empty/short key or missing allowed hosts and uses PostgreSQL, shared Redis and secure transport settings.

Run `ruff check .`, `ruff format .`, `python manage.py makemigrations --check --dry-run`, and pytest before commits. Keep .env, database files, uploaded media and generated static files out of Git. Database schema changes require committed migrations.
