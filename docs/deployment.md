# Deployment and operations

The [live preview](https://eventhub-donfitex.onrender.com/) deploys from GitHub `main` to Render. It uses Neon for PostgreSQL, managed authentication and event image storage. Event emails are queued but scheduled delivery is pending sender setup.

## Production checklist

Use Python 3.12+, PostgreSQL 16+ and HTTPS. Redis is optional. Configure durable image storage and an SMTP sender as needed. The Dockerfile runs Gunicorn as a non-root user. Do not use the development Compose web command for production.

1. Provision PostgreSQL. Configure Redis if using it, or run `python manage.py createcachetable` for the database cache.
2. Set `DJANGO_SETTINGS_MODULE=config.production`, a random SECRET_KEY of at least 50 characters, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS and either DATABASE_URL or the individual DB_* settings. Set REDIS_URL only when using Redis. Configure SMTP variables when enabling delivery. Configure DB_SSLMODE according to provider TLS requirements (defaults to require).
3. Configure object storage as below, or mount a persistent volume at MEDIA_ROOT. Serve `/media/` via the proxy as static content with no executable handlers, `X-Content-Type-Options: nosniff`, and a 5 MB request limit. Back up this volume. Django deliberately does not serve production uploads.
4. Run `python manage.py migrate --noinput` once per release. Run `python manage.py collectstatic --noinput` in the release image/container with the production environment. WhiteNoise serves collected static files.
5. Run `python manage.py check --deploy --settings=config.production`. Create the administrator with `createsuperuser`.
6. Start Gunicorn with `gunicorn config.wsgi:application --config gunicorn.conf.py`. Set worker count for available memory. Terminate TLS at the proxy. Forward HTTPS using the standard Forwarded/X-Forwarded-Proto mechanism trusted by Gunicorn only from FORWARDED_ALLOW_IPS; restrict ingress to that proxy. Do not expose the app port publicly.
7. Once SMTP is configured, schedule `send_notifications` every minute and `send_reminders` hourly with the same production environment.
8. Probe `/health/` over HTTPS. Test signup, login, organizer creation/publish, registration, cancellation, notification delivery, uploads, and restart persistence.

## Local PostgreSQL

Copy .env.example to .env; set DB_PASSWORD. Run `docker compose up -d db redis`, set DB_HOST=localhost in your local environment, then migrate and run Django. `docker compose run --rm web python manage.py migrate` initializes the container database before starting the web service.

## Recovery and monitoring

Schedule encrypted daily PostgreSQL backups and media snapshots. Retain off-site copies; perform a restore rehearsal in a separate environment before launch and periodically thereafter. Record recovery time and recovery point requirements. Back up before every migration. Roll back application images only if database migrations remain compatible; otherwise restore a verified backup during a maintenance window.

Monitor HTTPS health, error rate, response latency, database saturation, disk usage and pending/old notification rows. Alert on persistent delivery failures. Logs go to stdout/stderr and must be collected by the host. Never log credentials or authorization headers. Configure SMTP timeouts and delivery dashboards with the provider. Redis stores shared rate-limit/lockout counters; keep it private and configure authentication/TLS in REDIS_URL as appropriate.

## Render free preview

Set `PREVIEW_MODE=1`, `DATABASE_URL` to the dedicated Neon database, and
`NEON_AUTH_BASE_URL` and `NEON_AUTH_JWKS_URL` to that branch's managed auth endpoints.
Register the public HTTPS origin in Neon Auth. Store credentials in Render environment
variables or load a mounted secret file with `EVENTHUB_SECRET_FILE`.
Use `python scripts/render_start.py` to migrate, initialize the database cache,
collect static assets, and start Gunicorn. Set `WEB_CONCURRENCY=1` for the free instance.
When Redis is absent the preview uses a dedicated PostgreSQL cache table.
Scheduled notification delivery requires a transactional sender and scheduler.

For persistent event images, configure a private Neon Object Storage bucket. Set
`EVENT_IMAGE_S3_ENDPOINT`, `EVENT_IMAGE_S3_BUCKET`, `EVENT_IMAGE_S3_REGION`,
`EVENT_IMAGE_S3_KEY_ID`, and `EVENT_IMAGE_S3_SECRET` in Render. The app uses
path-style S3 requests and 15-minute signed image URLs.
