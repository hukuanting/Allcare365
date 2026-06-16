"""
Clinical Decision Support Django App Configuration
"""
from django.apps import AppConfig


class ClinicalDecisionSupportConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'clinical_decision_support'
    verbose_name = 'Clinical Decision Support'
    
    def ready(self):
        """Initialize the app"""
        # Import signals when they are created
        pass
