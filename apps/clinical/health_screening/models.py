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
    """Encounter Information - Aligned with USCDI v6"""
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='screenings')
    
    # Encounter Elements (USCDI v6)
    encounter_type = models.CharField(max_length=100, default='annual_physical', verbose_name='就診類型')
    encounter_identifier = models.CharField(max_length=100, blank=True, verbose_name='就診識別碼')
    encounter_time = models.DateTimeField(default=timezone.now, verbose_name='就診時間')
    encounter_location = models.CharField(max_length=200, blank=True, verbose_name='就診地點')
    encounter_disposition = models.CharField(max_length=200, blank=True, verbose_name='就診處置')
    
    screening_date = models.DateField(default=timezone.now, verbose_name='檢查日期')
    
    class Meta:
        db_table = 'health_screening_healthscreening'
        verbose_name = '就診/健康檢查'


class VitalSigns(BaseModel):
    """Vital Signs - USCDI v6 Complete List"""
    health_screening = models.OneToOneField(HealthScreening, on_delete=models.CASCADE, related_name='vital_signs')
    
    # Blood Pressure (USCDI v6)
    systolic_blood_pressure = models.IntegerField(null=True, blank=True, verbose_name='收縮壓')
    diastolic_blood_pressure = models.IntegerField(null=True, blank=True, verbose_name='舒張壓')
    average_blood_pressure = models.IntegerField(null=True, blank=True, verbose_name='平均血壓') # USCDI v6
    
    # Fundamental Functions (USCDI v6)
    heart_rate = models.IntegerField(null=True, blank=True, verbose_name='心率')
    respiratory_rate = models.IntegerField(null=True, blank=True, verbose_name='呼吸頻率')
    body_temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='體溫')
    body_height = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='身高(cm)')
    body_weight = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name='體重(kg)')
    
    # Oxygen (USCDI v6)
    pulse_oximetry = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='血氧飽和度')
    inhaled_oxygen_concentration = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='吸入氧氣濃度')
    
    # Percentiles (USCDI v6)
    bmi_percentile = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='BMI百分位數 (2-20歲)')
    weight_for_length_percentile = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='身長體重百分位數 (0-24月)')
    head_circumference_percentile = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='頭圍百分位數 (0-36月)')
    
    class Meta:
        db_table = 'health_screening_vitalsigns'
        verbose_name = '生命體徵'


class LaboratoryResults(BaseModel):
    """Laboratory - USCDI v6 Complete Elements"""
    health_screening = models.ForeignKey(HealthScreening, on_delete=models.CASCADE, related_name='lab_results')
    
    test_name = models.CharField(max_length=200, default='Unknown Test', verbose_name='檢測項目 (Tests)')
    value_result = models.CharField(max_length=100, default='Pending', verbose_name='數值/結果 (Values/Results)')
    result_unit = models.CharField(max_length=50, blank=True, verbose_name='單位 (Unit)')
    result_status = models.CharField(max_length=50, blank=True, verbose_name='結果狀態 (Status)')
    result_reference_range = models.CharField(max_length=100, blank=True, verbose_name='參考範圍')
    result_interpretation = models.CharField(max_length=100, blank=True, verbose_name='結果解釋')
    
    # Specimen Information (USCDI v6)
    specimen_type = models.CharField(max_length=100, blank=True, verbose_name='檢體類型')
    specimen_source_site = models.CharField(max_length=100, blank=True, verbose_name='檢體來源部位')
    specimen_identifier = models.CharField(max_length=100, blank=True, verbose_name='檢體識別碼')
    specimen_condition = models.CharField(max_length=200, blank=True, verbose_name='檢體狀況接受度')
    
    class Meta:
        db_table = 'health_screening_laboratoryresults'
        verbose_name = '實驗室檢驗'


