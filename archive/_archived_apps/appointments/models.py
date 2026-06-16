from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
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


class AppointmentType(BaseModel):
    """Types of appointments"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    duration_minutes = models.IntegerField(default=30)
    color = models.CharField(max_length=7, default='#007bff')  # Hex color code
    is_available_online = models.BooleanField(default=True)
    requires_referral = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'appointment_types'
    
    def __str__(self):
        return self.name


class Appointment(BaseModel):
    """Patient appointments"""
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='appointments')
    provider = models.ForeignKey('administration.Provider', on_delete=models.CASCADE, related_name='appointments')
    appointment_type = models.ForeignKey(AppointmentType, on_delete=models.SET_NULL, null=True, blank=True)
    facility = models.ForeignKey('administration.Facility', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Appointment Details
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    end_time = models.TimeField(blank=True, null=True)
    duration_minutes = models.IntegerField(default=30)
    
    # Status
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
        ('rescheduled', 'Rescheduled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    
    # Appointment Information
    chief_complaint = models.TextField(blank=True)
    reason_for_visit = models.TextField(blank=True)
    special_instructions = models.TextField(blank=True)
    
    # Check-in Information
    check_in_time = models.DateTimeField(blank=True, null=True)
    check_in_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='checked_in_appointments')
    
    # Cancellation Information
    cancellation_reason = models.TextField(blank=True)
    cancelled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cancelled_appointments')
    cancellation_date = models.DateTimeField(blank=True, null=True)
    
    # Follow-up
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateField(blank=True, null=True)
    
    # Billing
    is_billable = models.BooleanField(default=True)
    copay_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    copay_collected = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'appointments'
        indexes = [
            models.Index(fields=['patient', 'appointment_date']),
            models.Index(fields=['provider', 'appointment_date']),
            models.Index(fields=['appointment_date', 'appointment_time']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.provider} - {self.appointment_date}"
    
    def clean(self):
        """Validate appointment data"""
        if self.appointment_date and self.appointment_date < timezone.now().date():
            raise ValidationError("Appointment date cannot be in the past")
        
        if self.end_time and self.appointment_time and self.end_time <= self.appointment_time:
            raise ValidationError("End time must be after start time")
    
    def save(self, *args, **kwargs):
        """Override save to calculate end time"""
        if not self.end_time and self.appointment_time:
            from datetime import datetime, timedelta
            start_datetime = datetime.combine(self.appointment_date, self.appointment_time)
            end_datetime = start_datetime + timedelta(minutes=self.duration_minutes)
            self.end_time = end_datetime.time()
        super().save(*args, **kwargs)
    
    @property
    def is_today(self):
        """Check if appointment is today"""
        return self.appointment_date == timezone.now().date()
    
    @property
    def is_upcoming(self):
        """Check if appointment is in the future"""
        return self.appointment_date > timezone.now().date()
    
    @property
    def is_past(self):
        """Check if appointment is in the past"""
        return self.appointment_date < timezone.now().date()


class AppointmentNote(BaseModel):
    """Notes for appointments"""
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='notes')
    note_type = models.CharField(max_length=50, choices=[
        ('pre_visit', 'Pre-visit Note'),
        ('visit', 'Visit Note'),
        ('post_visit', 'Post-visit Note'),
        ('cancellation', 'Cancellation Note'),
        ('rescheduling', 'Rescheduling Note'),
    ])
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    is_visible_to_patient = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'appointment_notes'
    
    def __str__(self):
        return f"{self.appointment} - {self.note_type}"


class Schedule(BaseModel):
    """Provider schedules"""
    provider = models.ForeignKey('administration.Provider', on_delete=models.CASCADE, related_name='schedules')
    facility = models.ForeignKey('administration.Facility', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Schedule Details
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    # Availability
    is_available = models.BooleanField(default=True)
    max_patients = models.IntegerField(default=20)
    
    # Break Times
    break_start = models.TimeField(blank=True, null=True)
    break_end = models.TimeField(blank=True, null=True)
    
    # Schedule Type
    SCHEDULE_TYPE_CHOICES = [
        ('regular', 'Regular Schedule'),
        ('override', 'Schedule Override'),
        ('vacation', 'Vacation'),
        ('sick_leave', 'Sick Leave'),
        ('conference', 'Conference'),
        ('emergency', 'Emergency'),
    ]
    schedule_type = models.CharField(max_length=20, choices=SCHEDULE_TYPE_CHOICES, default='regular')
    
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'schedules'
        unique_together = ['provider', 'date', 'start_time']
        indexes = [
            models.Index(fields=['provider', 'date']),
            models.Index(fields=['date', 'is_available']),
        ]
    
    def __str__(self):
        return f"{self.provider.full_name} - {self.date} {self.start_time}-{self.end_time}"
    
    def clean(self):
        """Validate schedule data"""
        if self.end_time <= self.start_time:
            raise ValidationError("End time must be after start time")
        
        if self.break_start and self.break_end:
            if self.break_end <= self.break_start:
                raise ValidationError("Break end time must be after break start time")


class WaitingList(BaseModel):
    """Patient waiting list for appointments"""
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='waiting_list_entries')
    provider = models.ForeignKey('administration.Provider', on_delete=models.CASCADE, related_name='waiting_list')
    appointment_type = models.ForeignKey(AppointmentType, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Preferences
    preferred_date = models.DateField(blank=True, null=True)
    preferred_time = models.TimeField(blank=True, null=True)
    earliest_date = models.DateField()
    latest_date = models.DateField()
    
    # Priority
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    
    # Status
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('scheduled', 'Scheduled'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    # Notification
    notify_by_phone = models.BooleanField(default=True)
    notify_by_email = models.BooleanField(default=True)
    notify_by_sms = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'waiting_list'
        indexes = [
            models.Index(fields=['provider', 'priority', 'created_at']),
            models.Index(fields=['status', 'earliest_date']),
        ]
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.provider.full_name} - {self.priority}"


class RecurringAppointment(BaseModel):
    """Recurring appointment patterns"""
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='recurring_appointments')
    provider = models.ForeignKey('administration.Provider', on_delete=models.CASCADE, related_name='recurring_appointments')
    appointment_type = models.ForeignKey(AppointmentType, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Recurrence Pattern
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    
    # Pattern Details
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    appointment_time = models.TimeField()
    duration_minutes = models.IntegerField(default=30)
    
    # Days of week (for weekly patterns)
    monday = models.BooleanField(default=False)
    tuesday = models.BooleanField(default=False)
    wednesday = models.BooleanField(default=False)
    thursday = models.BooleanField(default=False)
    friday = models.BooleanField(default=False)
    saturday = models.BooleanField(default=False)
    sunday = models.BooleanField(default=False)
    
    # Status
    is_active = models.BooleanField(default=True)
    last_generated_date = models.DateField(blank=True, null=True)
    
    class Meta:
        db_table = 'recurring_appointments'
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.frequency} - {self.appointment_time}"


class AppointmentReminder(BaseModel):
    """Appointment reminder notifications"""
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='reminders')
    
    # Reminder Details
    REMINDER_TYPE_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('call', 'Phone Call'),
        ('push', 'Push Notification'),
    ]
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPE_CHOICES)
    
    # Scheduling
    scheduled_datetime = models.DateTimeField()
    sent_datetime = models.DateTimeField(blank=True, null=True)
    
    # Status
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    
    # Delivery tracking
    delivery_status = models.CharField(max_length=20, blank=True)
    error_message = models.TextField(blank=True)
    
    # Content
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField(blank=True)
    
    class Meta:
        db_table = 'appointment_reminders'
        ordering = ['-scheduled_datetime']
    
    def __str__(self):
        return f"{self.appointment.patient.get_full_name()} - {self.reminder_type} - {self.scheduled_datetime}"


class WaitlistEntry(BaseModel):
    """Patient waitlist for earlier appointments"""
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='waitlist_entries')
    provider = models.ForeignKey('administration.Provider', on_delete=models.CASCADE, related_name='waitlist_entries')
    appointment_type = models.ForeignKey(AppointmentType, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Preferences
    preferred_date = models.DateField(blank=True, null=True, help_text="Preferred appointment date (optional)")
    preferred_time_start = models.TimeField(blank=True, null=True)
    preferred_time_end = models.TimeField(blank=True, null=True)
    
    # Priority
    PRIORITY_CHOICES = [
        ('urgent', 'Urgent'),
        ('high', 'High'),
        ('normal', 'Normal'),
        ('low', 'Low'),
    ]
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    
    # Status
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('contacted', 'Contacted'),
        ('scheduled', 'Scheduled'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Contact attempts
    contact_attempts = models.IntegerField(default=0)
    last_contact_date = models.DateTimeField(blank=True, null=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'waitlist_entries'
        ordering = ['priority', 'created_at']
    
    def __str__(self):
        return f"{self.patient.get_full_name()} - {self.provider.get_full_name()} - {self.priority}"
