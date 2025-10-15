"""
URL configuration for document management system
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

# Web URL patterns
web_patterns = [
    path('', views.document_dashboard, name='document_dashboard'),
    path('list/', views.document_list, name='document_list'),
    path('detail/<uuid:pk>/', views.document_detail, name='document_detail'),
    path('upload/', views.document_upload, name='document_upload'),
    path('download/<uuid:pk>/', views.document_download, name='document_download'),
    path('share/<uuid:pk>/', views.document_share_view, name='document_share'),
    path('sign/<uuid:pk>/', views.document_sign_view, name='document_sign'),
    path('comment/<uuid:pk>/', views.document_comment_view, name='document_comment'),
    path('audit/<uuid:pk>/', views.document_audit_view, name='document_audit'),
    path('category/<uuid:category_id>/', views.document_by_category, name='document_by_category'),
    path('search/', views.document_search, name='document_search'),
    path('my-documents/', views.my_documents, name='my_documents'),
    path('shared-with-me/', views.shared_with_me, name='shared_with_me'),
    path('pending-signatures/', views.pending_signatures, name='pending_signatures'),
]

# URL patterns
urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    
    # Web views
    path('', include(web_patterns)),
]

# Separate API URLs for cleaner routing
api_urlpatterns = [
    path('', include(router.urls)),
]

app_name = 'documents'
