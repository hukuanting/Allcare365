from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# 創建API router
router = DefaultRouter()
router.register(r'', views.PatientViewSet, basename='patient')

app_name = 'patients'

urlpatterns = [
    # REST API 路由 (用於 /api/patients/)
    path('', include(router.urls)),
    
    # 前端頁面URL (移到不同的路徑避免衝突)
    path('list/', views.patient_list_view, name='patient_list'),
    path('detail/<uuid:patient_id>/', views.patient_detail_view, name='patient_detail'),
    
    # API URLs（用於AJAX請求） - 保持向後兼容
    path('api/list/', views.patient_api_list, name='patient_api_list'),
    path('api/statistics/', views.patient_statistics, name='patient_statistics'),
    path('api/create/', views.patient_create, name='patient_create'),
    
    # 根據RECONSTRUCTION_GUIDE.md建議新增的API端點
    path('api/search/advanced/', views.patient_advanced_search, name='patient_advanced_search'),
    path('api/<uuid:patient_id>/balance/', views.patient_balance, name='patient_balance'),
    path('api/<uuid:patient_id>/summary-report/', views.patient_summary_report, name='patient_summary_report'),
    
    # 保險信息管理API
    path('api/<uuid:patient_id>/insurance/create/', views.patient_insurance_create, name='patient_insurance_create'),
    path('api/<uuid:patient_id>/insurance/', views.patient_insurance_list, name='patient_insurance_list'),
    
    # 病史信息管理API
    path('api/<uuid:patient_id>/history/', views.patient_history_detail, name='patient_history_detail'),
    path('api/<uuid:patient_id>/history/update/', views.patient_history_update, name='patient_history_update'),
    
    # 雇主信息管理API
    path('api/<uuid:patient_id>/employer/create/', views.patient_employer_create, name='patient_employer_create'),
    path('api/<uuid:patient_id>/employer/', views.patient_employer_list, name='patient_employer_list'),
    
    # 重複檢測API
    path('api/duplicate-check/', views.patient_duplicate_check, name='patient_duplicate_check'),
]
