from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.utils import timezone
from django.urls import reverse
from patients.models import Patient
from medical_records.models import MedicalRecord, Prescription
from appointments.models import Appointment
from laboratory.models import LabOrder, LabResult
import uuid
from datetime import timedelta


class BaseModel(models.Model):
    """Base model with common fields for all models"""
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='%(class)s_created')
    updated_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='%(class)s_updated')
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class PatientPortalAccess(BaseModel):
    """Patient portal access management"""
    patient = models.OneToOneField(
        Patient, 
        on_delete=models.CASCADE, 
        related_name='portal_access'
    )
    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField()
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    last_login = models.DateTimeField(null=True, blank=True)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    password_reset_token = models.CharField(max_length=255, blank=True)
    password_reset_expires = models.DateTimeField(null=True, blank=True)
    verification_token = models.CharField(max_length=255, blank=True)
    
    # Security settings
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=32, blank=True)
    
    # Preferences
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    language_preference = models.CharField(max_length=10, default='en')
    
    class Meta:
        verbose_name = 'Patient Portal Access'
        verbose_name_plural = 'Patient Portal Accesses'
        
    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.username}"
    
    def is_locked(self):
        """Check if account is locked due to failed login attempts"""
        if self.locked_until:
            return timezone.now() < self.locked_until
        return False
    
    def lock_account(self, minutes=30):
        """Lock account for specified minutes"""
        self.locked_until = timezone.now() + timedelta(minutes=minutes)
        self.save()
    
    def unlock_account(self):
        """Unlock account and reset failed attempts"""
        self.locked_until = None
        self.failed_login_attempts = 0
        self.save()


class PortalMessage(BaseModel):
    """Messages between patients and healthcare providers"""
    
    MESSAGE_TYPES = [
        ('general', 'General Inquiry'),
        ('appointment', 'Appointment Request'),
        ('prescription', 'Prescription Refill'),
        ('test_results', 'Test Results Question'),
        ('billing', 'Billing Question'),
        ('medical', 'Medical Question'),
        ('urgent', 'Urgent Message'),
    ]
    
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
        ('replied', 'Replied'),
        ('closed', 'Closed'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='portal_messages')
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='portal_messages_received')
    subject = models.CharField(max_length=200)
    message = models.TextField()
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='general')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent')
    is_urgent = models.BooleanField(default=False)
    is_read_by_patient = models.BooleanField(default=False)
    is_read_by_provider = models.BooleanField(default=False)
    read_by_patient_date = models.DateTimeField(null=True, blank=True)
    read_by_provider_date = models.DateTimeField(null=True, blank=True)
    
    # Thread management
    parent_message = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='replies'
    )
    thread_id = models.UUIDField(default=uuid.uuid4)
    
    class Meta:
        verbose_name = 'Portal Message'
        verbose_name_plural = 'Portal Messages'
        ordering = ['-create_date']
        
    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.subject}"
    
    def mark_read_by_patient(self):
        """Mark message as read by patient"""
        if not self.is_read_by_patient:
            self.is_read_by_patient = True
            self.read_by_patient_date = timezone.now()
            self.save()
    
    def mark_read_by_provider(self):
        """Mark message as read by provider"""
        if not self.is_read_by_provider:
            self.is_read_by_provider = True
            self.read_by_provider_date = timezone.now()
            self.save()


class PortalMessageAttachment(BaseModel):
    """Attachments for portal messages"""
    message = models.ForeignKey(
        PortalMessage, 
        on_delete=models.CASCADE, 
        related_name='attachments'
    )
    file = models.FileField(upload_to='portal_attachments/%Y/%m/')
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    content_type = models.CharField(max_length=100)
    
    class Meta:
        verbose_name = 'Message Attachment'
        verbose_name_plural = 'Message Attachments'
        
    def __str__(self):
        return f"{self.message.subject} - {self.original_filename}"


class PatientPortalSession(BaseModel):
    """Track patient portal sessions for security"""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='portal_sessions')
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    login_time = models.DateTimeField(auto_now_add=True)
    logout_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Portal Session'
        verbose_name_plural = 'Portal Sessions'
        ordering = ['-login_time']
        
    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.login_time}"


class PatientPortalAuditLog(BaseModel):
    """Audit log for patient portal activities"""
    
    ACTION_TYPES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('view_records', 'View Medical Records'),
        ('view_appointments', 'View Appointments'),
        ('view_prescriptions', 'View Prescriptions'),
        ('view_lab_results', 'View Lab Results'),
        ('send_message', 'Send Message'),
        ('download_document', 'Download Document'),
        ('update_profile', 'Update Profile'),
        ('password_change', 'Password Change'),
        ('failed_login', 'Failed Login'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='portal_audit_logs')
    action = models.CharField(max_length=30, choices=ACTION_TYPES)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    success = models.BooleanField(default=True)
    
    # Override BaseModel fields to make them nullable for patient portal context
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='%(class)s_created', null=True, blank=True)
    updated_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='%(class)s_updated', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Portal Audit Log'
        verbose_name_plural = 'Portal Audit Logs'
        ordering = ['-create_date']
        
    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.action} - {self.create_date}"


