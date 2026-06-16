"""
Pharmacy models for drug management, prescriptions, and inventory.
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
import uuid


class PharmacyBaseModel(models.Model):
    """Base model with common fields for pharmacy models"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='pharmacy_%(class)s_created')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='pharmacy_%(class)s_updated')
    is_active = models.BooleanField(default=True)
    
    class Meta:
        abstract = True


class DrugCategory(PharmacyBaseModel):
    """Drug therapeutic categories"""
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    parent_category = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    
    class Meta:
        db_table = 'pharmacy_drug_categories'
        verbose_name_plural = 'Drug Categories'
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return self.name


class Drug(PharmacyBaseModel):
    """Drug master data"""
    # Basic drug information
    name = models.CharField(max_length=200, help_text="Brand or trade name")
    generic_name = models.CharField(max_length=200, help_text="Generic/chemical name")
    brand_name = models.CharField(max_length=200, blank=True, help_text="Brand name if different from name")
    
    # Identification codes
    ndc_number = models.CharField(max_length=20, unique=True, help_text="National Drug Code")
    upc_code = models.CharField(max_length=20, blank=True, help_text="Universal Product Code")
    manufacturer_code = models.CharField(max_length=50, blank=True)
    
    # Drug classification
    category = models.ForeignKey(DrugCategory, on_delete=models.SET_NULL, null=True, blank=True)
    therapeutic_class = models.CharField(max_length=100, blank=True)
    pharmacologic_class = models.CharField(max_length=100, blank=True)
    
    # Physical properties
    DOSAGE_FORM_CHOICES = [
        ('tablet', 'Tablet'),
        ('capsule', 'Capsule'),
        ('liquid', 'Liquid'),
        ('injection', 'Injection'),
        ('cream', 'Cream'),
        ('ointment', 'Ointment'),
        ('drops', 'Drops'),
        ('spray', 'Spray'),
        ('patch', 'Patch'),
        ('inhaler', 'Inhaler'),
        ('suppository', 'Suppository'),
        ('other', 'Other'),
    ]
    dosage_form = models.CharField(max_length=20, choices=DOSAGE_FORM_CHOICES)
    strength = models.CharField(max_length=100, help_text="e.g., 500mg, 10mg/ml")
    unit = models.CharField(max_length=20, help_text="mg, ml, g, etc.")
    
    # Manufacturer information
    manufacturer = models.CharField(max_length=200)
    supplier = models.CharField(max_length=200, blank=True)
    
    # Regulatory information
    CONTROLLED_SUBSTANCE_CHOICES = [
        ('', 'Not Controlled'),
        ('CI', 'Schedule I'),
        ('CII', 'Schedule II'),
        ('CIII', 'Schedule III'),
        ('CIV', 'Schedule IV'),
        ('CV', 'Schedule V'),
    ]
    controlled_substance = models.CharField(max_length=5, choices=CONTROLLED_SUBSTANCE_CHOICES, blank=True)
    
    # Clinical information
    contraindications = models.TextField(blank=True)
    warnings = models.TextField(blank=True)
    side_effects = models.TextField(blank=True)
    interactions = models.TextField(blank=True)
    
    # Inventory settings
    reorder_level = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    max_level = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    
    # Pricing
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    average_wholesale_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Status
    discontinued = models.BooleanField(default=False)
    discontinued_date = models.DateField(null=True, blank=True)
    
    class Meta:
        db_table = 'pharmacy_drugs'
        indexes = [
            models.Index(fields=['ndc_number']),
            models.Index(fields=['generic_name']),
            models.Index(fields=['name']),
            models.Index(fields=['category']),
            models.Index(fields=['controlled_substance']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.strength})"


