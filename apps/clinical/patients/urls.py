from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# 創建API router
router = DefaultRouter()
router.register(r'', views.PatientViewSet, basename='patient')
router.register(r'family-history', views.FamilyHealthHistoryViewSet, basename='family-history')
router.register(r'medical-devices', views.MedicalDeviceViewSet, basename='medical-devices')
router.register(r'care-team', views.CareTeamMemberViewSet, basename='care-team')
router.register(r'allergies', views.PatientAllergyViewSet, basename='allergies')
router.register(r'care-plans', views.CarePlanViewSet, basename='care-plans')
router.register(r'medications', views.PatientMedicationViewSet, basename='medications')
router.register(r'medical-orders', views.MedicalOrderViewSet, basename='medical-orders')
router.register(r'insurance', views.InsuranceDataViewSet, basename='insurance')
router.register(r'advance-directives', views.AdvanceDirectiveViewSet, basename='advance-directives')
router.register(r'clinical-notes', views.PatientDocumentViewSet, basename='clinical-notes')

app_name = 'apps.clinical.patients'

urlpatterns = [
    # REST API 路由 (用於 /api/patients/...)
    path('', include(router.urls)),
    
    # 前端頁面URL
    path('list/', views.patient_list_view, name='patient_list'),
    path('detail/<uuid:patient_id>/', views.patient_detail_view, name='patient_detail'),
]