class Problem(BaseModel):
    """Problems - USCDI v6 Complete"""
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='problems')
    
    problem_name = models.CharField(max_length=200, verbose_name='問題名稱')
    sdoh_problem = models.BooleanField(default=False, verbose_name='是否為 SDOH 問題') # USCDI v6
    
    # Dates (USCDI v6)
    date_of_onset = models.DateField(null=True, blank=True, verbose_name='發病日期')
    date_of_diagnosis = models.DateField(null=True, blank=True, verbose_name='診斷日期')
    date_of_resolution = models.DateField(null=True, blank=True, verbose_name='解決日期')
    
    status = models.CharField(max_length=50, default='active', verbose_name='狀態')
    
    class Meta:
        db_table = 'health_screening_problem'
        verbose_name = '健康問題'


class Procedure(BaseModel):
    """Procedures - USCDI v6"""
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='procedures')
    
    procedure_name = models.CharField(max_length=200, verbose_name='處置名稱')
    performance_time = models.DateTimeField(default=timezone.now, verbose_name='執行時間')
    sdoh_intervention = models.TextField(blank=True, verbose_name='SDOH 介入') # USCDI v6
    reason_for_referral = models.TextField(blank=True, verbose_name='轉診原因') # USCDI v6
    
    class Meta:
        db_table = 'health_screening_procedure'
        verbose_name = '醫療處置'


class Immunization(BaseModel):
    """Immunizations - USCDI v6"""
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='immunizations')
    vaccine_name = models.CharField(max_length=200, verbose_name='疫苗名稱')
    administration_date = models.DateTimeField(default=timezone.now, verbose_name='接種日期')
    lot_number = models.CharField(max_length=100, blank=True, verbose_name='批號 (Lot Number)') # USCDI v6
    
    class Meta:
        db_table = 'health_screening_immunization'
        verbose_name = '免疫接種'


class HealthStatusAssessment(BaseModel):
    """Health Status Assessments - USCDI v6"""
    health_screening = models.OneToOneField(HealthScreening, on_delete=models.CASCADE, related_name='assessments')
    
    # USCDI v6 Health Status Elements
    health_concerns = models.TextField(blank=True, default='', verbose_name='健康疑慮')
    functional_status = models.TextField(blank=True, default='', verbose_name='功能狀態')
    disability_status = models.TextField(blank=True, default='', verbose_name='殘疾狀態')
    mental_cognitive_status = models.TextField(blank=True, default='', verbose_name='精神/認知狀態')
    pregnancy_status = models.CharField(max_length=100, blank=True, default='', verbose_name='懷孕狀態')
    
    # Behaviors and SDOH (USCDI v6)
    alcohol_use = models.TextField(blank=True, default='', verbose_name='飲酒情況')
    substance_use = models.TextField(blank=True, default='', verbose_name='物質使用')
    physical_activity = models.TextField(blank=True, default='', verbose_name='體育活動')
    sdoh_assessment = models.TextField(blank=True, default='', verbose_name='SDOH 評估')
    smoking_status = models.CharField(max_length=100, blank=True, default='', verbose_name='吸菸狀態')
    
    class Meta:
        db_table = 'health_screening_healthstatusassessment'
        verbose_name = '健康狀態評估'


class ClinicalTestResult(BaseModel):
    """Clinical Tests - USCDI v6"""
    health_screening = models.ForeignKey(HealthScreening, on_delete=models.CASCADE, related_name='clinical_tests')
    
    test_name = models.CharField(max_length=200, verbose_name='測試名稱')
    result_value = models.CharField(max_length=200, verbose_name='結果數值/報告')
    test_date = models.DateTimeField(default=timezone.now, verbose_name='測試日期')
    interpretation = models.TextField(blank=True, verbose_name='結果解釋')
    
    class Meta:
        db_table = 'health_screening_clinicaltestresult'
        verbose_name = '臨床測試結果'


