from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    VaccineManufacturer, Vaccine, VaccineLot, ImmunizationSchedule,
    ScheduledVaccination, Immunization, ImmunizationObservation,
    ImmunizationContraindication, PatientImmunizationAlert
)


@admin.register(VaccineManufacturer)
class VaccineManufacturerAdmin(admin.ModelAdmin):
    """Vaccine manufacturer admin"""
    list_display = ['name', 'code', 'is_active', 'create_date']
    list_filter = ['is_active', 'create_date']
    search_fields = ['name', 'code']
    readonly_fields = ['uuid', 'create_date', 'update_date']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'is_active')
        }),
        ('System Information', {
            'fields': ('uuid', 'create_date', 'update_date'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Vaccine)
class VaccineAdmin(admin.ModelAdmin):
    """Vaccine admin"""
    list_display = ['name', 'cvx_code', 'manufacturer', 'vaccine_type', 'is_active', 'doses_required']
    list_filter = ['is_active', 'manufacturer', 'vaccine_type', 'create_date']
    search_fields = ['name', 'cvx_code', 'short_name']
    readonly_fields = ['uuid', 'create_date', 'update_date']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'short_name', 'cvx_code', 'manufacturer', 'vaccine_type', 'is_active')
        }),
        ('Dosage Information', {
            'fields': ('doses_required', 'interval_days', 'min_age_days', 'max_age_days')
        }),
        ('Storage Requirements', {
            'fields': ('storage_temp_min', 'storage_temp_max'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('uuid', 'create_date', 'update_date'),
            'classes': ('collapse',)
        }),
    )


class VaccineLotAdmin(admin.ModelAdmin):
    """Vaccine lot admin"""
    list_display = ['vaccine', 'lot_number', 'manufacturer', 'expiration_date', 'quantity_available', 'is_expired_display']
    list_filter = ['manufacturer', 'expiration_date', 'create_date']
    search_fields = ['lot_number', 'vaccine__name']
    readonly_fields = ['uuid', 'create_date', 'update_date', 'quantity_available', 'is_expired']
    
    fieldsets = (
        ('Lot Information', {
            'fields': ('vaccine', 'lot_number', 'manufacturer', 'expiration_date', 'storage_location')
        }),
        ('Inventory', {
            'fields': ('quantity_received', 'quantity_used', 'quantity_wasted', 'quantity_available')
        }),
        ('System Information', {
            'fields': ('uuid', 'create_date', 'update_date'),
            'classes': ('collapse',)
        }),
    )
    
    def is_expired_display(self, obj):
        """Display expired status with color"""
        if obj.is_expired:
            return format_html('<span style="color: red;">Expired</span>')
        return format_html('<span style="color: green;">Valid</span>')
    is_expired_display.short_description = 'Status'


admin.site.register(VaccineLot, VaccineLotAdmin)


class ScheduledVaccinationInline(admin.TabularInline):
    """Scheduled vaccination inline for immunization schedule"""
    model = ScheduledVaccination
    extra = 0
    fields = ['vaccine', 'dose_number', 'recommended_age_days', 'earliest_age_days', 'latest_age_days']


@admin.register(ImmunizationSchedule)
class ImmunizationScheduleAdmin(admin.ModelAdmin):
    """Immunization schedule admin"""
    list_display = ['name', 'age_group', 'is_active', 'create_date']
    list_filter = ['age_group', 'is_active', 'create_date']
    search_fields = ['name', 'description']
    readonly_fields = ['uuid', 'create_date', 'update_date']
    inlines = [ScheduledVaccinationInline]
    
    fieldsets = (
        ('Schedule Information', {
            'fields': ('name', 'description', 'age_group', 'is_active')
        }),
        ('System Information', {
            'fields': ('uuid', 'create_date', 'update_date'),
            'classes': ('collapse',)
        }),
    )


class ImmunizationObservationInline(admin.TabularInline):
    """Immunization observation inline"""
    model = ImmunizationObservation
    extra = 0
    fields = ['observation_type', 'observation_date', 'severity', 'description', 'reported_to_vaers']
    readonly_fields = ['uuid', 'create_date', 'update_date']


