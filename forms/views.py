"""
Views for the Clinical Forms Engine

Provides API endpoints and web views for form management and submission.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Q, Count, Avg
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

import json
from datetime import datetime, timedelta

from .models import (
    FormCategory, FormTemplate, FormField, FormSubmission, 
    FormValidationRule, FormAuditLog, StandardizedAssessment, FormReport
)
from .serializers import (
    FormCategorySerializer, FormTemplateSerializer, FormTemplateListSerializer,
    FormFieldSerializer, FormSubmissionSerializer, FormSubmissionCreateSerializer,
    FormValidationRuleSerializer, FormAuditLogSerializer, 
    StandardizedAssessmentSerializer, FormReportSerializer,
    FormAnalyticsSerializer, PatientFormSummarySerializer
)
from patients.models import Patient


def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_form_activity(template, patient, action, user, request, submission=None, details=None):
    """Log form activity for audit trail"""
    # Only log if patient is provided (required field)
    if patient:
        FormAuditLog.objects.create(
            template=template,
            patient=patient,
            submission=submission,
            action=action,
            performed_by=user,
            details=details or {},
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )


# ============================================================================
# API ViewSets
# ============================================================================

class FormCategoryViewSet(viewsets.ModelViewSet):
    """API ViewSet for form categories"""
    
    queryset = FormCategory.objects.filter(is_active=True)
    serializer_class = FormCategorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter categories with active forms"""
        return FormCategory.objects.filter(
            is_active=True,
            form_templates__is_active=True,
            form_templates__is_published=True
        ).distinct().order_by('display_order', 'name')


