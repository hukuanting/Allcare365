"""
Electronic Prescription (eRx) Models

This module defines the models for electronic prescription management,
including prescriptions, drug interactions, formulary information,
and prescription history.
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
import uuid

from patients.models import Patient


class ErxBaseModel(models.Model):
    """Base model for eRx system with custom related names"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='erx_%(class)s_created'
    )
    updated_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='erx_%(class)s_updated'
    )
    is_active = models.BooleanField(default=True)
    
    class Meta:
        abstract = True


class DrugFormulary(ErxBaseModel):
    """
    Drug formulary information for insurance and healthcare plans
    """
    
    FORMULARY_STATUS_CHOICES = [
        ('preferred', _('Preferred')),
        ('non_preferred', _('Non-Preferred')),
        ('prior_auth', _('Prior Authorization Required')),
        ('step_therapy', _('Step Therapy Required')),
        ('not_covered', _('Not Covered')),
    ]
    
    drug_name = models.CharField(
        max_length=255,
        help_text=_("Name of the drug")
    )
    
    generic_name = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Generic name of the drug")
    )
    
    ndc_number = models.CharField(
        max_length=20,
        blank=True,
        help_text=_("National Drug Code number")
    )
    
    rxnorm_code = models.CharField(
        max_length=20,
        blank=True,
        help_text=_("RxNorm code")
    )
    
    formulary_status = models.CharField(
        max_length=20,
        choices=FORMULARY_STATUS_CHOICES,
        default='preferred',
        help_text=_("Status in formulary")
    )
    
    tier_level = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text=_("Formulary tier level")
    )
    
    copay_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Copay amount")
    )
    
    prior_auth_required = models.BooleanField(
        default=False,
        help_text=_("Prior authorization required")
    )
    
    quantity_limit = models.IntegerField(
        null=True,
        blank=True,
        help_text=_("Quantity limit per prescription")
    )
    
    class Meta:
        db_table = 'erx_drug_formulary'
        verbose_name = _('Drug Formulary')
        verbose_name_plural = _('Drug Formularies')
        indexes = [
            models.Index(fields=['drug_name']),
            models.Index(fields=['ndc_number']),
            models.Index(fields=['rxnorm_code']),
        ]


class DrugInteraction(ErxBaseModel):
    """
    Drug-drug interaction information for eRx system
    """
    
    SEVERITY_CHOICES = [
        ('minor', _('Minor')),
        ('moderate', _('Moderate')),
        ('major', _('Major')),
        ('contraindicated', _('Contraindicated')),
    ]
    
    drug1_name = models.CharField(
        max_length=255,
        help_text=_("First drug name")
    )
    
    drug2_name = models.CharField(
        max_length=255,
        help_text=_("Second drug name")
    )
    
    interaction_severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        help_text=_("Severity of interaction")
    )
    
    interaction_description = models.TextField(
        help_text=_("Description of the interaction")
    )
    
    clinical_management = models.TextField(
        blank=True,
        help_text=_("Clinical management recommendations")
    )
    
    reference_source = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Source of interaction information")
    )
    
    class Meta:
        db_table = 'erx_drug_interactions'
        verbose_name = _('eRx Drug Interaction')
        verbose_name_plural = _('eRx Drug Interactions')
        indexes = [
            models.Index(fields=['drug1_name', 'drug2_name']),
            models.Index(fields=['interaction_severity']),
        ]


