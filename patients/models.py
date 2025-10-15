from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.utils import timezone
import uuid


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


class Patient(BaseModel):
    """Patient demographic and basic information"""
    
    # Demographics
    first_name = models.CharField(max_length=100, verbose_name='名字')
    last_name = models.CharField(max_length=100, verbose_name='姓氏')
    middle_name = models.CharField(max_length=100, blank=True, verbose_name='中間名')
    date_of_birth = models.DateField(verbose_name='出生日期')
    
    GENDER_CHOICES = [
        ('M', '男性'),
        ('F', '女性'),
        ('O', '其他'),
        ('U', '未知'),
    ]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, verbose_name='性別')
    
    # Identity Information
    social_security_number = models.CharField(max_length=20, blank=True, verbose_name='身份證號')
    driver_license = models.CharField(max_length=50, blank=True, verbose_name='駕照號碼')
    
    # Status Information
    STATUS_CHOICES = [
        ('active', '活躍'),
        ('inactive', '不活躍'),
        ('deceased', '已故'),
        ('test', '測試'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='狀態')
    deceased_date = models.DateField(null=True, blank=True, verbose_name='死亡日期')
    deceased_reason = models.CharField(max_length=200, blank=True, verbose_name='死亡原因')
    
    # Contact Information
    phone_validator = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="電話號碼格式：'+999999999'，最多15位數字"
    )
    phone_home = models.CharField(validators=[phone_validator], max_length=17, blank=True, verbose_name='家用電話')
    phone_mobile = models.CharField(validators=[phone_validator], max_length=17, blank=True, verbose_name='手機號碼')
    phone_work = models.CharField(validators=[phone_validator], max_length=17, blank=True, verbose_name='工作電話')
    email = models.EmailField(blank=True, verbose_name='電子郵件')
    
    # Address
    address_line1 = models.CharField(max_length=200, blank=True, verbose_name='地址第一行')
    address_line2 = models.CharField(max_length=200, blank=True, verbose_name='地址第二行')
    city = models.CharField(max_length=100, blank=True, verbose_name='城市')
    state = models.CharField(max_length=100, blank=True, verbose_name='州/省')
    postal_code = models.CharField(max_length=20, blank=True, verbose_name='郵遞區號')
    country = models.CharField(max_length=100, default='Taiwan', verbose_name='國家')
    
    # Medical Information
    medical_record_number = models.CharField(max_length=50, null=True, blank=True, verbose_name='病歷號')
    blood_type = models.CharField(max_length=5, blank=True, verbose_name='血型')
    
    # Language and Cultural Information
    LANGUAGE_CHOICES = [
        ('zh-tw', '繁體中文'),
        ('zh-cn', '簡體中文'),
        ('en', 'English'),
        ('es', 'Español'),
        ('other', '其他'),
    ]
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='zh-tw', verbose_name='語言')
    interpreter_required = models.BooleanField(default=False, verbose_name='需要翻譯')
    
    ETHNICITY_CHOICES = [
        ('han', '漢族'),
        ('taiwanese_aboriginal', '台灣原住民'),
        ('other', '其他'),
        ('prefer_not_to_say', '不願透露'),
    ]
    ethnoracial = models.CharField(max_length=50, choices=ETHNICITY_CHOICES, blank=True, verbose_name='種族')
    
    # Family and Social Information
    MARITAL_STATUS_CHOICES = [
        ('single', '單身'),
        ('married', '已婚'),
        ('divorced', '離婚'),
        ('widowed', '寡居'),
        ('separated', '分居'),
        ('unknown', '未知'),
    ]
    marital_status = models.CharField(max_length=50, choices=MARITAL_STATUS_CHOICES, blank=True, verbose_name='婚姻狀況')
    
    # Emergency Contact
    emergency_contact_name = models.CharField(max_length=200, blank=True, verbose_name='緊急聯絡人姓名')
    emergency_contact_phone = models.CharField(validators=[phone_validator], max_length=17, blank=True, verbose_name='緊急聯絡人電話')
    emergency_contact_relationship = models.CharField(max_length=100, blank=True, verbose_name='緊急聯絡人關係')
    
    # Referral Information
    referrer = models.CharField(max_length=200, blank=True, verbose_name='轉介醫師')
    referrer_notes = models.TextField(blank=True, verbose_name='轉介備註')
    
    # Additional Information
    occupation = models.CharField(max_length=200, blank=True, verbose_name='職業')
    additional_notes = models.TextField(blank=True, verbose_name='備註')
    
    # Financial Information
    financial_review_date = models.DateField(null=True, blank=True, verbose_name='財務審查日期')
    
    # Preferences
    hipaa_mail = models.BooleanField(default=True, verbose_name='HIPAA郵件同意')
    hipaa_voice = models.BooleanField(default=True, verbose_name='HIPAA語音同意')
    hipaa_notice = models.BooleanField(default=True, verbose_name='HIPAA通知同意')
    hipaa_message = models.TextField(blank=True, verbose_name='HIPAA消息')
    
    class Meta:
        db_table = 'patients'
        verbose_name = '患者'
        verbose_name_plural = '患者'
        ordering = ['last_name', 'first_name']
        constraints = [
            models.UniqueConstraint(
                fields=['medical_record_number'],
                condition=models.Q(is_active=True),
                name='unique_active_medical_record_number'
            )
        ]
    
    def __str__(self):
        return f"{self.last_name}{self.first_name}"
    
    @property
    def full_name(self):
        """獲取完整姓名"""
        return f"{self.last_name}{self.first_name}"
    
    @property
    def age(self):
        """計算年齡"""
        if self.date_of_birth:
            today = timezone.now().date()
            age = today.year - self.date_of_birth.year
            if today < self.date_of_birth.replace(year=today.year):
                age -= 1
            return age
        return None
    
    @property
    def address(self):
        """獲取完整地址"""
        address_parts = [
            self.address_line1,
            self.address_line2,
            self.city,
            self.state,
            self.postal_code,
            self.country
        ]
        return ', '.join([part for part in address_parts if part])
    
    @property
    def is_deceased(self):
        """檢查患者是否已故"""
        return self.status == 'deceased' or self.deceased_date is not None
    
    def save(self, *args, **kwargs):
        """保存時自動生成病歷號（如果未提供）或驗證唯一性"""
        if not self.medical_record_number:
            # 生成簡單的病歷號：年份 + 6位隨機數
            import random
            year = timezone.now().year
            random_num = random.randint(100000, 999999)
            self.medical_record_number = f"P{year}{random_num}"
            
            # 確保病歷號唯一性（只檢查活躍患者）
            while Patient.objects.filter(
                medical_record_number=self.medical_record_number,
                is_active=True
            ).exists():
                random_num = random.randint(100000, 999999)
                self.medical_record_number = f"P{year}{random_num}"
        else:
            # 如果提供了病歷號，檢查是否與現有活躍患者重複（排除自己）
            existing_patient = Patient.objects.filter(
                medical_record_number=self.medical_record_number,
                is_active=True  # 只檢查活躍患者
            ).exclude(id=self.id).first()
            
            if existing_patient:
                # 如果重複，自動生成新的病歷號
                import random
                year = timezone.now().year
                random_num = random.randint(100000, 999999)
                original_mrn = self.medical_record_number
                self.medical_record_number = f"P{year}{random_num}"
                
                # 確保新生成的病歷號唯一性（只檢查活躍患者）
                while Patient.objects.filter(
                    medical_record_number=self.medical_record_number,
                    is_active=True
                ).exists():
                    random_num = random.randint(100000, 999999)
                    self.medical_record_number = f"P{year}{random_num}"
                
                # 可以在這裡記錄日誌或發送通知
                print(f"病歷號 {original_mrn} 已存在，自動生成新病歷號: {self.medical_record_number}")
        
        super().save(*args, **kwargs)


