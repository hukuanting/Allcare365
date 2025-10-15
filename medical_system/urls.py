"""
URL configuration for Allcare365 project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.http import JsonResponse

def api_info(request):
    """API 信息頁面 - 指向前端"""
    return JsonResponse({
        'message': 'Allcare365 API Server',
        'version': '1.0.0',
        'frontend_url': 'http://localhost:3000',
        'api_docs': 'http://localhost:8000/api/',
        'admin_panel': 'http://localhost:8000/admin/'
    })

def profile_redirect(request):
    return redirect('/admin/')

urlpatterns = [
    path('', api_info, name='api_info'),
    path('accounts/profile/', profile_redirect, name='profile'),
    path('admin/', admin.site.urls),
    
    # API 認證系統
    path('api/auth/', include('authentication.api_urls', namespace='authentication_api')),

    # Web 認證系統
    path('auth/', include('authentication.web_urls', namespace='authentication_web')),
    
    # REST API 統一入口
    path('api/patients/', include('patients.urls')),
    path('api/health-screening/', include('health_screening.urls')),
    path('api/encounters/', include('encounters.urls')),
    path('api/appointments/', include('appointments.urls')),
    path('api/medical-records/', include('medical_records.urls')),
    path('api/reports/', include('reports.urls')),
    path('api/pharmacy/', include('pharmacy.urls')),
    path('api/laboratory/', include('laboratory.urls')),
    path('api/documents/', include('documents.urls')),
    path('api/billing/', include('billing.urls')),
    path('api/communications/', include('communications.urls')),
    path('api/forms/', include('forms.urls')),
    path('api/immunizations/', include('immunizations.urls')),
    path('api/erx/', include('erx.urls')),
    path('api/esign/', include('esign.urls')),
    path('api/code-systems/', include('code_systems.urls')),
    path('api/clinical-support/', include('clinical_decision_support.urls')),
    path('api/therapy-groups/', include('therapy_groups.urls')),
    path('api/patient-portal/', include('patient_portal.urls')),
    path('api/administration/', include('administration.urls')),
    
    # FHIR R4 Integration for ONC Certification
    path('fhir/', include('fhir_integration.urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