class RiskAssessmentRun(BaseModel):
    """A product risk-analysis execution anchored to patient source data."""
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='risk_assessment_runs')
    health_screening = models.ForeignKey(
        HealthScreening,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='risk_assessment_runs',
    )
    algorithm_scope = models.CharField(max_length=100, default='comprehensive')
    model_version = models.CharField(max_length=50, default='risk-engine-v1')
    status = models.CharField(max_length=50, default='completed')
    input_snapshot = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(default=timezone.now)
    error_message = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'risk_assessment_run'
        indexes = [
            models.Index(fields=['patient', '-generated_at']),
            models.Index(fields=['status']),
        ]


class RiskAssessmentResult(BaseModel):
    """Individual risk result produced by a risk assessment run."""
    run = models.ForeignKey(RiskAssessmentRun, on_delete=models.CASCADE, related_name='results')
    algorithm = models.CharField(max_length=100)
    outcome = models.CharField(max_length=150)
    risk_value = models.CharField(max_length=50, blank=True, default='')
    risk_score = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    risk_level = models.CharField(max_length=50, blank=True, default='')
    missing_data = models.JSONField(default=list, blank=True)
    fhir_resource = models.ForeignKey(
        'fhir_integration.FHIRResource',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='risk_results',
    )

    class Meta:
        db_table = 'risk_assessment_result'
        indexes = [
            models.Index(fields=['algorithm', 'outcome']),
        ]


class RiskRecommendation(BaseModel):
    """Clinical follow-up recommendation derived from risk results."""
    run = models.ForeignKey(RiskAssessmentRun, on_delete=models.CASCADE, related_name='recommendations')
    priority = models.CharField(max_length=50, default='routine')
    title = models.CharField(max_length=200)
    recommendation = models.TextField()
    follow_up_interval_days = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'risk_recommendation'
        indexes = [
            models.Index(fields=['priority']),
        ]


class Encounter(BaseModel):
    """就醫或健康資料輸入事件，可投影為 FHIR Encounter。"""
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='product_encounters')
    practitioner = models.ForeignKey('patients.Practitioner', on_delete=models.SET_NULL, null=True, blank=True, related_name='encounters')
    source_screening = models.ForeignKey(HealthScreening, on_delete=models.SET_NULL, null=True, blank=True, related_name='product_encounters')
    encounter_type = models.CharField(max_length=100, default='outpatient')
    status = models.CharField(max_length=50, default='finished')
    reason = models.CharField(max_length=250, blank=True, default='')
    location = models.CharField(max_length=250, blank=True, default='')
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    source_type = models.CharField(max_length=100, blank=True, default='')
    metadata_json = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'encounters'
        db_table_comment = '就醫、健檢、遠距或裝置資料輸入事件；作為 Observation、QuestionnaireResponse、CarePlan 的時間與情境主軸。FHIR 對應：Encounter。'
        indexes = [
            models.Index(fields=['patient', '-started_at']),
            models.Index(fields=['practitioner', '-started_at']),
            models.Index(fields=['status']),
            models.Index(fields=['encounter_type']),
        ]