class PatientAllergy(BaseModel):
    """Patient allergies"""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='allergies')
    allergen = models.CharField(max_length=200, verbose_name='過敏原')
    reaction = models.TextField(blank=True, verbose_name='過敏反應')
    severity = models.CharField(max_length=50, blank=True, verbose_name='嚴重程度')
    
    class Meta:
        db_table = 'patient_allergies'
        verbose_name = '患者過敏'
        verbose_name_plural = '患者過敏'
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.allergen}"


class PatientMedication(BaseModel):
    """Patient current medications"""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medications')
    medication_name = models.CharField(max_length=200, verbose_name='藥物名稱')
    dosage = models.CharField(max_length=100, verbose_name='劑量')
    frequency = models.CharField(max_length=100, verbose_name='頻率')
    start_date = models.DateField(null=True, blank=True, verbose_name='開始日期')
    end_date = models.DateField(null=True, blank=True, verbose_name='結束日期')
    prescribing_doctor = models.CharField(max_length=200, blank=True, verbose_name='開處方醫生')
    notes = models.TextField(blank=True, verbose_name='備註')
    
    class Meta:
        db_table = 'patient_medications'
        verbose_name = '患者用藥'
        verbose_name_plural = '患者用藥'
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.medication_name}"


class PatientVitals(BaseModel):
    """Patient vital signs"""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='vitals')
    
    # Vital Signs
    height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='身高(cm)')
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='體重(kg)')
    blood_pressure_systolic = models.IntegerField(null=True, blank=True, verbose_name='收縮壓')
    blood_pressure_diastolic = models.IntegerField(null=True, blank=True, verbose_name='舒張壓')
    heart_rate = models.IntegerField(null=True, blank=True, verbose_name='心率')
    temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='體溫(°C)')
    respiratory_rate = models.IntegerField(null=True, blank=True, verbose_name='呼吸頻率')
    oxygen_saturation = models.IntegerField(null=True, blank=True, verbose_name='血氧飽和度(%)')
    
    # Additional measurements
    bmi = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='BMI')
    
    # Date and time of measurement
    measurement_date = models.DateTimeField(default=timezone.now, verbose_name='測量時間')
    
    class Meta:
        db_table = 'patient_vitals'
        verbose_name = '患者生命體徵'
        verbose_name_plural = '患者生命體徵'
        ordering = ['-measurement_date']
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.measurement_date.strftime('%Y-%m-%d %H:%M')}"
    
    def save(self, *args, **kwargs):
        """保存時自動計算BMI"""
        if self.height and self.weight:
            height_m = float(self.height) / 100  # 轉換為米
            self.bmi = round(float(self.weight) / (height_m ** 2), 1)
        super().save(*args, **kwargs)


