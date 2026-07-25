"""Production-only Django settings for the public Allcare 365 demo.

This module deliberately leaves ``medical_system.settings`` suitable for local
development. Deployments must select this module explicitly through
``DJANGO_SETTINGS_MODULE`` and provide all required environment variables.
"""

from urllib.parse import parse_qs, unquote, urlparse

from decouple import Config, RepositoryEnv
from django.core.exceptions import ImproperlyConfigured

from .settings import *  # noqa: F403


_environment = Config(RepositoryEnv(str(BASE_DIR / ".env")))  # noqa: F405


def _required(name):
    value = _environment(name, default="").strip()
    if not value:
        raise ImproperlyConfigured(f"{name} must be set for production.")
    return value


def _csv(name):
    return [value.strip() for value in _required(name).split(",") if value.strip()]


SECRET_KEY = _required("SECRET_KEY")
DEBUG = False
PUBLIC_BASE_URL = _required("PUBLIC_BASE_URL").rstrip("/")
ALLOWED_HOSTS = _csv("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = _csv("CSRF_TRUSTED_ORIGINS")
CORS_ALLOWED_ORIGINS = _csv("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_ALL_ORIGINS = False
FHIR_ALLOW_ANONYMOUS_READ = False
FHIR_INCLUDE_CONFORMANCE_FIXTURES = False

database_url = urlparse(_required("DATABASE_URL"))
if database_url.scheme not in {"postgres", "postgresql"} or not database_url.hostname:
    raise ImproperlyConfigured("DATABASE_URL must be a valid PostgreSQL URL.")

database_options = parse_qs(database_url.query)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(database_url.path.lstrip("/")),
        "USER": unquote(database_url.username or ""),
        "PASSWORD": unquote(database_url.password or ""),
        "HOST": database_url.hostname,
        "PORT": database_url.port or 5432,
        "CONN_MAX_AGE": 600,
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {"sslmode": database_options.get("sslmode", ["require"])[0]},
    }
}

MIDDLEWARE = list(MIDDLEWARE)  # noqa: F405
MIDDLEWARE.insert(
    MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,
    "whitenoise.middleware.WhiteNoiseMiddleware",
)
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
