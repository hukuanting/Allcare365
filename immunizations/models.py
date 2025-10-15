from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.contrib.auth.models import User
import uuid


class BaseModel(models.Model):
    """Base model with common fields for all models"""
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='%(class)s_created')
    updated_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='%(class)s_updated')
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class VaccineManufacturer(BaseModel):
    """Vaccine manufacturer master data"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'vaccine_manufacturers'
        ordering = ['name']
        
    def __str__(self):
        return self.name


class Vaccine(BaseModel):
    """Vaccine master data with CVX codes"""
    cvx_code = models.CharField(max_length=64, unique=True, help_text="CDC CVX Code")
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=100, blank=True)
    manufacturer = models.ForeignKey(VaccineManufacturer, on_delete=models.PROTECT, null=True, blank=True)
    vaccine_type = models.CharField(max_length=100, help_text="Type of vaccine")
    is_active = models.BooleanField(default=True)
    
    # Vaccine properties
    min_age_days = models.IntegerField(null=True, blank=True, help_text="Minimum age in days")
    max_age_days = models.IntegerField(null=True, blank=True, help_text="Maximum age in days") 
    doses_required = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    interval_days = models.IntegerField(null=True, blank=True, help_text="Interval between doses in days")
    
    # Storage and handling
    storage_temp_min = models.FloatField(null=True, blank=True, help_text="Minimum storage temperature (°C)")
    storage_temp_max = models.FloatField(null=True, blank=True, help_text="Maximum storage temperature (°C)")
    
    class Meta:
        db_table = 'vaccines'
        ordering = ['name']
        
    def __str__(self):
        return f"{self.name} ({self.cvx_code})"


class VaccineLot(BaseModel):
    """Vaccine lot/batch management"""
    vaccine = models.ForeignKey(Vaccine, on_delete=models.CASCADE, related_name='lots')
    lot_number = models.CharField(max_length=50)
    manufacturer = models.ForeignKey(VaccineManufacturer, on_delete=models.PROTECT)
    expiration_date = models.DateField()
    
    # Inventory management
    quantity_received = models.IntegerField(default=0)
    quantity_used = models.IntegerField(default=0)
    quantity_wasted = models.IntegerField(default=0)
    
    # Storage location
    storage_location = models.CharField(max_length=100, blank=True)
    
    class Meta:
        db_table = 'vaccine_lots'
        unique_together = ['vaccine', 'lot_number', 'manufacturer']
        ordering = ['expiration_date']
        
    def __str__(self):
        return f"{self.vaccine.name} - {self.lot_number}"
    
    @property
    def quantity_available(self):
        """Calculate available quantity"""
        return self.quantity_received - self.quantity_used - self.quantity_wasted
    
    @property
    def is_expired(self):
        """Check if lot is expired"""
        return self.expiration_date < timezone.now().date()


class ImmunizationSchedule(BaseModel):
    """Immunization schedule templates"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    age_group = models.CharField(max_length=50, help_text="Target age group")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'immunization_schedules'
        ordering = ['name']
        
    def __str__(self):
        return f"{self.name} - {self.age_group}"


class ScheduledVaccination(BaseModel):
    """Scheduled vaccination within a schedule"""
    schedule = models.ForeignKey(ImmunizationSchedule, on_delete=models.CASCADE, related_name='vaccinations')
    vaccine = models.ForeignKey(Vaccine, on_delete=models.CASCADE)
    dose_number = models.IntegerField(validators=[MinValueValidator(1)])
    recommended_age_days = models.IntegerField(help_text="Recommended age in days")
    earliest_age_days = models.IntegerField(help_text="Earliest age in days")
    latest_age_days = models.IntegerField(null=True, blank=True, help_text="Latest age in days")
    
    class Meta:
        db_table = 'scheduled_vaccinations'
        unique_together = ['schedule', 'vaccine', 'dose_number']
        ordering = ['recommended_age_days']
        
    def __str__(self):
        return f"{self.schedule.name} - {self.vaccine.name} Dose {self.dose_number}"


