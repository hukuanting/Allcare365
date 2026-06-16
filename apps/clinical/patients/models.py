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
    """Patient demographic and basic information - Aligned with USCDI v6"""
    first_name = models.CharField(max_length=100, verbose_name='First Name')
    last_name = models.CharField(max_length=100, verbose_name='Last Name')
    middle_name = models.CharField(max_length=100, blank=True, verbose_name='Middle Name')
    name_suffix = models.CharField(max_length=20, blank=True, verbose_name='Name Suffix')
    previous_name = models.CharField(max_length=200, blank=True, verbose_name='Previous Name')
    
    date_of_birth = models.DateField(verbose_name='Date of Birth')
    date_of_death = models.DateField(null=True, blank=True, verbose_name='Date of Death')
    
    sex = models.CharField(max_length=50, blank=True, verbose_name='Sex')
    
    race = models.CharField(max_length=100, blank=True, verbose_name='Race')
    ethnicity = models.CharField(max_length=100, blank=True, verbose_name='Ethnicity')
    tribal_affiliation = models.CharField(max_length=200, blank=True, verbose_name='Tribal Affiliation')
    
    current_address_line1 = models.CharField(max_length=200, blank=True, verbose_name='Address Line 1')
    current_address_line2 = models.CharField(max_length=200, blank=True, verbose_name='Address Line 2')
    city = models.CharField(max_length=100, blank=True, verbose_name='City')
    state = models.CharField(max_length=100, blank=True, verbose_name='State')
    postal_code = models.CharField(max_length=20, blank=True, verbose_name='Postal Code')
    country = models.CharField(max_length=100, default='Taiwan', verbose_name='Country')
    previous_address = models.TextField(blank=True, verbose_name='Previous Address')
    
    phone_validator = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone format: '+999999999', up to 15 digits."
    )
    phone_number = models.CharField(validators=[phone_validator], max_length=17, blank=True, verbose_name='Phone Number')
    phone_number_type = models.CharField(max_length=50, blank=True, verbose_name='Phone Type')
    email_address = models.EmailField(blank=True, verbose_name='Email Address')
    
    preferred_language = models.CharField(max_length=50, default='zh-tw', verbose_name='Preferred Language')
    interpreter_needed = models.BooleanField(default=False, verbose_name='Interpreter Needed')
    
    related_person_name = models.CharField(max_length=200, blank=True, verbose_name='Related Person Name')
    relationship_type = models.CharField(max_length=100, blank=True, verbose_name='Relationship Type')
    
    occupation = models.CharField(max_length=200, blank=True, verbose_name='Occupation')
    occupation_industry = models.CharField(max_length=200, blank=True, verbose_name='Occupation Industry')

    medical_record_number = models.CharField(max_length=50, null=True, blank=True, verbose_name='MRN')
    status = models.CharField(max_length=20, default='active', verbose_name='Status')
    source_system = models.CharField(max_length=100, blank=True, default='', verbose_name='Source System')
    source_record_id = models.CharField(max_length=150, blank=True, default='', verbose_name='Source Record ID')
    last_imported_at = models.DateTimeField(null=True, blank=True, verbose_name='Last Imported At')
    metadata_json = models.JSONField(default=dict, blank=True, verbose_name='Metadata')
    
    class Meta:
        db_table = 'patients'
        db_table_comment = '病患主檔；保存 EHR/EMR 病患人口學資料與來源系統識別。FHIR 對應：Patient。'
        verbose_name = 'Patient'
        verbose_name_plural = 'Patients'
        indexes = [
            models.Index(fields=['medical_record_number']),
            models.Index(fields=['status']),
            models.Index(fields=['source_system', 'source_record_id']),
        ]

    def __str__(self):
        return f"{self.last_name}{self.first_name}"

    @property
    def age(self):
        if not self.date_of_birth:
            return 0
        today = timezone.now().date()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))


class CareTeamMember(BaseModel):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='care_team')
    name = models.CharField(max_length=200, default='unknown', verbose_name='Member Name')
    identifier = models.CharField(max_length=100, blank=True, default='', verbose_name='Identifier')
    role = models.CharField(max_length=100, default='provider', verbose_name='Role')
    location = models.CharField(max_length=200, blank=True, default='', verbose_name='Location')
    telecom = models.CharField(max_length=100, blank=True, default='', verbose_name='Telecom')
    
    class Meta:
        db_table = 'care_team_members'
        verbose_name = 'Care Team Member'


class Organization(BaseModel):
    name = models.CharField(max_length=200, default='unknown', verbose_name='Organization Name')
    identifier = models.CharField(max_length=100, blank=True, default='', verbose_name='Organization Identifier')
    type = models.CharField(max_length=100, blank=True, default='', verbose_name='Organization Type')
    
    address_line1 = models.CharField(max_length=200, default='', verbose_name='Address Line 1')
    address_line2 = models.CharField(max_length=200, blank=True, default='', verbose_name='Address Line 2')
    city = models.CharField(max_length=100, default='', verbose_name='City')
    state = models.CharField(max_length=100, default='', verbose_name='State')
    postal_code = models.CharField(max_length=20, default='', verbose_name='Postal Code')
    country = models.CharField(max_length=100, default='Taiwan', verbose_name='Country')
    
    class Meta:
        db_table = 'organizations'
        verbose_name = 'Organization'


