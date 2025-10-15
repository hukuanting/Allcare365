"""
Django Admin Configuration for ESign Module

Provides administrative interface for managing electronic signatures,
configurations, and audit logs.
"""

from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import (
    ESignSignature,
    ESignConfiguration, 
    ESignAuditLog,
    ESignTemplate
)


@admin.register(ESignSignature)
class ESignSignatureAdmin(admin.ModelAdmin):
    """Admin interface for electronic signatures"""
    
    list_display = [
        'id',
        'signer_name',
        'signature_type',
        'content_type',
        'object_id',
        'datetime_signed',
        'is_lock',
        'verification_status'
    ]
    
    list_filter = [
        'signature_type',
        'is_lock',
        'datetime_signed',
        'content_type',
        'signer__is_staff'
    ]
    
    search_fields = [
        'signer__username',
        'signer__first_name',
        'signer__last_name',
        'amendment_note'
    ]
    
    readonly_fields = [
        'content_hash',
        'signature_hash',
        'datetime_signed',
        'created_at',
        'updated_at',
        'verification_status'
    ]
    
    fieldsets = (
        (_('Signature Information'), {
            'fields': (
                'content_type',
                'object_id',
                'signer',
                'signature_type',
                'is_lock'
            )
        }),
        (_('Cryptographic Data'), {
            'fields': (
                'content_hash',
                'signature_hash',
                'verification_status'
            ),
            'classes': ('collapse',)
        }),
        (_('Additional Information'), {
            'fields': (
                'amendment_note',
                'signature_data',
                'ip_address',
                'user_agent'
            ),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': (
                'datetime_signed',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    def signer_name(self, obj):
        """Display signer's full name"""
        return obj.signer_full_name
    signer_name.short_description = _('Signer')
    
    def verification_status(self, obj):
        """Display signature verification status"""
        if obj.verify_signature():
            return format_html(
                '<span style="color: green;">✓ Valid</span>'
            )
        else:
            return format_html(
                '<span style="color: red;">✗ Invalid</span>'
            )
    verification_status.short_description = _('Verification')
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of signatures for audit purposes"""
        return False


@admin.register(ESignConfiguration)
class ESignConfigurationAdmin(admin.ModelAdmin):
    """Admin interface for ESign configurations"""
    
    list_display = [
        'module',
        'require_signature',
        'auto_lock_on_sign',
        'allow_amendments',
        'allowed_signers_count',
        'updated_at'
    ]
    
    list_filter = [
        'module',
        'require_signature',
        'auto_lock_on_sign',
        'allow_amendments',
        'notify_on_signature'
    ]
    
    fieldsets = (
        (_('Module Configuration'), {
            'fields': (
                'module',
                'require_signature',
                'auto_lock_on_sign',
                'allow_amendments'
            )
        }),
        (_('Access Control'), {
            'fields': (
                'allowed_signers',
            )
        }),
        (_('Validation Settings'), {
            'fields': (
                'signature_validity_days',
                'require_reason_for_amendment'
            )
        }),
        (_('Notifications'), {
            'fields': (
                'notify_on_signature',
                'notify_on_amendment'
            )
        }),
        (_('Advanced'), {
            'fields': (
                'configuration_data',
            ),
            'classes': ('collapse',)
        })
    )
    
    filter_horizontal = ['allowed_signers']
    
    def allowed_signers_count(self, obj):
        """Display count of allowed signers"""
        count = obj.allowed_signers.count()
        if count == 0:
            return _('All users')
        return f"{count} users"
    allowed_signers_count.short_description = _('Allowed Signers')


@admin.register(ESignAuditLog)
class ESignAuditLogAdmin(admin.ModelAdmin):
    """Admin interface for ESign audit logs"""
    
    list_display = [
        'id',
        'user',
        'action',
        'content_type',
        'object_id',
        'timestamp',
        'ip_address'
    ]
    
    list_filter = [
        'action',
        'content_type',
        'timestamp',
        'user__is_staff'
    ]
    
    search_fields = [
        'user__username',
        'user__first_name',
        'user__last_name',
        'ip_address'
    ]
    
    readonly_fields = [
        'signature',
        'user',
        'action',
        'content_type',
        'object_id',
        'action_details',
        'ip_address',
        'user_agent',
        'timestamp'
    ]
    
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        """Prevent manual creation of audit logs"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of audit logs"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent modification of audit logs"""
        return False


@admin.register(ESignTemplate)
class ESignTemplateAdmin(admin.ModelAdmin):
    """Admin interface for ESign templates"""
    
    list_display = [
        'name',
        'module',
        'is_active',
        'created_by',
        'created_at',
        'updated_at'
    ]
    
    list_filter = [
        'module',
        'is_active',
        'created_at'
    ]
    
    search_fields = [
        'name',
        'description'
    ]
    
    fieldsets = (
        (_('Template Information'), {
            'fields': (
                'name',
                'description',
                'module',
                'is_active'
            )
        }),
        (_('Template Configuration'), {
            'fields': (
                'template_data',
                'required_fields',
                'signature_workflow'
            )
        }),
        (_('Metadata'), {
            'fields': (
                'created_by',
            ),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['created_by']
    
    def save_model(self, request, obj, form, change):
        """Set created_by to current user"""
        if not change:  # Only set on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# Inline admin for signatures on other models
class ESignSignatureInline(admin.TabularInline):
    """Inline for showing signatures on related objects"""
    
    model = ESignSignature
    extra = 0
    readonly_fields = [
        'signer',
        'signature_type',
        'datetime_signed',
        'is_lock',
        'content_hash',
        'signature_hash'
    ]
    
    fields = [
        'signer',
        'signature_type',
        'datetime_signed',
        'is_lock',
        'amendment_note'
    ]
    
    def has_add_permission(self, request, obj=None):
        """Prevent adding signatures through inline"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deleting signatures through inline"""
        return False
