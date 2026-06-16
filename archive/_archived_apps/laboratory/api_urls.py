"""
Laboratory API URL configuration for /api/v1/laboratory/
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router for REST API endpoints
router = DefaultRouter()
router.register(r'providers', views.LabProviderViewSet)
router.register(r'test-categories', views.LabTestCategoryViewSet)
router.register(r'test-types', views.LabTestTypeViewSet)
router.register(r'orders', views.LabOrderViewSet)
router.register(r'order-items', views.LabOrderItemViewSet)
router.register(r'results', views.LabResultViewSet)
router.register(r'messages', views.LabMessageViewSet)
router.register(r'quality-control', views.QualityControlLogViewSet)

app_name = 'laboratory_api'

urlpatterns = [
    path('', include(router.urls)),
    path('statistics/', views.get_lab_statistics, name='statistics'),
    path('hl7/process/', views.process_hl7_message, name='process_hl7'),
]
