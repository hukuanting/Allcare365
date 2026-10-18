"""Strict production settings for Allcare 365.

This module deliberately leaves ``medical_system.settings`` suitable for local
development. Deployments must select this module explicitly through
``DJANGO_SETTINGS_MODULE`` and provide all required environment variables.
"""

from urllib.parse import parse_qs, unquote, urlparse
from datetime import timedelta
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

from decouple import AutoConfig
from django.core.exceptions import ImproperlyConfigured

from .settings import *  # noqa: F403


_environment = AutoConfig(search_path=BASE_DIR)  # noqa: F405


def _required(name):
    value = _environment(name, default="").strip()
    if not value:
        raise ImproperlyConfigured(f"{name} must be set for production.")
    return value


def _csv(name):
    return [value.strip() for value in _required(name).split(",") if value.strip()]


SECRET_KEY = _required("SECRET_KEY")
if len(SECRET_KEY) < 50:
    raise ImproperlyConfigured("SECRET_KEY must contain at least 50 characters in production.")
DEBUG = False
PUBLIC_BASE_URL = _required("PUBLIC_BASE_URL").rstrip("/")
if urlparse(PUBLIC_BASE_URL).scheme != "https":
    raise ImproperlyConfigured("PUBLIC_BASE_URL must use HTTPS in production.")
ALLOWED_HOSTS = _csv("ALLOWED_HOSTS")
if "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS must not contain a wildcard in production.")
CSRF_TRUSTED_ORIGINS = _csv("CSRF_TRUSTED_ORIGINS")
CORS_ALLOWED_ORIGINS = _csv("CORS_ALLOWED_ORIGINS")
if any(urlparse(origin).scheme != "https" for origin in CSRF_TRUSTED_ORIGINS + CORS_ALLOWED_ORIGINS):
    raise ImproperlyConfigured("Production CSRF and CORS origins must use HTTPS.")
CORS_ALLOW_ALL_ORIGINS = False
MFA_REQUIRED_FOR_PRIVILEGED = True
INFERNO_BULK_ALLOW_DYNAMIC_CLIENT_REGISTRATION = False
FHIR_ALLOW_ANONYMOUS_READ = False
FHIR_INCLUDE_CONFORMANCE_FIXTURES = False
OAUTH2_PROVIDER = dict(OAUTH2_PROVIDER)  # noqa: F405
OIDC_RSA_PRIVATE_KEY = _required("OIDC_RSA_PRIVATE_KEY").replace("\\n", "\n")
try:
    oidc_signing_key = load_pem_private_key(OIDC_RSA_PRIVATE_KEY.encode("utf-8"), password=None)
except (TypeError, ValueError) as exc:
    raise ImproperlyConfigured("OIDC_RSA_PRIVATE_KEY must be an unencrypted PEM private key.") from exc
if not isinstance(oidc_signing_key, RSAPrivateKey) or oidc_signing_key.key_size < 2048:
    raise ImproperlyConfigured("OIDC_RSA_PRIVATE_KEY must be an RSA key of at least 2048 bits.")
OAUTH2_PROVIDER["OIDC_RSA_PRIVATE_KEY"] = OIDC_RSA_PRIVATE_KEY

database_url = urlparse(_required("DATABASE_URL"))
if database_url.scheme not in {"postgres", "postgresql"}:
    raise ImproperlyConfigured("DATABASE_URL must be a valid PostgreSQL URL.")

database_options = parse_qs(database_url.query)
cloud_sql_socket = database_options.get("host", [""])[0]
if cloud_sql_socket.startswith("/cloudsql/"):
    # Cloud Run's Cloud SQL integration mounts an authenticated local socket;
    # the connector establishes the encrypted upstream connection to Cloud SQL.
    database_host = cloud_sql_socket
    database_connection_options = {}
elif database_url.hostname:
    database_host = database_url.hostname
    database_sslmode = database_options.get("sslmode", ["require"])[0]
    if database_sslmode not in {"verify-ca", "verify-full", "require"}:
        raise ImproperlyConfigured("DATABASE_URL sslmode must require TLS (require, verify-ca, or verify-full).")
    database_connection_options = {"sslmode": database_sslmode}
else:
    raise ImproperlyConfigured("DATABASE_URL must include a database host or Cloud SQL socket path.")
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(database_url.path.lstrip("/")),
        "USER": unquote(database_url.username or ""),
        "PASSWORD": unquote(database_url.password or ""),
        "HOST": database_host,
        "PORT": database_url.port or 5432,
        "CONN_MAX_AGE": 600,
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": database_connection_options,
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

# Clinical uploads/export snapshots must survive container replacement and
# must never be served as public media. Use workload identity/IAM, not keys in Git.
private_storage_backend = _required('PRIVATE_STORAGE_BACKEND')
if private_storage_backend == 'gcs':
    STORAGES['default'] = {
        'BACKEND': 'storages.backends.gcloud.GoogleCloudStorage',
        'OPTIONS': {
            'bucket_name': _required('PRIVATE_STORAGE_BUCKET'),
            'default_acl': None,
            'querystring_auth': True,
            'file_overwrite': False,
            'expiration': timedelta(minutes=5),
        },
    }
elif private_storage_backend == 's3':
    STORAGES['default'] = {
        'BACKEND': 'storages.backends.s3.S3Storage',
        'OPTIONS': {
            'bucket_name': _required('PRIVATE_STORAGE_BUCKET'),
            'region_name': _required('PRIVATE_STORAGE_REGION'),
            'default_acl': None,
            'querystring_auth': True,
            'file_overwrite': False,
            'querystring_expire': 300,
        },
    }
else:
    raise ImproperlyConfigured('PRIVATE_STORAGE_BACKEND must be gcs or s3.')
BULK_EXPORT_STORAGE_PRIVATE = True
BULK_EXPORT_TTL_SECONDS = _environment('BULK_EXPORT_TTL_SECONDS', default=86400, cast=int)
if not 60 <= BULK_EXPORT_TTL_SECONDS <= 604800:
    raise ImproperlyConfigured('BULK_EXPORT_TTL_SECONDS must be between 60 and 604800.')

cache_url = _required('CACHE_URL')
if urlparse(cache_url).scheme != 'rediss':
    raise ImproperlyConfigured('CACHE_URL must use rediss for the shared authentication cache.')
cache_options = {'ssl_cert_reqs': 'required'}
cache_tls_ca_cert = _environment('CACHE_TLS_CA_CERT', default='').strip()
if cache_tls_ca_cert:
    cache_options['ssl_ca_certs'] = cache_tls_ca_cert
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': cache_url,
        'KEY_PREFIX': 'allcare365-production',
        'OPTIONS': cache_options,
    },
}
# Container logs are collected centrally; do not retain PHI or bearer tokens.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {
        'apps.clinical.health_screening': {'level': 'INFO'},
        'oauthlib': {'level': 'WARNING'},
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
