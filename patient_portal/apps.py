from django.apps import AppConfig


class PatientPortalConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'patient_portal'
    verbose_name = 'Patient Portal'
    
    def ready(self):
        """Initialize app when Django starts"""
        # Import signals when app is ready
        # Currently no signals are defined for this app
        pass
