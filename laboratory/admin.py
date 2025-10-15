"""
Laboratory management admin interface.

This module provides Django admin interface for:
- Laboratory providers and configuration
- Lab test types and categories
- Lab orders and results
- Quality control and HL7 messaging
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    LabProvider, LabTestCategory, LabTestType, LabOrder, LabOrderItem,
    LabResult, LabMessage, QualityControlLog
)


@admin.register(LabProvider)
class LabProviderAdmin(admin.ModelAdmin):
    """Admin interface for laboratory providers"""
    list_display = ['name', 'interface_type', 'is_preferred', 'average_turnaround_time', 'is_active']
    list_filter = ['interface_type', 'is_preferred', 'is_active']
    search_fields = ['name', 'contact_name', 'clia_number']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['name', 'contact_name', 'phone', 'email', 'address']
        }),
        ('Technical Configuration', {
            'fields': ['interface_type', 'hl7_config', 'api_endpoint', 'api_key']
        }),
        ('Business Details', {
            'fields': ['lab_license_number', 'clia_number', 'average_turnaround_time', 'is_preferred']
        }),
        ('System Fields', {
            'fields': ['id', 'is_active', 'created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]


@admin.register(LabTestCategory)
class LabTestCategoryAdmin(admin.ModelAdmin):
    """Admin interface for lab test categories"""
    list_display = ['name', 'code', 'parent_category', 'sort_order', 'is_active']
    list_filter = ['parent_category', 'is_active']
    search_fields = ['name', 'code']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['sort_order', 'name']
    
    fieldsets = [
        ('Category Information', {
            'fields': ['name', 'code', 'description', 'parent_category', 'sort_order']
        }),
        ('System Fields', {
            'fields': ['id', 'is_active', 'created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]


@admin.register(LabTestType)
class LabTestTypeAdmin(admin.ModelAdmin):
    """Admin interface for lab test types"""
    list_display = ['name', 'category', 'specimen_type', 'result_type', 'cost', 'requires_fasting', 'is_active']
    list_filter = ['category', 'specimen_type', 'result_type', 'requires_fasting', 'is_active']
    search_fields = ['name', 'loinc_code', 'cpt_code', 'snomed_code']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['name', 'short_name', 'category']
        }),
        ('Medical Coding', {
            'fields': ['loinc_code', 'cpt_code', 'snomed_code']
        }),
        ('Specimen Information', {
            'fields': ['specimen_type', 'specimen_volume', 'collection_instructions']
        }),
        ('Reference Ranges', {
            'fields': ['units', 'reference_range_male', 'reference_range_female', 
                      'reference_range_pediatric', 'critical_low', 'critical_high']
        }),
        ('Result Configuration', {
            'fields': ['result_type', 'possible_values']
        }),
        ('Operational', {
            'fields': ['average_tat', 'cost', 'requires_fasting']
        }),
        ('System Fields', {
            'fields': ['id', 'is_active', 'created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]


class LabOrderItemInline(admin.TabularInline):
    """Inline admin for lab order items"""
    model = LabOrderItem
    extra = 0
    readonly_fields = ['id', 'created_at', 'updated_at']
    fields = ['test_type', 'specimen_id', 'collection_tube', 'status', 'cost']


@admin.register(LabOrder)
class LabOrderAdmin(admin.ModelAdmin):
    """Admin interface for lab orders"""
    list_display = ['order_number', 'patient_link', 'provider_link', 'priority', 'status', 'order_date', 'total_cost']
    list_filter = ['status', 'priority', 'order_date', 'lab_provider']
    search_fields = ['order_number', 'patient__first_name', 'patient__last_name', 'provider__user__first_name', 'provider__user__last_name']
    readonly_fields = ['id', 'order_number', 'created_at', 'updated_at']
    inlines = [LabOrderItemInline]
    date_hierarchy = 'order_date'
    
    fieldsets = [
        ('Order Information', {
            'fields': ['order_number', 'patient', 'provider', 'encounter', 'lab_provider']
        }),
        ('Order Details', {
            'fields': ['order_date', 'priority', 'clinical_info', 'diagnosis_codes']
        }),
        ('Collection Information', {
            'fields': ['collection_date', 'collection_location', 'collector_name']
        }),
        ('Status and External References', {
            'fields': ['status', 'status_notes', 'external_order_id', 'hl7_message_id']
        }),
        ('Billing', {
            'fields': ['total_cost', 'insurance_coverage']
        }),
        ('System Fields', {
            'fields': ['id', 'is_active', 'created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    def patient_link(self, obj):
        """Create link to patient"""
        if obj.patient:
            url = reverse('admin:patients_patient_change', args=[obj.patient.id])
            return format_html('<a href="{}">{}</a>', url, obj.patient.full_name)
        return '-'
    patient_link.short_description = 'Patient'
    
    def provider_link(self, obj):
        """Create link to provider"""
        if obj.provider:
            url = reverse('admin:administration_provider_change', args=[obj.provider.id])
            return format_html('<a href="{}">{}</a>', url, obj.provider.user.get_full_name())
        return '-'
    provider_link.short_description = 'Provider'


class LabResultInline(admin.TabularInline):
    """Inline admin for lab results"""
    model = LabResult
    extra = 0
    readonly_fields = ['id', 'is_critical', 'is_abnormal', 'created_at', 'updated_at']
    fields = ['result_value', 'units', 'abnormal_flag', 'result_status', 'verified_by', 'verified_date']


@admin.register(LabOrderItem)
class LabOrderItemAdmin(admin.ModelAdmin):
    """Admin interface for lab order items"""
    list_display = ['__str__', 'test_type', 'status', 'cost']
    list_filter = ['status', 'test_type__category']
    search_fields = ['lab_order__order_number', 'test_type__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [LabResultInline]
    
    fieldsets = [
        ('Order Item Information', {
            'fields': ['lab_order', 'test_type', 'specimen_id', 'collection_tube']
        }),
        ('Status and Cost', {
            'fields': ['status', 'cost']
        }),
        ('System Fields', {
            'fields': ['id', 'created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]


@admin.register(LabResult)
class LabResultAdmin(admin.ModelAdmin):
    """Admin interface for lab results"""
    list_display = ['test_name', 'patient_name', 'result_value', 'abnormal_flag', 'result_status', 'verified_date', 'is_critical_display']
    list_filter = ['abnormal_flag', 'result_status', 'pathologist_review', 'result_date']
    search_fields = ['order_item__test_type__name', 'order_item__lab_order__patient__first_name', 'order_item__lab_order__patient__last_name']
    readonly_fields = ['id', 'is_critical', 'is_abnormal', 'created_at', 'updated_at']
    date_hierarchy = 'result_date'
    
    fieldsets = [
        ('Result Information', {
            'fields': ['order_item', 'result_value', 'result_text', 'units', 'reference_range']
        }),
        ('Abnormal Flags', {
            'fields': ['abnormal_flag', 'result_status']
        }),
        ('Quality Control', {
            'fields': ['instrument_id', 'technician_id']
        }),
        ('Verification', {
            'fields': ['verified_by', 'verified_date', 'pathologist_review', 'pathologist_notes']
        }),
        ('External References', {
            'fields': ['external_result_id', 'hl7_message_id']
        }),
        ('System Fields', {
            'fields': ['id', 'is_critical', 'is_abnormal', 'created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    def test_name(self, obj):
        """Get test name"""
        return obj.order_item.test_type.name if obj.order_item else '-'
    test_name.short_description = 'Test'
    
    def patient_name(self, obj):
        """Get patient name"""
        return obj.order_item.lab_order.patient.full_name if obj.order_item else '-'
    patient_name.short_description = 'Patient'
    
    def is_critical_display(self, obj):
        """Display critical status with color"""
        if obj.is_critical:
            return format_html('<span style="color: red; font-weight: bold;">Critical</span>')
        return '-'
    is_critical_display.short_description = 'Critical'


@admin.register(LabMessage)
class LabMessageAdmin(admin.ModelAdmin):
    """Admin interface for HL7 messages"""
    list_display = ['message_type', 'lab_provider', 'processing_status', 'created_at']
    list_filter = ['message_type', 'processing_status', 'lab_provider']
    search_fields = ['external_message_id', 'lab_provider__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = [
        ('Message Information', {
            'fields': ['lab_provider', 'message_type', 'external_message_id']
        }),
        ('Message Content', {
            'fields': ['raw_message', 'parsed_data']
        }),
        ('Processing Status', {
            'fields': ['processing_status', 'error_message']
        }),
        ('References', {
            'fields': ['lab_order']
        }),
        ('System Fields', {
            'fields': ['id', 'created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]


@admin.register(QualityControlLog)
class QualityControlLogAdmin(admin.ModelAdmin):
    """Admin interface for quality control logs"""
    list_display = ['test_type', 'qc_type', 'passed_display', 'performed_by', 'created_at']
    list_filter = ['qc_type', 'passed', 'test_type__category']
    search_fields = ['test_type__name', 'performed_by', 'control_lot']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = [
        ('QC Information', {
            'fields': ['lab_provider', 'test_type', 'qc_type', 'control_lot']
        }),
        ('QC Values', {
            'fields': ['expected_value', 'measured_value', 'acceptable_range', 'passed']
        }),
        ('Technician and Equipment', {
            'fields': ['performed_by', 'instrument_id']
        }),
        ('Notes', {
            'fields': ['notes']
        }),
        ('System Fields', {
            'fields': ['id', 'created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    def passed_display(self, obj):
        """Display pass/fail status with color"""
        if obj.passed:
            return format_html('<span style="color: green; font-weight: bold;">Passed</span>')
        else:
            return format_html('<span style="color: red; font-weight: bold;">Failed</span>')
    passed_display.short_description = 'Status'
