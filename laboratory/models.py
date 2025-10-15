"""
Laboratory management models for healthcare system.

This module handles:
- Laboratory providers and external lab interfaces
- Lab test types and reference ranges
- Lab orders and order items
- Lab results and abnormal value detection
- HL7 message processing
- Quality control and compliance
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid


class LaboratoryBaseModel(models.Model):
    """Base model with common fields for laboratory models"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='laboratory_%(class)s_created')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='laboratory_%(class)s_updated')
    is_active = models.BooleanField(default=True)
    
    class Meta:
        abstract = True


class LabProvider(LaboratoryBaseModel):
    """External laboratory providers"""
    name = models.CharField(max_length=200)
    contact_name = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    
    # Technical configuration
    INTERFACE_TYPE_CHOICES = [
        ('hl7', 'HL7 Interface'),
        ('api', 'REST API'),
        ('ftp', 'FTP Upload'),
        ('manual', 'Manual Entry'),
        ('email', 'Email Results'),
    ]
    interface_type = models.CharField(max_length=20, choices=INTERFACE_TYPE_CHOICES, default='manual')
    
    # HL7 Configuration
    hl7_config = models.JSONField(default=dict, blank=True, help_text="HL7 interface configuration")
    api_endpoint = models.URLField(blank=True)
    api_key = models.CharField(max_length=200, blank=True)
    
    # Business details
    lab_license_number = models.CharField(max_length=100, blank=True)
    clia_number = models.CharField(max_length=20, blank=True, help_text="Clinical Laboratory Improvement Amendments number")
    
    # Operational
    average_turnaround_time = models.IntegerField(default=24, help_text="Average TAT in hours")
    is_preferred = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'laboratory_providers'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['interface_type']),
            models.Index(fields=['is_preferred']),
        ]
    
    def __str__(self):
        return self.name


class LabTestCategory(LaboratoryBaseModel):
    """Laboratory test categories for organization"""
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    parent_category = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    sort_order = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'laboratory_test_categories'
        verbose_name_plural = 'Lab Test Categories'
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['name']),
            models.Index(fields=['sort_order']),
        ]
    
    def __str__(self):
        return self.name


class LabTestType(LaboratoryBaseModel):
    """Types of laboratory tests available"""
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50, blank=True)
    category = models.ForeignKey(LabTestCategory, on_delete=models.CASCADE, related_name='tests')
    
    # Medical coding
    loinc_code = models.CharField(max_length=20, blank=True, help_text="Logical Observation Identifiers Names and Codes")
    cpt_code = models.CharField(max_length=20, blank=True, help_text="Current Procedural Terminology code")
    snomed_code = models.CharField(max_length=20, blank=True, help_text="SNOMED CT code")
    
    # Specimen information
    SPECIMEN_TYPE_CHOICES = [
        ('blood', 'Blood'),
        ('serum', 'Serum'),
        ('plasma', 'Plasma'),
        ('urine', 'Urine'),
        ('stool', 'Stool'),
        ('sputum', 'Sputum'),
        ('csf', 'Cerebrospinal Fluid'),
        ('tissue', 'Tissue'),
        ('swab', 'Swab'),
        ('other', 'Other'),
    ]
    specimen_type = models.CharField(max_length=20, choices=SPECIMEN_TYPE_CHOICES)
    specimen_volume = models.CharField(max_length=50, blank=True, help_text="Required specimen volume")
    collection_instructions = models.TextField(blank=True)
    
    # Reference ranges and units
    units = models.CharField(max_length=50, blank=True)
    reference_range_male = models.CharField(max_length=200, blank=True)
    reference_range_female = models.CharField(max_length=200, blank=True)
    reference_range_pediatric = models.CharField(max_length=200, blank=True)
    critical_low = models.CharField(max_length=50, blank=True)
    critical_high = models.CharField(max_length=50, blank=True)
    
    # Result configuration
    RESULT_TYPE_CHOICES = [
        ('numeric', 'Numeric'),
        ('text', 'Text'),
        ('coded', 'Coded'),
        ('binary', 'Binary (Positive/Negative)'),
    ]
    result_type = models.CharField(max_length=20, choices=RESULT_TYPE_CHOICES, default='numeric')
    possible_values = models.JSONField(default=list, blank=True, help_text="Possible values for coded results")
    
    # Operational
    average_tat = models.IntegerField(default=24, help_text="Average turnaround time in hours")
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    requires_fasting = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'laboratory_test_types'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['loinc_code']),
            models.Index(fields=['cpt_code']),
            models.Index(fields=['category']),
            models.Index(fields=['specimen_type']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.specimen_type})"