class PatientNote(BaseModel):
    """Patient notes and observations"""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='notes')
    title = models.CharField(max_length=200, verbose_name='標題')
    content = models.TextField(verbose_name='內容')
    note_type = models.CharField(max_length=50, default='general', verbose_name='備註類型')
    is_private = models.BooleanField(default=False, verbose_name='私人備註')
    
    class Meta:
        db_table = 'patient_notes'
        verbose_name = '患者備註'
        verbose_name_plural = '患者備註'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.title}"


class InsuranceData(BaseModel):
    """Patient insurance information"""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='insurance_data')
    
    INSURANCE_TYPE_CHOICES = [
        ('primary', '主要保險'),
        ('secondary', '次要保險'),
        ('tertiary', '第三保險'),
    ]
    
    type = models.CharField(max_length=20, choices=INSURANCE_TYPE_CHOICES, verbose_name='保險類型')
    provider = models.CharField(max_length=200, verbose_name='保險公司')
    plan_name = models.CharField(max_length=200, blank=True, verbose_name='保險計劃名稱')
    policy_number = models.CharField(max_length=100, verbose_name='保單號碼')
    group_number = models.CharField(max_length=100, blank=True, verbose_name='群組號碼')
    
    # Subscriber information
    subscriber_last_name = models.CharField(max_length=100, verbose_name='保戶姓氏')
    subscriber_first_name = models.CharField(max_length=100, verbose_name='保戶名字')
    subscriber_middle_name = models.CharField(max_length=100, blank=True, verbose_name='保戶中間名')
    subscriber_relationship = models.CharField(max_length=50, verbose_name='與保戶關係')
    subscriber_ss = models.CharField(max_length=20, blank=True, verbose_name='保戶身份證號')
    subscriber_date_of_birth = models.DateField(null=True, blank=True, verbose_name='保戶出生日期')
    subscriber_phone = models.CharField(max_length=20, blank=True, verbose_name='保戶電話')
    subscriber_address = models.TextField(blank=True, verbose_name='保戶地址')
    subscriber_employer = models.CharField(max_length=200, blank=True, verbose_name='保戶雇主')
    
    # Coverage details
    copay = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='共付額')
    deductible = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='自付額')
    effective_date = models.DateField(null=True, blank=True, verbose_name='生效日期')
    expiration_date = models.DateField(null=True, blank=True, verbose_name='失效日期')
    
    # Additional information
    accept_assignment = models.BooleanField(default=True, verbose_name='接受轉讓')
    
    class Meta:
        db_table = 'insurance_data'
        verbose_name = '患者保險信息'
        verbose_name_plural = '患者保險信息'
        unique_together = [['patient', 'type']]
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.provider} ({self.get_type_display()})"


