"""
FHIR Integration App Configuration
"""
from django.apps import AppConfig


class FhirIntegrationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'fhir_integration'
    verbose_name = 'FHIR R4 Integration'
    
    def ready(self):
        """Initialize FHIR integration when app is ready"""
        # Import signals if any
        pass