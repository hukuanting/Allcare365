from django.contrib import admin
from .models import (
    HealthScreening, VitalSigns, LaboratoryResults,
    Problem, Procedure, Immunization, HealthStatusAssessment
)

class VitalSignsInline(admin.StackedInline):
    model = VitalSigns
    extra = 0

class LaboratoryResultsInline(admin.TabularInline):
    model = LaboratoryResults
    extra = 0

class HealthStatusAssessmentInline(admin.StackedInline):
    model = HealthStatusAssessment
    extra = 0

@admin.register(HealthScreening)
class HealthScreeningAdmin(admin.ModelAdmin):
    list_display = ['patient', 'encounter_type', 'screening_date', 'encounter_location']
    list_filter = ['encounter_type', 'screening_date']
    inlines = [VitalSignsInline, LaboratoryResultsInline, HealthStatusAssessmentInline]

@admin.register(VitalSigns)
class VitalSignsAdmin(admin.ModelAdmin):
    list_display = ['health_screening', 'systolic_blood_pressure', 'diastolic_blood_pressure', 'heart_rate']

@admin.register(LaboratoryResults)
class LaboratoryResultsAdmin(admin.ModelAdmin):
    list_display = ['health_screening', 'test_name', 'value_result', 'result_status']

@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ['patient', 'problem_name', 'status', 'date_of_onset']
    list_filter = ['status', 'sdoh_problem']

@admin.register(Procedure)
class ProcedureAdmin(admin.ModelAdmin):
    list_display = ['patient', 'procedure_name', 'performance_time']

@admin.register(Immunization)
class ImmunizationAdmin(admin.ModelAdmin):
    list_display = ['patient', 'vaccine_name', 'administration_date', 'lot_number']

@admin.register(HealthStatusAssessment)

class HealthStatusAssessmentAdmin(admin.ModelAdmin):

    list_display = ['health_screening', 'smoking_status', 'pregnancy_status']