class HistoryData(BaseModel):
    """Patient medical and social history"""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='history_data')
    
    # Medical History
    medical_history = models.TextField(blank=True, verbose_name='病史')
    family_history = models.TextField(blank=True, verbose_name='家族史')
    social_history = models.TextField(blank=True, verbose_name='社會史')
    
    # Lifestyle factors
    tobacco = models.CharField(max_length=50, blank=True, choices=[
        ('never', '從不吸煙'),
        ('former', '曾經吸煙'),
        ('current', '目前吸煙'),
        ('unknown', '未知'),
    ], verbose_name='吸煙史')
    tobacco_details = models.TextField(blank=True, verbose_name='吸煙詳情')
    
    alcohol = models.CharField(max_length=50, blank=True, choices=[
        ('never', '從不飲酒'),
        ('occasional', '偶爾飲酒'),
        ('moderate', '適量飲酒'),
        ('heavy', '重度飲酒'),
        ('former', '曾經飲酒'),
        ('unknown', '未知'),
    ], verbose_name='飲酒史')
    alcohol_details = models.TextField(blank=True, verbose_name='飲酒詳情')
    
    # Exercise and diet
    exercise = models.CharField(max_length=100, blank=True, verbose_name='運動習慣')
    diet = models.TextField(blank=True, verbose_name='飲食習慣')
    
    # Reproductive history (for female patients)
    gravida = models.IntegerField(null=True, blank=True, verbose_name='懷孕次數')
    para = models.IntegerField(null=True, blank=True, verbose_name='生產次數')
    abortions = models.IntegerField(null=True, blank=True, verbose_name='流產次數')
    miscarriages = models.IntegerField(null=True, blank=True, verbose_name='自然流產次數')
    
    # Other
    coffee_consumption = models.CharField(max_length=100, blank=True, verbose_name='咖啡攝取')
    recreational_drugs = models.TextField(blank=True, verbose_name='娛樂性藥物使用')
    
    class Meta:
        db_table = 'history_data'
        verbose_name = '患者病史數據'
        verbose_name_plural = '患者病史數據'
    
    def __str__(self):
        return f"{self.patient.full_name} - 病史"


