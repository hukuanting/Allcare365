"""
Clinical Forms Engine Models

This module defines the data models for the clinical forms engine,
supporting dynamic form creation, submission, and validation.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import RegexValidator
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


class FormCategory(BaseModel):
    """Categories for organizing forms"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name_plural = "Form Categories"
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return self.name


class FormTemplate(BaseModel):
    """Template definition for clinical forms"""
    
    FORM_TYPES = [
        ('assessment', 'Assessment Form'),
        ('screening', 'Screening Form'),
        ('documentation', 'Documentation Form'),
        ('questionnaire', 'Questionnaire'),
        ('scale', 'Rating Scale'),
        ('checklist', 'Checklist'),
        ('soap', 'SOAP Note'),
        ('vitals', 'Vital Signs'),
        ('custom', 'Custom Form'),
    ]
    
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)  # 內部代碼，如 GAD7, PHQ9
    category = models.ForeignKey(FormCategory, on_delete=models.CASCADE, related_name='form_templates')
    form_type = models.CharField(max_length=20, choices=FORM_TYPES)
    version = models.CharField(max_length=10, default='1.0')
    description = models.TextField()
    instructions = models.TextField(blank=True, help_text="Instructions for completing the form")
    
    # Form Configuration
    is_standardized = models.BooleanField(default=False, help_text="Is this a standardized clinical form?")
    requires_authorization = models.BooleanField(default=False)
    auto_calculate_score = models.BooleanField(default=False)
    scoring_algorithm = models.JSONField(default=dict, blank=True)
    
    # Workflow Settings
    is_published = models.BooleanField(default=False)
    effective_date = models.DateTimeField(default=timezone.now)
    expiry_date = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    reference_url = models.URLField(blank=True, help_text="Reference to official documentation")
    copyright_info = models.TextField(blank=True)
    
    class Meta:
        ordering = ['category', 'name']
        unique_together = ['code', 'version']
    
    def __str__(self):
        return f"{self.name} v{self.version}"
    
    @property
    def is_active_form(self):
        """Check if form is currently active"""
        now = timezone.now()
        if self.expiry_date and now > self.expiry_date:
            return False
        return self.is_active and self.is_published and now >= self.effective_date
    
    def get_total_fields(self):
        """Get total number of fields in this form"""
        return self.form_fields.count()
    
    def get_required_fields(self):
        """Get number of required fields"""
        return self.form_fields.filter(is_required=True).count()


class FormField(BaseModel):
    """Individual field definition within a form template"""
    
    FIELD_TYPES = [
        ('text', 'Text Input'),
        ('textarea', 'Text Area'),
        ('number', 'Number'),
        ('decimal', 'Decimal'),
        ('email', 'Email'),
        ('url', 'URL'),
        ('date', 'Date'),
        ('time', 'Time'),
        ('datetime', 'Date and Time'),
        ('boolean', 'Yes/No'),
        ('radio', 'Radio Buttons'),
        ('checkbox', 'Checkboxes'),
        ('select', 'Dropdown'),
        ('multiselect', 'Multiple Select'),
        ('scale', 'Rating Scale'),
        ('file', 'File Upload'),
        ('signature', 'Digital Signature'),
        ('calculated', 'Calculated Field'),
        ('separator', 'Section Separator'),
        ('instruction', 'Instruction Text'),
    ]
    
    template = models.ForeignKey(FormTemplate, on_delete=models.CASCADE, related_name='form_fields')
    field_name = models.CharField(max_length=100)  # 內部欄位名稱
    field_label = models.CharField(max_length=200)  # 顯示標籤
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES)
    
    # Field Configuration
    help_text = models.TextField(blank=True)
    placeholder = models.CharField(max_length=200, blank=True)
    default_value = models.TextField(blank=True)
    
    # Validation Rules
    is_required = models.BooleanField(default=False)
    min_length = models.PositiveIntegerField(null=True, blank=True)
    max_length = models.PositiveIntegerField(null=True, blank=True)
    min_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    validation_regex = models.CharField(max_length=500, blank=True)
    validation_message = models.CharField(max_length=200, blank=True)
    
    # Display Configuration
    display_order = models.PositiveIntegerField(default=0)
    css_classes = models.CharField(max_length=200, blank=True)
    show_condition = models.JSONField(default=dict, blank=True, help_text="Conditional display rules")
    
    # For choice fields (radio, checkbox, select)
    choices = models.JSONField(default=list, blank=True, help_text="Options for choice fields")
    
    # For scale fields
    scale_min = models.IntegerField(null=True, blank=True)
    scale_max = models.IntegerField(null=True, blank=True)
    scale_step = models.IntegerField(default=1, null=True, blank=True)
    scale_labels = models.JSONField(default=dict, blank=True, help_text="Labels for scale endpoints")
    
    # For calculated fields
    calculation_formula = models.TextField(blank=True, help_text="Formula for calculated fields")
    
    class Meta:
        ordering = ['template', 'display_order', 'field_name']
        unique_together = ['template', 'field_name']
    
    def __str__(self):
        return f"{self.template.name} - {self.field_label}"
    
    def clean(self):
        """Validate field configuration"""
        from django.core.exceptions import ValidationError
        
        # Validate choices for choice fields
        if self.field_type in ['radio', 'checkbox', 'select', 'multiselect']:
            if not self.choices:
                raise ValidationError("Choice fields must have options defined")
        
        # Validate scale configuration
        if self.field_type == 'scale':
            if self.scale_min is None or self.scale_max is None:
                raise ValidationError("Scale fields must have min and max values")
            if self.scale_min >= self.scale_max:
                raise ValidationError("Scale min value must be less than max value")