class Observation(BaseModel):
    """標準化臨床觀測資料，可投影為 FHIR Observation。"""
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='product_observations')
    encounter = models.ForeignKey(Encounter, on_delete=models.SET_NULL, null=True, blank=True, related_name='observations')
    practitioner = models.ForeignKey('patients.Practitioner', on_delete=models.SET_NULL, null=True, blank=True, related_name='observations')
    observation_type = models.CharField(max_length=100, default='vital-signs')
    category = models.CharField(max_length=100, default='vital-signs')
    source_type = models.CharField(max_length=100, default='manual')
    code_system = models.CharField(max_length=200, blank=True, default='')
    code = models.CharField(max_length=100, blank=True, default='')
    display = models.CharField(max_length=250, blank=True, default='')
    value_quantity = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    value_unit = models.CharField(max_length=50, blank=True, default='')
    value_string = models.CharField(max_length=500, blank=True, default='')
    value_boolean = models.BooleanField(null=True, blank=True)
    value_json = models.JSONField(default=dict, blank=True)
    component_json = models.JSONField(default=list, blank=True)
    reference_range_json = models.JSONField(default=dict, blank=True)
    interpretation = models.CharField(max_length=100, blank=True, default='')
    status = models.CharField(max_length=50, default='final')
    effective_at = models.DateTimeField(default=timezone.now)
    issued_at = models.DateTimeField(null=True, blank=True)
    device_identifier = models.CharField(max_length=150, blank=True, default='')
    source_payload_json = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'observations'
        db_table_comment = '標準化觀測資料；支援血壓、血糖、體重、心率、檢驗、居家檢測、穿戴資料與生活習慣。FHIR 對應：Observation、DiagnosticReport result。'
        indexes = [
            models.Index(fields=['patient', '-effective_at']),
            models.Index(fields=['encounter']),
            models.Index(fields=['category', 'code']),
            models.Index(fields=['observation_type']),
            models.Index(fields=['source_type']),
        ]


class Questionnaire(BaseModel):
    """問卷定義，可投影為 FHIR Questionnaire。"""
    title = models.CharField(max_length=250)
    version = models.CharField(max_length=50, default='1.0.0')
    status = models.CharField(max_length=50, default='active')
    code_system = models.CharField(max_length=200, blank=True, default='')
    code = models.CharField(max_length=100, blank=True, default='')
    questionnaire_json = models.JSONField(default=dict, blank=True)
    scoring_json = models.JSONField(default=dict, blank=True)
    metadata_json = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'questionnaires'
        db_table_comment = '問卷版本與題目定義；保存生活習慣、SDOH、症狀與追蹤問卷。FHIR 對應：Questionnaire。'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['code']),
            models.Index(fields=['title', 'version']),
        ]
        unique_together = ['title', 'version']


class QuestionnaireResponse(BaseModel):
    """病患問卷答案與分數，可投影為 FHIR QuestionnaireResponse。"""
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='questionnaire_responses')
    questionnaire = models.ForeignKey(Questionnaire, on_delete=models.SET_NULL, null=True, blank=True, related_name='responses')
    encounter = models.ForeignKey(Encounter, on_delete=models.SET_NULL, null=True, blank=True, related_name='questionnaire_responses')
    authored_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=50, default='completed')
    source_type = models.CharField(max_length=100, default='manual')
    response_json = models.JSONField(default=dict, blank=True)
    score_json = models.JSONField(default=dict, blank=True)
    metadata_json = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'questionnaire_responses'
        db_table_comment = '問卷填答結果；保存完整 response_json 與 score_json 供疾病風險判讀與 FHIR 投影。FHIR 對應：QuestionnaireResponse、Observation survey。'
        indexes = [
            models.Index(fields=['patient', '-authored_at']),
            models.Index(fields=['questionnaire', 'status']),
            models.Index(fields=['source_type']),
        ]


class DataImportBatch(BaseModel):
    """資料匯入批次，可追蹤 CSV、Excel、FHIR Bulk、API 與裝置匯入。"""
    created_by_user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='data_import_batches')
    source_type = models.CharField(max_length=100, default='csv')
    original_filename = models.CharField(max_length=250, blank=True, default='')
    status = models.CharField(max_length=50, default='pending')
    total_rows = models.IntegerField(default=0)
    processed_rows = models.IntegerField(default=0)
    success_rows = models.IntegerField(default=0)
    failed_rows = models.IntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    import_options_json = models.JSONField(default=dict, blank=True)
    summary_json = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'data_import_batches'
        db_table_comment = '資料匯入批次；支援 CSV、Excel、FHIR Bulk、hospital API、device API 匯入狀態與摘要。FHIR 對應：Bulk Data export/import lineage、Provenance。'
        indexes = [
            models.Index(fields=['source_type', 'status']),
            models.Index(fields=['created_by_user', '-created_at']),
        ]


