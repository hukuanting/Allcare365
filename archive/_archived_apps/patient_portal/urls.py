"""
URL configuration for Patient Portal module.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# API Router
router = DefaultRouter()
router.register(r'portal-access', views.PatientPortalAccessViewSet)
router.register(r'messages', views.PortalMessageViewSet)
router.register(r'education-resources', views.PatientEducationResourceViewSet)
router.register(r'health-reminders', views.PatientHealthReminderViewSet)

app_name = 'patient_portal'

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    
    # Authentication API
    path('api/auth/login/', views.api_portal_login, name='api_login'),
    path('api/auth/logout/', views.portal_logout, name='api_logout'),
    path('api/auth/register/', views.portal_register, name='api_register'),
    path('api/auth/verify/', views.verify_portal_access, name='api_verify'),
    
    # Dashboard API
    path('api/dashboard/', views.api_portal_dashboard, name='api_dashboard'),
    
    # Web views
    path('', views.portal_home_view, name='home'),
    path('login/', views.portal_login_view, name='login'),
    path('logout/', views.portal_logout_view, name='logout'),
    path('dashboard/', views.portal_dashboard_view, name='dashboard'),
    path('medical-records/', views.medical_records_view, name='medical_records'),
    path('appointments/', views.appointments_view, name='appointments'),
    path('prescriptions/', views.prescriptions_view, name='prescriptions'),
    path('lab-results/', views.lab_results_view, name='lab_results'),
    path('messages/', views.messages_view, name='messages'),
    path('education/', views.education_view, name='education'),
    path('profile/', views.profile_view, name='profile'),
    
    # AJAX endpoints
    path('ajax/get-messages/', views.get_messages_ajax, name='get_messages_ajax'),
    path('ajax/send-message/', views.send_message_ajax, name='send_message_ajax'),
    path('ajax/get-lab-results/', views.get_lab_results_ajax, name='get_lab_results_ajax'),
    path('ajax/get-prescriptions/', views.get_prescriptions_ajax, name='get_prescriptions_ajax'),
    path('ajax/get-appointments/', views.get_appointments_ajax, name='get_appointments_ajax'),
    path('ajax/schedule-appointment/', views.schedule_appointment_ajax, name='schedule_appointment_ajax'),
]
