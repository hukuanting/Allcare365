from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class BaseModel(models.Model):
    """Base model with common fields for all models"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='%(class)s_created')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='%(class)s_updated')
    is_active = models.BooleanField(default=True)
    
    class Meta:
        abstract = True


class Provider(BaseModel):
    """Healthcare providers (doctors, nurses, etc.)"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='provider_profile')
    
    # Professional Information
    license_number = models.CharField(max_length=100, unique=True)
    npi_number = models.CharField(max_length=20, unique=True, blank=True)  # National Provider Identifier
    dea_number = models.CharField(max_length=20, blank=True)  # Drug Enforcement Administration
    
    PROVIDER_TYPE_CHOICES = [
        ('physician', 'Physician'),
        ('nurse', 'Nurse'),
        ('nurse_practitioner', 'Nurse Practitioner'),
        ('physician_assistant', 'Physician Assistant'),
        ('specialist', 'Specialist'),
        ('therapist', 'Therapist'),
        ('technician', 'Technician'),
        ('other', 'Other'),
    ]
    provider_type = models.CharField(max_length=20, choices=PROVIDER_TYPE_CHOICES)
    
    # Specialties
    primary_specialty = models.CharField(max_length=200, blank=True)
    secondary_specialty = models.CharField(max_length=200, blank=True)
    
    # Contact Information
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    
    # Professional Details
    medical_school = models.CharField(max_length=200, blank=True)
    residency = models.CharField(max_length=200, blank=True)
    board_certifications = models.TextField(blank=True)
    years_of_experience = models.IntegerField(blank=True, null=True)
    
    # Status
    is_accepting_patients = models.BooleanField(default=True)
    license_expiration_date = models.DateField(blank=True, null=True)
    
    class Meta:
        db_table = 'providers'
        indexes = [
            models.Index(fields=['license_number']),
            models.Index(fields=['npi_number']),
            models.Index(fields=['provider_type']),
        ]
    
    def __str__(self):
        return f"Dr. {self.user.first_name} {self.user.last_name}"
    
    @property
    def full_name(self):
        return f"{self.user.first_name} {self.user.last_name}"


class Facility(BaseModel):
    """Healthcare facilities"""
    name = models.CharField(max_length=200)
    facility_type = models.CharField(max_length=100, choices=[
        ('hospital', 'Hospital'),
        ('clinic', 'Clinic'),
        ('office', 'Medical Office'),
        ('urgent_care', 'Urgent Care'),
        ('emergency', 'Emergency Room'),
        ('laboratory', 'Laboratory'),
        ('imaging', 'Imaging Center'),
        ('pharmacy', 'Pharmacy'),
        ('other', 'Other'),
    ])
    
    # Address
    street_address = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    zip_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='USA')
    
    # Contact Information
    phone = models.CharField(max_length=20, blank=True)
    fax = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    
    # Operational Details
    operating_hours = models.TextField(blank=True)
    services_offered = models.TextField(blank=True)
    
    # Administrator
    administrator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        db_table = 'facilities'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['facility_type']),
        ]
    
    def __str__(self):
        return self.name


class Department(BaseModel):
    """Hospital/facility departments"""
    name = models.CharField(max_length=200)
    facility = models.ForeignKey(Facility, on_delete=models.CASCADE, related_name='departments')
    head_of_department = models.ForeignKey(Provider, on_delete=models.SET_NULL, null=True, blank=True)
    
    description = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    
    class Meta:
        db_table = 'departments'
        unique_together = ['name', 'facility']
    
    def __str__(self):
        return f"{self.facility.name} - {self.name}"


class UserProfile(BaseModel):
    """Extended user profile for system users"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin_profile')
    
    # Personal Information
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=50, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    
    # Professional Information
    employee_id = models.CharField(max_length=50, unique=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    job_title = models.CharField(max_length=200, blank=True)
    hire_date = models.DateField(blank=True, null=True)
    
    # System Preferences
    timezone = models.CharField(max_length=100, default='UTC')
    language = models.CharField(max_length=10, default='en')
    theme = models.CharField(max_length=20, default='light', choices=[
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('auto', 'Auto'),
    ])
    
    # Security
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    failed_login_attempts = models.IntegerField(default=0)
    account_locked_until = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'user_profiles'
    
    def __str__(self):
        return f"{self.user.username} - {self.job_title}"


class AuditLog(BaseModel):
    """Audit log for tracking system changes"""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    table_name = models.CharField(max_length=100)
    record_id = models.CharField(max_length=100)
    old_values = models.JSONField(blank=True, null=True)
    new_values = models.JSONField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'audit_logs'
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['table_name', 'record_id']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.action} - {self.timestamp}"


class SystemSetting(BaseModel):
    """System configuration settings"""
    category = models.CharField(max_length=100)
    key = models.CharField(max_length=200)
    value = models.TextField()
    description = models.TextField(blank=True)
    data_type = models.CharField(max_length=20, choices=[
        ('string', 'String'),
        ('integer', 'Integer'),
        ('boolean', 'Boolean'),
        ('json', 'JSON'),
        ('date', 'Date'),
        ('datetime', 'DateTime'),
    ], default='string')
    
    class Meta:
        db_table = 'system_settings'
        unique_together = ['category', 'key']
    
    def __str__(self):
        return f"{self.category}.{self.key}"
    
    def get_typed_value(self):
        """Return the value converted to the appropriate data type"""
        if self.data_type == 'boolean':
            return self.value.lower() in ('true', '1', 'yes', 'on')
        elif self.data_type == 'integer':
            return int(self.value)
        elif self.data_type == 'json':
            import json
            return json.loads(self.value)
        elif self.data_type == 'date':
            from datetime import datetime
            return datetime.strptime(self.value, '%Y-%m-%d').date()
        elif self.data_type == 'datetime':
            from datetime import datetime
            return datetime.fromisoformat(self.value)
        return self.value
