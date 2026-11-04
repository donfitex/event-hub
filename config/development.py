from .base import *  # noqa

SECRET_KEY = SECRET_KEY or "development-only-key-do-not-use-in-production"
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
if os.getenv("DB_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "eventhub"),
            "USER": os.getenv("DB_USER", "eventhub"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST"),
            "PORT": os.getenv("DB_PORT", "5432"),
        }
    }

if os.getenv("DATABASE_URL"):
    from .database import from_url

    DATABASES = {"default": from_url(os.environ["DATABASE_URL"])}