class DataImportRow(BaseModel):
    """資料匯入列級結果，保存 raw data 與轉換後目標。"""
    batch = models.ForeignKey(DataImportBatch, on_delete=models.CASCADE, related_name='rows')
    patient = models.ForeignKey('patients.Patient', on_delete=models.SET_NULL, null=True, blank=True, related_name='import_rows')
    row_number = models.IntegerField()
    status = models.CharField(max_length=50, default='pending')
    target_table = models.CharField(max_length=100, blank=True, default='')
    target_id = models.UUIDField(null=True, blank=True)
    raw_json = models.JSONField(default=dict, blank=True)
    normalized_json = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'data_import_rows'
        db_table_comment = '資料匯入明細列；保存原始列、標準化結果、錯誤訊息與落庫目標。FHIR 對應：Provenance。'
        indexes = [
            models.Index(fields=['batch', 'row_number']),
            models.Index(fields=['patient']),
            models.Index(fields=['status']),
            models.Index(fields=['target_table', 'target_id']),
        ]
        unique_together = ['batch', 'row_number']


class AIAnalysisJob(BaseModel):
    """疾病風險判讀工作，連接病患資料、問卷、觀測與模型版本。"""
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='ai_analysis_jobs')
    requested_by_user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_analysis_jobs')
    encounter = models.ForeignKey(Encounter, on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_analysis_jobs')
    job_type = models.CharField(max_length=100, default='risk_assessment')
    status = models.CharField(max_length=50, default='pending')
    model_name = models.CharField(max_length=150, default='allcare-risk-engine')
    model_version = models.CharField(max_length=100, default='v1')
    input_json = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'ai_analysis_jobs'
        db_table_comment = '疾病風險判讀工作；保存分析類型、模型版本、輸入快照與執行狀態。FHIR 對應：ServiceRequest、Provenance。'
        indexes = [
            models.Index(fields=['patient', '-created_at']),
            models.Index(fields=['job_type', 'status']),
            models.Index(fields=['model_name', 'model_version']),
        ]


class AIAnalysisResult(BaseModel):
    """疾病風險判讀結果，可投影為 RiskAssessment、Observation 或 DiagnosticReport。"""
    job = models.ForeignKey(AIAnalysisJob, on_delete=models.CASCADE, related_name='results')
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='ai_analysis_results')
    result_type = models.CharField(max_length=100, default='risk_assessment')
    model_version = models.CharField(max_length=100)
    confidence_score = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)
    risk_level = models.CharField(max_length=50, blank=True, default='')
    result_json = models.JSONField(default=dict, blank=True)
    explanation_json = models.JSONField(default=dict, blank=True)
    recommendation_text = models.TextField(blank=True, default='')
    requires_doctor_review = models.BooleanField(default=True)
    reviewed_by_practitioner = models.ForeignKey('patients.Practitioner', on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_ai_results')
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ai_analysis_results'
        db_table_comment = '疾病風險判讀結果；保存信心分數、解釋、建議與醫師審核狀態。FHIR 對應：RiskAssessment、Observation、DiagnosticReport、DocumentReference。'
        indexes = [
            models.Index(fields=['patient', '-created_at']),
            models.Index(fields=['result_type']),
            models.Index(fields=['requires_doctor_review']),
            models.Index(fields=['model_version']),
        ]


class CareTask(BaseModel):
    """照護追蹤任務，可投影為 FHIR Task。"""
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='care_tasks')
    care_plan = models.ForeignKey('patients.CarePlan', on_delete=models.CASCADE, related_name='tasks')
    assigned_practitioner = models.ForeignKey('patients.Practitioner', on_delete=models.SET_NULL, null=True, blank=True, related_name='care_tasks')
    source_ai_result = models.ForeignKey(AIAnalysisResult, on_delete=models.SET_NULL, null=True, blank=True, related_name='care_tasks')
    title = models.CharField(max_length=250)
    description = models.TextField(blank=True, default='')
    status = models.CharField(max_length=50, default='requested')
    priority = models.CharField(max_length=50, default='routine')
    due_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    metadata_json = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'care_tasks'
        db_table_comment = '照護追蹤任務；保存醫囑追蹤、回診、檢查、生活習慣任務。FHIR 對應：Task。'
        indexes = [
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['care_plan', 'status']),
            models.Index(fields=['assigned_practitioner', 'status']),
            models.Index(fields=['due_at']),
        ]


