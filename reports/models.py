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


class ReportTemplate(BaseModel):
    """Report templates for generating various reports"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    REPORT_TYPE_CHOICES = [
        ('patient_list', 'Patient List'),
        ('appointment_report', 'Appointment Report'),
        ('financial_report', 'Financial Report'),
        ('clinical_report', 'Clinical Report'),
        ('prescription_report', 'Prescription Report'),
        ('immunization_report', 'Immunization Report'),
        ('custom_report', 'Custom Report'),
    ]
    report_type = models.CharField(max_length=50, choices=REPORT_TYPE_CHOICES)
    
    # Report Configuration
    sql_query = models.TextField(blank=True, help_text="Custom SQL query for the report")
    filters_config = models.JSONField(default=dict, help_text="Configuration for report filters")
    columns_config = models.JSONField(default=dict, help_text="Configuration for report columns")
    
    # Output Configuration
    supports_pdf = models.BooleanField(default=True)
    supports_excel = models.BooleanField(default=True)
    supports_csv = models.BooleanField(default=True)
    
    # Access Control
    is_public = models.BooleanField(default=False)
    allowed_users = models.ManyToManyField(User, blank=True, related_name='accessible_reports')
    
    class Meta:
        db_table = 'report_templates'
        indexes = [
            models.Index(fields=['report_type']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.name


class ReportExecution(BaseModel):
    """Track report executions"""
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name='executions')
    executed_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='report_executions')
    
    # Execution Parameters
    parameters = models.JSONField(default=dict, help_text="Parameters used for this execution")
    
    # Execution Results
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    execution_time = models.DurationField(null=True, blank=True)
    
    # Results
    result_count = models.IntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    # Output Files
    output_format = models.CharField(max_length=10, choices=[
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('csv', 'CSV'),
        ('json', 'JSON'),
    ])
    file_path = models.CharField(max_length=500, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)
    
    class Meta:
        db_table = 'report_executions'
        indexes = [
            models.Index(fields=['executed_by', 'created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['template', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.template.name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class ScheduledReport(BaseModel):
    """Scheduled report executions"""
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name='schedules')
    scheduled_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scheduled_reports')
    
    # Schedule Configuration
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    
    # Schedule Details
    schedule_time = models.TimeField(help_text="Time to run the report")
    day_of_week = models.IntegerField(null=True, blank=True, help_text="For weekly reports (0=Monday)")
    day_of_month = models.IntegerField(null=True, blank=True, help_text="For monthly reports")
    
    # Parameters
    parameters = models.JSONField(default=dict, help_text="Default parameters for scheduled execution")
    output_format = models.CharField(max_length=10, choices=[
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('csv', 'CSV'),
    ], default='pdf')
    
    # Email Configuration
    email_recipients = models.TextField(blank=True, help_text="Comma-separated email addresses")
    email_subject = models.CharField(max_length=200, blank=True)
    email_body = models.TextField(blank=True)
    
    # Status
    is_enabled = models.BooleanField(default=True)
    last_execution = models.DateTimeField(null=True, blank=True)
    next_execution = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'scheduled_reports'
        indexes = [
            models.Index(fields=['is_enabled', 'next_execution']),
            models.Index(fields=['scheduled_by']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.frequency})"


class ReportFavorite(BaseModel):
    """User's favorite reports"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_reports')
    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, related_name='favorites')
    
    # Favorite Configuration
    custom_name = models.CharField(max_length=200, blank=True)
    saved_parameters = models.JSONField(default=dict, help_text="User's saved parameters")
    
    class Meta:
        db_table = 'report_favorites'
        unique_together = ['user', 'template']
        indexes = [
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.custom_name or self.template.name}"
