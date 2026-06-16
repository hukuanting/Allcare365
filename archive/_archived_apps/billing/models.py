from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
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


class InsuranceProvider(BaseModel):
    """Insurance companies and providers"""
    name = models.CharField(max_length=200)
    type = models.CharField(max_length=50, choices=[
        ('commercial', 'Commercial'),
        ('medicare', 'Medicare'),
        ('medicaid', 'Medicaid'),
        ('workers_comp', 'Workers Compensation'),
        ('auto', 'Auto Insurance'),
        ('self_pay', 'Self Pay'),
        ('other', 'Other'),
    ])
    
    # Contact Information
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    fax = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    
    # Billing Information
    claims_address = models.TextField(blank=True)
    electronic_payer_id = models.CharField(max_length=50, blank=True)
    
    # Terms
    payment_terms_days = models.IntegerField(default=30)
    copay_required = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'insurance_providers'
    
    def __str__(self):
        return self.name


class PatientInsurance(BaseModel):
    """Patient insurance coverage"""
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='insurance_coverage')
    insurance_provider = models.ForeignKey(InsuranceProvider, on_delete=models.CASCADE, related_name='covered_patients')
    
    # Policy Details
    policy_number = models.CharField(max_length=100)
    group_number = models.CharField(max_length=100, blank=True)
    member_id = models.CharField(max_length=100, blank=True)
    
    # Coverage Details
    COVERAGE_TYPE_CHOICES = [
        ('primary', 'Primary'),
        ('secondary', 'Secondary'),
        ('tertiary', 'Tertiary'),
    ]
    coverage_type = models.CharField(max_length=20, choices=COVERAGE_TYPE_CHOICES, default='primary')
    
    # Dates
    effective_date = models.DateField()
    expiration_date = models.DateField(blank=True, null=True)
    
    # Subscriber Information
    subscriber_name = models.CharField(max_length=200, blank=True)
    subscriber_relationship = models.CharField(max_length=50, blank=True)
    subscriber_dob = models.DateField(blank=True, null=True)
    subscriber_id = models.CharField(max_length=100, blank=True)
    
    # Coverage Details
    copay_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    deductible_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    out_of_pocket_max = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    last_verification_date = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'patient_insurance'
        unique_together = ['patient', 'insurance_provider', 'coverage_type']
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.insurance_provider.name} ({self.coverage_type})"


class Invoice(BaseModel):
    """Patient invoices"""
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='invoices')
    appointment = models.ForeignKey('appointments.Appointment', on_delete=models.SET_NULL, null=True, blank=True)
    medical_record = models.ForeignKey('medical_records.MedicalRecord', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Invoice Details
    invoice_number = models.CharField(max_length=50, unique=True)
    invoice_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    
    # Amounts
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    balance_due = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Status
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
        ('voided', 'Voided'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Notes
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'invoices'
        indexes = [
            models.Index(fields=['patient', 'invoice_date']),
            models.Index(fields=['status']),
            models.Index(fields=['due_date']),
        ]
    
    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.patient.full_name}"
    
    def calculate_totals(self):
        """Calculate invoice totals from line items"""
        line_items = self.line_items.all()
        self.subtotal = sum(item.total_amount for item in line_items)
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
        self.balance_due = self.total_amount - self.paid_amount
        self.save()


class InvoiceLineItem(BaseModel):
    """Individual line items on invoices"""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='line_items')
    
    # Service Details
    service_code = models.CharField(max_length=20)  # CPT code
    service_description = models.CharField(max_length=500)
    service_date = models.DateField()
    
    # Pricing
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Modifiers
    modifier_1 = models.CharField(max_length=10, blank=True)
    modifier_2 = models.CharField(max_length=10, blank=True)
    modifier_3 = models.CharField(max_length=10, blank=True)
    
    # Diagnosis
    diagnosis_code = models.CharField(max_length=20, blank=True)  # ICD-10 code
    
    class Meta:
        db_table = 'invoice_line_items'
    
    def save(self, *args, **kwargs):
        """Calculate total amount"""
        self.total_amount = self.quantity * self.unit_price
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.service_code} - {self.service_description}"


