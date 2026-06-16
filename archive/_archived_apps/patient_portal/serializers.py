from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    PatientPortalAccess, PortalMessage, PortalMessageAttachment,
    PatientPortalSession, PatientPortalAuditLog, PatientEducationResource,
    PatientPortalPreference, PatientFamilyAccess, PatientHealthReminder
)
from patients.models import Patient
from medical_records.models import MedicalRecord, Prescription
from appointments.models import Appointment
from laboratory.models import LabResult


class PatientPortalAccessSerializer(serializers.ModelSerializer):
    """Patient portal access serializer"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    
    class Meta:
        model = PatientPortalAccess
        fields = [
            'id', 'uuid', 'patient', 'patient_name', 'username', 'email',
            'is_active', 'is_verified', 'last_login', 'two_factor_enabled',
            'email_notifications', 'sms_notifications', 'language_preference',
            'create_date', 'update_date'
        ]
        read_only_fields = ['uuid', 'create_date', 'update_date', 'last_login']


class PortalMessageSerializer(serializers.ModelSerializer):
    """Portal message serializer"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    provider_name = serializers.CharField(source='provider.get_full_name', read_only=True)
    attachments = serializers.StringRelatedField(many=True, read_only=True)
    reply_count = serializers.SerializerMethodField()
    
    class Meta:
        model = PortalMessage
        fields = [
            'id', 'uuid', 'patient', 'patient_name', 'provider', 'provider_name',
            'subject', 'message', 'message_type', 'status', 'is_urgent',
            'is_read_by_patient', 'is_read_by_provider', 'parent_message',
            'thread_id', 'attachments', 'reply_count', 'create_date', 'update_date'
        ]
        read_only_fields = ['uuid', 'create_date', 'update_date', 'thread_id']
    
    def get_reply_count(self, obj):
        return obj.replies.count()


class PortalMessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating portal messages"""
    
    class Meta:
        model = PortalMessage
        fields = [
            'patient', 'provider', 'subject', 'message', 'message_type',
            'is_urgent', 'parent_message'
        ]


class PortalMessageAttachmentSerializer(serializers.ModelSerializer):
    """Portal message attachment serializer"""
    
    class Meta:
        model = PortalMessageAttachment
        fields = [
            'id', 'uuid', 'message', 'file', 'original_filename',
            'file_size', 'content_type', 'create_date'
        ]
        read_only_fields = ['uuid', 'create_date']


class PatientPortalSessionSerializer(serializers.ModelSerializer):
    """Patient portal session serializer"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    session_duration = serializers.SerializerMethodField()
    
    class Meta:
        model = PatientPortalSession
        fields = [
            'id', 'uuid', 'patient', 'patient_name', 'session_key',
            'ip_address', 'user_agent', 'login_time', 'logout_time',
            'is_active', 'session_duration'
        ]
        read_only_fields = ['uuid', 'login_time']
    
    def get_session_duration(self, obj):
        if obj.logout_time:
            duration = obj.logout_time - obj.login_time
            return duration.total_seconds()
        return None


class PatientPortalAuditLogSerializer(serializers.ModelSerializer):
    """Patient portal audit log serializer"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    
    class Meta:
        model = PatientPortalAuditLog
        fields = [
            'id', 'uuid', 'patient', 'patient_name', 'action', 'description',
            'ip_address', 'user_agent', 'success', 'create_date'
        ]
        read_only_fields = ['uuid', 'create_date']


class PatientEducationResourceSerializer(serializers.ModelSerializer):
    """Patient education resource serializer"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = PatientEducationResource
        fields = [
            'id', 'uuid', 'title', 'description', 'content', 'resource_type',
            'category', 'url', 'file', 'thumbnail', 'is_featured',
            'is_published', 'view_count', 'created_by_name', 'create_date'
        ]
        read_only_fields = ['uuid', 'view_count', 'create_date']


