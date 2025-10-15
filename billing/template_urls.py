"""
Template URLs for Billing module
"""

from django.urls import path
from . import template_views

app_name = 'billing_templates'

urlpatterns = [
    # 主要管理頁面
    path('', template_views.billing_management, name='billing_management'),
    
    # 發票管理
    path('invoices/', template_views.invoice_list_view, name='invoice_list'),
    path('invoices/create/', template_views.invoice_create_view, name='invoice_create'),
    path('invoices/<uuid:invoice_id>/', template_views.invoice_detail_view, name='invoice_detail'),
    
    # 付款管理
    path('payments/', template_views.payment_list_view, name='payment_list'),
    
    # 保險管理
    path('insurance/', template_views.insurance_management_view, name='insurance_management'),
    
    # 患者帳務
    path('patients/<uuid:patient_id>/', template_views.patient_billing_view, name='patient_billing'),
    
    # 報告
    path('reports/', template_views.billing_reports_view, name='billing_reports'),
    
    # API端點
    path('api/stats/', template_views.billing_stats_api, name='billing_stats_api'),
]