class Payment(BaseModel):
    """Patient payments"""
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='payments')
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    
    # Payment Details
    payment_date = models.DateField(default=timezone.now)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Payment Method
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('check', 'Check'),
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('insurance', 'Insurance'),
        ('other', 'Other'),
    ]
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    
    # Payment Reference
    reference_number = models.CharField(max_length=100, blank=True)
    check_number = models.CharField(max_length=50, blank=True)
    
    # Status
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('cleared', 'Cleared'),
        ('bounced', 'Bounced'),
        ('refunded', 'Refunded'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Processing
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        db_table = 'payments'
        indexes = [
            models.Index(fields=['patient', 'payment_date']),
            models.Index(fields=['invoice', 'payment_date']),
        ]
    
    def __str__(self):
        return f"Payment {self.amount} - {self.patient.full_name}"


class InsuranceClaim(BaseModel):
    """Insurance claims"""
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='insurance_claims')
    insurance_provider = models.ForeignKey(InsuranceProvider, on_delete=models.CASCADE, related_name='claims')
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='insurance_claims')
    
    # Claim Details
    claim_number = models.CharField(max_length=100, unique=True)
    claim_date = models.DateField(default=timezone.now)
    
    # Service Details
    service_date_from = models.DateField()
    service_date_to = models.DateField()
    place_of_service = models.CharField(max_length=10)
    
    # Amounts
    billed_amount = models.DecimalField(max_digits=10, decimal_places=2)
    allowed_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    patient_responsibility = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    # Status
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('denied', 'Denied'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Processing
    submission_date = models.DateTimeField(blank=True, null=True)
    response_date = models.DateTimeField(blank=True, null=True)
    
    # Notes
    notes = models.TextField(blank=True)
    denial_reason = models.TextField(blank=True)
    
    class Meta:
        db_table = 'insurance_claims'
        indexes = [
            models.Index(fields=['patient', 'claim_date']),
            models.Index(fields=['insurance_provider', 'claim_date']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Claim {self.claim_number} - {self.patient.full_name}"


class BillingCode(BaseModel):
    """Billing codes (CPT, HCPCS, etc.)"""
    code = models.CharField(max_length=20, unique=True)
    code_type = models.CharField(max_length=20, choices=[
        ('cpt', 'CPT'),
        ('hcpcs', 'HCPCS'),
        ('icd10', 'ICD-10'),
        ('revenue', 'Revenue Code'),
    ])
    description = models.TextField()
    
    # Pricing
    default_fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    # Validity
    effective_date = models.DateField(blank=True, null=True)
    expiration_date = models.DateField(blank=True, null=True)
    
    # Categories
    category = models.CharField(max_length=200, blank=True)
    subcategory = models.CharField(max_length=200, blank=True)
    
    # Billing Properties
    is_billable = models.BooleanField(default=True)
    requires_modifier = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'billing_codes'
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['code_type']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.description}"


class FeeSchedule(BaseModel):
    """Fee schedules for different insurance providers"""
    insurance_provider = models.ForeignKey(InsuranceProvider, on_delete=models.CASCADE, related_name='fee_schedules')
    billing_code = models.ForeignKey(BillingCode, on_delete=models.CASCADE, related_name='fee_schedules')
    
    # Fee Details
    fee_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Validity
    effective_date = models.DateField()
    expiration_date = models.DateField(blank=True, null=True)
    
    # Modifiers
    modifier_1 = models.CharField(max_length=10, blank=True)
    modifier_2 = models.CharField(max_length=10, blank=True)
    
    class Meta:
        db_table = 'fee_schedules'
        unique_together = ['insurance_provider', 'billing_code', 'effective_date']
    
    def __str__(self):
        return f"{self.billing_code.code} - {self.insurance_provider.name}: ${self.fee_amount}"


class BillingReport(BaseModel):
    """Billing reports and analytics"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Report Parameters
    report_type = models.CharField(max_length=50, choices=[
        ('revenue', 'Revenue Report'),
        ('outstanding', 'Outstanding Balances'),
        ('aging', 'Aging Report'),
        ('insurance', 'Insurance Report'),
        ('provider', 'Provider Report'),
        ('custom', 'Custom Report'),
    ])
    
    # Date Range
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Filters
    provider_filter = models.ForeignKey('administration.Provider', on_delete=models.SET_NULL, null=True, blank=True)
    insurance_filter = models.ForeignKey(InsuranceProvider, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Report Data
    report_data = models.JSONField(blank=True, null=True)
    
    # Status
    STATUS_CHOICES = [
        ('generating', 'Generating'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='generating')
    
    # Generated By
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    generation_date = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'billing_reports'
        indexes = [
            models.Index(fields=['generated_by', 'generation_date']),
            models.Index(fields=['report_type']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.generation_date.strftime('%Y-%m-%d')}"


class ArSession(BaseModel):
    """Accounts Receivable Session for batch processing payments and adjustments"""
    
    session_name = models.CharField(max_length=100, verbose_name='會話名稱')
    session_date = models.DateTimeField(default=timezone.now, verbose_name='會話日期')
    provider = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                related_name='ar_sessions', verbose_name='處理人員')
    
    SESSION_STATUS_CHOICES = [
        ('open', '開放中'),
        ('closed', '已關閉'),
        ('posted', '已過帳'),
        ('cancelled', '已取消'),
    ]
    status = models.CharField(max_length=20, choices=SESSION_STATUS_CHOICES, 
                             default='open', verbose_name='狀態')
    
    # Session totals
    total_payments = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='總付款金額')
    total_adjustments = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='總調整金額')
    total_writeoffs = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='總沖銷金額')
    
    # Session metadata
    notes = models.TextField(blank=True, verbose_name='備註')
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name='關閉時間')
    posted_at = models.DateTimeField(null=True, blank=True, verbose_name='過帳時間')
    
    class Meta:
        verbose_name = 'AR會話'
        verbose_name_plural = 'AR會話'
        ordering = ['-session_date']
        indexes = [
            models.Index(fields=['provider', '-session_date']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.session_name} - {self.session_date.strftime('%Y-%m-%d')}"
    
    @property
    def total_transactions(self):
        """Calculate total transaction amount"""
        return self.total_payments + self.total_adjustments + self.total_writeoffs
    
    def close_session(self):
        """Close the AR session"""
        if self.status == 'open':
            self.status = 'closed'
            self.closed_at = timezone.now()
            self.save()
    
    def post_session(self):
        """Post the AR session"""
        if self.status == 'closed':
            self.status = 'posted'
            self.posted_at = timezone.now()
            self.save()


class ArActivity(BaseModel):
    """Individual activities within an AR Session (payments, adjustments, writeoffs)"""
    
    ar_session = models.ForeignKey(ArSession, on_delete=models.CASCADE, 
                                  related_name='activities', verbose_name='AR會話')
    billing_record = models.ForeignKey(Invoice, on_delete=models.CASCADE, 
                                      related_name='ar_activities', verbose_name='計費記錄')
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, 
                               related_name='ar_activities', verbose_name='患者')
    
    ACTIVITY_TYPE_CHOICES = [
        ('payment', '付款'),
        ('adjustment', '調整'),
        ('writeoff', '沖銷'),
        ('refund', '退款'),
        ('transfer', '轉帳'),
    ]
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPE_CHOICES, verbose_name='活動類型')
    
    # Amount details
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='金額')
    
    REASON_CHOICES = [
        ('patient_payment', '患者付款'),
        ('insurance_payment', '保險給付'),
        ('admin_adjustment', '管理調整'),
        ('billing_error', '計費錯誤'),
        ('uncollectible', '無法收回'),
        ('charity_care', '慈善醫療'),
        ('contractual_adjustment', '合約調整'),
        ('other', '其他'),
    ]
    reason = models.CharField(max_length=50, choices=REASON_CHOICES, verbose_name='原因')
    
    # Payment details (for payment type activities)
    PAYMENT_METHOD_CHOICES = [
        ('cash', '現金'),
        ('check', '支票'),
        ('credit_card', '信用卡'),
        ('debit_card', '金融卡'),
        ('bank_transfer', '銀行轉帳'),
        ('insurance', '保險給付'),
        ('other', '其他'),
    ]
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, 
                                     blank=True, verbose_name='付款方式')
    reference_number = models.CharField(max_length=100, blank=True, verbose_name='參考號碼')
    
    # Activity metadata
    notes = models.TextField(blank=True, verbose_name='備註')
    activity_date = models.DateTimeField(default=timezone.now, verbose_name='活動日期')
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='ar_activities_processed', verbose_name='處理人員')
    
    class Meta:
        verbose_name = 'AR活動'
        verbose_name_plural = 'AR活動'
        ordering = ['-activity_date']
        indexes = [
            models.Index(fields=['ar_session', '-activity_date']),
            models.Index(fields=['patient', '-activity_date']),
            models.Index(fields=['activity_type']),
            models.Index(fields=['processed_by', '-activity_date']),
        ]
    
    def __str__(self):
        return f"{self.get_activity_type_display()} - {self.patient} - ${self.amount}"
    
    def save(self, *args, **kwargs):
        """Override save to update AR session totals"""
        super().save(*args, **kwargs)
        
        # Update AR session totals
        if self.ar_session:
            session = self.ar_session
            activities = session.activities.all()
            
            session.total_payments = sum(
                activity.amount for activity in activities 
                if activity.activity_type == 'payment'
            )
            session.total_adjustments = sum(
                activity.amount for activity in activities 
                if activity.activity_type == 'adjustment'
            )
            session.total_writeoffs = sum(
                activity.amount for activity in activities 
                if activity.activity_type == 'writeoff'
            )
            
            session.save()
