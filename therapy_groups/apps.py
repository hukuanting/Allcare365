"""
Therapy Groups Django App Configuration
"""
from django.apps import AppConfig


class TherapyGroupsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'therapy_groups'
    verbose_name = 'Therapy Groups'

    def ready(self):
        import therapy_groups.signals