class ElectronicPrescription(ErxBaseModel):
    """
    Electronic prescription model
    """
    
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('pending', _('Pending')),
        ('sent', _('Sent')),
        ('accepted', _('Accepted')),
        ('rejected', _('Rejected')),
        ('cancelled', _('Cancelled')),
        ('expired', _('Expired')),
    ]
    
    PRESCRIPTION_TYPE_CHOICES = [
        ('new', _('New Prescription')),
        ('refill', _('Refill')),
        ('change', _('Change')),
        ('cancel', _('Cancel')),
    ]
    
    # Basic information
    prescription_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        help_text=_("Unique prescription identifier")
    )
    
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='electronic_prescriptions',
        help_text=_("Patient for this prescription")
    )
    
    prescriber = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='prescribed_medications',
        help_text=_("Prescribing physician")
    )
    
    prescription_type = models.CharField(
        max_length=20,
        choices=PRESCRIPTION_TYPE_CHOICES,
        default='new',
        help_text=_("Type of prescription")
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        help_text=_("Current status")
    )
    
    # Drug information
    drug_name = models.CharField(
        max_length=255,
        help_text=_("Name of prescribed drug")
    )
    
    generic_name = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Generic name of drug")
    )
    
    strength = models.CharField(
        max_length=50,
        help_text=_("Drug strength")
    )
    
    dosage_form = models.CharField(
        max_length=50,
        help_text=_("Dosage form (tablet, capsule, etc.)")
    )
    
    ndc_number = models.CharField(
        max_length=20,
        blank=True,
        help_text=_("National Drug Code")
    )
    
    rxnorm_code = models.CharField(
        max_length=20,
        blank=True,
        help_text=_("RxNorm code")
    )
    
    # Prescription details
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text=_("Quantity to dispense")
    )
    
    quantity_unit = models.CharField(
        max_length=20,
        default='tablets',
        help_text=_("Unit of quantity")
    )
    
    days_supply = models.IntegerField(
        help_text=_("Days supply")
    )
    
    refills = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(11)],
        help_text=_("Number of refills")
    )
    
    # Dosing instructions
    sig_code = models.CharField(
        max_length=10,
        blank=True,
        help_text=_("Sig code")
    )
    
    directions = models.TextField(
        help_text=_("Directions for use")
    )
    
    # Prescription dates
    date_prescribed = models.DateTimeField(
        default=timezone.now,
        help_text=_("Date prescription was written")
    )
    
    date_sent = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Date prescription was sent")
    )
    
    effective_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Effective date")
    )
    
    expiration_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Expiration date")
    )
    
    # Pharmacy information
    pharmacy_ncpdp = models.CharField(
        max_length=20,
        blank=True,
        help_text=_("Pharmacy NCPDP ID")
    )
    
    pharmacy_name = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Pharmacy name")
    )
    
    pharmacy_address = models.TextField(
        blank=True,
        help_text=_("Pharmacy address")
    )
    
    pharmacy_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text=_("Pharmacy phone")
    )
    
    # Clinical information
    diagnosis_code = models.CharField(
        max_length=20,
        blank=True,
        help_text=_("ICD-10 diagnosis code")
    )
    
    clinical_notes = models.TextField(
        blank=True,
        help_text=_("Clinical notes")
    )
    
    # Flags
    dispense_as_written = models.BooleanField(
        default=False,
        help_text=_("Dispense as written (DAW)")
    )
    
    controlled_substance = models.BooleanField(
        default=False,
        help_text=_("Is controlled substance")
    )
    
    # External system integration
    external_prescription_id = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("External system prescription ID")
    )
    
    transmission_method = models.CharField(
        max_length=20,
        blank=True,
        help_text=_("Transmission method")
    )
    
    # Response information
    response_message = models.TextField(
        blank=True,
        help_text=_("Response message from pharmacy")
    )
    
    response_code = models.CharField(
        max_length=20,
        blank=True,
        help_text=_("Response code")
    )
    
    class Meta:
        db_table = 'erx_electronic_prescriptions'
        verbose_name = _('Electronic Prescription')
        verbose_name_plural = _('Electronic Prescriptions')
        indexes = [
            models.Index(fields=['patient', 'date_prescribed']),
            models.Index(fields=['prescriber', 'date_prescribed']),
            models.Index(fields=['status']),
            models.Index(fields=['prescription_id']),
        ]
        ordering = ['-date_prescribed']
    
    def __str__(self):
        return f"{self.drug_name} for {self.patient.full_name} by {self.prescriber.get_full_name()}"
    
    @property
    def is_controlled_substance(self):
        """Check if this is a controlled substance"""
        return self.controlled_substance
    
    @property
    def is_expired(self):
        """Check if prescription has expired"""
        if self.expiration_date:
            return timezone.now().date() > self.expiration_date
        return False
    
    @property
    def refills_remaining(self):
        """Calculate remaining refills"""
        return max(0, self.refills - self.prescription_refills.count())


