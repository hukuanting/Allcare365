"""
Pharmacy module template views for web interface.
Provides HTML views for pharmacy management, prescriptions, and inventory.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Sum, F
from django.utils import timezone
from django.core.paginator import Paginator
from .models import (
    Drug, DrugCategory, Prescription, PrescriptionRefill, 
    DrugInventory, InventoryTransaction
)
from patients.models import Patient


@login_required
def pharmacy_dashboard(request):
    """藥房管理主頁"""
    context = {
        'title': '藥房管理系統',
        'total_drugs': Drug.objects.filter(is_active=True).count(),
        'total_prescriptions': Prescription.objects.filter(is_active=True).count(),
        'pending_prescriptions': Prescription.objects.filter(status='pending').count(),
        'low_stock_items': DrugInventory.objects.filter(quantity_on_hand__lte=10).count(),
        'recent_prescriptions': Prescription.objects.filter(is_active=True).order_by('-created_at')[:10],
        'low_stock_drugs': DrugInventory.objects.filter(quantity_on_hand__lte=10).select_related('drug')[:10],
    }
    return render(request, 'pharmacy/pharmacy_dashboard.html', context)


@login_required
def drug_list(request):
    """藥物主檔列表"""
    drugs = Drug.objects.filter(is_active=True).select_related('category').order_by('name')
    
    # 搜尋和篩選
    search_query = request.GET.get('search')
    category_filter = request.GET.get('category')
    form_filter = request.GET.get('form')
    
    if search_query:
        drugs = drugs.filter(
            Q(name__icontains=search_query) |
            Q(generic_name__icontains=search_query) |
            Q(manufacturer__icontains=search_query)
        )
    
    if category_filter:
        drugs = drugs.filter(category_id=category_filter)
        
    if form_filter:
        drugs = drugs.filter(dosage_form=form_filter)
    
    # 分頁
    paginator = Paginator(drugs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'title': '藥物主檔',
        'page_obj': page_obj,
        'search_query': search_query,
        'category_filter': category_filter,
        'form_filter': form_filter,
        'categories': DrugCategory.objects.filter(is_active=True),
        'dosage_forms': Drug.DOSAGE_FORM_CHOICES,
    }
    return render(request, 'pharmacy/drug_list.html', context)


@login_required
def drug_detail(request, drug_id):
    """藥物詳情"""
    drug = get_object_or_404(Drug, id=drug_id, is_active=True)
    
    # 獲取庫存資訊
    try:
        inventory = DrugInventory.objects.get(drug=drug)
    except DrugInventory.DoesNotExist:
        inventory = None
    
    # 獲取最近的庫存異動
    recent_transactions = InventoryTransaction.objects.filter(
        drug_inventory__drug=drug
    ).order_by('-created_at')[:10]
    
    context = {
        'title': f'藥物詳情 - {drug.name}',
        'drug': drug,
        'inventory': inventory,
        'recent_transactions': recent_transactions,
    }
    return render(request, 'pharmacy/drug_detail.html', context)


@login_required
def prescription_list(request):
    """處方籤列表"""
    prescriptions = Prescription.objects.filter(is_active=True).select_related(
        'patient', 'provider', 'drug'
    ).order_by('-created_at')
    
    # 搜尋和篩選
    search_query = request.GET.get('search')
    status_filter = request.GET.get('status')
    
    if search_query:
        prescriptions = prescriptions.filter(
            Q(patient__first_name__icontains=search_query) |
            Q(patient__last_name__icontains=search_query) |
            Q(drug__name__icontains=search_query)
        )
    
    if status_filter:
        prescriptions = prescriptions.filter(status=status_filter)
    
    # 分頁
    paginator = Paginator(prescriptions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 狀態選項
    status_choices = [
        ('pending', 'Pending'),
        ('dispensed', 'Dispensed'),
        ('cancelled', 'Cancelled'),
        ('on_hold', 'On Hold'),
    ]
    
    context = {
        'title': '處方籤管理',
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'status_choices': status_choices,
    }
    return render(request, 'pharmacy/prescription_list.html', context)


@login_required
def prescription_detail(request, prescription_id):
    """處方籤詳情"""
    prescription = get_object_or_404(Prescription, id=prescription_id, is_active=True)
    
    # 獲取續藥記錄
    refills = PrescriptionRefill.objects.filter(
        prescription=prescription
    ).order_by('-refill_date')
    
    context = {
        'title': f'處方籤詳情 - {prescription.drug.name}',
        'prescription': prescription,
        'refills': refills,
    }
    return render(request, 'pharmacy/prescription_detail.html', context)


@login_required
def inventory_management(request):
    """庫存管理"""
    inventories = DrugInventory.objects.filter(is_active=True).select_related('drug').order_by('drug__name')
    
    # 搜尋和篩選
    search_query = request.GET.get('search')
    stock_filter = request.GET.get('stock')
    
    if search_query:
        inventories = inventories.filter(
            Q(drug__name__icontains=search_query) |
            Q(drug__generic_name__icontains=search_query)
        )
    
    if stock_filter == 'low':
        inventories = inventories.filter(quantity_on_hand__lte=10)
    elif stock_filter == 'out':
        inventories = inventories.filter(quantity_on_hand=0)
    
    # 分頁
    paginator = Paginator(inventories, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'title': '庫存管理',
        'page_obj': page_obj,
        'search_query': search_query,
        'stock_filter': stock_filter,
    }
    return render(request, 'pharmacy/inventory_management.html', context)


@login_required
def drug_categories(request):
    """藥物分類管理"""
    categories = DrugCategory.objects.filter(is_active=True).annotate(
        drug_count=Count('drug')
    ).order_by('name')
    
    context = {
        'title': '藥物分類管理',
        'categories': categories,
    }
    return render(request, 'pharmacy/drug_categories.html', context)


@login_required
def pharmacy_reports(request):
    """藥房報告"""
    # 統計資料
    total_drugs = Drug.objects.filter(is_active=True).count()
    total_prescriptions = Prescription.objects.filter(is_active=True).count()
    pending_prescriptions = Prescription.objects.filter(status='pending').count()
    low_stock_count = DrugInventory.objects.filter(quantity_on_hand__lte=10).count()
    
    # 最常開立的藥物
    top_prescribed = Prescription.objects.values('drug__name').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # 庫存價值統計
    inventory_value = DrugInventory.objects.aggregate(
        total_value=Sum(F('quantity_on_hand') * F('unit_cost'))
    )
    
    context = {
        'title': '藥房報告',
        'total_drugs': total_drugs,
        'total_prescriptions': total_prescriptions,
        'pending_prescriptions': pending_prescriptions,
        'low_stock_count': low_stock_count,
        'top_prescribed': top_prescribed,
        'inventory_value': inventory_value,
    }
    return render(request, 'pharmacy/pharmacy_reports.html', context)


@login_required
def patient_medication_history(request, patient_id):
    """病患用藥記錄"""
    patient = get_object_or_404(Patient, id=patient_id, is_active=True)
    
    # 獲取病患的處方記錄
    prescriptions = Prescription.objects.filter(
        patient=patient, is_active=True
    ).select_related('drug', 'provider').order_by('-created_at')
    
    # 分頁
    paginator = Paginator(prescriptions, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'title': f'{patient.first_name} {patient.last_name} - 用藥記錄',
        'patient': patient,
        'page_obj': page_obj,
    }
    return render(request, 'pharmacy/patient_medication_history.html', context)
