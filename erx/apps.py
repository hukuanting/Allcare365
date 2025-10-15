"""
Electronic Prescription (eRx) System

This module provides comprehensive electronic prescription functionality
including prescription management, drug interactions, formulary checking,
and integration with external e-prescription services.
"""

from django.apps import AppConfig


class ErxConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'erx'
    verbose_name = 'Electronic Prescription (eRx) System'
    
    def ready(self):
        """Initialize the eRx system when the app is ready"""
        import erx.signals
