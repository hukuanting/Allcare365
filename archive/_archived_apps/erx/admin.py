"""
Electronic Prescription (eRx) Admin Configuration

This module provides Django admin configuration for the eRx system
including prescriptions, formulary, interactions, and pharmacy directory.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from django.utils import timezone

from .models import (
    ElectronicPrescription,
    PrescriptionRefill,
    PrescriptionHistory,
    DrugFormulary,
    DrugInteraction,
    PharmacyDirectory
)


@admin.register(ElectronicPrescription)
class ElectronicPrescriptionAdmin(admin.ModelAdmin):
    """Admin configuration for Electronic Prescriptions"""
    
    list_display = [
        'prescription_id', 'patient', 'prescriber', 'drug_name',
        'status', 'date_prescribed', 'pharmacy_name', 'is_expired'
    ]
    
    list_filter = [
        'status', 'prescription_type', 'controlled_substance',
        'dispense_as_written', 'date_prescribed', 'prescriber'
    ]
    
    search_fields = [
        'prescription_id', 'patient__first_name', 'patient__last_name',
        'drug_name', 'generic_name', 'prescriber__first_name',
        'prescriber__last_name', 'pharmacy_name'
    ]
    
    readonly_fields = [
        'prescription_id', 'is_expired', 'refills_remaining',
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'prescription_id', 'patient', 'prescriber',
                'prescription_type', 'status'
            )
        }),
        ('Drug Information', {
            'fields': (
                'drug_name', 'generic_name', 'strength', 'dosage_form',
                'ndc_number', 'rxnorm_code'
            )
        }),
        ('Prescription Details', {
            'fields': (
                'quantity', 'quantity_unit', 'days_supply', 'refills',
                'refills_remaining', 'sig_code', 'directions'
            )
        }),
        ('Dates', {
            'fields': (
                'date_prescribed', 'date_sent', 'effective_date',
                'expiration_date', 'is_expired'
            )
        }),
        ('Pharmacy Information', {
            'fields': (
                'pharmacy_ncpdp', 'pharmacy_name', 'pharmacy_address',
                'pharmacy_phone'
            )
        }),
        ('Clinical Information', {
            'fields': (
                'diagnosis_code', 'clinical_notes'
            )
        }),
        ('Flags', {
            'fields': (
                'dispense_as_written', 'controlled_substance'
            )
        }),
        ('External Integration', {
            'fields': (
                'external_prescription_id', 'transmission_method',
                'response_message', 'response_code'
            )
        }),
        ('Audit Information', {
            'fields': (
                'created_at', 'updated_at'
            )
        })
    )
    
    actions = ['mark_as_sent', 'mark_as_cancelled']
    
    def mark_as_sent(self, request, queryset):
        """Mark selected prescriptions as sent"""
        updated = queryset.filter(status='draft').update(
            status='sent',
            date_sent=timezone.now()
        )
        self.message_user(request, f'{updated} prescriptions marked as sent.')
    mark_as_sent.short_description = "Mark selected prescriptions as sent"
    
    def mark_as_cancelled(self, request, queryset):
        """Mark selected prescriptions as cancelled"""
        updated = queryset.exclude(status__in=['cancelled', 'expired']).update(
            status='cancelled'
        )
        self.message_user(request, f'{updated} prescriptions marked as cancelled.')
    mark_as_cancelled.short_description = "Mark selected prescriptions as cancelled"
    
    def get_queryset(self, request):
        """Optimize queries with select_related"""
        queryset = super().get_queryset(request)
        return queryset.select_related('patient', 'prescriber')


class PrescriptionRefillInline(admin.TabularInline):
    """Inline admin for prescription refills"""
    model = PrescriptionRefill
    extra = 0
    readonly_fields = ['refill_number', 'date_filled']
    
    def get_queryset(self, request):
        """Order refills by date"""
        queryset = super().get_queryset(request)
        return queryset.order_by('-date_filled')


class PrescriptionHistoryInline(admin.TabularInline):
    """Inline admin for prescription history"""
    model = PrescriptionHistory
    extra = 0
    readonly_fields = ['action', 'user', 'timestamp', 'notes']
    
    def get_queryset(self, request):
        """Order history by timestamp"""
        queryset = super().get_queryset(request)
        return queryset.order_by('-timestamp')


@admin.register(PrescriptionRefill)
class PrescriptionRefillAdmin(admin.ModelAdmin):
    """Admin configuration for Prescription Refills"""
    
    list_display = [
        'prescription', 'refill_number', 'date_filled',
        'quantity_dispensed', 'pharmacy_ncpdp', 'pharmacist'
    ]
    
    list_filter = [
        'date_filled', 'pharmacy_ncpdp'
    ]
    
    search_fields = [
        'prescription__prescription_id', 'prescription__drug_name',
        'prescription__patient__first_name', 'prescription__patient__last_name',
        'pharmacist'
    ]
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        """Optimize queries with select_related"""
        queryset = super().get_queryset(request)
        return queryset.select_related('prescription', 'prescription__patient')


@admin.register(PrescriptionHistory)
class PrescriptionHistoryAdmin(admin.ModelAdmin):
    """Admin configuration for Prescription History"""
    
    list_display = [
        'prescription', 'action', 'user', 'timestamp'
    ]
    
    list_filter = [
        'action', 'timestamp', 'user'
    ]
    
    search_fields = [
        'prescription__prescription_id', 'prescription__drug_name',
        'user__first_name', 'user__last_name', 'notes'
    ]
    
    readonly_fields = ['timestamp', 'created_at', 'updated_at']
    
    def get_queryset(self, request):
        """Optimize queries with select_related"""
        queryset = super().get_queryset(request)
        return queryset.select_related('prescription', 'user')


@admin.register(DrugFormulary)
class DrugFormularyAdmin(admin.ModelAdmin):
    """Admin configuration for Drug Formulary"""
    
    list_display = [
        'drug_name', 'generic_name', 'formulary_status',
        'tier_level', 'copay_amount', 'prior_auth_required'
    ]
    
    list_filter = [
        'formulary_status', 'tier_level', 'prior_auth_required'
    ]
    
    search_fields = [
        'drug_name', 'generic_name', 'ndc_number', 'rxnorm_code'
    ]
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Drug Information', {
            'fields': (
                'drug_name', 'generic_name', 'ndc_number', 'rxnorm_code'
            )
        }),
        ('Formulary Status', {
            'fields': (
                'formulary_status', 'tier_level', 'copay_amount',
                'prior_auth_required', 'quantity_limit'
            )
        }),
        ('Audit Information', {
            'fields': (
                'created_at', 'updated_at'
            )
        })
    )


@admin.register(DrugInteraction)
class DrugInteractionAdmin(admin.ModelAdmin):
    """Admin configuration for Drug Interactions"""
    
    list_display = [
        'drug1_name', 'drug2_name', 'interaction_severity',
        'reference_source'
    ]
    
    list_filter = [
        'interaction_severity', 'reference_source'
    ]
    
    search_fields = [
        'drug1_name', 'drug2_name', 'interaction_description'
    ]
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Drug Information', {
            'fields': (
                'drug1_name', 'drug2_name', 'interaction_severity'
            )
        }),
        ('Interaction Details', {
            'fields': (
                'interaction_description', 'clinical_management',
                'reference_source'
            )
        }),
        ('Audit Information', {
            'fields': (
                'created_at', 'updated_at'
            )
        })
    )


@admin.register(PharmacyDirectory)
class PharmacyDirectoryAdmin(admin.ModelAdmin):
    """Admin configuration for Pharmacy Directory"""
    
    list_display = [
        'name', 'city', 'state', 'phone', 'accepts_erx',
        'accepts_controlled_substances', 'is_active'
    ]
    
    list_filter = [
        'state', 'accepts_erx', 'accepts_controlled_substances',
        'is_active', 'city'
    ]
    
    search_fields = [
        'name', 'ncpdp_id', 'address_line1', 'city', 'phone'
    ]
    
    readonly_fields = ['last_updated']
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'ncpdp_id', 'name', 'is_active'
            )
        }),
        ('Address', {
            'fields': (
                'address_line1', 'address_line2', 'city', 'state', 'zip_code'
            )
        }),
        ('Contact Information', {
            'fields': (
                'phone', 'fax', 'email'
            )
        }),
        ('Capabilities', {
            'fields': (
                'accepts_erx', 'accepts_controlled_substances'
            )
        }),
        ('Hours & Status', {
            'fields': (
                'hours_operation', 'last_updated'
            )
        })
    )
    
    actions = ['activate_pharmacies', 'deactivate_pharmacies']
    
    def activate_pharmacies(self, request, queryset):
        """Activate selected pharmacies"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} pharmacies activated.')
    activate_pharmacies.short_description = "Activate selected pharmacies"
    
    def deactivate_pharmacies(self, request, queryset):
        """Deactivate selected pharmacies"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} pharmacies deactivated.')
    deactivate_pharmacies.short_description = "Deactivate selected pharmacies"


# Register inlines with the ElectronicPrescription admin
ElectronicPrescriptionAdmin.inlines = [PrescriptionRefillInline, PrescriptionHistoryInline]
