"""
FHIR Integration URLs for ONC Certification
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# API Router
router = DefaultRouter()
router.register(r'resources', views.FHIRResourceViewSet, basename='fhir-resource')
router.register(r'uscdi', views.USCDIDataElementViewSet, basename='uscdi')
router.register(r'patients', views.FHIRPatientViewSet, basename='fhir-patient')

app_name = 'fhir_integration'

urlpatterns = [
    # FHIR API endpoints
    path('api/', include(router.urls)),
    
    # Standard FHIR R4 endpoints for ONC certification
    path('Patient/', views.FHIREndpointView().patient_search, name='patient-search'),
    path('Observation/', views.FHIREndpointView().observation_search, name='observation-search'),
    
    # FHIR metadata endpoint (required for ONC)
    path('metadata/', views.FHIRResourceViewSet.as_view({'get': 'metadata'}), name='capability-statement'),
]