class Practitioner(BaseModel):
    """醫事人員主檔，可投影為 FHIR Practitioner。"""
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='practitioner_profile')
    identifier = models.CharField(max_length=100, blank=True, default='', verbose_name='Practitioner Identifier')
    npi = models.CharField(max_length=20, blank=True, default='', verbose_name='NPI')
    license_number = models.CharField(max_length=100, blank=True, default='', verbose_name='License Number')
    first_name = models.CharField(max_length=100, verbose_name='First Name')
    last_name = models.CharField(max_length=100, verbose_name='Last Name')
    specialty = models.CharField(max_length=150, blank=True, default='', verbose_name='Specialty')
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True, related_name='practitioners')
    phone = models.CharField(max_length=30, blank=True, default='', verbose_name='Phone')
    email = models.EmailField(blank=True, default='', verbose_name='Email')
    status = models.CharField(max_length=50, default='active', verbose_name='Status')
    metadata_json = models.JSONField(default=dict, blank=True, verbose_name='Metadata')

    class Meta:
        db_table = 'practitioners'
        db_table_comment = '醫師與醫事人員主檔；保存醫師識別、執照、專科與機構資料。FHIR 對應：Practitioner、PractitionerRole。'
        indexes = [
            models.Index(fields=['identifier']),
            models.Index(fields=['npi']),
            models.Index(fields=['status']),
            models.Index(fields=['organization']),
        ]

    def __str__(self):
        return f"{self.last_name} {self.first_name}".strip()


class PatientPractitionerLink(BaseModel):
    """醫病關聯與照護授權。"""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='practitioner_links')
    practitioner = models.ForeignKey(Practitioner, on_delete=models.CASCADE, related_name='patient_links')
    link_type = models.CharField(max_length=50, default='primary_care')
    role = models.CharField(max_length=100, default='primary')
    status = models.CharField(max_length=50, default='active')
    start_at = models.DateTimeField(default=timezone.now)
    end_at = models.DateTimeField(null=True, blank=True)
    permissions_json = models.JSONField(default=dict, blank=True)
    metadata_json = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'patient_practitioner_links'
        db_table_comment = '醫病關聯與資料存取授權；保存照護團隊、授權範圍與期間。FHIR 對應：CareTeam、Consent、PractitionerRole。'
        indexes = [
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['practitioner', 'status']),
            models.Index(fields=['link_type']),
        ]
        unique_together = ['patient', 'practitioner', 'link_type']


class PatientAllergy(BaseModel):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='allergies')
    
    ALLERGY_TYPE_CHOICES = [
        ('medication', 'Medication Allergy'),
        ('drug_class', 'Drug Class Allergy'),
        ('non_medication', 'Non-Medication Allergy'),
    ]
    allergy_type = models.CharField(max_length=50, choices=ALLERGY_TYPE_CHOICES, default='medication', verbose_name='Allergy Type')
    substance = models.CharField(max_length=200, default='unknown', verbose_name='Substance')
    reaction = models.TextField(blank=True, default='', verbose_name='Reaction')
    severity = models.CharField(max_length=50, blank=True, default='', verbose_name='Severity')
    
    class Meta:
        db_table = 'patient_allergies'
        verbose_name = 'Patient Allergy'


class CarePlan(BaseModel):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='care_plans')
    care_plan = models.TextField(default='', verbose_name='Care Plan')
    assessment_and_plan = models.TextField(default='', verbose_name='Assessment and Plan')
    
    status = models.CharField(max_length=50, default='active', verbose_name='Status')
    start_date = models.DateField(default=timezone.now, verbose_name='Start Date')
    title = models.CharField(max_length=200, blank=True, default='', verbose_name='Title')
    category = models.CharField(max_length=100, default='assess-plan', verbose_name='Category')
    intent = models.CharField(max_length=50, default='plan', verbose_name='Intent')
    period_start = models.DateTimeField(null=True, blank=True, verbose_name='Period Start')
    period_end = models.DateTimeField(null=True, blank=True, verbose_name='Period End')
    source_ai_result_id = models.UUIDField(null=True, blank=True, verbose_name='Source AI Result ID')
    goal_json = models.JSONField(default=dict, blank=True, verbose_name='Goals')
    activity_json = models.JSONField(default=list, blank=True, verbose_name='Activities')
    metadata_json = models.JSONField(default=dict, blank=True, verbose_name='Metadata')
    
    class Meta:
        db_table = 'care_plans'
        db_table_comment = '照護計畫；保存疾病風險判讀或醫師建立的追蹤計畫、目標與活動。FHIR 對應：CarePlan。'
        verbose_name = 'Care Plan'
        indexes = [
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['category']),
            models.Index(fields=['source_ai_result_id']),
        ]