class LabOrder(LaboratoryBaseModel):
    """Laboratory orders placed by providers"""
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='laboratory_orders')
    provider = models.ForeignKey('administration.Provider', on_delete=models.CASCADE, related_name='laboratory_orders')
    encounter = models.ForeignKey('medical_records.MedicalRecord', on_delete=models.CASCADE, null=True, blank=True)
    lab_provider = models.ForeignKey(LabProvider, on_delete=models.CASCADE)
    
    # Order details
    order_number = models.CharField(max_length=50, unique=True)
    order_date = models.DateTimeField(default=timezone.now)
    
    PRIORITY_CHOICES = [
        ('routine', 'Routine'),
        ('urgent', 'Urgent'),
        ('stat', 'STAT'),
        ('asap', 'ASAP'),
    ]
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='routine')
    
    # Clinical information
    clinical_info = models.TextField(blank=True, help_text="Clinical indication and relevant history")
    diagnosis_codes = models.JSONField(default=list, blank=True, help_text="ICD-10 diagnosis codes")
    
    # Collection information
    collection_date = models.DateTimeField(null=True, blank=True)
    collection_location = models.CharField(max_length=200, blank=True)
    collector_name = models.CharField(max_length=200, blank=True)
    
    # Status tracking
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('collected', 'Collected'),
        ('received', 'Received by Lab'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    status_notes = models.TextField(blank=True)
    
    # External references
    external_order_id = models.CharField(max_length=100, blank=True)
    hl7_message_id = models.CharField(max_length=100, blank=True)
    
    # Billing
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    insurance_coverage = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'laboratory_orders'
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['patient']),
            models.Index(fields=['provider']),
            models.Index(fields=['order_date']),
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
        ]
    
    def __str__(self):
        return f"Lab Order {self.order_number} - {self.patient}"
    
    def generate_order_number(self):
        """Generate unique order number"""
        if not self.order_number:
            from django.utils import timezone
            import random
            date_str = timezone.now().strftime('%Y%m%d')
            random_str = f"{random.randint(1000, 9999)}"
            self.order_number = f"LAB{date_str}{random_str}"
    
    def save(self, *args, **kwargs):
        self.generate_order_number()
        super().save(*args, **kwargs)


