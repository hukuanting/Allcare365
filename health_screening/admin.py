from django.contrib import admin
from .models import (
    HealthScreening, VitalSigns, LaboratoryResults,
    CardiovascularRiskIndex, MedicalHistory, LifestyleQuestionnaire
)


class VitalSignsInline(admin.StackedInline):
    model = VitalSigns
    extra = 0


class LaboratoryResultsInline(admin.StackedInline):
    model = LaboratoryResults
    extra = 0


class CardiovascularRiskIndexInline(admin.StackedInline):
    model = CardiovascularRiskIndex
    extra = 0


class MedicalHistoryInline(admin.StackedInline):
    model = MedicalHistory
    extra = 0


class LifestyleQuestionnaireInline(admin.StackedInline):
    model = LifestyleQuestionnaire
    extra = 0


@admin.register(HealthScreening)
class HealthScreeningAdmin(admin.ModelAdmin):
    list_display = ['patient', 'screening_date', 'screening_type', 'age_at_screening', 'provider']
    list_filter = ['screening_type', 'screening_date', 'provider']
    search_fields = ['patient__first_name', 'patient__last_name']
    date_hierarchy = 'screening_date'
    inlines = [VitalSignsInline, LaboratoryResultsInline, CardiovascularRiskIndexInline, 
               MedicalHistoryInline, LifestyleQuestionnaireInline]
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('patient', 'screening_date', 'screening_type', 'age_at_screening', 'provider')
        }),
        ('系統資訊', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    readonly_fields = ['created_at', 'updated_at']


@admin.register(VitalSigns)
class VitalSignsAdmin(admin.ModelAdmin):
    list_display = ['health_screening', 'height_cm', 'weight_kg', 'bmi', 'systolic_bp_mmhg', 'diastolic_bp_mmhg']
    list_filter = ['health_screening__screening_date']
    search_fields = ['health_screening__patient__first_name', 'health_screening__patient__last_name']


@admin.register(LaboratoryResults)
class LaboratoryResultsAdmin(admin.ModelAdmin):
    list_display = ['health_screening', 'fasting_glucose_mgdl', 'hba1c_percent', 'total_cholesterol_mgdl', 'hdl_cholesterol_mgdl']
    list_filter = ['health_screening__screening_date']
    search_fields = ['health_screening__patient__first_name', 'health_screening__patient__last_name']
    
    fieldsets = (
        ('血液檢查', {
            'fields': ('rbc_count', 'rdw_cv_percent', 'wbc_count', 'platelet_count', 'monocyte_percent', 'monocyte_absolute')
        }),
        ('血糖代謝', {
            'fields': ('fasting_glucose_mgdl', 'impaired_fasting_glucose', 'hba1c_percent', 'estimated_avg_glucose_mgdl', 
                      'insulin_uiu_ml', 'homa_ir', 'egdr')
        }),
        ('血脂分析', {
            'fields': ('triglycerides_mgdl', 'total_cholesterol_mgdl', 'hdl_cholesterol_mgdl', 'ldl_cholesterol_mgdl',
                      'non_hdl_cholesterol_mgdl', 'plp_cholesterol_mgdl')
        }),
        ('血脂比值', {
            'fields': ('tc_hdl_ratio', 'ldl_hdl_ratio', 'tg_hdl_ratio', 'non_hdl_hdl_ratio', 
                      'atherogenic_index_plasma', 'triglyceride_glucose_index', 'tyg_bmi'),
            'classes': ('collapse',)
        }),
        ('肝功能', {
            'fields': ('alt_gpt_ul', 'ast_got_ul', 'ast_alt_ratio', 'ast_uln_ratio', 'ggt_ul',
                      'total_protein_gdl', 'albumin_gdl', 'globulin_gdl', 'albumin_globulin_ratio'),
            'classes': ('collapse',)
        }),
        ('腎功能', {
            'fields': ('urine_albumin_mgdl', 'urine_creatinine_mgdl', 'urine_albumin_creatinine_ratio'),
            'classes': ('collapse',)
        }),
        ('其他生化指標', {
            'fields': ('uric_acid_mgdl', 'homocysteine_umol_l', 'hs_crp_mgdl'),
            'classes': ('collapse',)
        })
    )


@admin.register(CardiovascularRiskIndex)
class CardiovascularRiskIndexAdmin(admin.ModelAdmin):
    list_display = ['health_screening', 'cardiometabolic_index', 'atherogenic_risk_plasma']
    list_filter = ['health_screening__screening_date']
    search_fields = ['health_screening__patient__first_name', 'health_screening__patient__last_name']


@admin.register(MedicalHistory)
class MedicalHistoryAdmin(admin.ModelAdmin):
    list_display = ['health_screening', 'diabetes_treated', 'hypertension_treated', 'hyperlipidemia_treated']
    list_filter = ['diabetes_treated', 'hypertension_treated', 'hyperlipidemia_treated', 'health_screening__screening_date']
    search_fields = ['health_screening__patient__first_name', 'health_screening__patient__last_name']


@admin.register(LifestyleQuestionnaire)
class LifestyleQuestionnaireAdmin(admin.ModelAdmin):
    list_display = ['health_screening', 'diet_score', 'exercise_score', 'is_current_smoker', 'drinking_status']
    list_filter = ['diet_score', 'exercise_score', 'is_current_smoker', 'drinking_status', 'health_screening__screening_date']
    search_fields = ['health_screening__patient__first_name', 'health_screening__patient__last_name']
    
    fieldsets = (
        ('生活方式評估', {
            'fields': ('diet_score', 'exercise_score')
        }),
        ('家族史', {
            'fields': ('family_diabetes', 'family_hypertension', 'family_heart_disease', 'family_cvd', 
                      'family_cancer', 'family_cancer_type')
        }),
        ('個人病史', {
            'fields': ('has_diabetes', 'has_coronary_heart_disease', 'has_cerebrovascular_disease',
                      'has_peripheral_vascular_disease', 'has_hypertension', 'has_dyslipidemia')
        }),
        ('吸菸史', {
            'fields': ('is_current_smoker', 'smoking_years', 'cigarettes_per_day', 'quit_smoking_when', 'is_former_smoker')
        }),
        ('飲酒習慣', {
            'fields': ('drinking_status', 'drinks_per_week')
        })
    )