class PatientMedication(BaseModel):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medications')
    medication = models.CharField(max_length=200, default='unknown', verbose_name='Medication')
    
    dose_unit_of_measure = models.CharField(max_length=50, blank=True, default='', verbose_name='Dose Unit')
    route_of_administration = models.CharField(max_length=100, blank=True, default='', verbose_name='Route')
    indication = models.CharField(max_length=200, blank=True, default='', verbose_name='Indication')
    dispense_status = models.CharField(max_length=50, default='active', verbose_name='Dispense Status')
    medication_instructions = models.TextField(blank=True, default='', verbose_name='Instructions')
    medication_adherence = models.CharField(max_length=100, blank=True, default='', verbose_name='Adherence')
    
    start_date = models.DateField(null=True, blank=True, verbose_name='Start Date')
    end_date = models.DateField(null=True, blank=True, verbose_name='End Date')
    
    class Meta:
        db_table = 'patient_medications'
        verbose_name = 'Patient Medication'


class MedicalOrder(BaseModel):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medical_orders')
    
    ORDER_TYPE_CHOICES = [
        ('medication', 'Medication Order'),
        ('laboratory', 'Laboratory Order'),
        ('diagnostic_imaging', 'Imaging Order'),
        ('clinical_test', 'Clinical Test Order'),
        ('procedure', 'Procedure Order'),
        ('portable', 'Portable Medical Order'),
    ]
    order_type = models.CharField(max_length=50, choices=ORDER_TYPE_CHOICES, default='medication', verbose_name='Order Type')
    order_detail = models.TextField(default='', verbose_name='Order Details')
    order_date = models.DateTimeField(default=timezone.now, verbose_name='Order Date')
    
    class Meta:
        db_table = 'medical_orders'
        verbose_name = 'Medical Order'


class InsuranceData(BaseModel):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='insurance_info')
    
    coverage_status = models.CharField(max_length=50, default='active', verbose_name='Coverage Status')
    coverage_type = models.CharField(max_length=100, default='health', verbose_name='Coverage Type')
    relationship_to_subscriber = models.CharField(max_length=50, default='self', verbose_name='Relationship')
    member_identifier = models.CharField(max_length=100, default='unknown', verbose_name='Member ID')
    subscriber_identifier = models.CharField(max_length=100, blank=True, verbose_name='Subscriber ID')
    group_identifier = models.CharField(max_length=100, blank=True, verbose_name='Group ID')
    payer_identifier = models.CharField(max_length=100, default='unknown', verbose_name='Payer ID')
    
    class Meta:
        db_table = 'insurance_data'
        verbose_name = 'Insurance Data'


class AdvanceDirective(BaseModel):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='advance_directives')
    
    patient_goals = models.TextField(blank=True, verbose_name='Patient Goals')
    sdoh_goals = models.TextField(blank=True, verbose_name='SDOH Goals')
    advance_directive_observation = models.TextField(blank=True, verbose_name='Advance Directive Observation')
    care_experience_preference = models.TextField(blank=True, verbose_name='Care Experience Preference')
    treatment_intervention_preference = models.TextField(blank=True, verbose_name='Treatment Preference')
    
    class Meta:
        db_table = 'advance_directives'
        verbose_name = 'Advance Directive'


class FamilyHealthHistory(BaseModel):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='family_history')
    
    relationship = models.CharField(max_length=100, verbose_name='Relationship')
    condition = models.CharField(max_length=200, verbose_name='Condition')
    deceased = models.BooleanField(default=False, verbose_name='Deceased')
    age_of_onset = models.IntegerField(null=True, blank=True, verbose_name='Age of Onset')
    
    class Meta:
        db_table = 'family_health_history'
        verbose_name = 'Family Health History'


class MedicalDevice(BaseModel):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medical_devices')
    
    device_name = models.CharField(max_length=200, verbose_name='Device Name')
    udi = models.CharField(max_length=100, verbose_name='UDI')
    implant_date = models.DateField(null=True, blank=True, verbose_name='Implant Date')
    status = models.CharField(max_length=50, default='active', verbose_name='Status')
    
    class Meta:
        db_table = 'medical_devices'
        verbose_name = 'Medical Device'


class PatientDocument(BaseModel):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='clinical_notes')
    
    NOTE_TYPE_CHOICES = [
        ('consultation', 'Consultation Note'),
        ('discharge_summary', 'Discharge Summary'),
        ('emergency', 'Emergency Department Note'),
        ('history_physical', 'History & Physical'),
        ('operative', 'Operative Note'),
        ('procedure', 'Procedure Note'),
        ('progress', 'Progress Note'),
    ]
    note_type = models.CharField(max_length=50, choices=NOTE_TYPE_CHOICES, default='progress', verbose_name='Note Type')
    content = models.TextField(default='', verbose_name='Narrative')
    document_date = models.DateTimeField(default=timezone.now, verbose_name='Date')
    
    class Meta:
        db_table = 'clinical_notes'
        verbose_name = 'Clinical Note'
