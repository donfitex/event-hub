from .base import *  # noqa
from django.core.exceptions import ImproperlyConfigured
from urllib.parse import urlsplit

if len(SECRET_KEY) < 50 or not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "Set a random SECRET_KEY of at least 50 characters and ALLOWED_HOSTS."
    )
from .database import from_url

if os.getenv("DATABASE_URL"):
    DATABASES = {"default": from_url(os.environ["DATABASE_URL"])}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["DB_NAME"],
            "USER": os.environ["DB_USER"],
            "PASSWORD": os.environ["DB_PASSWORD"],
            "HOST": os.environ["DB_HOST"],
            "PORT": os.getenv("DB_PORT", "5432"),
            "CONN_MAX_AGE": 60,
            "OPTIONS": {"sslmode": os.getenv("DB_SSLMODE", "require")},
        }
    }
if os.getenv("REDIS_URL"):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": os.environ["REDIS_URL"],
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.db.DatabaseCache",
            "LOCATION": "eventhub_cache",
        }
    }
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_REFERRER_POLICY = "same-origin"
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

if endpoint := os.getenv("EVENT_IMAGE_S3_ENDPOINT"):
    parsed = urlsplit(endpoint)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.netloc != parsed.hostname
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise ImproperlyConfigured("EVENT_IMAGE_S3_ENDPOINT must be an HTTPS origin.")
    EVENT_IMAGE_ORIGIN = f"https://{parsed.hostname}"
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "endpoint_url": EVENT_IMAGE_ORIGIN,
            "bucket_name": os.environ["EVENT_IMAGE_S3_BUCKET"],
            "access_key": os.environ["EVENT_IMAGE_S3_KEY_ID"],
            "secret_key": os.environ["EVENT_IMAGE_S3_SECRET"],
            "region_name": os.environ["EVENT_IMAGE_S3_REGION"],
            "addressing_style": "path",
            "signature_version": "s3v4",
            "querystring_expire": 900,
            "file_overwrite": False,
        },
    }
    EVENT_IMAGE_UPLOADS_ENABLED = True