class PatientPortalPreferenceSerializer(serializers.ModelSerializer):
    """Patient portal preference serializer"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    
    class Meta:
        model = PatientPortalPreference
        fields = [
            'id', 'uuid', 'patient', 'patient_name',
            'email_appointment_reminders', 'email_lab_results',
            'email_prescription_ready', 'email_messages',
            'sms_appointment_reminders', 'sms_lab_results',
            'sms_prescription_ready', 'sms_messages',
            'share_with_family', 'allow_research_contact',
            'theme', 'dashboard_widgets', 'create_date', 'update_date'
        ]
        read_only_fields = ['uuid', 'create_date', 'update_date']


class PatientFamilyAccessSerializer(serializers.ModelSerializer):
    """Patient family access serializer"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    is_expired_status = serializers.SerializerMethodField()
    
    class Meta:
        model = PatientFamilyAccess
        fields = [
            'id', 'uuid', 'patient', 'patient_name', 'family_member_name',
            'family_member_email', 'relationship', 'access_level',
            'can_view_medical_records', 'can_view_appointments',
            'can_view_prescriptions', 'can_view_lab_results',
            'can_schedule_appointments', 'can_send_messages',
            'is_active', 'expires_date', 'is_expired_status',
            'create_date', 'update_date'
        ]
        read_only_fields = ['uuid', 'create_date', 'update_date']
    
    def get_is_expired_status(self, obj):
        return obj.is_expired()


class PatientHealthReminderSerializer(serializers.ModelSerializer):
    """Patient health reminder serializer"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    
    class Meta:
        model = PatientHealthReminder
        fields = [
            'id', 'uuid', 'patient', 'patient_name', 'title', 'description',
            'reminder_type', 'frequency', 'remind_date', 'last_sent',
            'next_due', 'is_active', 'is_completed', 'completed_date',
            'send_email', 'send_sms', 'send_portal_notification',
            'create_date', 'update_date'
        ]
        read_only_fields = ['uuid', 'last_sent', 'create_date', 'update_date']


# Serializers for patient portal dashboard
class PatientDashboardAppointmentSerializer(serializers.ModelSerializer):
    """Simplified appointment serializer for dashboard"""
    provider_name = serializers.CharField(source='provider.get_full_name', read_only=True)
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'appointment_date', 'appointment_time', 'provider_name',
            'appointment_type', 'status', 'notes'
        ]


class PatientDashboardPrescriptionSerializer(serializers.ModelSerializer):
    """Simplified prescription serializer for dashboard"""
    medication_name = serializers.CharField(source='medication.name', read_only=True)
    prescriber_name = serializers.CharField(source='prescriber.get_full_name', read_only=True)
    
    class Meta:
        model = Prescription
        fields = [
            'id', 'medication_name', 'dosage', 'quantity', 'refills_remaining',
            'prescriber_name', 'date_prescribed', 'status'
        ]


class PatientDashboardLabResultSerializer(serializers.ModelSerializer):
    """Simplified lab result serializer for dashboard"""
    test_name = serializers.CharField(source='lab_order.test_name', read_only=True)
    ordered_by_name = serializers.CharField(source='lab_order.ordered_by.get_full_name', read_only=True)
    
    class Meta:
        model = LabResult
        fields = [
            'id', 'test_name', 'result_value', 'reference_range',
            'status', 'result_date', 'ordered_by_name'
        ]


class PatientPortalDashboardSerializer(serializers.Serializer):
    """Patient portal dashboard data serializer"""
    patient_info = serializers.DictField()
    upcoming_appointments = PatientDashboardAppointmentSerializer(many=True)
    recent_prescriptions = PatientDashboardPrescriptionSerializer(many=True)
    recent_lab_results = PatientDashboardLabResultSerializer(many=True)
    unread_messages = serializers.IntegerField()
    health_reminders = PatientHealthReminderSerializer(many=True)
    education_resources = PatientEducationResourceSerializer(many=True)


class PatientAuthenticationSerializer(serializers.Serializer):
    """Patient authentication serializer"""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    two_factor_code = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if not username or not password:
            raise serializers.ValidationError('Username and password are required')
        
        return attrs


class PatientRegistrationSerializer(serializers.Serializer):
    """Patient registration serializer"""
    username = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    password_confirm = serializers.CharField(write_only=True)
    
    # Patient identification
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    date_of_birth = serializers.DateField()
    medical_record_number = serializers.CharField(max_length=50, required=False)
    
    # Verification info
    phone_number = serializers.CharField(max_length=17, required=False)
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError('Passwords do not match')
        
        # Check if username already exists
        if PatientPortalAccess.objects.filter(username=attrs['username']).exists():
            raise serializers.ValidationError('Username already exists')
        
        # Check if email already exists
        if PatientPortalAccess.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError('Email already registered')
        
        return attrs