class Consent(BaseModel):
    """醫病資料授權與同意紀錄，可投影為 FHIR Consent。"""
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='consents')
    practitioner = models.ForeignKey('patients.Practitioner', on_delete=models.SET_NULL, null=True, blank=True, related_name='patient_consents')
    status = models.CharField(max_length=50, default='active')
    category = models.CharField(max_length=100, default='treatment')
    scope = models.CharField(max_length=100, default='patient-privacy')
    granted_at = models.DateTimeField(default=timezone.now)
    revoked_at = models.DateTimeField(null=True, blank=True)
    policy_uri = models.URLField(blank=True, default='')
    provision_json = models.JSONField(default=dict, blank=True)
    source_json = models.JSONField(default=dict, blank=True)
    metadata_json = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'consents'
        db_table_comment = '病患同意與資料授權；保存醫病授權、撤銷、政策與細部 provision。FHIR 對應：Consent。'
        indexes = [
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['practitioner', 'status']),
            models.Index(fields=['category']),
        ]


class ResearchAggregateReport(BaseModel):
    """Governed aggregate-only research output snapshot."""

    STATUS_CHOICES = [
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    REPORT_TYPE_CHOICES = [
        ('cohort_summary', 'Cohort Summary'),
        ('cohort_measure_report', 'FHIR MeasureReport'),
        ('patients_like_this', 'Patients Like This'),
    ]

    requested_by_user = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requested_research_aggregate_reports',
    )
    approved_by_user = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_research_aggregate_reports',
    )
    title = models.CharField(max_length=250)
    report_type = models.CharField(max_length=100, choices=REPORT_TYPE_CHOICES, default='cohort_summary')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='requested')
    dataset = models.CharField(max_length=100, default='h2u_cvd_csv')
    query_params_json = models.JSONField(default=dict, blank=True)
    privacy_json = models.JSONField(default=dict, blank=True)
    result_json = models.JSONField(default=dict, blank=True)
    fhir_json = models.JSONField(default=dict, blank=True)
    approval_note = models.TextField(blank=True, default='')
    requested_at = models.DateTimeField(default=timezone.now)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    metadata_json = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'research_aggregate_reports'
        indexes = [
            models.Index(fields=['status', '-requested_at']),
            models.Index(fields=['report_type', 'status']),
            models.Index(fields=['requested_by_user', '-requested_at']),
            models.Index(fields=['approved_by_user', '-approved_at']),
        ]


class DiagnosticImagingResult(BaseModel):
    """Diagnostic Imaging - USCDI v6"""
    health_screening = models.ForeignKey(HealthScreening, on_delete=models.CASCADE, related_name='imaging_results')
    
    imaging_test_name = models.CharField(max_length=200, verbose_name='影像檢查名稱')
    modality = models.CharField(max_length=100, verbose_name='檢查類別 (Modality)') # e.g., X-ray, MRI, CT
    findings = models.TextField(blank=True, verbose_name='發現 (Findings)')
    report_text = models.TextField(verbose_name='報告內容')
    image_url = models.URLField(blank=True, verbose_name='影像連結')
    test_date = models.DateTimeField(default=timezone.now, verbose_name='檢查日期')
    
    class Meta:
        db_table = 'health_screening_diagnosticimagingresult'
        verbose_name = '診斷影像報告'
