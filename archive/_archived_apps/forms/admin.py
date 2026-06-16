"""
Admin interface for the Clinical Forms Engine

Provides comprehensive admin interface for managing forms, templates, and submissions.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Avg
from .models import (
    FormCategory, FormTemplate, FormField, FormSubmission, 
    FormValidationRule, FormAuditLog, StandardizedAssessment, FormReport
)


@admin.register(FormCategory)
class FormCategoryAdmin(admin.ModelAdmin):
    """Admin for form categories"""
    
    list_display = ['name', 'description', 'display_order', 'form_count', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['display_order', 'name']
    
    def form_count(self, obj):
        """Get count of forms in this category"""
        return obj.form_templates.filter(is_active=True).count()
    
    form_count.short_description = 'Active Forms'


class FormFieldInline(admin.TabularInline):
    """Inline editor for form fields"""
    
    model = FormField
    extra = 0
    fields = [
        'field_name', 'field_label', 'field_type', 'is_required', 
        'display_order', 'choices', 'is_active'
    ]
    ordering = ['display_order']


class FormValidationRuleInline(admin.TabularInline):
    """Inline editor for validation rules"""
    
    model = FormValidationRule
    extra = 0
    fields = ['name', 'validation_logic', 'error_message', 'is_blocking', 'is_active']


@admin.register(FormTemplate)
class FormTemplateAdmin(admin.ModelAdmin):
    """Admin for form templates"""
    
    list_display = [
        'name', 'code', 'category', 'form_type', 'version', 
        'is_standardized', 'is_published', 'field_count', 
        'submission_count', 'is_active', 'created_at'
    ]
    list_filter = [
        'category', 'form_type', 'is_standardized', 'is_published', 
        'is_active', 'created_at'
    ]
    search_fields = ['name', 'code', 'description']
    ordering = ['category', 'name']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'category', 'form_type', 'version', 'description')
        }),
        ('Configuration', {
            'fields': (
                'instructions', 'is_standardized', 'requires_authorization',
                'auto_calculate_score', 'scoring_algorithm'
            )
        }),
        ('Publishing', {
            'fields': ('is_published', 'effective_date', 'expiry_date')
        }),
        ('Metadata', {
            'fields': ('reference_url', 'copyright_info'),
            'classes': ('collapse',)
        }),
        ('System', {
            'fields': ('is_active', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [FormFieldInline, FormValidationRuleInline]
    
    def field_count(self, obj):
        """Get count of fields in this template"""
        return obj.form_fields.count()
    
    field_count.short_description = 'Fields'
    
    def submission_count(self, obj):
        """Get count of submissions for this template"""
        count = obj.submissions.count()
        if count > 0:
            url = reverse('admin:forms_formsubmission_changelist') + f'?template__id__exact={obj.id}'
            return format_html('<a href="{}">{}</a>', url, count)
        return count
    
    submission_count.short_description = 'Submissions'
    
    def get_queryset(self, request):
        """Optimize queryset with prefetch"""
        return super().get_queryset(request).select_related('category').prefetch_related('form_fields', 'submissions')


@admin.register(FormField)
class FormFieldAdmin(admin.ModelAdmin):
    """Admin for form fields"""
    
    list_display = [
        'template', 'field_name', 'field_label', 'field_type', 
        'is_required', 'display_order', 'is_active'
    ]
    list_filter = ['field_type', 'is_required', 'is_active', 'template__category']
    search_fields = ['field_name', 'field_label', 'template__name']
    ordering = ['template', 'display_order']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('template', 'field_name', 'field_label', 'field_type', 'help_text')
        }),
        ('Configuration', {
            'fields': ('placeholder', 'default_value', 'display_order', 'css_classes')
        }),
        ('Validation', {
            'fields': (
                'is_required', 'min_length', 'max_length', 'min_value', 'max_value',
                'validation_regex', 'validation_message'
            )
        }),
        ('Choice Fields', {
            'fields': ('choices',),
            'classes': ('collapse',)
        }),
        ('Scale Fields', {
            'fields': ('scale_min', 'scale_max', 'scale_step', 'scale_labels'),
            'classes': ('collapse',)
        }),
        ('Advanced', {
            'fields': ('show_condition', 'calculation_formula', 'is_active'),
            'classes': ('collapse',)
        })
    )


@admin.register(FormSubmission)
class FormSubmissionAdmin(admin.ModelAdmin):
    """Admin for form submissions"""
    
    list_display = [
        'template', 'patient', 'submitted_by', 'submission_date', 
        'status', 'completion_percentage', 'score_display', 'review_status'
    ]
    list_filter = [
        'status', 'template__category', 'template', 'submission_date', 
        'reviewed_by', 'created_at'
    ]
    search_fields = [
        'template__name', 'patient__first_name', 'patient__last_name', 
        'submitted_by__first_name', 'submitted_by__last_name'
    ]
    ordering = ['-submission_date']
    
    readonly_fields = ['submission_date', 'calculated_scores', 'completion_percentage']
    
    fieldsets = (
        ('Submission Information', {
            'fields': ('template', 'patient', 'encounter', 'submitted_by', 'submission_date')
        }),
        ('Status', {
            'fields': ('status', 'completion_percentage')
        }),
        ('Form Data', {
            'fields': ('form_data', 'calculated_scores'),
            'classes': ('collapse',)
        }),
        ('Review', {
            'fields': ('reviewed_by', 'review_date', 'review_notes')
        }),
        ('Metadata', {
            'fields': ('completion_time_seconds', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        })
    )
    
    def completion_percentage(self, obj):
        """Display completion percentage"""
        percentage = obj.get_completion_percentage()
        if percentage == 100:
            color = 'green'
        elif percentage >= 80:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            color, percentage
        )
    
    completion_percentage.short_description = 'Completion'
    
    def score_display(self, obj):
        """Display calculated scores"""
        if obj.calculated_scores and 'total_score' in obj.calculated_scores:
            return f"{obj.calculated_scores['total_score']:.1f}"
        return "-"
    
    score_display.short_description = 'Score'
    
    def review_status(self, obj):
        """Display review status"""
        if obj.reviewed_by:
            return format_html(
                '<span style="color: green;">Reviewed by {}</span>',
                obj.reviewed_by.get_full_name()
            )
        elif obj.status == 'submitted':
            return format_html('<span style="color: orange;">Pending Review</span>')
        return "-"
    
    review_status.short_description = 'Review Status'
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related(
            'template', 'patient', 'submitted_by', 'reviewed_by'
        )


@admin.register(FormValidationRule)
class FormValidationRuleAdmin(admin.ModelAdmin):
    """Admin for form validation rules"""
    
    list_display = ['template', 'name', 'is_blocking', 'trigger_on_change', 'is_active']
    list_filter = ['is_blocking', 'trigger_on_change', 'is_active', 'template__category']
    search_fields = ['name', 'description', 'template__name']
    ordering = ['template', 'name']


@admin.register(FormAuditLog)
class FormAuditLogAdmin(admin.ModelAdmin):
    """Admin for form audit logs"""
    
    list_display = [
        'template', 'patient', 'action', 'performed_by', 
        'timestamp', 'ip_address'
    ]
    list_filter = ['action', 'timestamp', 'template__category']
    search_fields = [
        'template__name', 'patient__first_name', 'patient__last_name',
        'performed_by__first_name', 'performed_by__last_name'
    ]
    ordering = ['-timestamp']
    readonly_fields = ['timestamp']
    
    def has_add_permission(self, request):
        """Prevent manual addition of audit logs"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent modification of audit logs"""
        return False


