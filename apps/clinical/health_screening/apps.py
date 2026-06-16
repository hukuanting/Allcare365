from django.apps import AppConfig


class HealthScreeningConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.clinical.health_screening'
    label = 'health_screening'
    verbose_name = '健康檢查'
