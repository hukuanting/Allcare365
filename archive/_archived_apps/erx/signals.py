"""
Electronic Prescription (eRx) Signals

This module provides signal handlers for the eRx system to handle
prescription lifecycle events and maintain audit trails.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import ElectronicPrescription, PrescriptionHistory


@receiver(pre_save, sender=ElectronicPrescription)
def track_prescription_changes(sender, instance, **kwargs):
    """
    Track changes to prescriptions and create history records
    """
    if instance.pk:  # Only for existing prescriptions
        try:
            old_prescription = ElectronicPrescription.objects.get(pk=instance.pk)
            
            # Check for status changes
            if old_prescription.status != instance.status:
                # Status change will be logged after save
                instance._status_changed = True
                instance._old_status = old_prescription.status
                
        except ElectronicPrescription.DoesNotExist:
            pass


@receiver(post_save, sender=ElectronicPrescription)
def log_prescription_changes(sender, instance, created, **kwargs):
    """
    Log prescription changes to history
    """
    if created:
        # New prescription created
        PrescriptionHistory.objects.create(
            prescription=instance,
            action='created',
            user=instance.prescriber,
            notes=f"Prescription created for {instance.drug_name}"
        )
    elif hasattr(instance, '_status_changed') and instance._status_changed:
        # Status changed
        PrescriptionHistory.objects.create(
            prescription=instance,
            action='modified',
            user=instance.prescriber,  # In a real system, this would be the current user
            notes=f"Status changed from {instance._old_status} to {instance.status}",
            old_values={'status': instance._old_status},
            new_values={'status': instance.status}
        )
        
        # Clean up temporary attributes
        del instance._status_changed
        del instance._old_status