class FormSubmission(BaseModel):
    """A completed form submission"""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('reviewed', 'Reviewed'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('archived', 'Archived'),
    ]
    
    template = models.ForeignKey(FormTemplate, on_delete=models.CASCADE, related_name='submissions')
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='form_submissions')
    encounter = models.ForeignKey('medical_records.MedicalRecord', on_delete=models.CASCADE, null=True, blank=True, related_name='form_submissions')
    
    # Submission Details
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='form_submissions')
    submission_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    
    # Form Data
    form_data = models.JSONField(default=dict, help_text="Form field values")
    calculated_scores = models.JSONField(default=dict, blank=True, help_text="Calculated scores and results")
    
    # Review Information
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_submissions')
    review_date = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    
    # Metadata
    completion_time_seconds = models.PositiveIntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-submission_date']
    
    def __str__(self):
        return f"{self.template.name} - {self.patient} - {self.submission_date.strftime('%Y-%m-%d')}"
    
    def calculate_score(self):
        """Calculate score based on template scoring algorithm"""
        if not self.template.auto_calculate_score or not self.template.scoring_algorithm:
            return None
        
        algorithm = self.template.scoring_algorithm
        total_score = 0
        
        try:
            # Simple scoring algorithm - sum of weighted values
            for field_name, weight in algorithm.items():
                if field_name in self.form_data:
                    value = self.form_data[field_name]
                    if isinstance(value, (int, float)):
                        total_score += value * weight
                    elif isinstance(value, str) and value.isdigit():
                        total_score += int(value) * weight
            
            self.calculated_scores['total_score'] = total_score
            return total_score
            
        except Exception as e:
            # Log error and return None
            return None
    
    def get_completion_percentage(self):
        """Calculate completion percentage"""
        required_fields = self.template.form_fields.filter(is_required=True)
        if not required_fields.exists():
            return 100.0
        
        completed_required = 0
        for field in required_fields:
            if field.field_name in self.form_data and self.form_data[field.field_name]:
                completed_required += 1
        
        return (completed_required / required_fields.count()) * 100
    
    def is_complete(self):
        """Check if all required fields are completed"""
        return self.get_completion_percentage() == 100.0


class FormValidationRule(BaseModel):
    """Custom validation rules for forms"""
    
    template = models.ForeignKey(FormTemplate, on_delete=models.CASCADE, related_name='validation_rules')
    name = models.CharField(max_length=100)
    description = models.TextField()
    
    # Rule Configuration
    field_dependencies = models.JSONField(default=list, help_text="Fields this rule depends on")
    validation_logic = models.TextField(help_text="Validation logic (Python expression)")
    error_message = models.CharField(max_length=200)
    warning_message = models.CharField(max_length=200, blank=True)
    
    # Rule Settings
    is_blocking = models.BooleanField(default=True, help_text="Prevents submission if failed")
    trigger_on_change = models.BooleanField(default=False, help_text="Validate on field change")
    
    class Meta:
        ordering = ['template', 'name']
    
    def __str__(self):
        return f"{self.template.name} - {self.name}"


