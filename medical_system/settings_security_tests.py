"""Isolated PostgreSQL settings for production-security regression tests.

Never migrates the development/clinical database. All fixtures are synthetic.
"""
from .settings import *  # noqa: F403

DATABASES = {  # noqa: F405
    'default': {**DATABASES['default'], 'TEST': {'NAME': 'test_allcare365_security_v2'}},
}
MFA_REQUIRED_FOR_PRIVILEGED = False
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver', 'example.org']
MEDIA_ROOT = os.environ.get('SECURITY_TEST_MEDIA_ROOT', BASE_DIR / 'media' / 'security-tests')  # noqa: F405
BULK_EXPORT_STORAGE_PRIVATE = True  # Synthetic test files only, never deployment settings.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'WARNING'},
}
