"""Celery configuration for the Allcare 365 Django project."""

import os

try:
    from celery import Celery

    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False

    class Celery:
        """Fallback object so Django can start when Celery is not installed."""

        def __init__(self, *args, **kwargs):
            pass

        def config_from_object(self, *args, **kwargs):
            pass

        def autodiscover_tasks(self, *args, **kwargs):
            pass

        @property
        def conf(self):
            return self

        def update(self, *args, **kwargs):
            pass

        def task(self, *args, **kwargs):
            def decorator(func):
                return func

            return decorator


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medical_system.settings")

app = Celery("medical_system")
app.config_from_object("django.conf:settings", namespace="CELERY")

if CELERY_AVAILABLE:
    app.autodiscover_tasks()
    app.conf.update(
        timezone="UTC",
        enable_utc=True,
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        result_backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0"),
        broker_url=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
        task_always_eager=False,
        task_eager_propagates=False,
        task_ignore_result=False,
        task_store_eager_result=True,
        result_expires=3600,
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        worker_disable_rate_limits=False,
        task_compression="gzip",
        result_compression="gzip",
        task_routes={},
        beat_schedule={},
    )


if CELERY_AVAILABLE:

    @app.task(bind=True)
    def debug_task(self):
        """Debug task for testing Celery."""
        print(f"Request: {self.request!r}")

else:

    def debug_task():
        """Dummy debug task when Celery is not available."""
        print("Celery not available - debug task skipped")
