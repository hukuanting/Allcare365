from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
from decimal import Decimal


class BaseModel(models.Model):
    """Base model with common fields for all models"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='%(class)s_created')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='%(class)s_updated')
    is_active = models.BooleanField(default=True)
    
    class Meta:
        abstract = True


class HealthScreening(BaseModel):
    """健康檢查主記錄 - 符合 USCDI 標準"""
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, 
                               related_name='health_screenings', verbose_name='患者')
    screening_date = models.DateField(default=timezone.now, verbose_name='檢查日期')
    screening_type = models.CharField(max_length=100, default='annual_physical', verbose_name='檢查類型')
    provider = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='health_screenings_provided', verbose_name='檢查醫師')
    
    # Basic Demographics (USCDI Demographics)
    age_at_screening = models.IntegerField(null=True, blank=True, verbose_name='檢查時年齡')
    
    class Meta:
        verbose_name = '健康檢查'
        verbose_name_plural = '健康檢查'
        ordering = ['-screening_date']
        # 移除 unique_together 約束，允許同一患者同一天有多個健檢記錄
        # unique_together = ['patient', 'screening_date']
    
    def __str__(self):
        return f"{self.patient} - {self.screening_date}"
    
    def save(self, *args, **kwargs):
        # 自動計算檢查時年齡
        if self.patient and self.patient.date_of_birth and not self.age_at_screening:
            screening_year = self.screening_date.year
            birth_year = self.patient.date_of_birth.year
            age = screening_year - birth_year
            
            # 檢查是否還沒過生日
            if (self.screening_date.month, self.screening_date.day) < (self.patient.date_of_birth.month, self.patient.date_of_birth.day):
                age -= 1
            
            self.age_at_screening = age
        
        super().save(*args, **kwargs)


class VitalSigns(BaseModel):
    """生命徵象 - 符合 USCDI Vital Signs"""
    health_screening = models.OneToOneField(HealthScreening, on_delete=models.CASCADE,
                                           related_name='vital_signs', verbose_name='健康檢查')
    
    # Height and Weight (USCDI required)
    height_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='身高(cm)')
    weight_kg = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='體重(kg)')
    bmi = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='BMI')
    
    # Body Measurements
    neck_circumference_cm = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='頸圍(cm)')
    chest_circumference_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='胸圍(cm)')
    waist_circumference_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='腰圍(cm)')
    hip_circumference_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='臀圍(cm)')
    waist_height_ratio = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True, verbose_name='腰高比')
    waist_hip_ratio = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True, verbose_name='腰臀比')
    
    # Blood Pressure (USCDI required)
    pulse_rate_bpm = models.IntegerField(null=True, blank=True, 
                                        validators=[MinValueValidator(30), MaxValueValidator(200)],
                                        verbose_name='脈搏(次/分)')
    systolic_bp_mmhg = models.IntegerField(null=True, blank=True,
                                          validators=[MinValueValidator(70), MaxValueValidator(250)],
                                          verbose_name='收縮壓(mmHg)')
    diastolic_bp_mmhg = models.IntegerField(null=True, blank=True,
                                           validators=[MinValueValidator(40), MaxValueValidator(150)],
                                           verbose_name='舒張壓(mmHg)')
    pulse_pressure_mmhg = models.IntegerField(null=True, blank=True, verbose_name='脈壓(mmHg)')
    mean_arterial_pressure_mmhg = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='平均動脈壓(mmHg)')
    central_systolic_bp_mmhg = models.IntegerField(null=True, blank=True, verbose_name='中央收縮壓(mmHg)')
    central_diastolic_bp_mmhg = models.IntegerField(null=True, blank=True, verbose_name='中央舒張壓(mmHg)')
    
    class Meta:
        verbose_name = '生命徵象'
        verbose_name_plural = '生命徵象'
    
    def save(self, *args, **kwargs):
        # Auto-calculate BMI if height and weight are provided
        if self.height_cm and self.weight_kg:
            height_m = float(self.height_cm) / 100
            self.bmi = round(float(self.weight_kg) / (height_m ** 2), 1)
        
        # Auto-calculate pulse pressure
        if self.systolic_bp_mmhg and self.diastolic_bp_mmhg:
            self.pulse_pressure_mmhg = self.systolic_bp_mmhg - self.diastolic_bp_mmhg
            self.mean_arterial_pressure_mmhg = round(self.diastolic_bp_mmhg + (self.pulse_pressure_mmhg / 3), 1)
        
        # Auto-calculate waist-hip ratio
        if self.waist_circumference_cm and self.hip_circumference_cm:
            self.waist_hip_ratio = round(float(self.waist_circumference_cm) / float(self.hip_circumference_cm), 3)
        
        # Auto-calculate waist-height ratio
        if self.waist_circumference_cm and self.height_cm:
            self.waist_height_ratio = round(float(self.waist_circumference_cm) / float(self.height_cm), 3)
        
        super().save(*args, **kwargs)


class LaboratoryResults(BaseModel):
    """檢驗結果 - 符合 USCDI Laboratory"""
    health_screening = models.OneToOneField(HealthScreening, on_delete=models.CASCADE,
                                           related_name='laboratory_results', verbose_name='健康檢查')
    
    # Complete Blood Count (CBC)
    rbc_count = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, verbose_name='紅血球計數(10^6/μL)')
    rdw_cv_percent = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='紅血球分佈寬度(%)')
    wbc_count = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='白血球計數(10^3/μL)')
    platelet_count = models.IntegerField(null=True, blank=True, verbose_name='血小板計數(10^3/μL)')
    monocyte_percent = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='單核球百分比(%)')
    monocyte_absolute = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, verbose_name='單核球絕對值(×10^9/L)')
    
    # Glucose Metabolism (USCDI required for diabetes screening)
    fasting_glucose_mgdl = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='空腹血糖(mg/dL)')
    impaired_fasting_glucose = models.BooleanField(null=True, blank=True, verbose_name='空腹血糖異常')
    hba1c_percent = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='糖化血色素(%)')
    estimated_avg_glucose_mgdl = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='估計平均血糖(mg/dL)')
    insulin_uiu_ml = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name='胰島素(μIU/mL)')
    homa_ir = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='HOMA-IR')
    egdr = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='eGDR')
    
    # Lipid Profile (USCDI required)
    triglycerides_mgdl = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='三酸甘油脂(mg/dL)')
    total_cholesterol_mgdl = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='總膽固醇(mg/dL)')
    hdl_cholesterol_mgdl = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='高密度膽固醇(mg/dL)')
    ldl_cholesterol_mgdl = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='低密度膽固醇(mg/dL)')
    non_hdl_cholesterol_mgdl = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='非高密度膽固醇(mg/dL)')
    plp_cholesterol_mgdl = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='PLP膽固醇(mg/dL)')
    
    # Calculated Lipid Ratios
    tc_hdl_ratio = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, verbose_name='TC/HDL比值')
    ldl_hdl_ratio = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, verbose_name='LDL/HDL比值')
    tg_hdl_ratio = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='TG/HDL比值')
    non_hdl_hdl_ratio = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, verbose_name='非HDL/HDL比值')
    atherogenic_index_plasma = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True, verbose_name='動脈硬化指數(AIP)')
    triglyceride_glucose_index = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='TyG指數')
    tyg_bmi = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name='TyG-BMI')
    
    # Other Biomarkers
    uric_acid_mgdl = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='尿酸(mg/dL)')
    homocysteine_umol_l = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='同半胱胺酸(μmol/L)')
    hs_crp_mgdl = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='高敏感C反應蛋白(mg/L)')
    
    # Liver Function
    alt_gpt_ul = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='ALT/GPT(U/L)')
    ast_got_ul = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='AST/GOT(U/L)')
    ast_alt_ratio = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, verbose_name='AST/ALT比值')
    ast_uln_ratio = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, verbose_name='AST ULN比值')
    ggt_ul = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='GGT(U/L)')
    total_protein_gdl = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='總蛋白(g/dL)')
    albumin_gdl = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='白蛋白(g/dL)')
    globulin_gdl = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='球蛋白(g/dL)')
    albumin_globulin_ratio = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, verbose_name='白蛋白/球蛋白比值')
    
    # Kidney Function
    serum_creatinine_mgdl = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, verbose_name='血清肌酸酐(mg/dL)')
    urine_albumin_mgdl = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name='尿蛋白(mg/dL)')
    urine_creatinine_mgdl = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name='尿肌酸酐(mg/dL)')
    urine_albumin_creatinine_ratio = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='尿蛋白肌酸酐比值')
    
    class Meta:
        verbose_name = '檢驗結果'
        verbose_name_plural = '檢驗結果'
    
    def save(self, *args, **kwargs):
        # Auto-calculate ratios
        if self.total_cholesterol_mgdl and self.hdl_cholesterol_mgdl and self.hdl_cholesterol_mgdl > 0:
            self.tc_hdl_ratio = round(float(self.total_cholesterol_mgdl) / float(self.hdl_cholesterol_mgdl), 2)
        
        if self.ldl_cholesterol_mgdl and self.hdl_cholesterol_mgdl and self.hdl_cholesterol_mgdl > 0:
            self.ldl_hdl_ratio = round(float(self.ldl_cholesterol_mgdl) / float(self.hdl_cholesterol_mgdl), 2)
        
        if self.triglycerides_mgdl and self.hdl_cholesterol_mgdl and self.hdl_cholesterol_mgdl > 0:
            self.tg_hdl_ratio = round(float(self.triglycerides_mgdl) / float(self.hdl_cholesterol_mgdl), 2)
        
        if self.non_hdl_cholesterol_mgdl and self.hdl_cholesterol_mgdl and self.hdl_cholesterol_mgdl > 0:
            self.non_hdl_hdl_ratio = round(float(self.non_hdl_cholesterol_mgdl) / float(self.hdl_cholesterol_mgdl), 2)
        
        if self.ast_got_ul and self.alt_gpt_ul and self.alt_gpt_ul > 0:
            self.ast_alt_ratio = round(float(self.ast_got_ul) / float(self.alt_gpt_ul), 2)
        
        if self.total_protein_gdl and self.albumin_gdl:
            self.globulin_gdl = round(float(self.total_protein_gdl) - float(self.albumin_gdl), 1)
            if self.globulin_gdl > 0:
                self.albumin_globulin_ratio = round(float(self.albumin_gdl) / float(self.globulin_gdl), 2)
        
        if self.urine_albumin_mgdl and self.urine_creatinine_mgdl and self.urine_creatinine_mgdl > 0:
            self.urine_albumin_creatinine_ratio = round(float(self.urine_albumin_mgdl) / float(self.urine_creatinine_mgdl), 2)
        
        super().save(*args, **kwargs)


class CardiovascularRiskIndex(BaseModel):
    """心血管風險指數"""
    health_screening = models.OneToOneField(HealthScreening, on_delete=models.CASCADE,
                                           related_name='cardiovascular_risk', verbose_name='健康檢查')
    
    # Advanced Risk Indices
    cardiometabolic_index = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True, verbose_name='心血管代謝指數(CMI)')
    atherogenic_risk_plasma = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='動脈硬化風險(ARP)')
    
    # Gender-specific Visceral Adiposity Index
    visceral_adiposity_index_women = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True, verbose_name='女性內臟脂肪指數')
    visceral_adiposity_index_men = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True, verbose_name='男性內臟脂肪指數')
    
    # Chinese Visceral Adiposity Index
    cvai_female = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name='女性中國內臟脂肪指數')
    cvai_male = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name='男性中國內臟脂肪指數')
    
    # Monocyte to HDL ratio
    monocyte_hdl_ratio = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True, verbose_name='單核球/HDL比值')

    # 10-Year CVD Risk (Women)
    cvd_10_year_risk_women = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True, verbose_name='女性10年CVD風險')

    # 10-Year CVD Risk (Men)
    cvd_10_year_risk_men = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True, verbose_name='男性10年CVD風險')

    # 10-Year ASCVD Risk (Women)
    ascvd_10_year_risk_women = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True, verbose_name='女性10年ASCVD風險')

    # 10-Year ASCVD Risk (Men)
    ascvd_10_year_risk_men = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True, verbose_name='男性10年ASCVD風險')

    # 10-Year HF Risk (Women)
    hf_10_year_risk_women = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True, verbose_name='女性10年HF風險')

    # 10-Year HF Risk (Men)
    hf_10_year_risk_men = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True, verbose_name='男性10年HF風險')
    
    class Meta:
        verbose_name = '心血管風險指數'
        verbose_name_plural = '心血管風險指數'


class MedicalHistory(BaseModel):
    """病史和治療狀況 - 符合 USCDI Problems"""
    health_screening = models.OneToOneField(HealthScreening, on_delete=models.CASCADE,
                                           related_name='medical_history', verbose_name='健康檢查')
    
    # Current Treatment Status
    diabetes_treated = models.BooleanField(null=True, blank=True, verbose_name='糖尿病治療中')
    hypertension_treated = models.BooleanField(null=True, blank=True, verbose_name='高血壓治療中')
    hyperlipidemia_treated = models.BooleanField(null=True, blank=True, verbose_name='高血脂治療中')
    
    # Medical History
    hypertension_history = models.BooleanField(null=True, blank=True, verbose_name='高血壓病史')
    
    # Genetic Factors
    apoe_e4_positive = models.BooleanField(null=True, blank=True, verbose_name='APOE ε4陽性')
    
    class Meta:
        verbose_name = '病史'
        verbose_name_plural = '病史'


class LifestyleQuestionnaire(BaseModel):
    """生活方式問卷 - 符合 USCDI Health Concerns"""
    health_screening = models.OneToOneField(HealthScreening, on_delete=models.CASCADE,
                                           related_name='lifestyle', verbose_name='健康檢查')
    
    # Diet Assessment
    DIET_CHOICES = [
        ('0', '無蔬果'),
        ('1', '1份蔬果'),
        ('2', '2份蔬果'),
        ('3', '3份蔬果'),
        ('4', '4份蔬果'),
        ('5', '5份蔬果'),
        ('6', '6份蔬果'),
        ('7', '7份蔬果'),
        ('8+', '8份以上蔬果'),
        ('excellent', '優秀'),
        ('good', '良好'),
        ('fair', '普通'),
        ('poor', '不佳'),
    ]
    diet_score = models.CharField(max_length=20, choices=DIET_CHOICES, null=True, blank=True, verbose_name='飲食評分')
    
    # Exercise Assessment
    EXERCISE_CHOICES = [
        ('0', '不活動'),
        ('1', '輕度運動'),
        ('2', '中度運動'),
        ('3', '重度運動'),
        ('regularly', '規律運動'),
        ('sometimes', '偶爾運動'),
        ('rarely', '很少運動'),
        ('never', '從不運動'),
    ]
    exercise_score = models.CharField(max_length=20, choices=EXERCISE_CHOICES, null=True, blank=True, verbose_name='運動評分')
    
    # Detailed Exercise Assessment - NEW FIELDS
    EXERCISE_INTENSITY_CHOICES = [
        ('light', '輕度運動 (散步、伸展)'),
        ('moderate', '中度運動 (快走、游泳、騎車)'),
        ('vigorous', '高強度運動 (跑步、球類運動)'),
        ('intense', '劇烈運動 (競技運動、重訓)'),
    ]
    exercise_intensity = models.CharField(max_length=20, choices=EXERCISE_INTENSITY_CHOICES, null=True, blank=True, verbose_name='運動強度')
    
    EXERCISE_DURATION_CHOICES = [
        ('<15', '少於15分鐘'),
        ('15-30', '15-30分鐘'),
        ('30-60', '30-60分鐘'),
        ('60-90', '60-90分鐘'),
        ('>90', '超過90分鐘'),
    ]
    exercise_duration = models.CharField(max_length=10, choices=EXERCISE_DURATION_CHOICES, null=True, blank=True, verbose_name='每次運動時間')
    
    # Family History
    family_diabetes = models.BooleanField(null=True, blank=True, verbose_name='家族糖尿病史')
    family_hypertension = models.BooleanField(null=True, blank=True, verbose_name='家族高血壓史')
    family_heart_disease = models.BooleanField(null=True, blank=True, verbose_name='家族心臟病史')
    family_cvd = models.BooleanField(null=True, blank=True, verbose_name='家族心血管疾病史')
    family_cancer = models.BooleanField(null=True, blank=True, verbose_name='家族癌症史')
    family_cancer_type = models.CharField(max_length=100, null=True, blank=True, verbose_name='家族癌症類型')
    
    # Additional Family History - NEW FIELDS
    family_hyperlipidemia = models.BooleanField(null=True, blank=True, verbose_name='家族高血脂史')
    family_stroke = models.BooleanField(null=True, blank=True, verbose_name='家族中風史')
    family_other_diseases = models.TextField(null=True, blank=True, verbose_name='其他家族疾病史')
    
    # Personal Medical History
    has_diabetes = models.BooleanField(null=True, blank=True, verbose_name='有糖尿病')
    has_coronary_heart_disease = models.BooleanField(null=True, blank=True, verbose_name='有冠心病')
    has_cerebrovascular_disease = models.BooleanField(null=True, blank=True, verbose_name='有腦血管疾病')
    has_peripheral_vascular_disease = models.BooleanField(null=True, blank=True, verbose_name='有周邊血管疾病')
    has_hypertension = models.BooleanField(null=True, blank=True, verbose_name='有高血壓')
    has_dyslipidemia = models.BooleanField(null=True, blank=True, verbose_name='有血脂異常')
    
    # Detailed Personal Medical History - NEW FIELDS
    DIABETES_TYPE_CHOICES = [
        ('type1', '第一型糖尿病'),
        ('type2', '第二型糖尿病'),
        ('gestational', '妊娠糖尿病'),
        ('other', '其他類型'),
    ]
    personal_diabetes_type = models.CharField(max_length=20, choices=DIABETES_TYPE_CHOICES, null=True, blank=True, verbose_name='糖尿病類型')
    personal_diabetes_years = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='糖尿病患病年數')
    
    HEART_DISEASE_TYPE_CHOICES = [
        ('coronary', '冠心病'),
        ('myocardial', '心肌梗塞'),
        ('arrhythmia', '心律不整'),
        ('valve', '心瓣膜疾病'),
        ('other', '其他心臟疾病'),
    ]
    personal_heart_disease_type = models.CharField(max_length=20, choices=HEART_DISEASE_TYPE_CHOICES, null=True, blank=True, verbose_name='心臟病類型')
    
    personal_hypertension_years = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='高血壓患病年數')
    personal_hyperlipidemia_years = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='高血脂患病年數')
    personal_stroke = models.BooleanField(null=True, blank=True, verbose_name='個人中風史')
    personal_other_diseases = models.TextField(null=True, blank=True, verbose_name='其他個人疾病史')
    
    # Smoking History
    is_current_smoker = models.BooleanField(null=True, blank=True, verbose_name='目前吸菸')
    smoking_years = models.IntegerField(null=True, blank=True, verbose_name='吸菸年數')
    cigarettes_per_day = models.IntegerField(null=True, blank=True, verbose_name='每日菸量')
    quit_smoking_when = models.CharField(max_length=100, null=True, blank=True, verbose_name='戒菸時間')
    is_former_smoker = models.BooleanField(null=True, blank=True, verbose_name='曾經吸菸')
    
    # Alcohol Consumption
    DRINKING_CHOICES = [
        ('0', '不飲酒'),
        ('never', '從不飲酒'),
        ('rarely', '很少飲酒'),
        ('sometimes', '偶爾飲酒'),
        ('occasionally', '偶爾飲酒'),
        ('regularly', '規律飲酒'),
        ('frequently', '經常飲酒'),
        ('social', '社交飲酒'),
        ('moderate', '適度飲酒'),
        ('heavy', '重度飲酒'),
        ('daily', '每日飲酒'),
    ]
    drinking_status = models.CharField(max_length=20, choices=DRINKING_CHOICES, null=True, blank=True, verbose_name='飲酒狀況')
    drinks_per_week = models.IntegerField(null=True, blank=True, verbose_name='每週飲酒量')
    
    # Detailed Alcohol Information - NEW FIELDS
    ALCOHOL_TYPE_CHOICES = [
        ('beer', '啤酒'),
        ('wine', '葡萄酒'),
        ('spirits', '烈酒'),
        ('mixed', '混合飲用'),
    ]
    alcohol_type = models.CharField(max_length=20, choices=ALCOHOL_TYPE_CHOICES, null=True, blank=True, verbose_name='主要飲酒類型')
    
    # Medication and Allergy History - NEW FIELDS
    current_medications = models.TextField(null=True, blank=True, verbose_name='目前用藥')
    allergies = models.TextField(null=True, blank=True, verbose_name='過敏史')
    
    class Meta:
        verbose_name = '生活方式問卷'
        verbose_name_plural = '生活方式問卷'