class FormTemplateViewSet(viewsets.ModelViewSet):
    """API ViewSet for form templates"""
    
    queryset = FormTemplate.objects.filter(is_active=True, is_published=True)
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return FormTemplateListSerializer
        return FormTemplateSerializer
    
    def get_queryset(self):
        """Filter and search templates"""
        queryset = FormTemplate.objects.filter(is_active=True, is_published=True)
        
        # Filter by category
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category__id=category)
        
        # Filter by form type
        form_type = self.request.query_params.get('form_type', None)
        if form_type:
            queryset = queryset.filter(form_type=form_type)
        
        # Filter standardized forms
        standardized = self.request.query_params.get('standardized', None)
        if standardized is not None:
            queryset = queryset.filter(is_standardized=standardized.lower() == 'true')
        
        # Search
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(description__icontains=search)
            )
        
        return queryset.select_related('category').prefetch_related('form_fields')
    
    @action(detail=True, methods=['get'])
    def fields(self, request, pk=None):
        """Get form fields for a template"""
        template = self.get_object()
        fields = template.form_fields.filter(is_active=True).order_by('display_order')
        serializer = FormFieldSerializer(fields, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def submissions(self, request, pk=None):
        """Get submissions for a template"""
        template = self.get_object()
        submissions = template.submissions.all().order_by('-submission_date')
        
        # Filter by patient if specified
        patient_id = request.query_params.get('patient', None)
        if patient_id:
            submissions = submissions.filter(patient__id=patient_id)
        
        # Pagination
        page = self.paginate_queryset(submissions)
        if page is not None:
            serializer = FormSubmissionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = FormSubmissionSerializer(submissions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit a form for a template"""
        template = self.get_object()
        
        # Validate patient
        patient_id = request.data.get('patient')
        if not patient_id:
            return Response(
                {'error': 'Patient ID is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response(
                {'error': 'Patient not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create submission
        submission_data = {
            'template': template.id,
            'patient': patient.id,
            'form_data': request.data.get('form_data', {}),
            'encounter': request.data.get('encounter'),
            'completion_time_seconds': request.data.get('completion_time_seconds'),
            'status': request.data.get('status', 'submitted')
        }
        
        serializer = FormSubmissionCreateSerializer(
            data=submission_data, 
            context={'request': request}
        )
        
        if serializer.is_valid():
            submission = serializer.save()
            
            # Log activity
            log_form_activity(
                template=template,
                patient=patient,
                action='submitted',
                user=request.user,
                request=request,
                submission=submission,
                details={'completion_time': submission.completion_time_seconds}
            )
            
            return Response(
                FormSubmissionSerializer(submission).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FormSubmissionViewSet(viewsets.ModelViewSet):
    """API ViewSet for form submissions"""
    
    queryset = FormSubmission.objects.all()
    serializer_class = FormSubmissionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter submissions"""
        queryset = FormSubmission.objects.all()
        
        # Filter by patient
        patient_id = self.request.query_params.get('patient', None)
        if patient_id:
            queryset = queryset.filter(patient__id=patient_id)
        
        # Filter by template
        template_id = self.request.query_params.get('template', None)
        if template_id:
            queryset = queryset.filter(template__id=template_id)
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        if start_date:
            queryset = queryset.filter(submission_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(submission_date__lte=end_date)
        
        return queryset.select_related('template', 'patient', 'submitted_by').order_by('-submission_date')
    
    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """Review a form submission"""
        submission = self.get_object()
        
        review_data = {
            'status': request.data.get('status', 'reviewed'),
            'review_notes': request.data.get('review_notes', ''),
            'reviewed_by': request.user,
            'review_date': timezone.now()
        }
        
        for field, value in review_data.items():
            setattr(submission, field, value)
        
        submission.save()
        
        # Log activity
        log_form_activity(
            template=submission.template,
            patient=submission.patient,
            action='reviewed',
            user=request.user,
            request=request,
            submission=submission,
            details={'status': submission.status, 'notes': submission.review_notes}
        )
        
        return Response(FormSubmissionSerializer(submission).data)
    
    @action(detail=True, methods=['get'])
    def validate_data(self, request, pk=None):
        """Validate form submission data"""
        submission = self.get_object()
        
        # Get validation rules for the template
        validation_rules = submission.template.validation_rules.filter(is_active=True)
        
        validation_results = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'completion_percentage': submission.get_completion_percentage()
        }
        
        # Check required fields
        required_fields = submission.template.form_fields.filter(is_required=True)
        for field in required_fields:
            if field.field_name not in submission.form_data or not submission.form_data[field.field_name]:
                validation_results['errors'].append({
                    'field': field.field_name,
                    'message': f'{field.field_label} is required'
                })
                validation_results['is_valid'] = False
        
        # Apply custom validation rules
        for rule in validation_rules:
            try:
                # This is a simplified validation - in production, use a proper expression evaluator
                # For security, implement proper sandboxing
                result = eval(rule.validation_logic, {"data": submission.form_data})
                if not result:
                    error_data = {
                        'rule': rule.name,
                        'message': rule.error_message
                    }
                    if rule.is_blocking:
                        validation_results['errors'].append(error_data)
                        validation_results['is_valid'] = False
                    else:
                        validation_results['warnings'].append(error_data)
            except Exception:
                # Invalid rule - log and skip
                pass
        
        return Response(validation_results)


class StandardizedAssessmentViewSet(viewsets.ReadOnlyModelViewSet):
    """API ViewSet for standardized assessments"""
    
    queryset = StandardizedAssessment.objects.filter(is_active=True)
    serializer_class = StandardizedAssessmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter by assessment type"""
        queryset = StandardizedAssessment.objects.filter(
            is_active=True,
            template__is_active=True,
            template__is_published=True
        )
        
        assessment_type = self.request.query_params.get('type', None)
        if assessment_type:
            queryset = queryset.filter(assessment_type=assessment_type)
        
        return queryset.select_related('template')


# ============================================================================
# API Functions
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@login_required
def form_analytics(request):
    """Form analytics dashboard view"""
    
    # Date range filter
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not start_date:
        start_date = (timezone.now() - timedelta(days=30)).date()
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    
    if not end_date:
        end_date = timezone.now().date()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Get analytics for each template
    templates = FormTemplate.objects.filter(
        is_active=True,
        submissions__submission_date__range=[start_date, end_date]
    ).annotate(
        total_submissions=Count('submissions'),
        avg_completion_time=Avg('submissions__completion_time_seconds')
    ).distinct()
    
    analytics_data = []
    
    for template in templates:
        submissions = template.submissions.filter(
            submission_date__range=[start_date, end_date]
        )
        
        completed_submissions = submissions.filter(
            status__in=['submitted', 'reviewed', 'approved']
        ).count()
        
        completion_rate = (completed_submissions / template.total_submissions * 100) if template.total_submissions > 0 else 0
        
        analytics_data.append({
            'template': template,
            'total_submissions': template.total_submissions,
            'completed_submissions': completed_submissions,
            'completion_rate': completion_rate,
            'average_completion_time': template.avg_completion_time
        })
    
    context = {
        'analytics_data': analytics_data,
        'start_date': start_date,
        'end_date': end_date,
        'date_range_days': (end_date - start_date).days
    }
    
    return render(request, 'forms/analytics.html', context)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def patient_form_summary(request, patient_id):
    """Get form summary for a specific patient"""
    
    try:
        patient = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        return Response(
            {'error': 'Patient not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get patient's form statistics
    submissions = FormSubmission.objects.filter(patient=patient)
    
    total_forms = submissions.count()
    completed_forms = submissions.filter(
        status__in=['submitted', 'reviewed', 'approved']
    ).count()
    pending_forms = submissions.filter(status='draft').count()
    
    # Get recent submissions
    recent_submissions = submissions.order_by('-submission_date')[:5]
    
    # Calculate score trends for scored assessments
    score_trends = {}
    scored_templates = FormTemplate.objects.filter(
        auto_calculate_score=True,
        submissions__patient=patient
    ).distinct()
    
    for template in scored_templates:
        template_submissions = submissions.filter(
            template=template
        ).exclude(
            calculated_scores__isnull=True
        ).order_by('submission_date')
        
        trends = []
        for submission in template_submissions:
            if submission.calculated_scores and 'total_score' in submission.calculated_scores:
                trends.append({
                    'date': submission.submission_date.strftime('%Y-%m-%d'),
                    'score': submission.calculated_scores['total_score']
                })
        
        if trends:
            score_trends[template.name] = trends
    
    summary_data = {
        'patient_id': patient.id,
        'patient_name': patient.full_name,
        'total_forms': total_forms,
        'completed_forms': completed_forms,
        'pending_forms': pending_forms,
        'recent_submissions': FormSubmissionSerializer(recent_submissions, many=True).data,
        'score_trends': score_trends
    }
    
    serializer = PatientFormSummarySerializer(summary_data)
    return Response(serializer.data)


# ============================================================================
# Web Views
# ============================================================================

@login_required
def form_dashboard(request):
    """Forms dashboard view"""
    
    # Get summary statistics
    context = {
        'total_templates': FormTemplate.objects.filter(is_active=True).count(),
        'published_templates': FormTemplate.objects.filter(is_active=True, is_published=True).count(),
        'total_submissions': FormSubmission.objects.count(),
        'pending_reviews': FormSubmission.objects.filter(status='submitted').count(),
        
        # Recent activity
        'recent_submissions': FormSubmission.objects.select_related(
            'template', 'patient', 'submitted_by'
        ).order_by('-submission_date')[:10],
        
        # Categories
        'categories': FormCategory.objects.filter(is_active=True).order_by('display_order'),
        
        # Popular templates
        'popular_templates': FormTemplate.objects.filter(
            is_active=True, is_published=True
        ).annotate(
            submission_count=Count('submissions')
        ).order_by('-submission_count')[:5]
    }
    
    return render(request, 'forms/dashboard.html', context)


@login_required
def template_list(request):
    """List all form templates"""
    
    templates = FormTemplate.objects.filter(is_active=True, is_published=True)
    
    # Filter by category
    category_id = request.GET.get('category')
    if category_id:
        templates = templates.filter(category__id=category_id)
    
    # Filter by type
    form_type = request.GET.get('type')
    if form_type:
        templates = templates.filter(form_type=form_type)
    
    # Search
    search = request.GET.get('search')
    if search:
        templates = templates.filter(
            Q(name__icontains=search) |
            Q(code__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(templates, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'templates': page_obj,
        'categories': FormCategory.objects.filter(is_active=True),
        'form_types': FormTemplate.FORM_TYPES,
        'current_category': category_id,
        'current_type': form_type,
        'search_query': search
    }
    
    return render(request, 'forms/template_list.html', context)


@login_required
def template_detail(request, template_id):
    """View form template details"""
    
    template = get_object_or_404(
        FormTemplate, 
        id=template_id, 
        is_active=True, 
        is_published=True
    )
    
    # Log view activity
    log_form_activity(
        template=template,
        patient=None,
        action='viewed',
        user=request.user,
        request=request
    )
    
    context = {
        'template': template,
        'fields': template.form_fields.filter(is_active=True).order_by('display_order'),
        'recent_submissions': template.submissions.select_related('patient', 'submitted_by').order_by('-submission_date')[:5]
    }
    
    return render(request, 'forms/template_detail.html', context)


@login_required
def form_fill(request, template_id):
    """Fill out a form"""
    
    template = get_object_or_404(
        FormTemplate, 
        id=template_id, 
        is_active=True, 
        is_published=True
    )
    
    # Get patient from URL parameter
    patient_id = request.GET.get('patient')
    patient = None
    if patient_id:
        patient = get_object_or_404(Patient, id=patient_id)
    
    if request.method == 'POST':
        # Process form submission
        form_data = {}
        for field in template.form_fields.filter(is_active=True):
            field_value = request.POST.get(field.field_name)
            if field_value is not None:
                form_data[field.field_name] = field_value
        
        # Create submission
        submission = FormSubmission.objects.create(
            template=template,
            patient=patient,
            submitted_by=request.user,
            form_data=form_data,
            status='submitted'
        )
        
        # Calculate score if applicable
        if template.auto_calculate_score:
            submission.calculate_score()
            submission.save()
        
        # Log activity
        log_form_activity(
            template=template,
            patient=patient,
            action='submitted',
            user=request.user,
            request=request,
            submission=submission
        )
        
        messages.success(request, f'Form "{template.name}" submitted successfully.')
        
        if patient:
            return redirect('patients:patient_detail', patient_id=patient.id)
        else:
            return redirect('forms:submission_detail', submission_id=submission.id)
    
    # Log start activity
    if patient:
        log_form_activity(
            template=template,
            patient=patient,
            action='started',
            user=request.user,
            request=request
        )
    
    context = {
        'template': template,
        'patient': patient,
        'fields': template.form_fields.filter(is_active=True).order_by('display_order')
    }
    
    return render(request, 'forms/form_fill.html', context)


@login_required
def submission_detail(request, submission_id):
    """View form submission details"""
    
    submission = get_object_or_404(FormSubmission, id=submission_id)
    
    context = {
        'submission': submission,
        'fields': submission.template.form_fields.filter(is_active=True).order_by('display_order'),
        'audit_logs': submission.audit_logs.order_by('-timestamp')[:10]
    }
    
    return render(request, 'forms/submission_detail.html', context)


@login_required
def submission_list(request):
    """List form submissions"""
    
    submissions = FormSubmission.objects.select_related(
        'template', 'patient', 'submitted_by'
    ).all()
    
    # Filter by template
    template_id = request.GET.get('template')
    if template_id:
        submissions = submissions.filter(template__id=template_id)
    
    # Filter by patient
    patient_id = request.GET.get('patient')
    if patient_id:
        submissions = submissions.filter(patient__id=patient_id)
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        submissions = submissions.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(submissions.order_by('-submission_date'), 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'submissions': page_obj,
        'templates': FormTemplate.objects.filter(is_active=True, is_published=True),
        'status_choices': FormSubmission.STATUS_CHOICES,
        'current_template': template_id,
        'current_status': status_filter
    }
    
    return render(request, 'forms/submission_list.html', context)


@login_required
def template_create(request):
    """Create a new form template"""
    if request.method == 'POST':
        # Handle form template creation
        pass
    context = {
        'title': 'Create Form Template',
        'action': 'create'
    }
    return render(request, 'forms/template_form.html', context)

@login_required
def template_edit(request, template_id):
    """Edit an existing form template"""
    template = get_object_or_404(FormTemplate, id=template_id)
    if request.method == 'POST':
        # Handle form template editing
        pass
    context = {
        'title': 'Edit Form Template',
        'template': template,
        'action': 'edit'
    }
    return render(request, 'forms/template_form.html', context)

@login_required
def submission_edit(request, submission_id):
    """Edit a form submission"""
    submission = get_object_or_404(FormSubmission, id=submission_id)
    if request.method == 'POST':
        # Handle form submission editing
        pass
    context = {
        'submission': submission,
        'title': 'Edit Form Submission',
        'action': 'edit'
    }
    return render(request, 'forms/submission_form.html', context)

@login_required
def submission_export(request):
    """Export form submissions"""
    # Handle export logic
    context = {
        'title': 'Export Form Submissions'
    }
    return render(request, 'forms/submission_export.html', context)
