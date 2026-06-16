"""
Clinical Decision Support URLs

This module defines URL patterns for both API and web views.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# API Router
router = DefaultRouter()
router.register(r'rule-categories', views.RuleCategoryViewSet)
router.register(r'clinical-rules', views.ClinicalRuleViewSet)
router.register(r'clinical-alerts', views.ClinicalAlertViewSet)
router.register(r'drug-interactions', views.DrugInteractionViewSet)
router.register(r'preventive-care-reminders', views.PreventiveCareReminderViewSet)
router.register(r'patient-reminders', views.PatientReminderViewSet)
router.register(r'clinical-protocols', views.ClinicalProtocolViewSet)

app_name = 'clinical_decision_support'

urlpatterns = [
    # API URLs
    path('api/', include(router.urls)),
    
    # Web URLs
    path('', views.dashboard, name='dashboard'),
    path('rules/', views.rules_list, name='rules_list'),
    path('rules/<uuid:rule_id>/', views.rule_detail, name='rule_detail'),
    path('alerts/', views.alerts_list, name='alerts_list'),
    path('alerts/<uuid:alert_id>/acknowledge/', views.acknowledge_alert, name='acknowledge_alert'),
    path('drug-interactions/', views.drug_interactions, name='drug_interactions'),
    path('preventive-care/', views.preventive_care, name='preventive_care'),
    path('protocols/', views.protocols_list, name='protocols_list'),
    path('protocols/<uuid:protocol_id>/', views.protocol_detail, name='protocol_detail'),
    
    # AJAX URLs
    path('ajax/check-patient-alerts/', views.check_patient_alerts, name='check_patient_alerts'),
    path('ajax/execute-rule/', views.execute_rule_for_patient, name='execute_rule_for_patient'),
    path('ajax/check-drug-interactions/', views.check_drug_interactions, name='check_drug_interactions'),
]
