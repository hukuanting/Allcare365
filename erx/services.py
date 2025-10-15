"""
Electronic Prescription (eRx) Services

This module provides business logic for the eRx system including
prescription management, drug interaction checking, formulary validation,
and external service integration.
"""

from typing import List, Dict, Optional, Tuple
from django.db import transaction, models
from django.db.models import Q, Count
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import timedelta
import logging

from .models import (
    ElectronicPrescription,
    PrescriptionRefill,
    PrescriptionHistory,
    DrugFormulary,
    DrugInteraction,
    PharmacyDirectory
)
from patients.models import Patient

logger = logging.getLogger(__name__)


class ErxService:
    """
    Main service class for electronic prescription management
    """
    
    @staticmethod
    def create_prescription(
        patient: Patient,
        prescriber: User,
        prescription_data: Dict,
        check_interactions: bool = True
    ) -> ElectronicPrescription:
        """
        Create a new electronic prescription
        
        Args:
            patient: Patient object
            prescriber: Prescriber user
            prescription_data: Prescription details
            check_interactions: Whether to check drug interactions
            
        Returns:
            ElectronicPrescription object
        """
        try:
            with transaction.atomic():
                # Create prescription
                prescription = ElectronicPrescription.objects.create(
                    patient=patient,
                    prescriber=prescriber,
                    **prescription_data
                )
                
                # Check drug interactions if requested
                if check_interactions:
                    interactions = ErxService.check_drug_interactions(
                        prescription.drug_name,
                        patient
                    )
                    if interactions:
                        # Log interactions but don't block prescription
                        logger.warning(
                            f"Drug interactions found for prescription {prescription.prescription_id}: "
                            f"{interactions}"
                        )
                
                # Create history record
                PrescriptionHistory.objects.create(
                    prescription=prescription,
                    action='created',
                    user=prescriber,
                    notes=f"Prescription created for {prescription.drug_name}"
                )
                
                logger.info(f"Prescription created: {prescription.prescription_id}")
                return prescription
                
        except Exception as e:
            logger.error(f"Error creating prescription: {str(e)}")
            raise
    
    @staticmethod
    def send_prescription(
        prescription: ElectronicPrescription,
        user: User
    ) -> bool:
        """
        Send prescription to pharmacy
        
        Args:
            prescription: Prescription to send
            user: User sending the prescription
            
        Returns:
            Boolean indicating success
        """
        try:
            with transaction.atomic():
                # Validate prescription before sending
                if not ErxService.validate_prescription(prescription):
                    raise ValueError("Prescription validation failed")
                
                # Update prescription status
                prescription.status = 'sent'
                prescription.date_sent = timezone.now()
                prescription.save()
                
                # Create history record
                PrescriptionHistory.objects.create(
                    prescription=prescription,
                    action='sent',
                    user=user,
                    notes=f"Prescription sent to pharmacy {prescription.pharmacy_name}"
                )
                
                # Here you would integrate with external eRx service
                # For now, we'll simulate successful transmission
                
                logger.info(f"Prescription sent: {prescription.prescription_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error sending prescription: {str(e)}")
            return False
    
    @staticmethod
    def validate_prescription(prescription: ElectronicPrescription) -> bool:
        """
        Validate prescription before sending
        
        Args:
            prescription: Prescription to validate
            
        Returns:
            Boolean indicating if valid
        """
        errors = []
        
        # Check required fields
        if not prescription.drug_name:
            errors.append("Drug name is required")
        
        if not prescription.directions:
            errors.append("Directions are required")
        
        if prescription.quantity <= 0:
            errors.append("Quantity must be positive")
        
        if prescription.days_supply <= 0:
            errors.append("Days supply must be positive")
        
        # Check pharmacy information
        if not prescription.pharmacy_ncpdp and not prescription.pharmacy_name:
            errors.append("Pharmacy information is required")
        
        # Check controlled substance requirements
        if prescription.controlled_substance:
            if not prescription.diagnosis_code:
                errors.append("Diagnosis code required for controlled substances")
        
        # Check expiration
        if prescription.expiration_date and prescription.expiration_date < timezone.now().date():
            errors.append("Prescription has expired")
        
        if errors:
            logger.error(f"Prescription validation errors: {errors}")
            return False
        
        return True
    
    @staticmethod
    def check_drug_interactions(
        drug_name: str,
        patient: Patient
    ) -> List[Dict]:
        """
        Check for drug interactions
        
        Args:
            drug_name: Name of the drug to check
            patient: Patient object
            
        Returns:
            List of interaction dictionaries
        """
        interactions = []
        
        # Get patient's current medications
        current_prescriptions = ElectronicPrescription.objects.filter(
            patient=patient,
            status__in=['sent', 'accepted'],
            expiration_date__gte=timezone.now().date()
        )
        
        current_drugs = [p.drug_name for p in current_prescriptions]
        
        # Check interactions with current medications
        for current_drug in current_drugs:
            drug_interactions = DrugInteraction.objects.filter(
                Q(drug1_name__icontains=drug_name, drug2_name__icontains=current_drug) |
                Q(drug1_name__icontains=current_drug, drug2_name__icontains=drug_name)
            )
            
            for interaction in drug_interactions:
                interactions.append({
                    'drug1': interaction.drug1_name,
                    'drug2': interaction.drug2_name,
                    'severity': interaction.interaction_severity,
                    'description': interaction.interaction_description,
                    'management': interaction.clinical_management
                })
        
        return interactions
    
    @staticmethod
    def check_formulary(
        drug_name: str,
        patient: Patient
    ) -> Optional[Dict]:
        """
        Check drug formulary status
        
        Args:
            drug_name: Name of the drug
            patient: Patient object
            
        Returns:
            Formulary information or None
        """
        # This would integrate with patient's insurance formulary
        # For now, we'll check our local formulary database
        try:
            formulary = DrugFormulary.objects.filter(
                drug_name__icontains=drug_name
            ).first()
            
            if formulary:
                return {
                    'drug_name': formulary.drug_name,
                    'formulary_status': formulary.formulary_status,
                    'tier_level': formulary.tier_level,
                    'copay_amount': formulary.copay_amount,
                    'prior_auth_required': formulary.prior_auth_required,
                    'quantity_limit': formulary.quantity_limit
                }
        except Exception as e:
            logger.error(f"Error checking formulary: {str(e)}")
        
        return None
    
    @staticmethod
    def search_pharmacies(
        search_criteria: Dict
    ) -> List[PharmacyDirectory]:
        """
        Search for pharmacies
        
        Args:
            search_criteria: Search parameters
            
        Returns:
            List of pharmacy objects
        """
        query = PharmacyDirectory.objects.filter(is_active=True)
        
        if search_criteria.get('search_term'):
            query = query.filter(
                Q(name__icontains=search_criteria['search_term']) |
                Q(address_line1__icontains=search_criteria['search_term'])
            )
        
        if search_criteria.get('city'):
            query = query.filter(city__icontains=search_criteria['city'])
        
        if search_criteria.get('state'):
            query = query.filter(state__iexact=search_criteria['state'])
        
        if search_criteria.get('zip_code'):
            query = query.filter(zip_code__startswith=search_criteria['zip_code'])
        
        if search_criteria.get('accepts_erx'):
            query = query.filter(accepts_erx=True)
        
        if search_criteria.get('accepts_controlled_substances'):
            query = query.filter(accepts_controlled_substances=True)
        
        return query.order_by('name')[:50]  # Limit results
    
    @staticmethod
    def cancel_prescription(
        prescription: ElectronicPrescription,
        user: User,
        reason: str = ""
    ) -> bool:
        """
        Cancel a prescription
        
        Args:
            prescription: Prescription to cancel
            user: User canceling the prescription
            reason: Reason for cancellation
            
        Returns:
            Boolean indicating success
        """
        try:
            with transaction.atomic():
                # Check if prescription can be cancelled
                if prescription.status in ['cancelled', 'expired']:
                    raise ValueError("Prescription already cancelled or expired")
                
                # Update status
                old_status = prescription.status
                prescription.status = 'cancelled'
                prescription.save()
                
                # Create history record
                PrescriptionHistory.objects.create(
                    prescription=prescription,
                    action='cancelled',
                    user=user,
                    notes=f"Prescription cancelled: {reason}",
                    old_values={'status': old_status},
                    new_values={'status': 'cancelled'}
                )
                
                logger.info(f"Prescription cancelled: {prescription.prescription_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error cancelling prescription: {str(e)}")
            return False
    
    @staticmethod
    def process_refill(
        prescription: ElectronicPrescription,
        refill_data: Dict,
        user: User
    ) -> Optional[PrescriptionRefill]:
        """
        Process a prescription refill
        
        Args:
            prescription: Original prescription
            refill_data: Refill details
            user: User processing the refill
            
        Returns:
            PrescriptionRefill object or None
        """
        try:
            with transaction.atomic():
                # Check if refills are available
                if prescription.refills_remaining <= 0:
                    raise ValueError("No refills remaining")
                
                # Check if prescription is expired
                if prescription.is_expired:
                    raise ValueError("Prescription has expired")
                
                # Create refill record
                refill_number = prescription.prescription_refills.count() + 1
                refill = PrescriptionRefill.objects.create(
                    prescription=prescription,
                    refill_number=refill_number,
                    **refill_data
                )
                
                # Create history record
                PrescriptionHistory.objects.create(
                    prescription=prescription,
                    action='refilled',
                    user=user,
                    notes=f"Refill {refill_number} processed"
                )
                
                logger.info(f"Refill processed: {prescription.prescription_id}")
                return refill
                
        except Exception as e:
            logger.error(f"Error processing refill: {str(e)}")
            return None
    
    @staticmethod
    def get_patient_prescriptions(
        patient: Patient,
        status: Optional[str] = None,
        active_only: bool = False
    ) -> List[ElectronicPrescription]:
        """
        Get prescriptions for a patient
        
        Args:
            patient: Patient object
            status: Optional status filter
            active_only: Only return active prescriptions
            
        Returns:
            List of prescription objects
        """
        query = ElectronicPrescription.objects.filter(patient=patient)
        
        if status:
            query = query.filter(status=status)
        
        if active_only:
            query = query.filter(
                status__in=['sent', 'accepted'],
                expiration_date__gte=timezone.now().date()
            )
        
        return query.order_by('-date_prescribed')
    
    @staticmethod
    def get_prescription_analytics(
        user: User,
        start_date: Optional[timezone.datetime] = None,
        end_date: Optional[timezone.datetime] = None
    ) -> Dict:
        """
        Get prescription analytics for a user
        
        Args:
            user: User (prescriber)
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            Dictionary with analytics data
        """
        query = ElectronicPrescription.objects.filter(prescriber=user)
        
        if start_date:
            query = query.filter(date_prescribed__gte=start_date)
        
        if end_date:
            query = query.filter(date_prescribed__lte=end_date)
        
        total_prescriptions = query.count()
        
        # Status breakdown
        status_counts = {}
        for status_choice in ElectronicPrescription.STATUS_CHOICES:
            status = status_choice[0]
            count = query.filter(status=status).count()
            status_counts[status] = count
        
        # Top prescribed drugs
        top_drugs = (
            query.values('drug_name')
            .annotate(count=Count('drug_name'))
            .order_by('-count')[:10]
        )
        
        # Controlled substances
        controlled_count = query.filter(controlled_substance=True).count()
        
        return {
            'total_prescriptions': total_prescriptions,
            'status_breakdown': status_counts,
            'top_drugs': list(top_drugs),
            'controlled_substances': controlled_count,
            'date_range': {
                'start': start_date,
                'end': end_date
            }
        }