class DrugInteraction(PharmacyBaseModel):
    """Drug-to-drug interactions"""
    drug1 = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='interactions_as_drug1')
    drug2 = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='interactions_as_drug2')
    
    SEVERITY_CHOICES = [
        ('minor', 'Minor'),
        ('moderate', 'Moderate'),
        ('major', 'Major'),
        ('contraindicated', 'Contraindicated'),
    ]
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    
    description = models.TextField()
    clinical_management = models.TextField(blank=True)
    mechanism = models.TextField(blank=True)
    
    # References
    reference_source = models.CharField(max_length=200, blank=True)
    reference_date = models.DateField(null=True, blank=True)
    
    class Meta:
        db_table = 'pharmacy_drug_interactions'
        unique_together = ['drug1', 'drug2']
        indexes = [
            models.Index(fields=['severity']),
            models.Index(fields=['drug1', 'drug2']),
        ]
    
    def __str__(self):
        return f"{self.drug1.name} + {self.drug2.name} ({self.severity})"


class DrugAllergy(PharmacyBaseModel):
    """Patient drug allergies"""
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='drug_allergies')
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, null=True, blank=True)
    allergen = models.CharField(max_length=200, help_text="Drug name or allergen if drug not in system")
    
    REACTION_SEVERITY_CHOICES = [
        ('mild', 'Mild'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
        ('life_threatening', 'Life Threatening'),
    ]
    severity = models.CharField(max_length=20, choices=REACTION_SEVERITY_CHOICES)
    
    reaction_description = models.TextField()
    onset_date = models.DateField(null=True, blank=True)
    verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_allergies')
    verified_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'pharmacy_drug_allergies'
        indexes = [
            models.Index(fields=['patient']),
            models.Index(fields=['drug']),
            models.Index(fields=['severity']),
        ]
    
    def __str__(self):
        allergen_name = self.drug.name if self.drug else self.allergen
        return f"{self.patient} - {allergen_name}"


class DrugInventory(PharmacyBaseModel):
    """Drug inventory by facility and lot"""
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='inventory')
    facility = models.ForeignKey('administration.Facility', on_delete=models.CASCADE)
    warehouse = models.CharField(max_length=100, default='Main')
    
    # Lot information
    lot_number = models.CharField(max_length=50)
    expiration_date = models.DateField()
    
    # Quantities
    quantity_on_hand = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    quantity_allocated = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    
    # Cost information
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        db_table = 'pharmacy_drug_inventory'
        unique_together = ['drug', 'facility', 'lot_number']
        indexes = [
            models.Index(fields=['drug', 'facility']),
            models.Index(fields=['expiration_date']),
            models.Index(fields=['quantity_on_hand']),
        ]
    
    @property
    def quantity_available(self):
        return self.quantity_on_hand - self.quantity_allocated
    
    @property
    def total_cost(self):
        return self.quantity_on_hand * self.unit_cost
    
    def __str__(self):
        return f"{self.drug.name} - Lot {self.lot_number} ({self.quantity_on_hand} available)"


