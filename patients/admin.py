from django.contrib import admin
from .models import Patient, PatientAllergy, PatientMedication, PatientVitals, PatientNote


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['medical_record_number', 'last_name', 'first_name', 'date_of_birth', 'gender', 'is_active']
    list_filter = ['gender', 'is_active', 'marital_status']
    search_fields = ['first_name', 'last_name', 'medical_record_number', 'phone_mobile', 'email']
    ordering = ['last_name', 'first_name']
    readonly_fields = ['medical_record_number', 'created_at', 'updated_at']


@admin.register(PatientAllergy)
class PatientAllergyAdmin(admin.ModelAdmin):
    list_display = ['patient', 'allergen', 'reaction', 'severity']
    list_filter = ['severity', 'created_at']
    search_fields = ['patient__first_name', 'patient__last_name', 'allergen']


@admin.register(PatientMedication)
class PatientMedicationAdmin(admin.ModelAdmin):
    list_display = ['patient', 'medication_name', 'dosage', 'frequency']
    list_filter = ['start_date', 'end_date']
    search_fields = ['patient__first_name', 'patient__last_name', 'medication_name']


@admin.register(PatientVitals)
class PatientVitalsAdmin(admin.ModelAdmin):
    list_display = ['patient', 'measurement_date', 'height', 'weight', 'blood_pressure_systolic', 'blood_pressure_diastolic']
    list_filter = ['measurement_date']
    search_fields = ['patient__first_name', 'patient__last_name']
    ordering = ['-measurement_date']


@admin.register(PatientNote)
class PatientNoteAdmin(admin.ModelAdmin):
    list_display = ['patient', 'title', 'note_type', 'created_at', 'is_private']
    list_filter = ['note_type', 'is_private', 'created_at']
    search_fields = ['patient__first_name', 'patient__last_name', 'title', 'content']
    ordering = ['-created_at']
