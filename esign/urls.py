"""
Electronic Signature System URL Configuration

This module defines URL patterns for the electronic signature system,
including REST API endpoints for signatures, configuration, templates, and audit logs.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'signatures', views.ESignSignatureViewSet, basename='esign-signature')
router.register(r'configuration', views.ESignConfigurationViewSet, basename='esign-configuration')
router.register(r'templates', views.ESignTemplateViewSet, basename='esign-template')
router.register(r'audit-logs', views.ESignAuditLogViewSet, basename='esign-audit-log')

app_name = 'esign'

urlpatterns = [
    # API endpoints
    path('api/v1/', include(router.urls)),
    
    # Additional specific endpoints
    path('api/v1/signatures/<int:pk>/verify/', 
         views.ESignSignatureViewSet.as_view({'post': 'verify_signature'}), 
         name='verify-signature'),
    
    path('api/v1/signatures/<int:pk>/lock/', 
         views.ESignSignatureViewSet.as_view({'post': 'lock_signature'}), 
         name='lock-signature'),
    
    path('api/v1/signatures/<int:pk>/unlock/', 
         views.ESignSignatureViewSet.as_view({'post': 'unlock_signature'}), 
         name='unlock-signature'),
    
    path('api/v1/signatures/<int:pk>/status/', 
         views.ESignSignatureViewSet.as_view({'get': 'status'}), 
         name='signature-status'),
    
    path('api/v1/signatures/<int:pk>/audit-log/', 
         views.ESignSignatureViewSet.as_view({'get': 'audit_log'}), 
         name='signature-audit-log'),
    
    path('api/v1/templates/<int:pk>/render/', 
         views.ESignTemplateViewSet.as_view({'post': 'render'}), 
         name='render-template'),
    
    path('api/v1/audit-logs/summary/', 
         views.ESignAuditLogViewSet.as_view({'get': 'summary'}), 
         name='audit-log-summary'),
]