class PatientEducationResource(BaseModel):
    """Health education resources for patients"""
    
    RESOURCE_TYPES = [
        ('article', 'Article'),
        ('video', 'Video'),
        ('pdf', 'PDF Document'),
        ('infographic', 'Infographic'),
        ('quiz', 'Health Quiz'),
        ('tool', 'Health Tool'),
    ]
    
    CATEGORIES = [
        ('general', 'General Health'),
        ('chronic_disease', 'Chronic Disease Management'),
        ('prevention', 'Disease Prevention'),
        ('nutrition', 'Nutrition'),
        ('exercise', 'Exercise & Fitness'),
        ('mental_health', 'Mental Health'),
        ('medication', 'Medication Management'),
        ('emergency', 'Emergency Care'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    content = models.TextField(blank=True)
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPES)
    category = models.CharField(max_length=30, choices=CATEGORIES)
    url = models.URLField(blank=True)
    file = models.FileField(upload_to='education_resources/', blank=True)
    thumbnail = models.ImageField(upload_to='education_thumbnails/', blank=True)
    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    view_count = models.PositiveIntegerField(default=0)
    
    # Medical conditions this resource applies to
    applicable_conditions = models.ManyToManyField(
        'medical_records.Diagnosis',
        blank=True,
        related_name='education_resources'
    )
    
    class Meta:
        verbose_name = 'Patient Education Resource'
        verbose_name_plural = 'Patient Education Resources'
        ordering = ['-is_featured', '-create_date']
        
    def __str__(self):
        return self.title
    
    def increment_view_count(self):
        """Increment view count"""
        self.view_count += 1
        self.save(update_fields=['view_count'])


class PatientPortalPreference(BaseModel):
    """Patient portal preferences and settings"""
    patient = models.OneToOneField(
        Patient, 
        on_delete=models.CASCADE, 
        related_name='portal_preferences'
    )
    
    # Notification preferences
    email_appointment_reminders = models.BooleanField(default=True)
    email_lab_results = models.BooleanField(default=True)
    email_prescription_ready = models.BooleanField(default=True)
    email_messages = models.BooleanField(default=True)
    
    sms_appointment_reminders = models.BooleanField(default=False)
    sms_lab_results = models.BooleanField(default=False)
    sms_prescription_ready = models.BooleanField(default=False)
    sms_messages = models.BooleanField(default=False)
    
    # Privacy settings
    share_with_family = models.BooleanField(default=False)
    allow_research_contact = models.BooleanField(default=False)
    
    # Interface preferences
    theme = models.CharField(
        max_length=20, 
        choices=[('light', 'Light'), ('dark', 'Dark')], 
        default='light'
    )
    dashboard_widgets = models.JSONField(default=list)
    
    class Meta:
        verbose_name = 'Portal Preference'
        verbose_name_plural = 'Portal Preferences'
        
    def __str__(self):
        return f"{self.patient.get_full_name()} - Preferences"


class PatientFamilyAccess(BaseModel):
    """Family member access to patient records"""
    
    RELATIONSHIP_TYPES = [
        ('parent', 'Parent'),
        ('guardian', 'Legal Guardian'),
        ('spouse', 'Spouse'),
        ('child', 'Child'),
        ('sibling', 'Sibling'),
        ('power_of_attorney', 'Power of Attorney'),
        ('healthcare_proxy', 'Healthcare Proxy'),
        ('other', 'Other'),
    ]
    
    ACCESS_LEVELS = [
        ('full', 'Full Access'),
        ('limited', 'Limited Access'),
        ('emergency_only', 'Emergency Only'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='family_access')
    family_member_name = models.CharField(max_length=200)
    family_member_email = models.EmailField()
    relationship = models.CharField(max_length=30, choices=RELATIONSHIP_TYPES)
    access_level = models.CharField(max_length=20, choices=ACCESS_LEVELS, default='limited')
    
    # Permissions
    can_view_medical_records = models.BooleanField(default=False)
    can_view_appointments = models.BooleanField(default=True)
    can_view_prescriptions = models.BooleanField(default=False)
    can_view_lab_results = models.BooleanField(default=False)
    can_schedule_appointments = models.BooleanField(default=False)
    can_send_messages = models.BooleanField(default=True)
    
    is_active = models.BooleanField(default=True)
    expires_date = models.DateField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Family Access'
        verbose_name_plural = 'Family Access'
        unique_together = ['patient', 'family_member_email']
        
    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.family_member_name}"
    
    def is_expired(self):
        """Check if access has expired"""
        if self.expires_date:
            return timezone.now().date() > self.expires_date
        return False


class PatientHealthReminder(BaseModel):
    """Health reminders and alerts for patients"""
    
    REMINDER_TYPES = [
        ('medication', 'Medication Reminder'),
        ('appointment', 'Appointment Reminder'),
        ('screening', 'Health Screening'),
        ('vaccination', 'Vaccination Due'),
        ('followup', 'Follow-up Care'),
        ('lifestyle', 'Lifestyle Reminder'),
        ('custom', 'Custom Reminder'),
    ]
    
    FREQUENCY_CHOICES = [
        ('once', 'One Time'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        ('custom', 'Custom'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='health_reminders')
    title = models.CharField(max_length=200)
    description = models.TextField()
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPES)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='once')
    
    # Timing
    remind_date = models.DateTimeField()
    last_sent = models.DateTimeField(null=True, blank=True)
    next_due = models.DateTimeField(null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_completed = models.BooleanField(default=False)
    completed_date = models.DateTimeField(null=True, blank=True)
    
    # Delivery methods
    send_email = models.BooleanField(default=True)
    send_sms = models.BooleanField(default=False)
    send_portal_notification = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Health Reminder'
        verbose_name_plural = 'Health Reminders'
        ordering = ['remind_date']
        
    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.title}"
    
    def mark_completed(self):
        """Mark reminder as completed"""
        self.is_completed = True
        self.completed_date = timezone.now()
        self.save()
