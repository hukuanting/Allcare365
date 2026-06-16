"""
Code Systems URL Configuration

This module defines URL patterns for the code systems API endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CodeSystemVersionViewSet, 
    ICD10CodeViewSet, 
    CPTCodeViewSet, 
    SNOMEDConceptViewSet, 
    RxNormConceptViewSet, 
    LOINCCodeViewSet, 
    CodeMappingViewSet, 
    CustomCodeSetViewSet, 
    CustomCodeViewSet, 
    search_codes, 
    validate_code,
)

app_name = 'code_systems_api'

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'versions', CodeSystemVersionViewSet, basename='codesystemversion')
router.register(r'icd10', ICD10CodeViewSet, basename='icd10code')
router.register(r'cpt', CPTCodeViewSet, basename='cptcode')
router.register(r'snomed', SNOMEDConceptViewSet, basename='snomedconcept')
router.register(r'rxnorm', RxNormConceptViewSet, basename='rxnormconcept')
router.register(r'loinc', LOINCCodeViewSet, basename='loinccode')
router.register(r'mappings', CodeMappingViewSet, basename='codemapping')
router.register(r'custom-sets', CustomCodeSetViewSet, basename='customcodeset')
router.register(r'custom-codes', CustomCodeViewSet, basename='customcode')

urlpatterns = [
    # API endpoints
    path('', include(router.urls)),
    path('search/', search_codes, name='code-search'),
    path('validate/', validate_code, name='code-validate'),
    # Additional views for code mapping
    path('mapping/search/', search_codes, name='code-mapping-search'),
]
