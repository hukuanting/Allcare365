"""
Pharmacy module template URLs for web interface.
"""

from django.urls import path
from . import template_views

app_name = 'pharmacy_web'

urlpatterns = [
    # 主頁
    path('', template_views.pharmacy_dashboard, name='pharmacy_dashboard'),
    
    # 藥物主檔管理
    path('drugs/', template_views.drug_list, name='drug_list'),
    path('drugs/<uuid:drug_id>/', template_views.drug_detail, name='drug_detail'),
    
    # 處方籤管理
    path('prescriptions/', template_views.prescription_list, name='prescription_list'),
    path('prescriptions/<uuid:prescription_id>/', template_views.prescription_detail, name='prescription_detail'),
    
    # 庫存管理
    path('inventory/', template_views.inventory_management, name='inventory_management'),
    
    # 分類管理
    path('categories/', template_views.drug_categories, name='drug_categories'),
    
    # 報告
    path('reports/', template_views.pharmacy_reports, name='pharmacy_reports'),
    
    # 病患用藥記錄
    path('patients/<uuid:patient_id>/medications/', template_views.patient_medication_history, name='patient_medication_history'),
]
