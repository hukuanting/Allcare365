"""
Forms module URL configuration for MedicalCare System
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# API router setup
router = DefaultRouter()
router.register(r'categories', views.FormCategoryViewSet, basename='formcategory')
router.register(r'templates', views.FormTemplateViewSet, basename='formtemplate')
router.register(r'submissions', views.FormSubmissionViewSet, basename='formsubmission')
router.register(r'assessments', views.StandardizedAssessmentViewSet, basename='standardizedassessment')

app_name = 'forms'

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    
    # Web views
    path('', views.form_dashboard, name='dashboard'),
    
    # Form Template management
    path('templates/', views.template_list, name='template_list'),
    path('templates/create/', views.template_create, name='template_create'),
    path('templates/<uuid:template_id>/', views.template_detail, name='template_detail'),
    path('templates/<uuid:template_id>/edit/', views.template_edit, name='template_edit'),
    
    # Form filling and submission
    path('fill/<uuid:template_id>/', views.form_fill, name='form_fill'),
    
    # Form submissions
    path('submissions/', views.submission_list, name='submission_list'),
    path('submissions/<uuid:submission_id>/', views.submission_detail, name='submission_detail'),
    path('submissions/<uuid:submission_id>/edit/', views.submission_edit, name='submission_edit'),
    path('submissions/export/', views.submission_export, name='submission_export'),
    
    # Analytics
    path('analytics/', views.form_analytics, name='analytics'),
    
    # Patient summary
    path('patient/<uuid:patient_id>/summary/', views.patient_form_summary, name='patient_summary'),
]
