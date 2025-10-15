"""
URL configuration for pharmacy app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DrugCategoryViewSet, DrugViewSet, DrugInteractionViewSet,
    DrugAllergyViewSet, DrugInventoryViewSet, PrescriptionViewSet,
    PrescriptionRefillViewSet, InventoryTransactionViewSet,
    pharmacy_dashboard, inventory_alerts
)

# Create router for API endpoints
router = DefaultRouter()
router.register(r'categories', DrugCategoryViewSet, basename='drugcategory')
router.register(r'drugs', DrugViewSet, basename='drug')
router.register(r'interactions', DrugInteractionViewSet, basename='druginteraction')
router.register(r'allergies', DrugAllergyViewSet, basename='drugallergy')
router.register(r'inventory', DrugInventoryViewSet, basename='druginventory')
router.register(r'prescriptions', PrescriptionViewSet, basename='prescription')
router.register(r'refills', PrescriptionRefillViewSet, basename='prescriptionrefill')
router.register(r'transactions', InventoryTransactionViewSet, basename='inventorytransaction')

app_name = 'pharmacy'

urlpatterns = [
    # API endpoints (直接路由，不再加 api/ 前綴)
    path('', include(router.urls)),
    
    # Web views
    path('dashboard/', pharmacy_dashboard, name='dashboard'),
    path('alerts/', inventory_alerts, name='inventory_alerts'),
]
