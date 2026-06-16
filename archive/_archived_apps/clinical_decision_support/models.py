"""
Clinical Decision Support Models

This module provides models for implementing clinical decision support rules,
alerts, reminders, and drug interaction checks.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
import json


class BaseModel(models.Model):
    """Base model with common fields"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='%(class)s_created')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='%(class)s_updated')
    is_active = models.BooleanField(default=True)
    
    class Meta:
        abstract = True


class RuleCategory(BaseModel):
    """Categories for organizing clinical rules"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#007bff', help_text="Hex color code")
    icon = models.CharField(max_length=50, blank=True, help_text="Font Awesome icon class")
    display_order = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name_plural = "Rule Categories"
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return self.name


class ClinicalRule(BaseModel):
    """Clinical decision support rules"""
    
    RULE_TYPES = [
        ('medication_alert', 'Medication Alert'),
        ('allergy_check', 'Allergy Check'),
        ('lab_alert', 'Laboratory Alert'),
        ('interaction_check', 'Drug Interaction Check'),
        ('contraindication', 'Contraindication'),
        ('preventive_care', 'Preventive Care Reminder'),
        ('chronic_care', 'Chronic Care Management'),
        ('age_based', 'Age-Based Reminder'),
        ('diagnosis_based', 'Diagnosis-Based Alert'),
        ('procedure_alert', 'Procedure Alert'),
        ('vital_signs', 'Vital Signs Alert'),
        ('custom', 'Custom Rule'),
    ]
    
    SEVERITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    ACTION_TYPES = [
        ('alert', 'Show Alert'),
        ('warning', 'Show Warning'),
        ('block', 'Block Action'),
        ('reminder', 'Send Reminder'),
        ('notification', 'Send Notification'),
        ('order_set', 'Suggest Order Set'),
        ('protocol', 'Activate Protocol'),
    ]
    
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    category = models.ForeignKey(RuleCategory, on_delete=models.CASCADE, related_name='rules')
    rule_type = models.CharField(max_length=30, choices=RULE_TYPES)
    description = models.TextField()
    
    # Rule Configuration
    condition_logic = models.JSONField(
        default=dict,
        help_text="JSON configuration defining when this rule triggers"
    )
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    action_config = models.JSONField(
        default=dict,
        help_text="JSON configuration defining what action to take"
    )
    
    # Priority and Timing
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS, default='medium')
    priority = models.PositiveIntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(10)])
    
    # Rule Scheduling
    is_real_time = models.BooleanField(default=True, help_text="Execute rule in real-time")
    check_frequency_hours = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="For non-real-time rules, how often to check (in hours)"
    )
    
    # Rule Validity
    effective_date = models.DateTimeField(default=timezone.now)
    expiry_date = models.DateTimeField(null=True, blank=True)
    
    # Rule Metadata
    evidence_level = models.CharField(max_length=20, blank=True, help_text="Evidence quality (A, B, C)")
    reference_url = models.URLField(blank=True, help_text="Link to clinical guidelines")
    version = models.CharField(max_length=10, default='1.0')
    
    class Meta:
        ordering = ['-priority', 'name']
        unique_together = ['code', 'version']
    
    def __str__(self):
        return f"{self.name} ({self.get_rule_type_display()})"
    
    def is_rule_active(self):
        """Check if rule is currently active"""
        now = timezone.now()
        if self.expiry_date and now > self.expiry_date:
            return False
        return self.is_active and now >= self.effective_date
    
    def evaluate_condition(self, context):
        """Evaluate rule condition against given context"""
        # This would contain the rule evaluation logic
        # For now, return True as placeholder
        return True


class ClinicalAlert(BaseModel):
    """Generated clinical alerts"""
    
    ALERT_STATUS = [
        ('active', 'Active'),
        ('acknowledged', 'Acknowledged'),
        ('dismissed', 'Dismissed'),
        ('resolved', 'Resolved'),
        ('expired', 'Expired'),
    ]
    
    rule = models.ForeignKey(ClinicalRule, on_delete=models.CASCADE, related_name='alerts')
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='clinical_alerts')
    encounter = models.ForeignKey(
        'medical_records.MedicalRecord',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='clinical_alerts'
    )
    
    # Alert Details
    title = models.CharField(max_length=200)
    message = models.TextField()
    alert_level = models.CharField(max_length=10, choices=ClinicalRule.SEVERITY_LEVELS)
    
    # Alert Context
    trigger_data = models.JSONField(
        default=dict,
        help_text="Data that triggered this alert"
    )
    recommended_actions = models.JSONField(
        default=list,
        help_text="Recommended actions to address the alert"
    )
    
    # Alert Management
    status = models.CharField(max_length=15, choices=ALERT_STATUS, default='active')
    acknowledged_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='clinical_alerts_acknowledged_by'
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledgment_note = models.TextField(blank=True)
    
    # Alert Lifecycle
    triggered_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-triggered_at', '-alert_level']
        indexes = [
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['rule', 'status']),
            models.Index(fields=['triggered_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.patient} ({self.get_status_display()})"
    
    def acknowledge(self, user, note=""):
        """Acknowledge the alert"""
        self.status = 'acknowledged'
        self.acknowledged_by = user
        self.acknowledged_at = timezone.now()
        self.acknowledgment_note = note
        self.save()
    
    def dismiss(self, user, note=""):
        """Dismiss the alert"""
        self.status = 'dismissed'
        self.acknowledged_by = user
        self.acknowledged_at = timezone.now()
        self.acknowledgment_note = note
        self.save()


class DrugInteraction(BaseModel):
    """Drug interaction definitions"""
    
    INTERACTION_SEVERITY = [
        ('minor', 'Minor'),
        ('moderate', 'Moderate'),
        ('major', 'Major'),
        ('contraindicated', 'Contraindicated'),
    ]
    
    drug_1 = models.CharField(max_length=200, help_text="First drug name or code")
    drug_2 = models.CharField(max_length=200, help_text="Second drug name or code")
    interaction_type = models.CharField(max_length=50)
    severity = models.CharField(max_length=15, choices=INTERACTION_SEVERITY)
    
    # Interaction Details
    mechanism = models.TextField(help_text="How the interaction occurs")
    clinical_effect = models.TextField(help_text="Clinical effects of the interaction")
    management = models.TextField(help_text="How to manage the interaction")
    
    # Evidence
    evidence_level = models.CharField(max_length=20, blank=True)
    reference_source = models.CharField(max_length=200, blank=True)
    reference_url = models.URLField(blank=True)
    
    class Meta:
        ordering = ['drug_1', 'drug_2']
        unique_together = ['drug_1', 'drug_2']
        indexes = [
            models.Index(fields=['drug_1']),
            models.Index(fields=['drug_2']),
            models.Index(fields=['severity']),
        ]
    
    def __str__(self):
        return f"{self.drug_1} + {self.drug_2} ({self.get_severity_display()})"


class PreventiveCareReminder(BaseModel):
    """Preventive care reminders and guidelines"""
    
    REMINDER_TYPES = [
        ('screening', 'Screening'),
        ('immunization', 'Immunization'),
        ('lifestyle', 'Lifestyle Counseling'),
        ('medication', 'Preventive Medication'),
        ('followup', 'Follow-up Care'),
    ]
    
    name = models.CharField(max_length=200)
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPES)
    description = models.TextField()
    
    # Target Population
    target_age_min = models.PositiveIntegerField(null=True, blank=True)
    target_age_max = models.PositiveIntegerField(null=True, blank=True)
    target_gender = models.CharField(max_length=10, blank=True, choices=[('M', 'Male'), ('F', 'Female')])
    target_conditions = models.JSONField(default=list, help_text="ICD-10 codes or condition names")
    
    # Scheduling
    interval_months = models.PositiveIntegerField(help_text="Reminder interval in months")
    lead_time_days = models.PositiveIntegerField(default=30, help_text="Days before due date to remind")
    
    # Clinical Guidelines
    guideline_source = models.CharField(max_length=200, blank=True)
    evidence_grade = models.CharField(max_length=10, blank=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_reminder_type_display()})"
    
    def is_applicable_to_patient(self, patient):
        """Check if this reminder applies to a specific patient"""
        # Age check
        if hasattr(patient, 'age'):
            age = patient.age
            if self.target_age_min and age < self.target_age_min:
                return False
            if self.target_age_max and age > self.target_age_max:
                return False
        
        # Gender check
        if self.target_gender and patient.gender != self.target_gender:
            return False
        
        return True


class PatientReminder(BaseModel):
    """Patient-specific reminders"""
    
    REMINDER_STATUS = [
        ('pending', 'Pending'),
        ('due', 'Due'),
        ('overdue', 'Overdue'),
        ('completed', 'Completed'),
        ('dismissed', 'Dismissed'),
        ('not_applicable', 'Not Applicable'),
    ]
    
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='reminders')
    preventive_care = models.ForeignKey(PreventiveCareReminder, on_delete=models.CASCADE)
    
    # Reminder Scheduling
    due_date = models.DateField()
    last_completed_date = models.DateField(null=True, blank=True)
    next_due_date = models.DateField(null=True, blank=True)
    
    # Reminder Status
    status = models.CharField(max_length=15, choices=REMINDER_STATUS, default='pending')
    priority = models.PositiveIntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(10)])
    
    # Completion Details
    completed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='completed_reminders'
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    completion_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['due_date', '-priority']
        unique_together = ['patient', 'preventive_care', 'due_date']
        indexes = [
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['due_date', 'status']),
        ]
    
    def __str__(self):
        return f"{self.preventive_care.name} - {self.patient} (Due: {self.due_date})"
    
    def mark_completed(self, user, notes=""):
        """Mark reminder as completed"""
        self.status = 'completed'
        self.completed_by = user
        self.completed_at = timezone.now()
        self.completion_notes = notes
        self.last_completed_date = timezone.now().date()
        
        # Calculate next due date
        if self.preventive_care.interval_months:
            from dateutil.relativedelta import relativedelta
            self.next_due_date = self.due_date + relativedelta(months=self.preventive_care.interval_months)
        
        self.save()


class RuleExecution(BaseModel):
    """Log of rule executions"""
    
    EXECUTION_STATUS = [
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
        ('error', 'Error'),
    ]
    
    rule = models.ForeignKey(ClinicalRule, on_delete=models.CASCADE, related_name='executions')
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='rule_executions')
    
    # Execution Details
    executed_at = models.DateTimeField(auto_now_add=True)
    execution_time_ms = models.PositiveIntegerField(help_text="Execution time in milliseconds")
    status = models.CharField(max_length=10, choices=EXECUTION_STATUS)
    
    # Execution Context
    input_data = models.JSONField(default=dict, help_text="Input data used for rule evaluation")
    output_data = models.JSONField(default=dict, help_text="Output from rule execution")
    error_message = models.TextField(blank=True)
    
    # Results
    condition_met = models.BooleanField(default=False)
    alert_generated = models.BooleanField(default=False)
    alert = models.ForeignKey(ClinicalAlert, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-executed_at']
        indexes = [
            models.Index(fields=['rule', 'executed_at']),
            models.Index(fields=['patient', 'executed_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.rule.name} - {self.patient} ({self.get_status_display()})"


class ClinicalProtocol(BaseModel):
    """Clinical care protocols and pathways"""
    
    PROTOCOL_TYPES = [
        ('treatment', 'Treatment Protocol'),
        ('diagnostic', 'Diagnostic Protocol'),
        ('prevention', 'Prevention Protocol'),
        ('emergency', 'Emergency Protocol'),
        ('chronic_care', 'Chronic Care Protocol'),
    ]
    
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    protocol_type = models.CharField(max_length=20, choices=PROTOCOL_TYPES)
    description = models.TextField()
    
    # Protocol Configuration
    steps = models.JSONField(
        default=list,
        help_text="Ordered list of protocol steps"
    )
    conditions = models.JSONField(
        default=dict,
        help_text="Conditions for protocol activation"
    )
    
    # Clinical Guidelines
    guideline_source = models.CharField(max_length=200, blank=True)
    evidence_level = models.CharField(max_length=20, blank=True)
    version = models.CharField(max_length=10, default='1.0')
    
    class Meta:
        ordering = ['name']
        unique_together = ['code', 'version']
    
    def __str__(self):
        return f"{self.name} v{self.version}"


class ProtocolExecution(BaseModel):
    """Execution of clinical protocols"""
    
    EXECUTION_STATUS = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('suspended', 'Suspended'),
    ]
    
    protocol = models.ForeignKey(ClinicalProtocol, on_delete=models.CASCADE, related_name='executions')
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='protocol_executions')
    encounter = models.ForeignKey(
        'medical_records.MedicalRecord',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='protocol_executions'
    )
    
    # Execution Details
    started_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='started_protocols')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Protocol State
    status = models.CharField(max_length=15, choices=EXECUTION_STATUS, default='active')
    current_step = models.PositiveIntegerField(default=0)
    step_results = models.JSONField(default=dict, help_text="Results from each protocol step")
    
    # Notes and Documentation
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['protocol', 'status']),
        ]
    
    def __str__(self):
        return f"{self.protocol.name} - {self.patient} ({self.get_status_display()})"
