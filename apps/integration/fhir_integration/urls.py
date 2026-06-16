"""
FHIR Integration URLs for ONC Certification
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .compliance_views import USCDIComplianceViewSet
from .smart_config import smart_configuration

# API Router

router = DefaultRouter(trailing_slash=False)

router.register(r'resources', views.FHIRResourceViewSet, basename='fhir-resource')

router.register(r'uscdi', views.USCDIDataElementViewSet, basename='uscdi')

router.register(r'Patient', views.FHIRPatientViewSet, basename='patient')
router.register(r'Practitioner', views.FHIRResourceViewSet, basename='practitioner')
router.register(r'PractitionerRole', views.FHIRResourceViewSet, basename='practitionerrole')
router.register(r'Organization', views.FHIRResourceViewSet, basename='organization')
router.register(r'Location', views.FHIRResourceViewSet, basename='location')
router.register(r'Observation', views.FHIRObservationViewSet, basename='observation')
router.register(r'AllergyIntolerance', views.FHIRResourceViewSet, basename='allergyintolerance')
router.register(r'Condition', views.FHIRResourceViewSet, basename='condition')
router.register(r'Encounter', views.FHIRResourceViewSet, basename='encounter')
router.register(r'Immunization', views.FHIRResourceViewSet, basename='immunization')
router.register(r'Medication', views.FHIRResourceViewSet, basename='medication')
router.register(r'MedicationRequest', views.FHIRResourceViewSet, basename='medicationrequest')
router.register(r'Procedure', views.FHIRResourceViewSet, basename='procedure')
router.register(r'DiagnosticReport', views.FHIRResourceViewSet, basename='diagnosticreport')
router.register(r'DocumentReference', views.FHIRResourceViewSet, basename='documentreference')
router.register(r'CarePlan', views.FHIRResourceViewSet, basename='careplan')
router.register(r'CareTeam', views.FHIRResourceViewSet, basename='careteam')
router.register(r'Goal', views.FHIRResourceViewSet, basename='goal')
router.register(r'Device', views.FHIRResourceViewSet, basename='device')
router.register(r'Provenance', views.FHIRResourceViewSet, basename='provenance')
router.register(r'RelatedPerson', views.FHIRResourceViewSet, basename='relatedperson')
router.register(r'ServiceRequest', views.FHIRResourceViewSet, basename='servicerequest')
router.register(r'Coverage', views.FHIRResourceViewSet, basename='coverage')
router.register(r'MedicationDispense', views.FHIRResourceViewSet, basename='medicationdispense')
router.register(r'Specimen', views.FHIRResourceViewSet, basename='specimen')
router.register(r'Media', views.FHIRResourceViewSet, basename='media')

router.register(r'Group', views.BulkExportViewSet, basename='group')

router.register(r'compliance', USCDIComplianceViewSet, basename='compliance')

urlpatterns = [



    # FHIR metadata endpoint (required for ONC)



    path('metadata', views.FHIRResourceViewSet.as_view({'get': 'metadata'}), name='capability-statement'),
    
    # EHR Launch simulation endpoint
    path('launch', views.ehr_launch, name='fhir_ehr_launch'),



    



        # SMART on FHIR Configuration (Duplicate here for Inferno compatibility at /fhir/ base)



    



        path('.well-known/smart-configuration', smart_configuration, name='fhir_smart_configuration'),



    



        



    



        # JWKS endpoint



    



        path('jwks', views.jwks, name='fhir_jwks'),



    



        



    



        # Bulk Export Status & Download Endpoints (Manual routing for custom patterns)



    



    





    path('bulk-status/<str:job_id>', views.BulkExportViewSet.as_view({'get': 'job_status', 'delete': 'cancel_job'}), name='bulk-status'),

    path('bulk-download/<str:job_id>/<str:file_name>', views.BulkExportViewSet.as_view({'get': 'download_file'}), name='bulk-download'),



    # Standard FHIR R4 endpoints for ONC certification via router

    path('', include(router.urls)),

]


