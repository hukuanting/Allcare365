"""
Django admin configuration for pharmacy models.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    DrugCategory, Drug, DrugInteraction, DrugAllergy,
    DrugInventory, Prescription, PrescriptionRefill, InventoryTransaction
)


@admin.register(DrugCategory)
class DrugCategoryAdmin(admin.ModelAdmin):
    """Admin interface for drug categories"""
    list_display = ['name', 'code', 'parent_category', 'is_active', 'created_at']
    list_filter = ['is_active', 'parent_category', 'created_at']
    search_fields = ['name', 'code', 'description']
    ordering = ['name']
    list_per_page = 25
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'description', 'parent_category')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(Drug)
class DrugAdmin(admin.ModelAdmin):
    """Admin interface for drugs"""
    list_display = [
        'name', 'generic_name', 'brand_name', 'category', 
        'strength', 'dosage_form', 'is_active', 'controlled_substance'
    ]
    list_filter = [
        'category', 'dosage_form', 'is_active', 'controlled_substance',
        'created_at'
    ]
    search_fields = [
        'name', 'generic_name', 'brand_name', 'ndc_number',
        'manufacturer', 'description'
    ]
    ordering = ['name']
    list_per_page = 25
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'generic_name', 'brand_name', 'category')
        }),
        ('Drug Details', {
            'fields': (
                'strength', 'form', 'route_of_administration',
                'manufacturer', 'ndc_number'
            )
        }),
        ('Clinical Information', {
            'fields': (
                'indication', 'contraindications', 'side_effects',
                'dosage_instructions', 'warnings'
            )
        }),
        ('Regulatory', {
            'fields': (
                'controlled_substance', 'controlled_substance_schedule',
                'requires_prescription'
            )
        }),
        ('Status', {
            'fields': ('is_active', 'description')
        }),
    )


@admin.register(DrugInteraction)
class DrugInteractionAdmin(admin.ModelAdmin):
    """Admin interface for drug interactions"""
    list_display = ['drug1', 'drug2', 'severity', 'description', 'is_active']
    list_filter = ['severity', 'is_active']
    search_fields = ['drug1__name', 'drug2__name', 'description']
    ordering = ['drug1__name', 'drug2__name']
    list_per_page = 25
    
    fieldsets = (
        ('Drugs', {
            'fields': ('drug1', 'drug2')
        }),
        ('Interaction Details', {
            'fields': ('severity', 'description', 'mechanism')
        }),
        ('Clinical Information', {
            'fields': ('clinical_management', 'reference_source', 'reference_date')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )


@admin.register(DrugAllergy)
class DrugAllergyAdmin(admin.ModelAdmin):
    """Admin interface for drug allergies"""
    list_display = ['patient', 'drug', 'severity', 'reaction_description', 'onset_date']
    list_filter = ['severity', 'onset_date']
    search_fields = ['patient__first_name', 'patient__last_name', 'drug__name']
    ordering = ['-onset_date']
    list_per_page = 25
    
    fieldsets = (
        ('Patient & Drug', {
            'fields': ('patient', 'drug', 'allergen')
        }),
        ('Allergy Details', {
            'fields': ('severity', 'reaction_description', 'onset_date')
        }),
        ('Clinical Information', {
            'fields': ('verified', 'verified_by', 'verified_date')
        }),
    )


@admin.register(DrugInventory)
class DrugInventoryAdmin(admin.ModelAdmin):
    """Admin interface for drug inventory"""
    list_display = [
        'drug', 'lot_number', 'quantity_available', 'unit_cost',
        'expiration_date', 'facility', 'warehouse'
    ]
    list_filter = ['expiration_date', 'facility', 'warehouse']
    search_fields = ['drug__name', 'lot_number']
    ordering = ['drug__name', 'expiration_date']
    list_per_page = 25
    
    def get_queryset(self, request):
        """Add annotations for inventory status"""
        qs = super().get_queryset(request)
        return qs.select_related('drug')
    
    fieldsets = (
        ('Drug Information', {
            'fields': ('drug', 'lot_number', 'facility', 'warehouse')
        }),
        ('Inventory', {
            'fields': (
                'quantity_on_hand', 'quantity_allocated', 'unit_cost'
            )
        }),
        ('Dates', {
            'fields': ('expiration_date',)
        }),
    )


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    """Admin interface for prescriptions"""
    list_display = [
        'patient', 'drug', 'provider', 'quantity', 'refills_remaining',
        'prescribed_date', 'status'
    ]
    list_filter = ['status', 'prescribed_date', 'provider']
    search_fields = [
        'patient__first_name', 'patient__last_name',
        'drug__name', 'provider__first_name', 'provider__last_name'
    ]
    ordering = ['-prescribed_date']
    list_per_page = 25
    
    def get_queryset(self, request):
        """Optimize queries"""
        qs = super().get_queryset(request)
        return qs.select_related('patient', 'drug', 'provider')
    
    fieldsets = (
        ('Prescription Details', {
            'fields': ('patient', 'drug', 'provider', 'prescribed_date')
        }),
        ('Dosage', {
            'fields': (
                'quantity', 'unit', 'dosage_instructions', 'frequency',
                'refills', 'refills_remaining'
            )
        }),
        ('Status', {
            'fields': ('status', 'dispensed_date', 'dispensed_by')
        }),
    )


@admin.register(PrescriptionRefill)
class PrescriptionRefillAdmin(admin.ModelAdmin):
    """Admin interface for prescription refills"""
    list_display = [
        'prescription', 'dispensed_date', 'quantity_dispensed',
        'dispensed_by', 'refill_number'
    ]
    list_filter = ['dispensed_date', 'dispensed_by']
    search_fields = [
        'prescription__patient__first_name',
        'prescription__patient__last_name',
        'prescription__drug__name'
    ]
    ordering = ['-dispensed_date']
    list_per_page = 25
    
    def get_queryset(self, request):
        """Optimize queries"""
        qs = super().get_queryset(request)
        return qs.select_related('prescription', 'prescription__patient', 'prescription__drug')
    
    fieldsets = (
        ('Refill Information', {
            'fields': ('prescription', 'refill_number', 'requested_date')
        }),
        ('Dispensed', {
            'fields': ('quantity_dispensed', 'dispensed_date', 'dispensed_by')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    """Admin interface for inventory transactions"""
    list_display = [
        'drug_inventory', 'transaction_type', 'quantity_change', 'created_at',
        'reference_number', 'created_by'
    ]
    list_filter = ['transaction_type', 'created_at', 'created_by']
    search_fields = [
        'drug_inventory__drug__name', 'reference_number',
        'created_by__first_name', 'created_by__last_name'
    ]
    ordering = ['-created_at']
    list_per_page = 25
    
    def get_queryset(self, request):
        """Optimize queries"""
        qs = super().get_queryset(request)
        return qs.select_related('drug_inventory', 'drug_inventory__drug', 'created_by')
    
    fieldsets = (
        ('Transaction Details', {
            'fields': (
                'drug_inventory', 'transaction_type', 'quantity_change',
                'quantity_before', 'quantity_after', 'created_by'
            )
        }),
        ('Reference', {
            'fields': ('reference_number', 'prescription', 'reason')
        }),
        ('Cost', {
            'fields': ('unit_cost', 'total_cost')
        }),
    )


# Custom admin site configuration
admin.site.site_header = "MedicalCare System - Pharmacy Administration"
admin.site.site_title = "Pharmacy Admin"
admin.site.index_title = "Pharmacy Management"