class EmployerData(BaseModel):
    """Patient employer information"""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='employer_data')
    
    # Employer details
    employer_name = models.CharField(max_length=200, verbose_name='雇主名稱')
    employer_address = models.TextField(blank=True, verbose_name='雇主地址')
    employer_city = models.CharField(max_length=100, blank=True, verbose_name='雇主城市')
    employer_state = models.CharField(max_length=50, blank=True, verbose_name='雇主州/省')
    employer_postal_code = models.CharField(max_length=20, blank=True, verbose_name='雇主郵遞區號')
    employer_country = models.CharField(max_length=100, blank=True, verbose_name='雇主國家')
    
    # Contact information
    employer_phone = models.CharField(max_length=20, blank=True, verbose_name='雇主電話')
    employer_fax = models.CharField(max_length=20, blank=True, verbose_name='雇主傳真')
    employer_email = models.EmailField(blank=True, verbose_name='雇主電子郵件')
    
    # Employment details
    position = models.CharField(max_length=200, blank=True, verbose_name='職位')
    department = models.CharField(max_length=200, blank=True, verbose_name='部門')
    employment_start_date = models.DateField(null=True, blank=True, verbose_name='入職日期')
    employment_end_date = models.DateField(null=True, blank=True, verbose_name='離職日期')
    
    # Contact person at employer
    contact_person = models.CharField(max_length=200, blank=True, verbose_name='雇主聯繫人')
    contact_phone = models.CharField(max_length=20, blank=True, verbose_name='聯繫人電話')
    
    # Additional information
    is_current_employer = models.BooleanField(default=True, verbose_name='是否為當前雇主')
    
    class Meta:
        db_table = 'employer_data'
        verbose_name = '患者雇主信息'
        verbose_name_plural = '患者雇主信息'
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.employer_name}"


class PatientDocument(BaseModel):
    """Patient document management"""
    DOCUMENT_TYPE_CHOICES = [
        ('medical_record', '病歷文件'),
        ('lab_result', '檢驗報告'),
        ('imaging', '影像資料'),
        ('prescription', '處方箋'),
        ('insurance', '保險文件'),
        ('consent_form', '同意書'),
        ('referral', '轉診單'),
        ('discharge_summary', '出院摘要'),
        ('progress_note', '病程記錄'),
        ('other', '其他'),
    ]
    
    DOCUMENT_STATUS_CHOICES = [
        ('active', '有效'),
        ('archived', '已歸檔'),
        ('deleted', '已刪除'),
        ('pending', '待審核'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='patient_documents')
    
    # Document identification
    title = models.CharField(max_length=200, verbose_name='文件標題')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES, verbose_name='文件類型')
    description = models.TextField(blank=True, verbose_name='文件描述')
    
    # File information
    file = models.FileField(upload_to='patient_documents/%Y/%m/%d/', verbose_name='文件檔案')
    original_filename = models.CharField(max_length=255, verbose_name='原始檔案名稱')
    file_size = models.PositiveIntegerField(verbose_name='檔案大小(bytes)')
    mime_type = models.CharField(max_length=100, verbose_name='MIME 類型')
    
    # Document metadata
    document_date = models.DateField(verbose_name='文件日期')
    document_status = models.CharField(max_length=20, choices=DOCUMENT_STATUS_CHOICES, default='active', verbose_name='文件狀態')
    
    # Associated provider/facility
    provider_name = models.CharField(max_length=200, blank=True, verbose_name='提供者名稱')
    facility_name = models.CharField(max_length=200, blank=True, verbose_name='醫療機構名稱')
    
    # Access control
    is_confidential = models.BooleanField(default=False, verbose_name='是否機密')
    access_restricted = models.BooleanField(default=False, verbose_name='是否限制存取')
    
    # Notes
    notes = models.TextField(blank=True, verbose_name='備註')
    
    class Meta:
        db_table = 'patient_documents'
        verbose_name = '患者文件'
        verbose_name_plural = '患者文件'
        ordering = ['-document_date', '-created_at']
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.title}"
    
    def save(self, *args, **kwargs):
        if self.file:
            self.original_filename = self.file.name
            self.file_size = self.file.size
        super().save(*args, **kwargs)
