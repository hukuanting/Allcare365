"""
Laboratory module template URLs for web interface.
"""

from django.urls import path
from . import template_views

app_name = 'laboratory_web'

urlpatterns = [
    # 主頁
    path('', template_views.laboratory_dashboard, name='laboratory_dashboard'),
    
    # 檢驗申請單管理
    path('orders/', template_views.lab_order_list, name='lab_order_list'),
    path('orders/create/', template_views.lab_order_create, name='lab_order_create'),
    path('orders/<uuid:order_id>/', template_views.lab_order_detail, name='lab_order_detail'),
    
    # 檢驗結果管理
    path('results/', template_views.lab_result_list, name='lab_result_list'),
    path('results/<uuid:result_id>/', template_views.lab_result_detail, name='lab_result_detail'),
    
    # 檢驗項目管理
    path('tests/', template_views.lab_test_management, name='lab_test_management'),
    
    # 實驗室提供商管理
    path('providers/', template_views.lab_provider_management, name='lab_provider_management'),
    
    # 報告
    path('reports/', template_views.lab_reports, name='lab_reports'),
    
    # 患者檢驗歷史
    path('patients/<uuid:patient_id>/history/', template_views.patient_lab_history, name='patient_lab_history'),
]
