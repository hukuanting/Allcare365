"""
Celery configuration for Medical System project.
"""
import os
try:
    from celery import Celery
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    # Create a dummy Celery class for when celery is not installed
    class Celery:
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

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medical_system.settings')

app = Celery('medical_system')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
if CELERY_AVAILABLE:
    app.autodiscover_tasks()

# Celery configuration
if CELERY_AVAILABLE:
    app.conf.update(
    timezone='UTC',
    enable_utc=True,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    result_backend='redis://redis:6379/0',
    broker_url='redis://redis:6379/0',
    task_always_eager=False,
    task_eager_propagates=False,
    task_ignore_result=False,
    task_store_eager_result=True,
    result_expires=3600,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    task_compression='gzip',
    result_compression='gzip',
    task_routes={
        'appointments.tasks.*': {'queue': 'appointments'},
        'notifications.tasks.*': {'queue': 'notifications'},
        'billing.tasks.*': {'queue': 'billing'},
        'reports.tasks.*': {'queue': 'reports'},
    },
    beat_schedule={
        'check-appointment-reminders': {
            'task': 'appointments.tasks.send_appointment_reminders',
            'schedule': 300.0,  # Every 5 minutes
        },
        'process-billing-queue': {
            'task': 'billing.tasks.process_billing_queue',
            'schedule': 600.0,  # Every 10 minutes
        },
        'generate-daily-reports': {
            'task': 'reports.tasks.generate_daily_report',
            'schedule': 86400.0,  # Daily
        },
        'cleanup-old-logs': {
            'task': 'logs.tasks.cleanup_old_logs',
            'schedule': 604800.0,  # Weekly
        },
    },
    )

if CELERY_AVAILABLE:
    @app.task(bind=True)
    def debug_task(self):
        """Debug task for testing Celery."""
        print(f'Request: {self.request!r}')
else:
    def debug_task():
        """Dummy debug task when Celery is not available."""
        print('Celery not available - debug task skipped')
