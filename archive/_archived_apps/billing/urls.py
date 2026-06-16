from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# 創建路由器
router = DefaultRouter()
router.register(r'insurance-providers', views.InsuranceProviderViewSet)
router.register(r'patient-insurance', views.PatientInsuranceViewSet)
router.register(r'invoices', views.InvoiceViewSet)
router.register(r'invoice-items', views.InvoiceLineItemViewSet)
router.register(r'payments', views.PaymentViewSet)
router.register(r'insurance-claims', views.InsuranceClaimViewSet)
router.register(r'billing-codes', views.BillingCodeViewSet)
router.register(r'fee-schedules', views.FeeScheduleViewSet)
router.register(r'statistics', views.BillingStatisticsViewSet, basename='billing-statistics')

app_name = 'billing'

urlpatterns = [
    path('', include(router.urls)),
    # 可以在這裡添加其他非 API 路由
]
