from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
from patients.models import Patient, BaseModel


class Encounter(BaseModel):
    """Patient encounter/visit model based on form_encounter table"""
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='encounters', verbose_name='病患')
    provider = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                related_name='provider_encounters', verbose_name='醫師')
    
    # Encounter details
    encounter_date = models.DateTimeField(default=timezone.now, verbose_name='看診日期')
    encounter_class = models.CharField(max_length=50, default='ambulatory', verbose_name='看診類別')
    
    ENCOUNTER_REASON_CHOICES = [
        ('routine', '例行檢查'),
        ('follow_up', '追蹤'),
        ('emergency', '急診'),
        ('consultation', '諮詢'),
        ('procedure', '手術/處置'),
        ('other', '其他'),
    ]
    reason = models.CharField(max_length=50, choices=ENCOUNTER_REASON_CHOICES, 
                             default='routine', verbose_name='看診原因')
    
    # Chief complaint and assessment
    chief_complaint = models.TextField(blank=True, verbose_name='主訴')
    history_present_illness = models.TextField(blank=True, verbose_name='現病史')
    assessment = models.TextField(blank=True, verbose_name='診斷')
    plan = models.TextField(blank=True, verbose_name='治療計劃')
    
    # Vital signs
    temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='體溫 (°C)')
    pulse = models.IntegerField(null=True, blank=True, verbose_name='脈搏 (次/分)')
    respiration = models.IntegerField(null=True, blank=True, verbose_name='呼吸 (次/分)')
    blood_pressure_systolic = models.IntegerField(null=True, blank=True, verbose_name='收縮壓')
    blood_pressure_diastolic = models.IntegerField(null=True, blank=True, verbose_name='舒張壓')
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='體重 (kg)')
    height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='身高 (cm)')
    
    # Status and workflow
    STATUS_CHOICES = [
        ('scheduled', '已排程'),
        ('in_progress', '進行中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
        ('no_show', '未到診'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled', verbose_name='狀態')
    
    # Billing and coding
    billing_code = models.CharField(max_length=20, blank=True, verbose_name='計費代碼')
    facility = models.CharField(max_length=100, blank=True, verbose_name='機構')
    
    # Notes
    notes = models.TextField(blank=True, verbose_name='備註')
    
    class Meta:
        verbose_name = '看診紀錄'
        verbose_name_plural = '看診紀錄'
        ordering = ['-encounter_date']
        indexes = [
            models.Index(fields=['patient', '-encounter_date']),
            models.Index(fields=['provider', '-encounter_date']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.patient} - {self.encounter_date.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def bmi(self):
        """Calculate BMI if height and weight are available"""
        if self.height and self.weight and self.height > 0:
            height_m = float(self.height) / 100  # Convert cm to meters
            return round(float(self.weight) / (height_m ** 2), 2)
        return None
    
    @property
    def blood_pressure(self):
        """Return formatted blood pressure"""
        if self.blood_pressure_systolic and self.blood_pressure_diastolic:
            return f"{self.blood_pressure_systolic}/{self.blood_pressure_diastolic}"
        return None


class EncounterForm(BaseModel):
    """Forms associated with encounters"""
    
    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE, 
                                 related_name='forms', verbose_name='看診紀錄')
    
    FORM_TYPE_CHOICES = [
        ('soap', 'SOAP Notes'),
        ('physical_exam', '理學檢查'),
        ('medication', '用藥紀錄'),
        ('lab_order', '檢驗單'),
        ('imaging_order', '影像檢查單'),
        ('prescription', '處方簽'),
        ('referral', '轉診單'),
        ('other', '其他'),
    ]
    form_type = models.CharField(max_length=50, choices=FORM_TYPE_CHOICES, verbose_name='表單類型')
    form_name = models.CharField(max_length=100, verbose_name='表單名稱')
    form_data = models.JSONField(default=dict, verbose_name='表單資料')
    
    class Meta:
        verbose_name = '看診表單'
        verbose_name_plural = '看診表單'
        ordering = ['encounter', 'form_type']
    
    def __str__(self):
        return f"{self.encounter} - {self.get_form_type_display()}"


class EncounterDiagnosis(BaseModel):
    """Diagnoses associated with encounters"""
    
    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE, 
                                 related_name='diagnoses', verbose_name='看診紀錄')
    
    # ICD codes and diagnosis
    icd_code = models.CharField(max_length=20, blank=True, verbose_name='ICD代碼')
    diagnosis_text = models.CharField(max_length=500, verbose_name='診斷描述')
    
    DIAGNOSIS_TYPE_CHOICES = [
        ('primary', '主要診斷'),
        ('secondary', '次要診斷'),
        ('rule_out', '排除診斷'),
        ('differential', '鑑別診斷'),
    ]
    diagnosis_type = models.CharField(max_length=20, choices=DIAGNOSIS_TYPE_CHOICES, 
                                     default='primary', verbose_name='診斷類型')
    
    # Status
    is_confirmed = models.BooleanField(default=False, verbose_name='已確認')
    
    class Meta:
        verbose_name = '看診診斷'
        verbose_name_plural = '看診診斷'
        ordering = ['encounter', 'diagnosis_type']
    
    def __str__(self):
        return f"{self.encounter} - {self.diagnosis_text}"
