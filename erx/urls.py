"""
Electronic Prescription (eRx) URL Configuration

This module provides URL routing for the eRx system API endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'erx'

# Create router for viewsets
router = DefaultRouter()
router.register(r'prescriptions', views.ElectronicPrescriptionViewSet, basename='prescription')
router.register(r'refills', views.PrescriptionRefillViewSet, basename='refill')
router.register(r'history', views.PrescriptionHistoryViewSet, basename='history')
router.register(r'formulary', views.DrugFormularyViewSet, basename='formulary')
router.register(r'interactions', views.DrugInteractionViewSet, basename='interaction')
router.register(r'pharmacies', views.PharmacyDirectoryViewSet, basename='pharmacy')

urlpatterns = [
    # API endpoints
    path('api/v1/', include(router.urls)),
]