class FormAuditLog(BaseModel):
    """Audit trail for form activities"""
    
    ACTION_CHOICES = [
        ('created', 'Form Created'),
        ('viewed', 'Form Viewed'),
        ('started', 'Form Started'),
        ('saved', 'Form Saved (Draft)'),
        ('submitted', 'Form Submitted'),
        ('reviewed', 'Form Reviewed'),
        ('approved', 'Form Approved'),
        ('rejected', 'Form Rejected'),
        ('modified', 'Form Modified'),
        ('deleted', 'Form Deleted'),
        ('exported', 'Form Exported'),
        ('printed', 'Form Printed'),
    ]
    
    submission = models.ForeignKey(FormSubmission, on_delete=models.CASCADE, related_name='audit_logs', null=True, blank=True)
    template = models.ForeignKey(FormTemplate, on_delete=models.CASCADE, related_name='audit_logs')
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='form_audit_logs')
    
    # Action Details
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(default=timezone.now)
    
    # Context Information
    details = models.JSONField(default=dict, blank=True, help_text="Additional action details")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.action} - {self.template.name} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class StandardizedAssessment(BaseModel):
    """Predefined standardized clinical assessments"""
    
    ASSESSMENT_TYPES = [
        ('gad7', 'GAD-7 (Generalized Anxiety Disorder 7-item)'),
        ('phq9', 'PHQ-9 (Patient Health Questionnaire-9)'),
        ('phq2', 'PHQ-2 (Patient Health Questionnaire-2)'),
        ('mmse', 'MMSE (Mini-Mental State Examination)'),
        ('moca', 'MoCA (Montreal Cognitive Assessment)'),
        ('audit', 'AUDIT (Alcohol Use Disorders Identification Test)'),
        ('cage', 'CAGE Questionnaire'),
        ('epworth', 'Epworth Sleepiness Scale'),
        ('beck_depression', 'Beck Depression Inventory'),
        ('hamilton_depression', 'Hamilton Depression Rating Scale'),
        ('pain_scale', 'Pain Assessment Scale'),
        ('fall_risk', 'Fall Risk Assessment'),
        ('medication_adherence', 'Medication Adherence Scale'),
        ('quality_of_life', 'Quality of Life Assessment'),
    ]
    
    assessment_type = models.CharField(max_length=30, choices=ASSESSMENT_TYPES, unique=True)
    template = models.OneToOneField(FormTemplate, on_delete=models.CASCADE, related_name='standardized_assessment')
    
    # Assessment Metadata
    reference_citation = models.TextField(blank=True)
    clinical_use = models.TextField(help_text="Clinical applications and use cases")
    scoring_interpretation = models.JSONField(default=dict, help_text="Score ranges and interpretations")
    
    # Validation
    is_validated = models.BooleanField(default=False, help_text="Clinically validated assessment")
    validation_studies = models.TextField(blank=True)
    
    class Meta:
        ordering = ['assessment_type']
    
    def __str__(self):
        return f"{self.get_assessment_type_display()}"


class FormReport(BaseModel):
    """Generated reports from form data"""
    
    REPORT_TYPES = [
        ('individual', 'Individual Patient Report'),
        ('summary', 'Summary Report'),
        ('trend', 'Trend Analysis'),
        ('comparison', 'Comparison Report'),
        ('population', 'Population Analysis'),
        ('quality', 'Quality Metrics'),
    ]
    
    FORMATS = [
        ('pdf', 'PDF Document'),
        ('excel', 'Excel Spreadsheet'),
        ('csv', 'CSV File'),
        ('json', 'JSON Data'),
        ('xml', 'XML File'),
    ]
    
    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    templates = models.ManyToManyField(FormTemplate, related_name='reports')
    
    # Report Configuration
    filters = models.JSONField(default=dict, help_text="Report filters and criteria")
    date_range_start = models.DateField(null=True, blank=True)
    date_range_end = models.DateField(null=True, blank=True)
    
    # Output Settings
    output_format = models.CharField(max_length=10, choices=FORMATS, default='pdf')
    include_patient_details = models.BooleanField(default=True)
    include_scores = models.BooleanField(default=True)
    include_trends = models.BooleanField(default=False)
    
    # Generated Report
    generated_file = models.FileField(upload_to='form_reports/', null=True, blank=True)
    generation_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
