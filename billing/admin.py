from django.contrib import admin
from .models import (
    InsuranceProvider, PatientInsurance, Invoice, InvoiceLineItem,
    Payment, InsuranceClaim, BillingCode, FeeSchedule, BillingReport,
    ArSession, ArActivity
)


@admin.register(InsuranceProvider)
class InsuranceProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'phone', 'email', 'is_active']
    list_filter = ['type', 'is_active']
    search_fields = ['name', 'email', 'phone']


@admin.register(PatientInsurance)
class PatientInsuranceAdmin(admin.ModelAdmin):
    list_display = ['patient', 'insurance_provider', 'policy_number', 'coverage_type', 'is_active']
    list_filter = ['insurance_provider', 'coverage_type', 'is_active']
    search_fields = ['patient__first_name', 'patient__last_name', 'policy_number']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'patient', 'total_amount', 'balance_due', 'status', 'invoice_date']
    list_filter = ['status', 'invoice_date', 'due_date']
    search_fields = ['invoice_number', 'patient__first_name', 'patient__last_name']
    readonly_fields = ['invoice_number', 'total_amount', 'balance_due']


@admin.register(InvoiceLineItem)
class InvoiceLineItemAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'service_code', 'service_description', 'quantity', 'unit_price', 'total_amount']
    list_filter = ['invoice__status', 'created_at']
    search_fields = ['invoice__invoice_number', 'service_code', 'service_description']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'amount', 'payment_method', 'payment_date', 'status']
    list_filter = ['payment_method', 'status', 'payment_date']
    search_fields = ['invoice__invoice_number', 'reference_number']


@admin.register(InsuranceClaim)
class InsuranceClaimAdmin(admin.ModelAdmin):
    list_display = ['claim_number', 'patient', 'insurance_provider', 'billed_amount', 'status', 'submission_date']
    list_filter = ['status', 'submission_date', 'insurance_provider']
    search_fields = ['claim_number', 'patient__first_name', 'patient__last_name']


@admin.register(BillingCode)
class BillingCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'description', 'default_fee', 'code_type', 'is_active']
    list_filter = ['code_type', 'is_active']
    search_fields = ['code', 'description']


@admin.register(FeeSchedule)
class FeeScheduleAdmin(admin.ModelAdmin):
    list_display = ['billing_code', 'insurance_provider', 'fee_amount', 'effective_date', 'expiration_date']
    list_filter = ['insurance_provider', 'effective_date']
    search_fields = ['billing_code__code', 'insurance_provider__name']


@admin.register(BillingReport)
class BillingReportAdmin(admin.ModelAdmin):
    list_display = ['name', 'report_type', 'generated_by', 'generation_date']
    list_filter = ['report_type', 'generation_date']
    search_fields = ['name', 'generated_by__username']


@admin.register(ArSession)
class ArSessionAdmin(admin.ModelAdmin):
    list_display = ['session_name', 'session_date', 'provider', 'status', 'total_transactions']
    list_filter = ['status', 'session_date', 'provider']
    search_fields = ['session_name', 'provider__username']
    readonly_fields = ['total_payments', 'total_adjustments', 'total_writeoffs', 'total_transactions']
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('session_name', 'session_date', 'provider', 'status')
        }),
        ('金額統計', {
            'fields': ('total_payments', 'total_adjustments', 'total_writeoffs'),
            'classes': ('collapse',)
        }),
        ('時間戳記', {
            'fields': ('closed_at', 'posted_at'),
            'classes': ('collapse',)
        }),
        ('備註', {
            'fields': ('notes',)
        })
    )


@admin.register(ArActivity)
class ArActivityAdmin(admin.ModelAdmin):
    list_display = ['ar_session', 'patient', 'activity_type', 'amount', 'reason', 'activity_date']
    list_filter = ['activity_type', 'reason', 'payment_method', 'activity_date']
    search_fields = ['patient__first_name', 'patient__last_name', 'reference_number']
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('ar_session', 'billing_record', 'patient', 'activity_type', 'amount')
        }),
        ('詳細資訊', {
            'fields': ('reason', 'payment_method', 'reference_number', 'activity_date', 'processed_by')
        }),
        ('備註', {
            'fields': ('notes',)
        })
    )