@admin.register(Immunization)
class ImmunizationAdmin(admin.ModelAdmin):
    """Immunization admin"""
    list_display = ['patient', 'vaccine', 'administered_date', 'administered_by', 'completion_status', 'dose_number']
    list_filter = ['completion_status', 'administered_date', 'vaccine', 'administered_by', 'create_date']
    search_fields = ['patient__first_name', 'patient__last_name', 'vaccine__name']
    readonly_fields = ['uuid', 'create_date', 'update_date', 'is_overdue']
    date_hierarchy = 'administered_date'
    inlines = [ImmunizationObservationInline]
    
    fieldsets = (
        ('Patient Information', {
            'fields': ('patient', 'administered_date', 'administered_by', 'administered_by_name')
        }),
        ('Vaccine Information', {
            'fields': ('vaccine', 'vaccine_lot', 'dose_number', 'amount_administered', 'amount_administered_unit')
        }),
        ('Administration Details', {
            'fields': ('route', 'administration_site', 'completion_status', 'information_source')
        }),
        ('Documentation', {
            'fields': ('vis_date', 'education_date', 'note'),
            'classes': ('collapse',)
        }),
        ('Provider Information', {
            'fields': ('ordering_provider', 'reason_code', 'reason_description'),
            'classes': ('collapse',)
        }),
        ('Refusal Information', {
            'fields': ('refusal_reason',),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('uuid', 'external_id', 'added_erroneously', 'is_overdue', 'create_date', 'update_date'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related(
            'patient', 'vaccine', 'vaccine_lot', 'administered_by', 'ordering_provider'
        )


@admin.register(ImmunizationObservation)
class ImmunizationObservationAdmin(admin.ModelAdmin):
    """Immunization observation admin"""
    list_display = ['immunization', 'observation_type', 'observation_date', 'severity', 'reported_to_vaers']
    list_filter = ['observation_type', 'severity', 'reported_to_vaers', 'observation_date']
    search_fields = ['immunization__patient__first_name', 'immunization__patient__last_name', 'description']
    readonly_fields = ['uuid', 'create_date', 'update_date']
    date_hierarchy = 'observation_date'
    
    fieldsets = (
        ('Observation Information', {
            'fields': ('immunization', 'observation_type', 'observation_date', 'severity')
        }),
        ('Details', {
            'fields': ('description', 'action_taken', 'outcome')
        }),
        ('Reporting', {
            'fields': ('reported_to_vaers', 'vaers_id'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('uuid', 'create_date', 'update_date'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ImmunizationContraindication)
class ImmunizationContraindicationAdmin(admin.ModelAdmin):
    """Immunization contraindication admin"""
    list_display = ['vaccine', 'contraindication_type', 'severity', 'is_permanent']
    list_filter = ['contraindication_type', 'severity', 'is_permanent', 'vaccine']
    search_fields = ['vaccine__name', 'description']
    readonly_fields = ['uuid', 'create_date', 'update_date']
    
    fieldsets = (
        ('Contraindication Information', {
            'fields': ('vaccine', 'contraindication_type', 'severity', 'is_permanent')
        }),
        ('Details', {
            'fields': ('description',)
        }),
        ('System Information', {
            'fields': ('uuid', 'create_date', 'update_date'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PatientImmunizationAlert)
class PatientImmunizationAlertAdmin(admin.ModelAdmin):
    """Patient immunization alert admin"""
    list_display = ['patient', 'vaccine', 'alert_type', 'alert_date', 'due_date', 'is_active', 'acknowledged_by']
    list_filter = ['alert_type', 'is_active', 'alert_date', 'due_date']
    search_fields = ['patient__first_name', 'patient__last_name', 'vaccine__name']
    readonly_fields = ['uuid', 'create_date', 'update_date']
    date_hierarchy = 'alert_date'
    
    fieldsets = (
        ('Alert Information', {
            'fields': ('patient', 'vaccine', 'alert_type', 'alert_date', 'due_date')
        }),
        ('Message', {
            'fields': ('message', 'is_active')
        }),
        ('Acknowledgment', {
            'fields': ('acknowledged_by', 'acknowledged_date'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('uuid', 'create_date', 'update_date'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related(
            'patient', 'vaccine', 'acknowledged_by'
        )


# Admin customizations
admin.site.site_header = "MedicalCare System - Immunization Management"
admin.site.site_title = "Immunization Admin"
admin.site.index_title = "Welcome to Immunization Administration"
