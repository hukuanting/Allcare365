"""
Django ESign Application Configuration

Electronic Signature system for medical records, forms, and encounters.
Provides HIPAA-compliant digital signatures with audit trails.
"""

from django.apps import AppConfig


class ESignConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'esign'
    verbose_name = 'Electronic Signatures'
    
    def ready(self):
        """Initialize application-specific settings"""
        # TODO: Uncomment when signals module is implemented
        # import esign.signals  # Register signal handlers
        pass
