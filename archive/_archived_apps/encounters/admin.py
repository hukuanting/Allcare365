from django.contrib import admin
from .models import Encounter, EncounterForm, EncounterDiagnosis


@admin.register(Encounter)
class EncounterAdmin(admin.ModelAdmin):
    list_display = ['patient', 'provider', 'encounter_date', 'reason', 'status']
    list_filter = ['status', 'reason', 'encounter_date', 'provider']
    search_fields = ['patient__first_name', 'patient__last_name', 'chief_complaint']
    date_hierarchy = 'encounter_date'
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('patient', 'provider', 'encounter_date', 'encounter_class', 'reason', 'status')
        }),
        ('臨床資訊', {
            'fields': ('chief_complaint', 'history_present_illness', 'assessment', 'plan')
        }),
        ('生命徵象', {
            'fields': (
                'temperature', 'pulse', 'respiration',
                ('blood_pressure_systolic', 'blood_pressure_diastolic'),
                ('weight', 'height')
            )
        }),
        ('其他資訊', {
            'fields': ('billing_code', 'facility', 'notes')
        }),
        ('系統資訊', {
            'fields': ('id', 'created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )


@admin.register(EncounterForm)
class EncounterFormAdmin(admin.ModelAdmin):
    list_display = ['encounter', 'form_type', 'form_name', 'created_at']
    list_filter = ['form_type', 'created_at']
    search_fields = ['encounter__patient__first_name', 'encounter__patient__last_name', 'form_name']


@admin.register(EncounterDiagnosis)
class EncounterDiagnosisAdmin(admin.ModelAdmin):
    list_display = ['encounter', 'icd_code', 'diagnosis_text', 'diagnosis_type', 'is_confirmed']
    list_filter = ['diagnosis_type', 'is_confirmed', 'created_at']
    search_fields = ['encounter__patient__first_name', 'encounter__patient__last_name', 'icd_code', 'diagnosis_text']
