"""
API URL configuration for document management system
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# API router for REST endpoints
router = DefaultRouter()
router.register(r'categories', views.DocumentCategoryViewSet)
router.register(r'templates', views.DocumentTemplateViewSet)
router.register(r'documents', views.DocumentViewSet)
router.register(r'versions', views.DocumentVersionViewSet)
router.register(r'shares', views.DocumentShareViewSet)
router.register(r'signatures', views.DocumentSignatureViewSet)
router.register(r'comments', views.DocumentCommentViewSet)
router.register(r'audit-logs', views.DocumentAuditLogViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
