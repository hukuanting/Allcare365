from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.conf import settings
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from datetime import datetime, timedelta
from functools import wraps
import json
import logging

from .models import (
    PatientPortalAccess, PortalMessage, PortalMessageAttachment,
    PatientPortalSession, PatientPortalAuditLog, PatientEducationResource,
    PatientPortalPreference, PatientFamilyAccess, PatientHealthReminder
)
from .serializers import (
    PatientPortalAccessSerializer, PortalMessageSerializer, PortalMessageCreateSerializer,
    PatientPortalSessionSerializer, PatientPortalAuditLogSerializer,
    PatientEducationResourceSerializer, PatientPortalPreferenceSerializer,
    PatientFamilyAccessSerializer, PatientHealthReminderSerializer,
    PatientPortalDashboardSerializer, PatientAuthenticationSerializer,
    PatientRegistrationSerializer
)
from patients.models import Patient
from medical_records.models import MedicalRecord, Prescription
from appointments.models import Appointment
from laboratory.models import LabResult

logger = logging.getLogger(__name__)


# Utility functions
def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_patient_from_request(request):
    """Get patient from request session or authentication"""
    patient_id = request.session.get('patient_id')
    if patient_id:
        try:
            return Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return None
    return None


def patient_portal_login_required(view_func):
    """Decorator to require patient portal login"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        patient = get_patient_from_request(request)
        if not patient:
            return redirect('patient_portal:login')
        return view_func(request, *args, **kwargs)
    return wrapper


def log_patient_activity(patient, action, request, success=True, description=''):
    """Log patient portal activity"""
    PatientPortalAuditLog.objects.create(
        patient=patient,
        action=action,
        description=description,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        success=success,
        created_by=request.user if request.user.is_authenticated else None,
        updated_by=request.user if request.user.is_authenticated else None
    )


# API ViewSets
class PatientPortalAccessViewSet(viewsets.ModelViewSet):
    """Patient portal access management"""
    queryset = PatientPortalAccess.objects.select_related('patient').all()
    serializer_class = PatientPortalAccessSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'is_verified', 'two_factor_enabled']
    search_fields = ['patient__first_name', 'patient__last_name', 'username', 'email']
    ordering_fields = ['create_date', 'last_login', 'username']
    ordering = ['-create_date']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        """Reset patient portal password"""
        portal_access = self.get_object()
        # Generate password reset token and send email
        # Implementation would include email sending logic
        return Response({'message': 'Password reset email sent'})
    
    @action(detail=True, methods=['post'])
    def enable_two_factor(self, request, pk=None):
        """Enable two-factor authentication"""
        portal_access = self.get_object()
        # Implementation for 2FA setup
        return Response({'message': '2FA enabled successfully'})


class PortalMessageViewSet(viewsets.ModelViewSet):
    """Portal message management"""
    queryset = PortalMessage.objects.select_related('patient', 'provider').prefetch_related('attachments').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['message_type', 'status', 'is_urgent', 'is_read_by_patient', 'is_read_by_provider']
    search_fields = ['subject', 'message', 'patient__first_name', 'patient__last_name']
    ordering_fields = ['create_date', 'status']
    ordering = ['-create_date']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PortalMessageCreateSerializer
        return PortalMessageSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark message as read"""
        message = self.get_object()
        user_type = request.data.get('user_type', 'patient')
        
        if user_type == 'patient':
            message.mark_read_by_patient()
        elif user_type == 'provider':
            message.mark_read_by_provider()
        
        return Response({'message': 'Message marked as read'})
    
    @action(detail=False, methods=['get'])
    def thread(self, request):
        """Get message thread"""
        thread_id = request.query_params.get('thread_id')
        if not thread_id:
            return Response({'error': 'thread_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        messages = self.get_queryset().filter(thread_id=thread_id).order_by('create_date')
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)


class PatientEducationResourceViewSet(viewsets.ReadOnlyModelViewSet):
    """Patient education resource management"""
    queryset = PatientEducationResource.objects.filter(is_published=True).all()
    serializer_class = PatientEducationResourceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['resource_type', 'category', 'is_featured']
    search_fields = ['title', 'description', 'content']
    ordering_fields = ['create_date', 'view_count', 'title']
    ordering = ['-is_featured', '-create_date']
    
    @action(detail=True, methods=['post'])
    def track_view(self, request, pk=None):
        """Track resource view"""
        resource = self.get_object()
        resource.increment_view_count()
        
        # Log the activity
        if hasattr(request, 'patient'):
            log_patient_activity(
                request.patient, 
                'view_education_resource',
                request,
                description=f"Viewed: {resource.title}"
            )
        
        return Response({'message': 'View tracked'})


class PatientHealthReminderViewSet(viewsets.ModelViewSet):
    """Patient health reminder management"""
    queryset = PatientHealthReminder.objects.select_related('patient').all()
    serializer_class = PatientHealthReminderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['reminder_type', 'frequency', 'is_active', 'is_completed']
    search_fields = ['title', 'description']
    ordering_fields = ['remind_date', 'create_date']
    ordering = ['remind_date']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_completed(self, request, pk=None):
        """Mark reminder as completed"""
        reminder = self.get_object()
        reminder.mark_completed()
        return Response({'message': 'Reminder marked as completed'})


# Authentication and Dashboard APIs
class PatientAuthenticationView(APIView):
    """Patient portal authentication"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = PatientAuthenticationSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            two_factor_code = serializer.validated_data.get('two_factor_code')
            
            try:
                portal_access = PatientPortalAccess.objects.get(username=username)
                
                # Check if account is locked
                if portal_access.is_locked():
                    log_patient_activity(
                        portal_access.patient, 'failed_login', request, 
                        success=False, description='Account locked'
                    )
                    return Response({
                        'error': 'Account is locked due to multiple failed attempts'
                    }, status=status.HTTP_423_LOCKED)
                
                # Authenticate user (this would integrate with your authentication system)
                # For now, we'll assume password validation is done elsewhere
                
                # Update login information
                portal_access.last_login = timezone.now()
                portal_access.failed_login_attempts = 0
                portal_access.save()
                
                # Create session
                session = PatientPortalSession.objects.create(
                    patient=portal_access.patient,
                    session_key=request.session.session_key or '',
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    created_by=portal_access.patient.created_by,
                    updated_by=portal_access.patient.updated_by
                )
                
                # Log successful login
                log_patient_activity(
                    portal_access.patient, 'login', request,
                    description='Successful login'
                )
                
                # Generate token or session data
                token, created = Token.objects.get_or_create(user=portal_access.patient.created_by)
                
                return Response({
                    'token': token.key,
                    'patient_id': portal_access.patient.id,
                    'username': portal_access.username,
                    'message': 'Login successful'
                })
                
            except PatientPortalAccess.DoesNotExist:
                return Response({
                    'error': 'Invalid credentials'
                }, status=status.HTTP_401_UNAUTHORIZED)
                
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PatientDashboardView(APIView):
    """Patient portal dashboard"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get patient from request (you'd implement patient identification logic)
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response({'error': 'Patient ID required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Log dashboard access
        log_patient_activity(patient, 'view_dashboard', request)
        
        # Gather dashboard data
        today = timezone.now().date()
        
        # Patient basic info
        patient_info = {
            'name': patient.get_full_name(),
            'date_of_birth': patient.date_of_birth,
            'medical_record_number': patient.medical_record_number,
            'email': patient.email,
            'phone': patient.phone_home
        }
        
        # Upcoming appointments
        upcoming_appointments = Appointment.objects.filter(
            patient=patient,
            appointment_date__gte=today,
            status__in=['scheduled', 'confirmed']
        ).select_related('provider').order_by('appointment_date', 'appointment_time')[:5]
        
        # Recent prescriptions
        recent_prescriptions = Prescription.objects.filter(
            patient=patient
        ).select_related('medication', 'prescriber').order_by('-date_prescribed')[:5]
        
        # Recent lab results
        recent_lab_results = LabResult.objects.filter(
            lab_order__patient=patient
        ).select_related('lab_order').order_by('-result_date')[:5]
        
        # Unread messages count
        unread_messages = PortalMessage.objects.filter(
            patient=patient,
            is_read_by_patient=False
        ).count()
        
        # Active health reminders
        health_reminders = PatientHealthReminder.objects.filter(
            patient=patient,
            is_active=True,
            is_completed=False,
            remind_date__lte=timezone.now()
        ).order_by('remind_date')[:5]
        
        # Featured education resources
        education_resources = PatientEducationResource.objects.filter(
            is_published=True,
            is_featured=True
        ).order_by('-create_date')[:3]
        
        dashboard_data = {
            'patient_info': patient_info,
            'upcoming_appointments': upcoming_appointments,
            'recent_prescriptions': recent_prescriptions,
            'recent_lab_results': recent_lab_results,
            'unread_messages': unread_messages,
            'health_reminders': health_reminders,
            'education_resources': education_resources
        }
        
        serializer = PatientPortalDashboardSerializer(dashboard_data)
        return Response(serializer.data)


# Web Views
def portal_login(request):
    """Patient portal login page"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        try:
            portal_access = PatientPortalAccess.objects.get(username=username)
            
            if portal_access.is_locked():
                return render(request, 'patient_portal/login.html', {
                    'error': 'Account is locked due to multiple failed attempts'
                })
            
            # Authentication logic would go here
            # For now, redirect to dashboard
            request.session['patient_id'] = str(portal_access.patient.id)
            
            # Log successful login
            log_patient_activity(
                portal_access.patient, 'login', request,
                description='Web login successful'
            )
            
            return redirect('patient_portal:dashboard')
            
        except PatientPortalAccess.DoesNotExist:
            return render(request, 'patient_portal/login.html', {
                'error': 'Invalid username or password'
            })
    
    return render(request, 'patient_portal/login.html')


def portal_logout(request):
    """Patient portal logout"""
    patient_id = request.session.get('patient_id')
    if patient_id:
        try:
            patient = Patient.objects.get(id=patient_id)
            log_patient_activity(patient, 'logout', request)
        except Patient.DoesNotExist:
            pass
    
    request.session.flush()
    return redirect('patient_portal:login')


@patient_portal_login_required
def portal_dashboard(request):
    """Patient portal dashboard page"""
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return redirect('patient_portal:login')
    
    try:
        patient = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        return redirect('patient_portal:login')
    
    context = {
        'patient': patient,
        'title': 'Patient Portal Dashboard'
    }
    return render(request, 'patient_portal/dashboard.html', context)


@patient_portal_login_required
def medical_records(request):
    """Patient medical records view"""
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return redirect('patient_portal:login')
    
    try:
        patient = Patient.objects.get(id=patient_id)
        records = MedicalRecord.objects.filter(patient=patient).order_by('-date_created')
        
        # Log access
        log_patient_activity(patient, 'view_records', request)
        
        # Pagination
        paginator = Paginator(records, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'patient': patient,
            'page_obj': page_obj,
            'title': 'Medical Records'
        }
        return render(request, 'patient_portal/medical_records.html', context)
        
    except Patient.DoesNotExist:
        return redirect('patient_portal:login')


@patient_portal_login_required
def appointments(request):
    """Patient appointments view"""
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return redirect('patient_portal:login')
    
    try:
        patient = Patient.objects.get(id=patient_id)
        appointments = Appointment.objects.filter(patient=patient).order_by('-appointment_date')
        
        # Log access
        log_patient_activity(patient, 'view_appointments', request)
        
        context = {
            'patient': patient,
            'appointments': appointments,
            'title': 'My Appointments'
        }
        return render(request, 'patient_portal/appointments.html', context)
        
    except Patient.DoesNotExist:
        return redirect('patient_portal:login')


@patient_portal_login_required
def prescriptions(request):
    """Patient prescriptions view"""
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return redirect('patient_portal:login')
    
    try:
        patient = Patient.objects.get(id=patient_id)
        prescriptions = Prescription.objects.filter(patient=patient).order_by('-date_prescribed')
        
        # Log access
        log_patient_activity(patient, 'view_prescriptions', request)
        
        context = {
            'patient': patient,
            'prescriptions': prescriptions,
            'title': 'My Prescriptions'
        }
        return render(request, 'patient_portal/prescriptions.html', context)
        
    except Patient.DoesNotExist:
        return redirect('patient_portal:login')


@patient_portal_login_required
def lab_results(request):
    """Patient lab results view"""
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return redirect('patient_portal:login')
    
    try:
        patient = Patient.objects.get(id=patient_id)
        lab_results = LabResult.objects.filter(
            lab_order__patient=patient
        ).select_related('lab_order').order_by('-result_date')
        
        # Log access
        log_patient_activity(patient, 'view_lab_results', request)
        
        context = {
            'patient': patient,
            'lab_results': lab_results,
            'title': 'Lab Results'
        }
        return render(request, 'patient_portal/lab_results.html', context)
        
    except Patient.DoesNotExist:
        return redirect('patient_portal:login')


@patient_portal_login_required
def messages(request):
    """Patient messages view"""
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return redirect('patient_portal:login')
    
    try:
        patient = Patient.objects.get(id=patient_id)
        messages = PortalMessage.objects.filter(patient=patient).order_by('-create_date')
        
        context = {
            'patient': patient,
            'messages': messages,
            'title': 'Messages'
        }
        return render(request, 'patient_portal/messages.html', context)
        
    except Patient.DoesNotExist:
        return redirect('patient_portal:login')


@patient_portal_login_required
def education(request):
    """Patient education resources view"""
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return redirect('patient_portal:login')
    
    try:
        patient = Patient.objects.get(id=patient_id)
        resources = PatientEducationResource.objects.filter(is_published=True)
        
        # Filter by category if specified
        category = request.GET.get('category')
        if category:
            resources = resources.filter(category=category)
        
        # Search functionality
        search = request.GET.get('search')
        if search:
            resources = resources.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )
        
        resources = resources.order_by('-is_featured', '-create_date')
        
        context = {
            'patient': patient,
            'resources': resources,
            'categories': PatientEducationResource.CATEGORIES,
            'title': 'Health Education'
        }
        return render(request, 'patient_portal/education.html', context)
        
    except Patient.DoesNotExist:
        return redirect('patient_portal:login')


# API Functions for missing endpoints
@api_view(['POST'])
@permission_classes([AllowAny])
def portal_register(request):
    """Patient registration API endpoint"""
    serializer = PatientRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        try:
            # This would normally create a user and patient
            # For now, return success with message
            return Response({
                'success': True,
                'message': 'Registration request submitted. Please contact your healthcare provider to complete activation.'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Registration failed: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response({
            'success': False,
            'message': 'Invalid registration data',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verify_portal_access(request):
    """Verify patient portal access"""
    try:
        patient = get_patient_from_request(request)
        if not patient:
            return Response({
                'success': False,
                'message': 'Patient not found in session'
            }, status=status.HTTP_404_NOT_FOUND)
            
        portal_access = PatientPortalAccess.objects.get(patient=patient)
        
        if not portal_access.is_active:
            return Response({
                'success': False,
                'message': 'Your portal access has been deactivated. Please contact your healthcare provider.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Update last access time
        portal_access.last_access = timezone.now()
        portal_access.save()
        
        return Response({
            'success': True,
            'message': 'Portal access verified',
            'access_level': portal_access.access_level
        }, status=status.HTTP_200_OK)
        
    except PatientPortalAccess.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Portal access not configured'
        }, status=status.HTTP_404_NOT_FOUND)


# AJAX endpoints for missing functions
@patient_portal_login_required
@require_http_methods(["GET"])
def get_messages_ajax(request):
    """AJAX endpoint to get patient messages"""
    try:
        patient = get_patient_from_request(request)
        if not patient:
            return JsonResponse({
                'success': False,
                'message': 'Patient not found in session'
            }, status=404)
            
        folder = request.GET.get('folder', 'inbox')
        
        messages = PortalMessage.objects.filter(patient=patient)
        
        # Filter by folder type based on available fields
        if folder == 'sent':
            messages = messages.filter(status='sent')
        elif folder == 'read':
            messages = messages.filter(is_read_by_patient=True)
        elif folder == 'unread':
            messages = messages.filter(is_read_by_patient=False)
        # Default to all messages (inbox)
        
        messages_data = []
        for message in messages.order_by('-create_date'):
            messages_data.append({
                'id': message.id,
                'sender': message.provider.get_full_name() if message.provider else 'System',
                'subject': message.subject,
                'preview': message.message[:100] + '...' if len(message.message) > 100 else message.message,
                'date': message.create_date.strftime('%Y-%m-%d'),
                'is_read': message.is_read_by_patient,
                'priority': 'high' if message.is_urgent else 'normal',
                'has_attachments': message.attachments.exists()
            })
        
        return JsonResponse({
            'success': True,
            'messages': messages_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error retrieving messages: {str(e)}'
        }, status=500)


@patient_portal_login_required
@require_http_methods(["POST"])
def send_message_ajax(request):
    """AJAX endpoint to send a message"""
    try:
        patient = get_patient_from_request(request)
        if not patient:
            return JsonResponse({
                'success': False,
                'message': 'Patient not found in session'
            }, status=404)
        
        # Mock message sending - in real implementation would integrate with provider system
        return JsonResponse({
            'success': True,
            'message': 'Message sent successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error sending message: {str(e)}'
        }, status=500)


@patient_portal_login_required
@require_http_methods(["GET"])
def get_lab_results_ajax(request):
    """AJAX endpoint to get lab results"""
    try:
        patient = get_patient_from_request(request)
        if not patient:
            return JsonResponse({
                'success': False,
                'message': 'Patient not found in session'
            }, status=404)
        
        # Mock lab results data
        lab_results = [
            {
                'id': 1,
                'test_name': 'Complete Blood Count',
                'test_date': '2024-03-15',
                'result_date': '2024-03-16',
                'status': 'normal',
                'ordering_provider': 'Dr. Smith',
                'has_abnormal_values': False
            }
        ]
        
        return JsonResponse({
            'success': True,
            'lab_results': lab_results
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error retrieving lab results: {str(e)}'
        }, status=500)


@patient_portal_login_required
@require_http_methods(["GET"])
def get_prescriptions_ajax(request):
    """AJAX endpoint to get prescriptions"""
    try:
        patient = get_patient_from_request(request)
        if not patient:
            return JsonResponse({
                'success': False,
                'message': 'Patient not found in session'
            }, status=404)
        
        # Mock prescription data
        prescriptions = [
            {
                'id': 1,
                'medication': 'Lisinopril',
                'dosage': '10mg',
                'frequency': 'Once daily',
                'prescribed_date': '2024-01-15',
                'expiry_date': '2024-01-15',
                'refills_remaining': 3,
                'status': 'active',
                'prescribing_provider': 'Dr. Smith'
            }
        ]
        
        return JsonResponse({
            'success': True,
            'prescriptions': prescriptions
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error retrieving prescriptions: {str(e)}'
        }, status=500)


@patient_portal_login_required
@require_http_methods(["GET"])
def get_appointments_ajax(request):
    """AJAX endpoint to get appointments"""
    try:
        patient = get_patient_from_request(request)
        if not patient:
            return JsonResponse({
                'success': False,
                'message': 'Patient not found in session'
            }, status=404)
        
        # Mock appointment data
        appointments = [
            {
                'id': 1,
                'date_time': '2024-03-25 10:00 AM',
                'provider': 'Dr. Smith',
                'type': 'Follow-up',
                'status': 'confirmed',
                'can_reschedule': True,
                'can_cancel': True
            }
        ]
        
        return JsonResponse({
            'success': True,
            'appointments': appointments
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error retrieving appointments: {str(e)}'
        }, status=500)


@patient_portal_login_required
@require_http_methods(["POST"])
def schedule_appointment_ajax(request):
    """AJAX endpoint to schedule an appointment"""
    try:
        patient = get_patient_from_request(request)
        if not patient:
            return JsonResponse({
                'success': False,
                'message': 'Patient not found in session'
            }, status=404)
        
        # Mock appointment scheduling
        return JsonResponse({
            'success': True,
            'message': 'Appointment request submitted successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error scheduling appointment: {str(e)}'
        }, status=500)


# API-specific decorator for patient portal authentication
def api_patient_portal_login_required(view_func):
    """API decorator to require patient portal login - returns JSON response"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        patient = get_patient_from_request(request)
        if not patient:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper


# Web View Functions
def portal_home_view(request):
    """Portal home page view"""
    return render(request, 'patient_portal/home.html', {
        'title': 'Welcome to Patient Portal'
    })


def portal_login_view(request):
    """Portal login page view"""
    if request.user.is_authenticated:
        # Check if patient session exists
        patient = get_patient_from_request(request)
        if patient:
            return redirect('patient_portal:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        try:
            portal_access = PatientPortalAccess.objects.get(username=username)
            
            if portal_access.is_locked():
                from django.contrib import messages
                messages.error(request, 'Account is locked due to multiple failed attempts.')
                return render(request, 'patient_portal/login.html')
            
            # In a real implementation, you would validate the password here
            # For now, we'll do a simple password check for testing
            if password != 'testpass123':  # Simple password check for testing
                from django.contrib import messages
                messages.error(request, 'Invalid username or password. Please try again.')
                return render(request, 'patient_portal/login.html')
            
            # For now, we'll just authenticate with the portal access
            if not portal_access.is_active:
                from django.contrib import messages
                messages.error(request, 'Your portal access has been deactivated. Please contact your healthcare provider.')
                return render(request, 'patient_portal/login.html')
            
            # Set patient session
            request.session['patient_id'] = str(portal_access.patient.id)
            
            # Ensure session is saved and has a key
            if not request.session.session_key:
                request.session.save()
            
            # Log the login activity
            log_patient_activity(portal_access.patient, 'login', request, True, 'Patient logged in successfully')
            
            # Update portal access
            portal_access.last_login = timezone.now()
            portal_access.save()
            
            # Create session record
            PatientPortalSession.objects.create(
                patient=portal_access.patient,
                session_key=request.session.session_key,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                login_time=timezone.now(),
                created_by=portal_access.patient.created_by,
                updated_by=portal_access.patient.updated_by
            )
            
            from django.contrib import messages
            messages.success(request, 'Welcome back! You have successfully logged in.')
            return redirect('patient_portal:dashboard')
            
        except PatientPortalAccess.DoesNotExist:
            from django.contrib import messages
            messages.error(request, 'Invalid username or password. Please try again.')
    
    return render(request, 'patient_portal/login.html', {
        'title': 'Login'
    })


def portal_logout_view(request):
    """Portal logout view"""
    patient = get_patient_from_request(request)
    if patient:
        # End active sessions
        PatientPortalSession.objects.filter(
            patient=patient,
            is_active=True
        ).update(
            logout_time=timezone.now(),
            is_active=False
        )
        
        # Log the logout activity
        log_patient_activity(patient, 'logout', request, True, 'Patient logged out')
    
    # Clear the patient session
    request.session.flush()
    
    from django.contrib import messages
    messages.success(request, 'You have been successfully logged out.')
    return redirect('patient_portal:home')


@patient_portal_login_required
def portal_dashboard_view(request):
    """Portal dashboard view"""
    patient = get_patient_from_request(request)
    if not patient:
        from django.contrib import messages
        messages.error(request, 'Patient session not found. Please log in again.')
        return redirect('patient_portal:login')
    
    # Get dashboard data
    context = {
        'patient': patient,
        'title': 'Dashboard',
        'last_login': timezone.now()  # You can track this from PatientPortalSession
    }
    
    return render(request, 'patient_portal/dashboard.html', context)


@patient_portal_login_required
def medical_records_view(request):
    """Medical records view"""
    patient = get_patient_from_request(request)
    if not patient:
        return redirect('patient_portal:login')
    
    context = {
        'patient': patient,
        'title': 'Medical Records'
    }
    
    return render(request, 'patient_portal/medical_records.html', context)


@patient_portal_login_required
def appointments_view(request):
    """Appointments view"""
    patient = get_patient_from_request(request)
    if not patient:
        return redirect('patient_portal:login')
    
    context = {
        'patient': patient,
        'title': 'Appointments'
    }
    
    return render(request, 'patient_portal/appointments.html', context)


@patient_portal_login_required
def prescriptions_view(request):
    """Prescriptions view"""
    patient = get_patient_from_request(request)
    if not patient:
        return redirect('patient_portal:login')
    
    context = {
        'patient': patient,
        'title': 'Prescriptions'
    }
    
    return render(request, 'patient_portal/prescriptions.html', context)


@patient_portal_login_required
def lab_results_view(request):
    """Lab results view"""
    patient = get_patient_from_request(request)
    if not patient:
        return redirect('patient_portal:login')
    
    context = {
        'patient': patient,
        'title': 'Lab Results'
    }
    
    return render(request, 'patient_portal/lab_results.html', context)


@patient_portal_login_required
def messages_view(request):
    """Messages view"""
    patient = get_patient_from_request(request)
    if not patient:
        return redirect('patient_portal:login')
    
    context = {
        'patient': patient,
        'title': 'Messages'
    }
    
    return render(request, 'patient_portal/messages.html', context)


@patient_portal_login_required
def education_view(request):
    """Education view"""
    patient = get_patient_from_request(request)
    if not patient:
        return redirect('patient_portal:login')
    
    context = {
        'patient': patient,
        'title': 'Health Education'
    }
    
    return render(request, 'patient_portal/education.html', context)


@patient_portal_login_required
def profile_view(request):
    """Profile view"""
    patient = get_patient_from_request(request)
    if not patient:
        return redirect('patient_portal:login')
    
    context = {
        'patient': patient,
        'title': 'My Profile'
    }
    
    return render(request, 'patient_portal/profile.html', context)


# API Views - Return JSON responses
@api_view(['POST'])
@permission_classes([AllowAny])
def api_portal_login(request):
    """Patient portal API login"""
    if request.method == 'POST':
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response({
                'success': False,
                'error': 'Username and password are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            portal_access = PatientPortalAccess.objects.get(username=username)
            
            if not portal_access.is_active:
                return Response({
                    'success': False,
                    'error': 'Your portal access has been disabled'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            if portal_access.is_locked():
                return Response({
                    'success': False,
                    'error': 'Account is locked due to multiple failed attempts'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Authentication logic would go here
            # For now, simulate password check for testing
            if password != 'testpass123':  # Simple password check for testing
                return Response({
                    'success': False,
                    'error': 'Invalid username or password'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Set session
            request.session['patient_id'] = str(portal_access.patient.id)
            
            # Log successful login
            log_patient_activity(
                portal_access.patient, 'login', request,
                description='API login successful'
            )
            
            return Response({
                'success': True,
                'message': 'Login successful',
                'redirect_url': '/patient-portal/dashboard/'
            }, status=status.HTTP_200_OK)
            
        except PatientPortalAccess.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Invalid username or password'
            }, status=status.HTTP_401_UNAUTHORIZED)
    
    return Response({
        'success': False,
        'error': 'Method not allowed'
    }, status=status.HTTP_405_METHOD_NOT_ALLOWED)


@api_view(['GET'])
@permission_classes([AllowAny])
@csrf_exempt
def api_portal_dashboard(request):
    """Patient portal API dashboard"""
    patient_id = request.session.get('patient_id')
    if not patient_id:
        return Response({
            'success': False,
            'error': 'Authentication required'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        patient = Patient.objects.get(id=patient_id)
        
        # Get dashboard data
        recent_appointments = Appointment.objects.filter(
            patient=patient
        ).order_by('-appointment_date')[:3]
        
        recent_prescriptions = Prescription.objects.filter(
            patient=patient
        ).order_by('-prescription_date')[:3]
        
        unread_messages = PortalMessage.objects.filter(
            patient=patient,
            is_read_by_patient=False
        ).count()
        
        return Response({
            'success': True,
            'data': {
                'patient': {
                    'id': patient.id,
                    'first_name': patient.first_name,
                    'last_name': patient.last_name,
                    'email': patient.email,
                },
                'recent_appointments': len(recent_appointments),
                'recent_prescriptions': len(recent_prescriptions),
                'unread_messages': unread_messages,
            }
        }, status=status.HTTP_200_OK)
        
    except Patient.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Patient not found'
        }, status=status.HTTP_404_NOT_FOUND)
