"""
FHIR Integration Admin Interface
"""
from django.contrib import admin
from .models import FHIRResource, USCDIDataElement, FHIRPatientResource


@admin.register(FHIRResource)
class FHIRResourceAdmin(admin.ModelAdmin):
    list_display = ['resource_type', 'resource_id', 'version_id', 'last_updated', 'is_active']
    list_filter = ['resource_type', 'is_active', 'last_updated']
    search_fields = ['resource_id', 'resource_type']
    readonly_fields = ['id', 'last_updated']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('resource_type', 'resource_id', 'version_id', 'is_active')
        }),
        ('FHIR Data', {
            'fields': ('resource_data',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'last_updated'),
            'classes': ('collapse',)
        })
    )


@admin.register(USCDIDataElement)
class USCDIDataElementAdmin(admin.ModelAdmin):
    list_display = ['uscdi_class', 'data_element', 'is_required']
    list_filter = ['uscdi_class', 'is_required']
    search_fields = ['data_element', 'uscdi_class']


@admin.register(FHIRPatientResource)
class FHIRPatientResourceAdmin(admin.ModelAdmin):
    list_display = ['patient', 'identifier_system', 'identifier_value']
    search_fields = ['patient__first_name', 'patient__last_name', 'identifier_value']
    raw_id_fields = ['patient', 'fhir_resource']