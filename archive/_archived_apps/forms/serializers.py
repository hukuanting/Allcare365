"""
Serializers for the Clinical Forms Engine

Provides API serialization for form templates, submissions, and related data.
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    FormCategory, FormTemplate, FormField, FormSubmission, 
    FormValidationRule, FormAuditLog, StandardizedAssessment, FormReport
)


class FormCategorySerializer(serializers.ModelSerializer):
    """Serializer for form categories"""
    
    form_count = serializers.SerializerMethodField()
    
    class Meta:
        model = FormCategory
        fields = [
            'id', 'name', 'description', 'display_order', 
            'is_active', 'created_at', 'updated_at', 'form_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_form_count(self, obj):
        """Get count of active forms in this category"""
        return obj.form_templates.filter(is_active=True, is_published=True).count()


class FormFieldSerializer(serializers.ModelSerializer):
    """Serializer for form fields"""
    
    class Meta:
        model = FormField
        fields = [
            'id', 'field_name', 'field_label', 'field_type', 'help_text',
            'placeholder', 'default_value', 'is_required', 'min_length',
            'max_length', 'min_value', 'max_value', 'validation_regex',
            'validation_message', 'display_order', 'css_classes', 'show_condition',
            'choices', 'scale_min', 'scale_max', 'scale_step', 'scale_labels',
            'calculation_formula', 'is_active'
        ]
        read_only_fields = ['id']


class FormTemplateSerializer(serializers.ModelSerializer):
    """Serializer for form templates"""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    form_fields = FormFieldSerializer(many=True, read_only=True)
    total_fields = serializers.SerializerMethodField()
    required_fields = serializers.SerializerMethodField()
    submission_count = serializers.SerializerMethodField()
    
    class Meta:
        model = FormTemplate
        fields = [
            'id', 'name', 'code', 'category', 'category_name', 'form_type',
            'version', 'description', 'instructions', 'is_standardized',
            'requires_authorization', 'auto_calculate_score', 'scoring_algorithm',
            'is_published', 'effective_date', 'expiry_date', 'reference_url',
            'copyright_info', 'is_active', 'created_at', 'updated_at',
            'form_fields', 'total_fields', 'required_fields', 'submission_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_total_fields(self, obj):
        """Get total number of fields"""
        return obj.get_total_fields()
    
    def get_required_fields(self, obj):
        """Get number of required fields"""
        return obj.get_required_fields()
    
    def get_submission_count(self, obj):
        """Get total submission count"""
        return obj.submissions.count()


class FormTemplateListSerializer(serializers.ModelSerializer):
    """Simplified serializer for form template lists"""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    total_fields = serializers.SerializerMethodField()
    
    class Meta:
        model = FormTemplate
        fields = [
            'id', 'name', 'code', 'category_name', 'form_type', 'version',
            'description', 'is_standardized', 'is_published', 'total_fields'
        ]
    
    def get_total_fields(self, obj):
        return obj.get_total_fields()


class FormSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for form submissions"""
    
    template_name = serializers.CharField(source='template.name', read_only=True)
    template_code = serializers.CharField(source='template.code', read_only=True)
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    submitted_by_name = serializers.CharField(source='submitted_by.get_full_name', read_only=True)
    completion_percentage = serializers.SerializerMethodField()
    is_complete = serializers.SerializerMethodField()
    
    class Meta:
        model = FormSubmission
        fields = [
            'id', 'template', 'template_name', 'template_code', 'patient',
            'patient_name', 'encounter', 'submitted_by', 'submitted_by_name',
            'submission_date', 'status', 'form_data', 'calculated_scores',
            'reviewed_by', 'review_date', 'review_notes', 'completion_time_seconds',
            'completion_percentage', 'is_complete', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_completion_percentage(self, obj):
        """Get completion percentage"""
        return obj.get_completion_percentage()
    
    def get_is_complete(self, obj):
        """Check if submission is complete"""
        return obj.is_complete()


class FormSubmissionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating form submissions"""
    
    class Meta:
        model = FormSubmission
        fields = [
            'template', 'patient', 'encounter', 'form_data', 
            'completion_time_seconds', 'status'
        ]
    
    def create(self, validated_data):
        """Create a new form submission"""
        validated_data['submitted_by'] = self.context['request'].user
        submission = super().create(validated_data)
        
        # Calculate scores if applicable
        if submission.template.auto_calculate_score:
            submission.calculate_score()
            submission.save()
        
        return submission


class FormValidationRuleSerializer(serializers.ModelSerializer):
    """Serializer for form validation rules"""
    
    class Meta:
        model = FormValidationRule
        fields = [
            'id', 'template', 'name', 'description', 'field_dependencies',
            'validation_logic', 'error_message', 'warning_message',
            'is_blocking', 'trigger_on_change', 'is_active'
        ]
        read_only_fields = ['id']


class FormAuditLogSerializer(serializers.ModelSerializer):
    """Serializer for form audit logs"""
    
    performed_by_name = serializers.CharField(source='performed_by.get_full_name', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    
    class Meta:
        model = FormAuditLog
        fields = [
            'id', 'submission', 'template', 'template_name', 'patient',
            'patient_name', 'action', 'performed_by', 'performed_by_name',
            'timestamp', 'details', 'ip_address', 'user_agent'
        ]
        read_only_fields = ['id', 'timestamp']


class StandardizedAssessmentSerializer(serializers.ModelSerializer):
    """Serializer for standardized assessments"""
    
    template_name = serializers.CharField(source='template.name', read_only=True)
    
    class Meta:
        model = StandardizedAssessment
        fields = [
            'id', 'assessment_type', 'template', 'template_name',
            'reference_citation', 'clinical_use', 'scoring_interpretation',
            'is_validated', 'validation_studies', 'is_active'
        ]
        read_only_fields = ['id']


class FormReportSerializer(serializers.ModelSerializer):
    """Serializer for form reports"""
    
    template_names = serializers.SerializerMethodField()
    
    class Meta:
        model = FormReport
        fields = [
            'id', 'name', 'report_type', 'templates', 'template_names',
            'filters', 'date_range_start', 'date_range_end', 'output_format',
            'include_patient_details', 'include_scores', 'include_trends',
            'generated_file', 'generation_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'generated_file', 'generation_date']
    
    def get_template_names(self, obj):
        """Get names of associated templates"""
        return [template.name for template in obj.templates.all()]


# Nested serializers for complex operations
class FormFieldCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating form fields"""
    
    class Meta:
        model = FormField
        fields = [
            'field_name', 'field_label', 'field_type', 'help_text',
            'placeholder', 'default_value', 'is_required', 'min_length',
            'max_length', 'min_value', 'max_value', 'validation_regex',
            'validation_message', 'display_order', 'css_classes', 'show_condition',
            'choices', 'scale_min', 'scale_max', 'scale_step', 'scale_labels',
            'calculation_formula'
        ]


class FormTemplateCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating form templates with fields"""
    
    form_fields = FormFieldCreateSerializer(many=True, required=False)
    
    class Meta:
        model = FormTemplate
        fields = [
            'name', 'code', 'category', 'form_type', 'version', 'description',
            'instructions', 'is_standardized', 'requires_authorization',
            'auto_calculate_score', 'scoring_algorithm', 'reference_url',
            'copyright_info', 'form_fields'
        ]
    
    def create(self, validated_data):
        """Create form template with fields"""
        form_fields_data = validated_data.pop('form_fields', [])
        
        template = FormTemplate.objects.create(**validated_data)
        
        for field_data in form_fields_data:
            FormField.objects.create(template=template, **field_data)
        
        return template


# Statistics and Analytics Serializers
class FormAnalyticsSerializer(serializers.Serializer):
    """Serializer for form analytics data"""
    
    template_id = serializers.UUIDField()
    template_name = serializers.CharField()
    total_submissions = serializers.IntegerField()
    completed_submissions = serializers.IntegerField()
    completion_rate = serializers.FloatField()
    average_completion_time = serializers.FloatField(allow_null=True)
    average_score = serializers.FloatField(allow_null=True)
    score_distribution = serializers.DictField()
    submission_trends = serializers.ListField()


class PatientFormSummarySerializer(serializers.Serializer):
    """Serializer for patient form summary"""
    
    patient_id = serializers.UUIDField()
    patient_name = serializers.CharField()
    total_forms = serializers.IntegerField()
    completed_forms = serializers.IntegerField()
    pending_forms = serializers.IntegerField()
    recent_submissions = FormSubmissionSerializer(many=True)
    score_trends = serializers.DictField()