class PrescriptionRefill(ErxBaseModel):
    """
    Model for tracking prescription refills
    """
    
    prescription = models.ForeignKey(
        ElectronicPrescription,
        on_delete=models.CASCADE,
        related_name='prescription_refills',
        help_text=_("Original prescription")
    )
    
    refill_number = models.IntegerField(
        help_text=_("Refill number")
    )
    
    date_filled = models.DateTimeField(
        help_text=_("Date refill was filled")
    )
    
    quantity_dispensed = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text=_("Quantity dispensed")
    )
    
    days_supply = models.IntegerField(
        help_text=_("Days supply for this refill")
    )
    
    pharmacy_ncpdp = models.CharField(
        max_length=20,
        blank=True,
        help_text=_("Pharmacy NCPDP ID")
    )
    
    pharmacist = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Dispensing pharmacist")
    )
    
    class Meta:
        db_table = 'erx_prescription_refills'
        verbose_name = _('Prescription Refill')
        verbose_name_plural = _('Prescription Refills')
        indexes = [
            models.Index(fields=['prescription', 'refill_number']),
            models.Index(fields=['date_filled']),
        ]
        ordering = ['-date_filled']
    
    def __str__(self):
        return f"Refill {self.refill_number} for {self.prescription}"


class PrescriptionHistory(ErxBaseModel):
    """
    Model for tracking prescription history and changes
    """
    
    ACTION_CHOICES = [
        ('created', _('Created')),
        ('modified', _('Modified')),
        ('sent', _('Sent')),
        ('accepted', _('Accepted')),
        ('rejected', _('Rejected')),
        ('cancelled', _('Cancelled')),
    ]
    
    prescription = models.ForeignKey(
        ElectronicPrescription,
        on_delete=models.CASCADE,
        related_name='history',
        help_text=_("Related prescription")
    )
    
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        help_text=_("Action performed")
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        help_text=_("User who performed action")
    )
    
    timestamp = models.DateTimeField(
        default=timezone.now,
        help_text=_("When action was performed")
    )
    
    notes = models.TextField(
        blank=True,
        help_text=_("Additional notes")
    )
    
    old_values = models.JSONField(
        default=dict,
        help_text=_("Previous values")
    )
    
    new_values = models.JSONField(
        default=dict,
        help_text=_("New values")
    )
    
    class Meta:
        db_table = 'erx_prescription_history'
        verbose_name = _('Prescription History')
        verbose_name_plural = _('Prescription Histories')
        indexes = [
            models.Index(fields=['prescription', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.action} by {self.user.username} at {self.timestamp}"


class PharmacyDirectory(ErxBaseModel):
    """
    Directory of pharmacies for electronic prescriptions
    """
    
    ncpdp_id = models.CharField(
        max_length=20,
        unique=True,
        help_text=_("NCPDP ID")
    )
    
    name = models.CharField(
        max_length=255,
        help_text=_("Pharmacy name")
    )
    
    address_line1 = models.CharField(
        max_length=255,
        help_text=_("Address line 1")
    )
    
    address_line2 = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Address line 2")
    )
    
    city = models.CharField(
        max_length=100,
        help_text=_("City")
    )
    
    state = models.CharField(
        max_length=2,
        help_text=_("State")
    )
    
    zip_code = models.CharField(
        max_length=10,
        help_text=_("ZIP code")
    )
    
    phone = models.CharField(
        max_length=20,
        help_text=_("Phone number")
    )
    
    fax = models.CharField(
        max_length=20,
        blank=True,
        help_text=_("Fax number")
    )
    
    email = models.EmailField(
        blank=True,
        help_text=_("Email address")
    )
    
    # Capabilities
    accepts_erx = models.BooleanField(
        default=True,
        help_text=_("Accepts electronic prescriptions")
    )
    
    accepts_controlled_substances = models.BooleanField(
        default=False,
        help_text=_("Accepts controlled substances")
    )
    
    hours_operation = models.JSONField(
        default=dict,
        help_text=_("Hours of operation")
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text=_("Is pharmacy active")
    )
    
    last_updated = models.DateTimeField(
        auto_now=True,
        help_text=_("Last updated")
    )
    
    class Meta:
        db_table = 'erx_pharmacy_directory'
        verbose_name = _('Pharmacy')
        verbose_name_plural = _('Pharmacies')
        indexes = [
            models.Index(fields=['ncpdp_id']),
            models.Index(fields=['name']),
            models.Index(fields=['city', 'state']),
        ]
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.city}, {self.state})"
    
    @property
    def full_address(self):
        """Get full address string"""
        address = self.address_line1
        if self.address_line2:
            address += f", {self.address_line2}"
        address += f", {self.city}, {self.state} {self.zip_code}"
        return address
