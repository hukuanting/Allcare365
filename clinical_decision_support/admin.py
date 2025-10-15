"""
Clinical Decision Support Admin Configuration

This module provides Django admin interface for CDS models.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
import json

from .models import (
    RuleCategory, ClinicalRule, ClinicalAlert, DrugInteraction,
    PreventiveCareReminder, PatientReminder, RuleExecution,
    ClinicalProtocol, ProtocolExecution
)


@admin.register(RuleCategory)
class RuleCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'color_display', 'icon', 'display_order', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['display_order', 'name']
    
    def color_display(self, obj):
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; border: 1px solid #ccc;"></div>',
            obj.color
        )
    color_display.short_description = 'Color'


@admin.register(ClinicalRule)
class ClinicalRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'rule_type', 'priority', 'is_active', 'created_at']
    list_filter = ['category', 'rule_type', 'priority', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['-priority', 'name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'category', 'rule_type')
        }),
        ('Rule Configuration', {
            'fields': ('priority', 'conditions', 'actions', 'target_population')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category')


@admin.register(ClinicalAlert)
class ClinicalAlertAdmin(admin.ModelAdmin):
    list_display = ['title', 'patient_link', 'alert_level', 'rule_link', 'acknowledged_status', 'triggered_at']
    list_filter = ['alert_level', 'status', 'acknowledged_at', 'triggered_at']
    search_fields = ['title', 'message', 'patient__first_name', 'patient__last_name']
    ordering = ['-triggered_at']
    readonly_fields = ['triggered_at', 'created_at', 'updated_at']
    
    def patient_link(self, obj):
        if obj.patient:
            url = reverse('admin:patients_patient_change', args=[obj.patient.id])
            return format_html('<a href="{}">{}</a>', url, obj.patient)
        return '-'
    patient_link.short_description = 'Patient'
    
    def rule_link(self, obj):
        if obj.rule:
            url = reverse('admin:clinical_decision_support_clinicalrule_change', args=[obj.rule.id])
            return format_html('<a href="{}">{}</a>', url, obj.rule.name)
        return '-'
    rule_link.short_description = 'Rule'
    
    def acknowledged_status(self, obj):
        if obj.acknowledged_at:
            return format_html(
                '<span style="color: green;">✓ {}</span>', 
                obj.acknowledged_at.strftime('%Y-%m-%d %H:%M')
            )
        return format_html('<span style="color: red;">✗ Not acknowledged</span>')
    acknowledged_status.short_description = 'Acknowledged'


@admin.register(DrugInteraction)
class DrugInteractionAdmin(admin.ModelAdmin):
    list_display = ['drug_1', 'drug_2', 'severity', 'interaction_type', 'is_active']
    list_filter = ['severity', 'interaction_type', 'is_active']
    search_fields = ['drug_1', 'drug_2', 'mechanism']
    ordering = ['-severity', 'drug_1']
    
    fieldsets = (
        ('Drug Information', {
            'fields': ('drug_1', 'drug_2', 'interaction_type', 'severity')
        }),
        ('Interaction Details', {
            'fields': ('mechanism', 'clinical_effect', 'management')
        }),
        ('References', {
            'fields': ('evidence_level', 'reference_source', 'reference_url'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        })
    )


@admin.register(PreventiveCareReminder)
class PreventiveCareReminderAdmin(admin.ModelAdmin):
    list_display = ['name', 'reminder_type', 'age_range_display', 'interval_months', 'is_active']
    list_filter = ['reminder_type', 'is_active']
    search_fields = ['name', 'description']
    ordering = ['name']
    
    def age_range_display(self, obj):
        return f"{obj.target_age_min or 'Any'} - {obj.target_age_max or 'Any'}"
    age_range_display.short_description = 'Age Range'


@admin.register(PatientReminder)
class PatientReminderAdmin(admin.ModelAdmin):
    list_display = ['patient_link', 'preventive_care', 'due_date', 'status', 'priority']
    list_filter = ['status', 'priority', 'due_date']
    search_fields = ['patient__first_name', 'patient__last_name', 'preventive_care__name']
    ordering = ['-due_date']
    
    def patient_link(self, obj):
        url = reverse('admin:patients_patient_change', args=[obj.patient.id])
        return format_html('<a href="{}">{}</a>', url, obj.patient)
    patient_link.short_description = 'Patient'


@admin.register(RuleExecution)
class RuleExecutionAdmin(admin.ModelAdmin):
    list_display = ['rule_link', 'patient_link', 'created_by', 'created_at', 'result_summary']
    list_filter = ['created_at']
    search_fields = ['rule__name', 'patient__first_name', 'patient__last_name']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
    
    def rule_link(self, obj):
        url = reverse('admin:clinical_decision_support_clinicalrule_change', args=[obj.rule.id])
        return format_html('<a href="{}">{}</a>', url, obj.rule.name)
    rule_link.short_description = 'Rule'
    
    def patient_link(self, obj):
        url = reverse('admin:patients_patient_change', args=[obj.patient.id])
        return format_html('<a href="{}">{}</a>', url, obj.patient)
    patient_link.short_description = 'Patient'
    
    def result_summary(self, obj):
        if obj.result:
            try:
                result = obj.result if isinstance(obj.result, dict) else json.loads(obj.result)
                status = result.get('status', 'unknown')
                alerts = result.get('alerts_triggered', 0)
                return f"Status: {status}, Alerts: {alerts}"
            except:
                return 'Invalid result format'
        return 'No result'
    result_summary.short_description = 'Result'


@admin.register(ClinicalProtocol)
class ClinicalProtocolAdmin(admin.ModelAdmin):
    list_display = ['name', 'version', 'protocol_type', 'is_active', 'created_at']
    list_filter = ['protocol_type', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'code']
    ordering = ['name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'description', 'version', 'protocol_type')
        }),
        ('Protocol Details', {
            'fields': ('steps', 'conditions')
        }),
        ('Guidelines', {
            'fields': ('guideline_source', 'evidence_level'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(ProtocolExecution)
class ProtocolExecutionAdmin(admin.ModelAdmin):
    list_display = ['protocol_link', 'patient_link', 'status', 'created_by', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['protocol__name', 'patient__first_name', 'patient__last_name']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    def protocol_link(self, obj):
        url = reverse('admin:clinical_decision_support_clinicalprotocol_change', args=[obj.protocol.id])
        return format_html('<a href="{}">{}</a>', url, obj.protocol.name)
    protocol_link.short_description = 'Protocol'
    
    def patient_link(self, obj):
        url = reverse('admin:patients_patient_change', args=[obj.patient.id])
        return format_html('<a href="{}">{}</a>', url, obj.patient)
    patient_link.short_description = 'Patient'
