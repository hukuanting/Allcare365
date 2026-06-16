from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    PatientPortalAccess, PortalMessage, PortalMessageAttachment,
    PatientPortalSession, PatientPortalAuditLog, PatientEducationResource,
    PatientPortalPreference, PatientFamilyAccess, PatientHealthReminder
)


@admin.register(PatientPortalAccess)
class PatientPortalAccessAdmin(admin.ModelAdmin):
    list_display = [
        'patient', 'username', 'email', 'is_active', 'is_verified',
        'last_login', 'failed_login_attempts', 'two_factor_enabled'
    ]
    list_filter = [
        'is_active', 'is_verified', 'two_factor_enabled',
        'email_notifications', 'sms_notifications', 'create_date'
    ]
    search_fields = ['patient__first_name', 'patient__last_name', 'username', 'email']
    readonly_fields = ['uuid', 'create_date', 'update_date', 'last_login']
    
    fieldsets = (
        ('Patient Information', {
            'fields': ('patient', 'username', 'email')
        }),
        ('Account Status', {
            'fields': ('is_active', 'is_verified', 'last_login', 'failed_login_attempts', 'locked_until')
        }),
        ('Security', {
            'fields': ('two_factor_enabled', 'two_factor_secret')
        }),
        ('Preferences', {
            'fields': ('email_notifications', 'sms_notifications', 'language_preference')
        }),
        ('System Fields', {
            'fields': ('uuid', 'created_by', 'updated_by', 'create_date', 'update_date'),
            'classes': ('collapse',)
        })
    )
    
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if obj:  # Editing existing object
            readonly_fields.extend(['patient', 'username'])
        return readonly_fields


class PortalMessageAttachmentInline(admin.TabularInline):
    model = PortalMessageAttachment
    extra = 0
    readonly_fields = ['uuid', 'file_size', 'content_type', 'create_date']