@admin.register(StandardizedAssessment)
class StandardizedAssessmentAdmin(admin.ModelAdmin):
    """Admin for standardized assessments"""
    
    list_display = ['assessment_type', 'template', 'is_validated', 'is_active']
    list_filter = ['assessment_type', 'is_validated', 'is_active']
    search_fields = ['assessment_type', 'template__name', 'clinical_use']
    
    fieldsets = (
        ('Assessment Information', {
            'fields': ('assessment_type', 'template')
        }),
        ('Clinical Details', {
            'fields': ('reference_citation', 'clinical_use', 'scoring_interpretation')
        }),
        ('Validation', {
            'fields': ('is_validated', 'validation_studies')
        }),
        ('System', {
            'fields': ('is_active',)
        })
    )


@admin.register(FormReport)
class FormReportAdmin(admin.ModelAdmin):
    """Admin for form reports"""
    
    list_display = [
        'name', 'report_type', 'output_format', 'template_count',
        'generation_date', 'created_at'
    ]
    list_filter = ['report_type', 'output_format', 'generation_date', 'created_at']
    search_fields = ['name']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Report Information', {
            'fields': ('name', 'report_type', 'templates')
        }),
        ('Configuration', {
            'fields': (
                'filters', 'date_range_start', 'date_range_end', 
                'output_format'
            )
        }),
        ('Options', {
            'fields': (
                'include_patient_details', 'include_scores', 'include_trends'
            )
        }),
        ('Generated Report', {
            'fields': ('generated_file', 'generation_date'),
            'classes': ('collapse',)
        })
    )
    
    def template_count(self, obj):
        """Get count of templates in this report"""
        return obj.templates.count()
    
    template_count.short_description = 'Templates'


# Custom admin actions
@admin.action(description='Publish selected templates')
def publish_templates(modeladmin, request, queryset):
    """Publish selected form templates"""
    updated = queryset.update(is_published=True)
    modeladmin.message_user(
        request, f'{updated} templates were successfully published.'
    )


@admin.action(description='Unpublish selected templates')
def unpublish_templates(modeladmin, request, queryset):
    """Unpublish selected form templates"""
    updated = queryset.update(is_published=False)
    modeladmin.message_user(
        request, f'{updated} templates were successfully unpublished.'
    )


@admin.action(description='Mark as reviewed')
def mark_reviewed(modeladmin, request, queryset):
    """Mark selected submissions as reviewed"""
    from django.utils import timezone
    updated = queryset.update(
        status='reviewed',
        reviewed_by=request.user,
        review_date=timezone.now()
    )
    modeladmin.message_user(
        request, f'{updated} submissions were marked as reviewed.'
    )


# Add actions to admin classes
FormTemplateAdmin.actions = [publish_templates, unpublish_templates]
FormSubmissionAdmin.actions = [mark_reviewed]
