from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# API 路由
router = DefaultRouter()
router.register(r'screenings', views.HealthScreeningViewSet, basename='health-screening')

app_name = 'health_screening'

urlpatterns = [
    # 工具路由 - 放在router之前，避免被攔截
    path('parse-file/', views.parse_file, name='parse_file'),
    path('download-template/', views.download_template, name='download_template'),
    path('download-error-report/', views.download_error_report, name='download_error_report'),
    
    # API 路由
    path('', include(router.urls)),
    
    # 額外的 API 端點
    path('bulk-import/', views.HealthScreeningViewSet.as_view({'post': 'bulk_import'}), name='api_bulk_import'),
    path('fhir-import/', views.HealthScreeningViewSet.as_view({'post': 'fhir_import'}), name='api_fhir_import'),
    path('<uuid:pk>/risk-analysis/', views.HealthScreeningViewSet.as_view({'post': 'calculate_comprehensive_risk'}), name='api_risk_analysis'),
    
    # Web 頁面路由
    path('dashboard/', views.dashboard, name='dashboard'),
    path('create/', views.create_screening, name='create'),
    path('bulk-import-page/', views.bulk_import, name='bulk_import_page'),
    path('list/', views.screening_list, name='list'),
    path('detail/<uuid:screening_id>/', views.screening_detail, name='detail'),
    path('edit/<uuid:screening_id>/', views.screening_edit, name='edit'),
    path('reports/', views.reports, name='reports'),
]