class LabOrderItem(LaboratoryBaseModel):
    """Individual test items within a lab order"""
    lab_order = models.ForeignKey(LabOrder, on_delete=models.CASCADE, related_name='order_items')
    test_type = models.ForeignKey(LabTestType, on_delete=models.CASCADE)
    
    # Item-specific details
    specimen_id = models.CharField(max_length=50, blank=True)
    collection_tube = models.CharField(max_length=50, blank=True)
    
    # Status (can be different from overall order status)
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('collected', 'Collected'),
        ('received', 'Received'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Billing
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    class Meta:
        db_table = 'laboratory_order_items'
        unique_together = ['lab_order', 'test_type']
        indexes = [
            models.Index(fields=['lab_order']),
            models.Index(fields=['test_type']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.lab_order.order_number} - {self.test_type.name}"


class LabResult(LaboratoryBaseModel):
    """Laboratory test results"""
    order_item = models.ForeignKey(LabOrderItem, on_delete=models.CASCADE, related_name='results')
    
    # Result values
    result_value = models.TextField(help_text="Primary result value")
    result_text = models.TextField(blank=True, help_text="Additional text or interpretation")
    units = models.CharField(max_length=50, blank=True)
    reference_range = models.CharField(max_length=200, blank=True)
    
    # Abnormal flags
    ABNORMAL_FLAG_CHOICES = [
        ('', 'Normal'),
        ('L', 'Low'),
        ('H', 'High'),
        ('LL', 'Critical Low'),
        ('HH', 'Critical High'),
        ('A', 'Abnormal'),
        ('AA', 'Critical'),
        ('>', 'Above Instrument Scale'),
        ('<', 'Below Instrument Scale'),
    ]
    abnormal_flag = models.CharField(max_length=10, choices=ABNORMAL_FLAG_CHOICES, blank=True)
    
    # Result metadata
    result_date = models.DateTimeField(default=timezone.now)
    result_status = models.CharField(max_length=20, choices=[
        ('preliminary', 'Preliminary'),
        ('final', 'Final'),
        ('corrected', 'Corrected'),
        ('amended', 'Amended'),
    ], default='final')
    
    # Quality control
    instrument_id = models.CharField(max_length=100, blank=True)
    technician_id = models.CharField(max_length=100, blank=True)
    
    # Verification
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_lab_results')
    verified_date = models.DateTimeField(null=True, blank=True)
    pathologist_review = models.BooleanField(default=False)
    pathologist_notes = models.TextField(blank=True)
    
    # External references
    external_result_id = models.CharField(max_length=100, blank=True)
    hl7_message_id = models.CharField(max_length=100, blank=True)
    
    class Meta:
        db_table = 'laboratory_results'
        indexes = [
            models.Index(fields=['order_item']),
            models.Index(fields=['result_date']),
            models.Index(fields=['abnormal_flag']),
            models.Index(fields=['result_status']),
            models.Index(fields=['verified_date']),
        ]
    
    def __str__(self):
        return f"{self.order_item.test_type.name}: {self.result_value}"
    
    @property
    def is_critical(self):
        """Check if result is critical"""
        return self.abnormal_flag in ['LL', 'HH', 'AA']
    
    @property
    def is_abnormal(self):
        """Check if result is abnormal"""
        return bool(self.abnormal_flag)


class LabMessage(LaboratoryBaseModel):
    """HL7 messages for lab communication"""
    lab_provider = models.ForeignKey(LabProvider, on_delete=models.CASCADE)
    
    MESSAGE_TYPE_CHOICES = [
        ('ORM', 'Order Message'),
        ('ORU', 'Result Message'),
        ('ADT', 'Patient Admin'),
        ('ACK', 'Acknowledgment'),
    ]
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPE_CHOICES)
    
    # Message content
    raw_message = models.TextField(help_text="Raw HL7 message")
    parsed_data = models.JSONField(default=dict, blank=True)
    
    # Processing status
    PROCESSING_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
        ('rejected', 'Rejected'),
    ]
    processing_status = models.CharField(max_length=20, choices=PROCESSING_STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True)
    
    # References
    lab_order = models.ForeignKey(LabOrder, on_delete=models.SET_NULL, null=True, blank=True)
    external_message_id = models.CharField(max_length=100, blank=True)
    
    class Meta:
        db_table = 'laboratory_messages'
        indexes = [
            models.Index(fields=['message_type']),
            models.Index(fields=['processing_status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['lab_provider']),
        ]
    
    def __str__(self):
        return f"{self.message_type} - {self.processing_status}"


class QualityControlLog(LaboratoryBaseModel):
    """Quality control and calibration records"""
    lab_provider = models.ForeignKey(LabProvider, on_delete=models.CASCADE)
    test_type = models.ForeignKey(LabTestType, on_delete=models.CASCADE)
    
    QC_TYPE_CHOICES = [
        ('calibration', 'Calibration'),
        ('control', 'Quality Control'),
        ('proficiency', 'Proficiency Testing'),
        ('maintenance', 'Instrument Maintenance'),
    ]
    qc_type = models.CharField(max_length=20, choices=QC_TYPE_CHOICES)
    
    # QC details
    control_lot = models.CharField(max_length=50, blank=True)
    expected_value = models.CharField(max_length=100, blank=True)
    measured_value = models.CharField(max_length=100, blank=True)
    acceptable_range = models.CharField(max_length=100, blank=True)
    
    # Status
    passed = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    # Technician
    performed_by = models.CharField(max_length=200, blank=True)
    instrument_id = models.CharField(max_length=100, blank=True)
    
    class Meta:
        db_table = 'laboratory_qc_logs'
        indexes = [
            models.Index(fields=['test_type']),
            models.Index(fields=['qc_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['passed']),
        ]
    
    def __str__(self):
        return f"{self.test_type.name} - {self.qc_type} ({self.created_at.date()})"