@admin.register(PortalMessage)
class PortalMessageAdmin(admin.ModelAdmin):
    list_display = [
        'patient', 'provider', 'subject', 'message_type', 'status',
        'is_urgent', 'is_read_by_patient', 'is_read_by_provider', 'create_date'
    ]
    list_filter = [
        'message_type', 'status', 'is_urgent', 'is_read_by_patient',
        'is_read_by_provider', 'create_date'
    ]
    search_fields = [
        'patient__first_name', 'patient__last_name', 'provider__first_name',
        'provider__last_name', 'subject', 'message'
    ]
    readonly_fields = ['uuid', 'thread_id', 'create_date', 'update_date']
    inlines = [PortalMessageAttachmentInline]
    
    fieldsets = (
        ('Message Details', {
            'fields': ('patient', 'provider', 'subject', 'message')
        }),
        ('Classification', {
            'fields': ('message_type', 'status', 'is_urgent', 'parent_message')
        }),
        ('Read Status', {
            'fields': (
                'is_read_by_patient', 'read_by_patient_date',
                'is_read_by_provider', 'read_by_provider_date'
            )
        }),
        ('System Fields', {
            'fields': ('uuid', 'thread_id', 'created_by', 'updated_by', 'create_date', 'update_date'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('patient', 'provider')


@admin.register(PatientPortalSession)
class PatientPortalSessionAdmin(admin.ModelAdmin):
    list_display = [
        'patient', 'ip_address', 'login_time', 'logout_time',
        'is_active', 'session_duration'
    ]
    list_filter = ['is_active', 'login_time']
    search_fields = ['patient__first_name', 'patient__last_name', 'ip_address']
    readonly_fields = ['uuid', 'session_key', 'login_time', 'session_duration']
    
    def session_duration(self, obj):
        if obj.logout_time:
            duration = obj.logout_time - obj.login_time
            return f"{duration.total_seconds():.0f} seconds"
        return "Active"
    session_duration.short_description = 'Duration'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('patient')


@admin.register(PatientPortalAuditLog)
class PatientPortalAuditLogAdmin(admin.ModelAdmin):
    list_display = [
        'patient', 'action', 'ip_address', 'success', 'create_date'
    ]
    list_filter = ['action', 'success', 'create_date']
    search_fields = [
        'patient__first_name', 'patient__last_name', 'action',
        'description', 'ip_address'
    ]
    readonly_fields = ['uuid', 'create_date', 'update_date']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('patient')
    
    def has_add_permission(self, request):
        return False  # Audit logs should not be manually created
    
    def has_change_permission(self, request, obj=None):
        return False  # Audit logs should not be modified


@admin.register(PatientEducationResource)
class PatientEducationResourceAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'resource_type', 'category', 'is_featured',
        'is_published', 'view_count', 'create_date'
    ]
    list_filter = [
        'resource_type', 'category', 'is_featured', 'is_published', 'create_date'
    ]
    search_fields = ['title', 'description', 'content']
    readonly_fields = ['uuid', 'view_count', 'create_date', 'update_date']
    
    fieldsets = (
        ('Content', {
            'fields': ('title', 'description', 'content', 'url', 'file', 'thumbnail')
        }),
        ('Classification', {
            'fields': ('resource_type', 'category', 'applicable_conditions')
        }),
        ('Publishing', {
            'fields': ('is_featured', 'is_published')
        }),
        ('Statistics', {
            'fields': ('view_count',)
        }),
        ('System Fields', {
            'fields': ('uuid', 'created_by', 'updated_by', 'create_date', 'update_date'),
            'classes': ('collapse',)
        })
    )
    
    filter_horizontal = ['applicable_conditions']


@admin.register(PatientPortalPreference)
class PatientPortalPreferenceAdmin(admin.ModelAdmin):
    list_display = [
        'patient', 'email_appointment_reminders', 'sms_appointment_reminders',
        'theme', 'share_with_family'
    ]
    list_filter = [
        'email_appointment_reminders', 'email_lab_results',
        'sms_appointment_reminders', 'theme', 'share_with_family'
    ]
    search_fields = ['patient__first_name', 'patient__last_name']
    readonly_fields = ['uuid', 'create_date', 'update_date']
    
    fieldsets = (
        ('Patient', {
            'fields': ('patient',)
        }),
        ('Email Notifications', {
            'fields': (
                'email_appointment_reminders', 'email_lab_results',
                'email_prescription_ready', 'email_messages'
            )
        }),
        ('SMS Notifications', {
            'fields': (
                'sms_appointment_reminders', 'sms_lab_results',
                'sms_prescription_ready', 'sms_messages'
            )
        }),
        ('Privacy Settings', {
            'fields': ('share_with_family', 'allow_research_contact')
        }),
        ('Interface', {
            'fields': ('theme', 'dashboard_widgets')
        }),
        ('System Fields', {
            'fields': ('uuid', 'created_by', 'updated_by', 'create_date', 'update_date'),
            'classes': ('collapse',)
        })
    )


@admin.register(PatientFamilyAccess)
class PatientFamilyAccessAdmin(admin.ModelAdmin):
    list_display = [
        'patient', 'family_member_name', 'relationship', 'access_level',
        'is_active', 'expires_date', 'is_expired_status'
    ]
    list_filter = [
        'relationship', 'access_level', 'is_active',
        'can_view_medical_records', 'can_schedule_appointments'
    ]
    search_fields = [
        'patient__first_name', 'patient__last_name',
        'family_member_name', 'family_member_email'
    ]
    readonly_fields = ['uuid', 'create_date', 'update_date', 'is_expired_status']
    
    fieldsets = (
        ('Family Member', {
            'fields': ('patient', 'family_member_name', 'family_member_email', 'relationship')
        }),
        ('Access Control', {
            'fields': ('access_level', 'is_active', 'expires_date')
        }),
        ('Permissions', {
            'fields': (
                'can_view_medical_records', 'can_view_appointments',
                'can_view_prescriptions', 'can_view_lab_results',
                'can_schedule_appointments', 'can_send_messages'
            )
        }),
        ('System Fields', {
            'fields': ('uuid', 'created_by', 'updated_by', 'create_date', 'update_date'),
            'classes': ('collapse',)
        })
    )
    
    def is_expired_status(self, obj):
        if obj.is_expired():
            return format_html('<span style="color: red;">Expired</span>')
        return format_html('<span style="color: green;">Active</span>')
    is_expired_status.short_description = 'Status'


@admin.register(PatientHealthReminder)
class PatientHealthReminderAdmin(admin.ModelAdmin):
    list_display = [
        'patient', 'title', 'reminder_type', 'frequency',
        'remind_date', 'is_active', 'is_completed'
    ]
    list_filter = [
        'reminder_type', 'frequency', 'is_active', 'is_completed',
        'send_email', 'send_sms', 'remind_date'
    ]
    search_fields = [
        'patient__first_name', 'patient__last_name',
        'title', 'description'
    ]
    readonly_fields = ['uuid', 'last_sent', 'create_date', 'update_date']
    
    fieldsets = (
        ('Reminder Details', {
            'fields': ('patient', 'title', 'description', 'reminder_type')
        }),
        ('Scheduling', {
            'fields': ('frequency', 'remind_date', 'next_due')
        }),
        ('Status', {
            'fields': ('is_active', 'is_completed', 'completed_date', 'last_sent')
        }),
        ('Delivery Methods', {
            'fields': ('send_email', 'send_sms', 'send_portal_notification')
        }),
        ('System Fields', {
            'fields': ('uuid', 'created_by', 'updated_by', 'create_date', 'update_date'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('patient')


# Register the PortalMessageAttachment model if needed separately
admin.site.register(PortalMessageAttachment)
