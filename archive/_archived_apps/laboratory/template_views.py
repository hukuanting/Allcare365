"""
Laboratory module template views for web interface.
Provides HTML views for laboratory management, test orders, and results.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from django.core.paginator import Paginator
from .models import (
    LabProvider, LabTestCategory, LabTestType, 
    LabOrder, LabOrderItem, LabResult
)
from patients.models import Patient


@login_required
def laboratory_dashboard(request):
    """實驗室管理主頁"""
    context = {
        'title': '實驗室管理系統',
        'recent_orders': LabOrder.objects.filter(is_active=True).order_by('-created_at')[:10],
        'pending_results': LabResult.objects.filter(result_status='preliminary').count(),
        'total_orders': LabOrder.objects.filter(is_active=True).count(),
        'total_tests': LabTestType.objects.filter(is_active=True).count(),
        'active_providers': LabProvider.objects.filter(is_active=True).count(),
    }
    return render(request, 'laboratory/laboratory_dashboard.html', context)


@login_required
def lab_order_list(request):
    """檢驗申請單列表"""
    orders = LabOrder.objects.filter(is_active=True).order_by('-created_at')
    
    # 搜尋和篩選
    search_query = request.GET.get('search')
    status_filter = request.GET.get('status')
    
    if search_query:
        orders = orders.filter(
            Q(order_number__icontains=search_query) |
            Q(patient__first_name__icontains=search_query) |
            Q(patient__last_name__icontains=search_query)
        )
    
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    # 分頁
    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'title': '檢驗申請單',
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'status_choices': LabOrder.STATUS_CHOICES,
    }
    return render(request, 'laboratory/lab_order_list.html', context)


@login_required
def lab_order_detail(request, order_id):
    """檢驗申請單詳情"""
    order = get_object_or_404(LabOrder, id=order_id, is_active=True)
    order_items = LabOrderItem.objects.filter(lab_order=order, is_active=True)
    results = LabResult.objects.filter(lab_order_item__lab_order=order, is_active=True)
    
    context = {
        'title': f'檢驗申請單 - {order.order_number}',
        'order': order,
        'order_items': order_items,
        'results': results,
    }
    return render(request, 'laboratory/lab_order_detail.html', context)


@login_required
def lab_order_create(request):
    """新增檢驗申請單"""
    if request.method == 'POST':
        patient_id = request.POST.get('patient_id')
        ordering_provider_id = request.POST.get('ordering_provider_id')
        test_ids = request.POST.getlist('test_ids')
        
        try:
            patient = Patient.objects.get(id=patient_id)
            from administration.models import Provider
            ordering_provider = Provider.objects.get(id=ordering_provider_id)
            
            # 創建檢驗申請單
            order = LabOrder.objects.create(
                patient=patient,
                ordering_provider=ordering_provider,
                order_date=timezone.now().date(),
                status='ordered',
                priority='routine',
                notes=request.POST.get('notes', ''),
                created_by=request.user
            )
            
            # 添加檢驗項目
            for test_id in test_ids:
                test_type = LabTestType.objects.get(id=test_id)
                LabOrderItem.objects.create(
                    lab_order=order,
                    test_type=test_type,
                    status='ordered',
                    created_by=request.user
                )
            
            messages.success(request, f'檢驗申請單 {order.order_number} 創建成功！')
            return redirect('laboratory_web:lab_order_detail', order_id=order.id)
            
        except Exception as e:
            messages.error(request, f'創建檢驗申請單失敗：{str(e)}')
    
    # 獲取數據
    patients = Patient.objects.filter(is_active=True)[:100]
    from administration.models import Provider
    providers = Provider.objects.filter(is_active=True)
    test_categories = LabTestCategory.objects.filter(is_active=True).prefetch_related('tests')
    
    context = {
        'title': '新增檢驗申請單',
        'patients': patients,
        'providers': providers,
        'test_categories': test_categories,
    }
    return render(request, 'laboratory/lab_order_create.html', context)


@login_required
def lab_result_list(request):
    """檢驗結果列表"""
    results = LabResult.objects.filter(is_active=True).select_related(
        'order_item__lab_order__patient', 
        'order_item__test_type'
    ).order_by('-result_date')
    
    # 搜尋和篩選
    search_query = request.GET.get('search')
    status_filter = request.GET.get('status')
    
    if search_query:
        results = results.filter(
            Q(order_item__lab_order__order_number__icontains=search_query) |
            Q(order_item__lab_order__patient__first_name__icontains=search_query) |
            Q(order_item__lab_order__patient__last_name__icontains=search_query)
        )
    
    if status_filter:
        results = results.filter(result_status=status_filter)
    
    # 分頁
    paginator = Paginator(results, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 創建狀態選項
    status_choices = [
        ('preliminary', 'Preliminary'),
        ('final', 'Final'),
        ('corrected', 'Corrected'),
        ('amended', 'Amended'),
    ]
    
    context = {
        'title': '檢驗結果',
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'status_choices': status_choices,
    }
    return render(request, 'laboratory/lab_result_list.html', context)


@login_required
def lab_result_detail(request, result_id):
    """檢驗結果詳情"""
    result = get_object_or_404(LabResult, id=result_id, is_active=True)
    
    context = {
        'title': f'檢驗結果 - {result.lab_order_item.test_type.name}',
        'result': result,
    }
    return render(request, 'laboratory/lab_result_detail.html', context)


@login_required
def lab_test_management(request):
    """檢驗項目管理"""
    test_types = LabTestType.objects.filter(is_active=True).select_related('category')
    categories = LabTestCategory.objects.filter(is_active=True).annotate(
        test_count=Count('tests')
    )
    
    context = {
        'title': '檢驗項目管理',
        'test_types': test_types,
        'categories': categories,
    }
    return render(request, 'laboratory/lab_test_management.html', context)


@login_required
def lab_provider_management(request):
    """實驗室提供商管理"""
    providers = LabProvider.objects.filter(is_active=True)
    
    context = {
        'title': '實驗室提供商管理',
        'providers': providers,
    }
    return render(request, 'laboratory/lab_provider_management.html', context)


@login_required
def lab_reports(request):
    """實驗室報告"""
    # 統計數據
    total_orders = LabOrder.objects.filter(is_active=True).count()
    pending_orders = LabOrder.objects.filter(status='ordered', is_active=True).count()
    completed_orders = LabOrder.objects.filter(status='completed', is_active=True).count()
    
    # 近期趨勢
    recent_orders = LabOrder.objects.filter(
        is_active=True,
        created_at__gte=timezone.now() - timezone.timedelta(days=30)
    ).order_by('-created_at')
    
    context = {
        'title': '實驗室報告',
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'recent_orders': recent_orders,
    }
    return render(request, 'laboratory/lab_reports.html', context)


@login_required
def patient_lab_history(request, patient_id):
    """患者檢驗歷史"""
    patient = get_object_or_404(Patient, id=patient_id, is_active=True)
    lab_orders = LabOrder.objects.filter(
        patient=patient, 
        is_active=True
    ).order_by('-order_date')
    
    context = {
        'title': f'{patient.first_name} {patient.last_name} - 檢驗歷史',
        'patient': patient,
        'lab_orders': lab_orders,
    }
    return render(request, 'laboratory/patient_lab_history.html', context)
