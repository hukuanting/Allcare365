"""
Template views for Billing module
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import (
    InsuranceProvider, PatientInsurance, Invoice, InvoiceLineItem,
    Payment, InsuranceClaim, BillingCode, FeeSchedule
)
from patients.models import Patient


@login_required
def billing_management(request):
    """帳務管理主頁"""
    context = {
        'page_title': '帳務管理',
        'active_menu': 'billing'
    }
    return render(request, 'billing/billing_management.html', context)


@login_required
def invoice_list_view(request):
    """發票列表視圖"""
    # 獲取過濾參數
    status = request.GET.get('status', '')
    patient = request.GET.get('patient', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search = request.GET.get('search', '')
    
    # 基礎查詢
    invoices = Invoice.objects.select_related('patient').order_by('-invoice_date', '-created_at')
    
    # 應用過濾器
    if status:
        invoices = invoices.filter(status=status)
    if patient:
        invoices = invoices.filter(patient_id=patient)
    if date_from:
        invoices = invoices.filter(invoice_date__gte=date_from)
    if date_to:
        invoices = invoices.filter(invoice_date__lte=date_to)
    if search:
        invoices = invoices.filter(
            Q(invoice_number__icontains=search) |
            Q(patient__first_name__icontains=search) |
            Q(patient__last_name__icontains=search)
        )
    
    # 分頁
    paginator = Paginator(invoices, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 準備選項數據
    patients = Patient.objects.filter(is_active=True).order_by('last_name', 'first_name')
    
    context = {
        'invoices': page_obj,
        'patients': patients,
        'current_filters': {
            'status': status,
            'patient': patient,
            'date_from': date_from,
            'date_to': date_to,
            'search': search,
        }
    }
    
    return render(request, 'billing/invoice_list.html', context)


@login_required
def invoice_detail_view(request, invoice_id):
    """發票詳情視圖"""
    invoice = get_object_or_404(
        Invoice.objects.select_related('patient').prefetch_related(
            'line_items', 'payments', 'insurance_claims'
        ),
        id=invoice_id
    )
    
    context = {
        'invoice': invoice,
        'page_title': f'發票詳情 - {invoice.invoice_number}',
        'active_menu': 'billing'
    }
    
    return render(request, 'billing/invoice_detail.html', context)


@login_required
def invoice_create_view(request):
    """創建發票視圖"""
    # 獲取患者ID（可能從URL參數傳入）
    patient_id = request.GET.get('patient_id')
    patient = None
    if patient_id:
        patient = get_object_or_404(Patient, id=patient_id)
    
    # 準備表單選項數據
    patients = Patient.objects.filter(is_active=True).order_by('last_name', 'first_name')
    billing_codes = BillingCode.objects.filter(is_active=True).order_by('code')
    
    context = {
        'patients': patients,
        'billing_codes': billing_codes,
        'selected_patient': patient,
        'page_title': '新增發票',
        'active_menu': 'billing'
    }
    
    return render(request, 'billing/invoice_create.html', context)


@login_required
def payment_list_view(request):
    """付款記錄列表視圖"""
    # 獲取過濾參數
    method = request.GET.get('method', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search = request.GET.get('search', '')
    
    # 基礎查詢
    payments = Payment.objects.select_related('invoice', 'invoice__patient').order_by('-payment_date', '-created_at')
    
    # 應用過濾器
    if method:
        payments = payments.filter(payment_method=method)
    if date_from:
        payments = payments.filter(payment_date__gte=date_from)
    if date_to:
        payments = payments.filter(payment_date__lte=date_to)
    if search:
        payments = payments.filter(
            Q(transaction_id__icontains=search) |
            Q(invoice__invoice_number__icontains=search) |
            Q(invoice__patient__first_name__icontains=search) |
            Q(invoice__patient__last_name__icontains=search)
        )
    
    # 分頁
    paginator = Paginator(payments, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'payments': page_obj,
        'current_filters': {
            'method': method,
            'date_from': date_from,
            'date_to': date_to,
            'search': search,
        }
    }
    
    return render(request, 'billing/payment_list.html', context)


@login_required
def insurance_management_view(request):
    """保險管理視圖"""
    # 獲取過濾參數
    provider_type = request.GET.get('type', '')
    search = request.GET.get('search', '')
    
    # 保險公司查詢
    insurance_providers = InsuranceProvider.objects.filter(is_active=True)
    
    if provider_type:
        insurance_providers = insurance_providers.filter(type=provider_type)
    if search:
        insurance_providers = insurance_providers.filter(
            Q(name__icontains=search) |
            Q(electronic_payer_id__icontains=search)
        )
    
    insurance_providers = insurance_providers.order_by('name')
    
    # 患者保險查詢
    patient_insurances = PatientInsurance.objects.select_related(
        'patient', 'insurance_provider'
    ).filter(is_active=True).order_by('-updated_at')[:10]
    
    context = {
        'insurance_providers': insurance_providers,
        'patient_insurances': patient_insurances,
        'current_filters': {
            'type': provider_type,
            'search': search,
        },
        'page_title': '保險管理',
        'active_menu': 'billing'
    }
    
    return render(request, 'billing/insurance_management.html', context)


@login_required
def billing_reports_view(request):
    """帳務報告視圖"""
    context = {
        'page_title': '帳務報告',
        'active_menu': 'billing'
    }
    return render(request, 'billing/billing_reports.html', context)


@login_required
def billing_stats_api(request):
    """帳務統計API"""
    # 計算統計數據
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # 基礎統計
    total_invoices = Invoice.objects.count()
    total_revenue = Invoice.objects.aggregate(
        total=Sum('total_amount')
    )['total'] or Decimal('0')
    
    pending_amount = Invoice.objects.filter(
        status__in=['pending', 'partially_paid']
    ).aggregate(
        total=Sum('outstanding_amount')
    )['total'] or Decimal('0')
    
    month_revenue = Invoice.objects.filter(
        invoice_date__gte=month_ago
    ).aggregate(
        total=Sum('total_amount')
    )['total'] or Decimal('0')
    
    # 狀態統計
    status_stats = Invoice.objects.values('status').annotate(
        count=Count('id'),
        amount=Sum('total_amount')
    ).order_by('-count')
    
    # 付款方式統計
    payment_method_stats = Payment.objects.values('payment_method').annotate(
        count=Count('id'),
        amount=Sum('amount')
    ).order_by('-amount')
    
    # 保險公司統計
    insurance_stats = PatientInsurance.objects.select_related('insurance_provider').values(
        'insurance_provider__name'
    ).annotate(count=Count('id')).order_by('-count')[:5]
    
    # 每日收入趨勢
    daily_stats = []
    for i in range(30):
        date = today - timedelta(days=i)
        amount = Invoice.objects.filter(invoice_date=date).aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0')
        daily_stats.append({
            'date': date.strftime('%Y-%m-%d'),
            'amount': float(amount)
        })
    daily_stats.reverse()
    
    stats = {
        'overview': {
            'total_invoices': total_invoices,
            'total_revenue': float(total_revenue),
            'pending_amount': float(pending_amount),
            'month_revenue': float(month_revenue),
            'collection_rate': round(
                (float(total_revenue - pending_amount) / max(float(total_revenue), 1)) * 100, 1
            ) if total_revenue > 0 else 0
        },
        'status_distribution': [
            {
                'status': item['status'],
                'count': item['count'],
                'amount': float(item['amount'] or 0)
            } for item in status_stats
        ],
        'payment_methods': [
            {
                'method': item['payment_method'],
                'count': item['count'],
                'amount': float(item['amount'] or 0)
            } for item in payment_method_stats
        ],
        'insurance_distribution': list(insurance_stats),
        'daily_revenue': daily_stats
    }
    
    return JsonResponse(stats)


@login_required
def patient_billing_view(request, patient_id):
    """患者帳務視圖"""
    patient = get_object_or_404(Patient, id=patient_id)
    
    # 獲取患者的發票
    invoices = Invoice.objects.filter(patient=patient).order_by('-invoice_date')
    
    # 獲取患者的付款記錄
    payments = Payment.objects.filter(invoice__patient=patient).order_by('-payment_date')
    
    # 獲取患者的保險資訊
    insurances = PatientInsurance.objects.filter(
        patient=patient, is_active=True
    ).select_related('insurance_provider')
    
    # 計算患者帳務摘要
    total_billed = invoices.aggregate(
        total=Sum('total_amount')
    )['total'] or Decimal('0')
    
    total_paid = payments.aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')
    
    outstanding = total_billed - total_paid
    
    context = {
        'patient': patient,
        'invoices': invoices,
        'payments': payments,
        'insurances': insurances,
        'billing_summary': {
            'total_billed': total_billed,
            'total_paid': total_paid,
            'outstanding': outstanding
        },
        'page_title': f'患者帳務 - {patient.first_name} {patient.last_name}',
        'active_menu': 'billing'
    }
    
    return render(request, 'billing/patient_billing.html', context)