class Immunization(BaseModel):
    """Individual immunization record"""
    from patients.models import Patient
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='immunizations')
    vaccine = models.ForeignKey(Vaccine, on_delete=models.PROTECT)
    vaccine_lot = models.ForeignKey(VaccineLot, on_delete=models.PROTECT, null=True, blank=True)
    
    # Administration details
    administered_date = models.DateTimeField()
    administered_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='administered_immunizations')
    administered_by_name = models.CharField(max_length=255, blank=True, help_text="Alternative to administered_by")
    
    # Dosage information
    amount_administered = models.FloatField(null=True, blank=True)
    amount_administered_unit = models.CharField(max_length=50, blank=True)
    dose_number = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    
    # Administration method
    route = models.CharField(max_length=100, blank=True, help_text="Route of administration")
    administration_site = models.CharField(max_length=100, blank=True, help_text="Site of administration")
    
    # Documentation
    vis_date = models.DateField(null=True, blank=True, help_text="Date of VIS Statement")
    education_date = models.DateField(null=True, blank=True)
    note = models.TextField(blank=True)
    
    # Status and completion
    completion_status = models.CharField(max_length=50, choices=[
        ('completed', 'Completed'),
        ('partially_completed', 'Partially Completed'),
        ('not_completed', 'Not Completed'),
        ('refused', 'Refused'),
        ('deferred', 'Deferred'),
    ], default='completed')
    
    information_source = models.CharField(max_length=50, choices=[
        ('new_immunization_record', 'New Immunization Record'),
        ('historical_information_source', 'Historical Information Source'),
        ('historical_information_birth_certificate', 'Historical Information Birth Certificate'),
        ('historical_information_school_record', 'Historical Information School Record'),
        ('historical_information_other_provider', 'Historical Information Other Provider'),
    ], default='new_immunization_record')
    
    # Refusal tracking
    refusal_reason = models.CharField(max_length=31, blank=True, choices=[
        ('parental_decision', 'Parental Decision'),
        ('religious_exemption', 'Religious Exemption'),
        ('medical_contraindication', 'Medical Contraindication'),
        ('patient_decision', 'Patient Decision'),
        ('other', 'Other'),
    ])
    
    # Provider information
    ordering_provider = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, 
                                        related_name='ordered_immunizations')
    
    # Reason codes
    reason_code = models.CharField(max_length=31, blank=True, 
                                 help_text="Medical code explaining reason")
    reason_description = models.TextField(blank=True, 
                                        help_text="Human readable description of reason")
    
    # Quality control
    added_erroneously = models.BooleanField(default=False)
    external_id = models.CharField(max_length=20, blank=True)
    
    class Meta:
        db_table = 'immunizations'
        ordering = ['-administered_date']
        indexes = [
            models.Index(fields=['patient', 'administered_date']),
            models.Index(fields=['vaccine', 'administered_date']),
        ]
        
    def __str__(self):
        return f"{self.patient} - {self.vaccine.name} ({self.administered_date.strftime('%Y-%m-%d')})"
    
    @property
    def is_overdue(self):
        """Check if immunization is overdue based on schedule"""
        # This would require complex logic based on patient age and schedule
        # For now, return False as placeholder
        return False


class ImmunizationObservation(BaseModel):
    """Observations related to immunizations (adverse events, reactions)"""
    immunization = models.ForeignKey(Immunization, on_delete=models.CASCADE, related_name='observations')
    observation_type = models.CharField(max_length=50, choices=[
        ('adverse_event', 'Adverse Event'),
        ('allergic_reaction', 'Allergic Reaction'),
        ('local_reaction', 'Local Reaction'),
        ('systemic_reaction', 'Systemic Reaction'),
        ('other', 'Other'),
    ])
    
    observation_date = models.DateTimeField()
    severity = models.CharField(max_length=20, choices=[
        ('mild', 'Mild'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
    ])
    
    description = models.TextField()
    action_taken = models.TextField(blank=True)
    outcome = models.CharField(max_length=100, blank=True)
    
    # Reporting
    reported_to_vaers = models.BooleanField(default=False)
    vaers_id = models.CharField(max_length=50, blank=True)
    
    class Meta:
        db_table = 'immunization_observations'
        ordering = ['-observation_date']
        
    def __str__(self):
        return f"{self.immunization} - {self.observation_type} ({self.severity})"


class ImmunizationContraindication(BaseModel):
    """Contraindications for specific vaccines"""
    vaccine = models.ForeignKey(Vaccine, on_delete=models.CASCADE, related_name='contraindications')
    contraindication_type = models.CharField(max_length=50, choices=[
        ('allergy', 'Allergy'),
        ('immune_deficiency', 'Immune Deficiency'),
        ('pregnancy', 'Pregnancy'),
        ('age_restriction', 'Age Restriction'),
        ('medical_condition', 'Medical Condition'),
        ('medication_interaction', 'Medication Interaction'),
        ('other', 'Other'),
    ])
    
    description = models.TextField()
    is_permanent = models.BooleanField(default=False)
    severity = models.CharField(max_length=20, choices=[
        ('absolute', 'Absolute Contraindication'),
        ('relative', 'Relative Contraindication'),
        ('precaution', 'Precaution'),
    ])
    
    class Meta:
        db_table = 'immunization_contraindications'
        ordering = ['vaccine', 'contraindication_type']
        
    def __str__(self):
        return f"{self.vaccine.name} - {self.contraindication_type}"


class PatientImmunizationAlert(BaseModel):
    """Patient-specific immunization alerts and reminders"""
    from patients.models import Patient
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='immunization_alerts')
    vaccine = models.ForeignKey(Vaccine, on_delete=models.CASCADE)
    alert_type = models.CharField(max_length=50, choices=[
        ('due', 'Due'),
        ('overdue', 'Overdue'),
        ('contraindicated', 'Contraindicated'),
        ('refused', 'Refused'),
        ('deferred', 'Deferred'),
    ])
    
    alert_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    message = models.TextField()
    is_active = models.BooleanField(default=True)
    acknowledged_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    acknowledged_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'patient_immunization_alerts'
        ordering = ['-alert_date']
        
    def __str__(self):
        return f"{self.patient} - {self.vaccine.name} {self.alert_type}"
