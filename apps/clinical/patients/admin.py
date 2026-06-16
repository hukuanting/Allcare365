from django.contrib import admin
from .models import (
    Patient, CareTeamMember, Organization, PatientAllergy, 
    CarePlan, PatientMedication, MedicalOrder, InsuranceData, 
    AdvanceDirective, PatientDocument
)

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['medical_record_number', 'last_name', 'first_name', 'date_of_birth', 'sex', 'status']
    list_filter = ['sex', 'status']
    search_fields = ['first_name', 'last_name', 'medical_record_number', 'email_address']

@admin.register(CareTeamMember)
class CareTeamMemberAdmin(admin.ModelAdmin):
    list_display = ['patient', 'name', 'role', 'location']
    list_filter = ['role']

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'city', 'state']

@admin.register(PatientAllergy)
class PatientAllergyAdmin(admin.ModelAdmin):
    list_display = ['patient', 'allergy_type', 'substance', 'severity']
    list_filter = ['allergy_type', 'severity']

@admin.register(CarePlan)
class CarePlanAdmin(admin.ModelAdmin):
    list_display = ['patient', 'status', 'start_date']

@admin.register(PatientMedication)
class PatientMedicationAdmin(admin.ModelAdmin):
    list_display = ['patient', 'medication', 'dispense_status', 'start_date']
    list_filter = ['dispense_status']

@admin.register(MedicalOrder)
class MedicalOrderAdmin(admin.ModelAdmin):
    list_display = ['patient', 'order_type', 'order_date']
    list_filter = ['order_type']

@admin.register(InsuranceData)
class InsuranceDataAdmin(admin.ModelAdmin):
    list_display = ['patient', 'coverage_status', 'coverage_type']

@admin.register(AdvanceDirective)
class AdvanceDirectiveAdmin(admin.ModelAdmin):
    list_display = ['patient']

@admin.register(PatientDocument)
class PatientDocumentAdmin(admin.ModelAdmin):
    list_display = ['patient', 'note_type', 'document_date']
    list_filter = ['note_type']