class Prescription(PharmacyBaseModel):
    """Patient prescriptions"""
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='pharmacy_prescriptions')
    provider = models.ForeignKey('administration.Provider', on_delete=models.CASCADE, related_name='pharmacy_prescriptions')
    encounter = models.ForeignKey('medical_records.MedicalRecord', on_delete=models.CASCADE, null=True, blank=True)
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE)
    
    # Prescription details
    prescribed_date = models.DateField(default=timezone.now)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    
    # Dosage information
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    quantity_dispensed = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    unit = models.CharField(max_length=20, help_text="tablets, ml, doses, etc.")
    
    # Refill information
    refills = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    refills_remaining = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    
    # Dosage instructions
    dosage_instructions = models.TextField(help_text="Complete dosage instructions")
    sig_code = models.CharField(max_length=20, blank=True, help_text="Standardized sig code")
    frequency = models.CharField(max_length=50, help_text="e.g., BID, TID, QID, PRN")
    duration = models.CharField(max_length=50, blank=True, help_text="e.g., 7 days, 2 weeks")
    
    # Route of administration
    ROUTE_CHOICES = [
        ('oral', 'Oral'),
        ('topical', 'Topical'),
        ('injection', 'Injection'),
        ('inhalation', 'Inhalation'),
        ('sublingual', 'Sublingual'),
        ('rectal', 'Rectal'),
        ('ophthalmic', 'Ophthalmic'),
        ('otic', 'Otic'),
        ('nasal', 'Nasal'),
        ('transdermal', 'Transdermal'),
    ]
    route = models.CharField(max_length=20, choices=ROUTE_CHOICES, default='oral')
    
    # Status
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('on_hold', 'On Hold'),
        ('discontinued', 'Discontinued'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Dispensing information
    pharmacy = models.CharField(max_length=200, blank=True)
    pharmacy_phone = models.CharField(max_length=20, blank=True)
    dispensed_date = models.DateField(null=True, blank=True)
    dispensed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='dispensed_prescriptions')
    
    # Clinical information
    indication = models.TextField(blank=True, help_text="Reason for prescription")
    notes = models.TextField(blank=True)
    
    # Electronic prescription
    e_prescribed = models.BooleanField(default=False)
    dea_number = models.CharField(max_length=20, blank=True)
    
    class Meta:
        db_table = 'pharmacy_prescriptions'
        indexes = [
            models.Index(fields=['patient', 'prescribed_date']),
            models.Index(fields=['provider']),
            models.Index(fields=['drug']),
            models.Index(fields=['status']),
            models.Index(fields=['prescribed_date']),
        ]
    
    def __str__(self):
        return f"{self.patient} - {self.drug.name} ({self.prescribed_date})"


class PrescriptionRefill(PharmacyBaseModel):
    """Prescription refill records"""
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='refill_records')
    refill_number = models.IntegerField(validators=[MinValueValidator(1)])
    
    # Refill details
    requested_date = models.DateField()
    approved_date = models.DateField(null=True, blank=True)
    dispensed_date = models.DateField(null=True, blank=True)
    
    quantity_dispensed = models.IntegerField(validators=[MinValueValidator(1)])
    days_supply = models.IntegerField(validators=[MinValueValidator(1)])
    
    # Personnel
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='requested_refills')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_refills')
    dispensed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='dispensed_refills')
    
    # Status
    STATUS_CHOICES = [
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('dispensed', 'Dispensed'),
        ('denied', 'Denied'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='requested')
    
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'pharmacy_prescription_refills'
        unique_together = ['prescription', 'refill_number']
        indexes = [
            models.Index(fields=['prescription']),
            models.Index(fields=['requested_date']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.prescription} - Refill #{self.refill_number}"


class InventoryTransaction(PharmacyBaseModel):
    """Inventory transactions for audit trail"""
    drug_inventory = models.ForeignKey(DrugInventory, on_delete=models.CASCADE, related_name='transactions')
    
    TRANSACTION_TYPE_CHOICES = [
        ('purchase', 'Purchase'),
        ('dispensing', 'Dispensing'),
        ('adjustment', 'Adjustment'),
        ('transfer', 'Transfer'),
        ('return', 'Return'),
        ('destruction', 'Destruction'),
        ('loss', 'Loss'),
    ]
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    
    # Quantities
    quantity_before = models.IntegerField()
    quantity_change = models.IntegerField()  # Can be negative
    quantity_after = models.IntegerField()
    
    # Reference information
    reference_number = models.CharField(max_length=50, blank=True, help_text="PO number, prescription ID, etc.")
    prescription = models.ForeignKey(Prescription, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Additional details
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    reason = models.TextField(blank=True)
    
    class Meta:
        db_table = 'pharmacy_inventory_transactions'
        indexes = [
            models.Index(fields=['drug_inventory']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['prescription']),
        ]
    
    def __str__(self):
        return f"{self.drug_inventory.drug.name} - {self.transaction_type} ({self.quantity_change:+d})"
