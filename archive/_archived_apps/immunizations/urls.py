from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# API Router
router = DefaultRouter()
router.register(r'manufacturers', views.VaccineManufacturerViewSet)
router.register(r'vaccines', views.VaccineViewSet)
router.register(r'lots', views.VaccineLotViewSet)
router.register(r'schedules', views.ImmunizationScheduleViewSet)
router.register(r'immunizations', views.ImmunizationViewSet)
router.register(r'observations', views.ImmunizationObservationViewSet)
router.register(r'contraindications', views.ImmunizationContraindicationViewSet)
router.register(r'alerts', views.PatientImmunizationAlertViewSet)

app_name = 'immunizations'

urlpatterns = [
    # API URLs
    path('api/v1/', include(router.urls)),
    
    # Web URLs
    path('', views.immunization_dashboard, name='dashboard'),
    path('list/', views.immunization_list, name='list'),
    path('detail/<int:pk>/', views.immunization_detail, name='detail'),
    path('patient/<uuid:patient_id>/history/', views.patient_immunization_history, name='patient_history'),
    path('inventory/', views.vaccine_inventory, name='inventory'),
    path('reports/', views.immunization_reports, name='reports'),
]
