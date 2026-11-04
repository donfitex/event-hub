from urllib.parse import urlsplit, unquote, parse_qs


def from_url(value):
    url = urlsplit(value)
    if url.scheme not in {"postgres", "postgresql"}:
        raise ValueError("DATABASE_URL must be PostgreSQL.")
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(url.path.lstrip("/")),
        "USER": unquote(url.username or ""),
        "PASSWORD": unquote(url.password or ""),
        "HOST": url.hostname,
        "PORT": url.port or 5432,
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"sslmode": parse_qs(url.query).get("sslmode", ["require"])[0]},
    }
