from rest_framework import serializers
from django.utils import timezone
from decimal import Decimal
from .models import (
    InsuranceProvider, PatientInsurance, Invoice, InvoiceLineItem,
    Payment, InsuranceClaim, BillingCode, FeeSchedule
)
from patients.models import Patient
from administration.models import Provider, Facility


class InsuranceProviderSerializer(serializers.ModelSerializer):
    """保險公司序列化器"""
    
    class Meta:
        model = InsuranceProvider
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class PatientInsuranceSerializer(serializers.ModelSerializer):
    """病患保險序列化器"""
    insurance_provider_name = serializers.CharField(source='insurance_provider.name', read_only=True)
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    is_active_display = serializers.BooleanField(source='is_active', read_only=True)
    
    class Meta:
        model = PatientInsurance
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def validate(self, data):
        """驗證保險資料"""
        if data.get('effective_date') and data.get('expiration_date'):
            if data['expiration_date'] <= data['effective_date']:
                raise serializers.ValidationError("到期日期必須晚於生效日期")
        
        return data


class InvoiceLineItemSerializer(serializers.ModelSerializer):
    """發票項目序列化器"""
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = InvoiceLineItem
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def validate(self, data):
        """驗證發票項目"""
        if data.get('quantity') and data['quantity'] <= 0:
            raise serializers.ValidationError("數量必須大於0")
        
        if data.get('unit_price') and data['unit_price'] <= 0:
            raise serializers.ValidationError("單價必須大於0")
        
        return data


class InvoiceSerializer(serializers.ModelSerializer):
    """發票序列化器"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    provider_name = serializers.CharField(source='provider.get_full_name', read_only=True)
    facility_name = serializers.CharField(source='facility.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Invoice
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'invoice_number')
    
    def validate(self, data):
        """驗證發票資料"""
        if data.get('due_date') and data.get('invoice_date'):
            if data['due_date'] <= data['invoice_date']:
                raise serializers.ValidationError("到期日期必須晚於發票日期")
        
        return data


class InvoiceDetailSerializer(serializers.ModelSerializer):
    """發票詳細序列化器"""
    patient = serializers.StringRelatedField(read_only=True)
    provider = serializers.StringRelatedField(read_only=True)
    facility = serializers.StringRelatedField(read_only=True)
    items = InvoiceLineItemSerializer(many=True, read_only=True)
    payments = serializers.SerializerMethodField()
    balance_due = serializers.SerializerMethodField()
    
    class Meta:
        model = Invoice
        fields = '__all__'
    
    def get_payments(self, obj):
        """獲取付款記錄"""
        payments = obj.payments.all()
        return PaymentSerializer(payments, many=True).data
    
    def get_balance_due(self, obj):
        """計算欠款餘額"""
        total_paid = sum(payment.amount for payment in obj.payments.all())
        return obj.total_amount - total_paid


class PaymentSerializer(serializers.ModelSerializer):
    """付款序列化器"""
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    patient_name = serializers.CharField(source='invoice.patient.get_full_name', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def validate(self, data):
        """驗證付款資料"""
        if data.get('amount') and data['amount'] <= 0:
            raise serializers.ValidationError("付款金額必須大於0")
        
        # 檢查付款金額是否超過發票餘額
        if data.get('invoice') and data.get('amount'):
            invoice = data['invoice']
            total_paid = sum(payment.amount for payment in invoice.payments.all())
            balance_due = invoice.total_amount - total_paid
            
            if data['amount'] > balance_due:
                raise serializers.ValidationError("付款金額超過發票餘額")
        
        return data


class InsuranceClaimSerializer(serializers.ModelSerializer):
    """保險理賠序列化器"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    insurance_provider_name = serializers.CharField(source='insurance_provider.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = InsuranceClaim
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'claim_number')
    
    def validate(self, data):
        """驗證理賠資料"""
        if data.get('claim_amount') and data['claim_amount'] <= 0:
            raise serializers.ValidationError("理賠金額必須大於0")
        
        if data.get('approved_amount') and data['approved_amount'] < 0:
            raise serializers.ValidationError("批准金額不能為負數")
        
        return data


class BillingCodeSerializer(serializers.ModelSerializer):
    """計費代碼序列化器"""
    
    class Meta:
        model = BillingCode
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def validate_code(self, value):
        """驗證代碼格式"""
        if not value.replace('.', '').replace('-', '').isalnum():
            raise serializers.ValidationError("代碼格式無效")
        return value


class FeeScheduleSerializer(serializers.ModelSerializer):
    """費用表序列化器"""
    billing_code_display = serializers.CharField(source='billing_code.code', read_only=True)
    
    class Meta:
        model = FeeSchedule
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def validate(self, data):
        """驗證費用表資料"""
        if data.get('fee_amount') and data['fee_amount'] <= 0:
            raise serializers.ValidationError("費用金額必須大於0")
        
        if data.get('effective_date') and data.get('expiration_date'):
            if data['expiration_date'] <= data['effective_date']:
                raise serializers.ValidationError("到期日期必須晚於生效日期")
        
        return data


class BillingStatisticsSerializer(serializers.Serializer):
    """計費統計序列化器"""
    total_invoices = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_payments = serializers.DecimalField(max_digits=15, decimal_places=2)
    outstanding_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    invoices_by_status = serializers.ListField()
    payments_by_method = serializers.ListField()
    monthly_revenue = serializers.ListField()
    top_billing_codes = serializers.ListField()
    insurance_claims_summary = serializers.ListField()
    aging_report = serializers.ListField()


class PatientBillingSerializer(serializers.Serializer):
    """病患計費序列化器"""
    patient_info = serializers.DictField()
    total_invoices = serializers.IntegerField()
    total_billed = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_paid = serializers.DecimalField(max_digits=15, decimal_places=2)
    outstanding_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    recent_invoices = serializers.ListField()
    recent_payments = serializers.ListField()
    insurance_info = serializers.ListField()
    outstanding_invoices = serializers.ListField()


class RevenueSummarySerializer(serializers.Serializer):
    """收入摘要序列化器"""
    period = serializers.CharField()
    total_revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    cash_payments = serializers.DecimalField(max_digits=15, decimal_places=2)
    card_payments = serializers.DecimalField(max_digits=15, decimal_places=2)
    check_payments = serializers.DecimalField(max_digits=15, decimal_places=2)
    insurance_payments = serializers.DecimalField(max_digits=15, decimal_places=2)
    invoice_count = serializers.IntegerField()
    payment_count = serializers.IntegerField()
    average_invoice_amount = serializers.DecimalField(max_digits=10, decimal_places=2)


class AgingReportSerializer(serializers.Serializer):
    """帳齡報告序列化器"""
    patient_name = serializers.CharField()
    invoice_number = serializers.CharField()
    invoice_date = serializers.DateField()
    due_date = serializers.DateField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    balance_due = serializers.DecimalField(max_digits=10, decimal_places=2)
    days_overdue = serializers.IntegerField()
    aging_category = serializers.CharField()
