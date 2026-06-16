"""
Document Management Admin Configuration

Django admin interface for document management models.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from .models import (
    DocumentCategory, DocumentTemplate, Document, DocumentVersion,
    DocumentShare, DocumentSignature, DocumentComment, DocumentAuditLog
)


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    """Admin for document categories"""
    list_display = ['name', 'parent_category', 'access_level', 'requires_signature', 'document_count', 'is_active']
    list_filter = ['access_level', 'requires_signature', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['name']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'parent_category')
        }),
        ('Category Settings', {
            'fields': ('requires_signature', 'auto_expire_days', 'allowed_file_types', 'max_file_size_mb')
        }),
        ('Access Control', {
            'fields': ('access_level', 'is_active')
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )
    
    def document_count(self, obj):
        """Get number of documents in category"""
        return obj.documents.count()
    document_count.short_description = 'Documents'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('parent_category').annotate(
            document_count=Count('documents')
        )


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    """Admin for document templates"""
    list_display = ['name', 'category', 'template_type', 'version', 'is_default', 'effective_date', 'is_active']
    list_filter = ['template_type', 'is_default', 'category', 'is_active', 'effective_date']
    search_fields = ['name', 'description']
    ordering = ['category', 'name']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'category', 'template_type')
        }),
        ('Template File', {
            'fields': ('template_file',)
        }),
        ('Version Information', {
            'fields': ('version', 'is_default', 'effective_date', 'expiration_date')
        }),
        ('Form Fields', {
            'fields': ('form_fields',),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category')


class DocumentVersionInline(admin.TabularInline):
    """Inline for document versions"""
    model = DocumentVersion
    extra = 0
    readonly_fields = ['file_size', 'file_hash', 'created_at', 'created_by']
    fields = ['version_number', 'file', 'file_size', 'version_notes', 'is_current']


class DocumentShareInline(admin.TabularInline):
    """Inline for document shares"""
    model = DocumentShare
    extra = 0
    readonly_fields = ['access_count', 'created_at', 'created_by']
    fields = ['shared_with_user', 'can_view', 'can_download', 'can_edit', 'access_end_date']


class DocumentSignatureInline(admin.TabularInline):
    """Inline for document signatures"""
    model = DocumentSignature
    extra = 0
    readonly_fields = ['signed_at', 'ip_address', 'is_verified']
    fields = ['signer', 'signature_type', 'signature_intent', 'signed_at', 'is_verified']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Admin for documents"""
    list_display = ['title', 'category', 'document_type', 'patient_link', 'status', 'document_date', 'file_size_display', 'is_confidential']
    list_filter = ['category', 'document_type', 'status', 'is_confidential', 'access_level', 'created_at']
    search_fields = ['title', 'description', 'original_filename', 'patient__first_name', 'patient__last_name']
    ordering = ['-document_date', '-created_at']
    readonly_fields = ['file_size', 'mime_type', 'file_hash', 'last_accessed', 'last_accessed_by', 'created_at', 'updated_at', 'created_by', 'updated_by']
    date_hierarchy = 'document_date'
    
    fieldsets = (
        ('Document Information', {
            'fields': ('title', 'description', 'category', 'template', 'document_type')
        }),
        ('File Information', {
            'fields': ('file', 'original_filename', 'file_size', 'mime_type', 'file_hash')
        }),
        ('Associations', {
            'fields': ('patient', 'encounter', 'provider')
        }),
        ('Status & Version', {
            'fields': ('status', 'version', 'previous_version', 'is_current_version')
        }),
        ('Access Control', {
            'fields': ('is_confidential', 'access_level', 'retention_date')
        }),
        ('Access Tracking', {
            'fields': ('last_accessed', 'last_accessed_by'),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [DocumentVersionInline, DocumentShareInline, DocumentSignatureInline]
    
    def patient_link(self, obj):
        """Create link to patient"""
        if obj.patient:
            url = reverse('admin:patients_patient_change', args=[obj.patient.pk])
            return format_html('<a href="{}">{}</a>', url, obj.patient.full_name)
        return '-'
    patient_link.short_description = 'Patient'
    
    def file_size_display(self, obj):
        """Display file size in MB"""
        return f"{obj.file_size / (1024*1024):.2f} MB"
    file_size_display.short_description = 'File Size'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'category', 'patient', 'provider', 'created_by'
        )


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    """Admin for document versions"""
    list_display = ['document', 'version_number', 'file_size_display', 'is_current', 'created_at']
    list_filter = ['is_current', 'created_at']
    search_fields = ['document__title', 'version_number', 'version_notes']
    ordering = ['-created_at']
    readonly_fields = ['file_size', 'file_hash', 'created_at', 'created_by']
    
    def file_size_display(self, obj):
        """Display file size in MB"""
        return f"{obj.file_size / (1024*1024):.2f} MB"
    file_size_display.short_description = 'File Size'


@admin.register(DocumentShare)
class DocumentShareAdmin(admin.ModelAdmin):
    """Admin for document shares"""
    list_display = ['document', 'shared_with_user', 'can_view', 'can_download', 'can_edit', 'access_count', 'access_valid']
    list_filter = ['can_view', 'can_download', 'can_edit', 'can_delete', 'can_share', 'created_at']
    search_fields = ['document__title', 'shared_with_user__username', 'shared_with_user__first_name', 'shared_with_user__last_name']
    ordering = ['-created_at']
    readonly_fields = ['access_count', 'created_at', 'created_by']
    
    def access_valid(self, obj):
        """Check if access is valid"""
        return obj.is_access_valid()
    access_valid.boolean = True
    access_valid.short_description = 'Access Valid'


@admin.register(DocumentSignature)
class DocumentSignatureAdmin(admin.ModelAdmin):
    """Admin for document signatures"""
    list_display = ['document', 'signer', 'signature_type', 'signed_at', 'is_verified']
    list_filter = ['signature_type', 'is_verified', 'signed_at']
    search_fields = ['document__title', 'signer__username', 'signer__first_name', 'signer__last_name']
    ordering = ['-signed_at']
    readonly_fields = ['signature_hash', 'signed_at', 'ip_address', 'user_agent', 'verification_date']
    
    fieldsets = (
        ('Signature Information', {
            'fields': ('document', 'signer', 'signature_type', 'signature_intent')
        }),
        ('Signature Data', {
            'fields': ('signature_data', 'signature_hash'),
            'classes': ('collapse',)
        }),
        ('Context Information', {
            'fields': ('signed_at', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Verification', {
            'fields': ('is_verified', 'verification_method', 'verification_date', 'witness')
        })
    )


@admin.register(DocumentComment)
class DocumentCommentAdmin(admin.ModelAdmin):
    """Admin for document comments"""
    list_display = ['document', 'author', 'comment_type', 'comment_preview', 'created_at']
    list_filter = ['comment_type', 'created_at']
    search_fields = ['document__title', 'author__username', 'comment']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    def comment_preview(self, obj):
        """Show comment preview"""
        return obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
    comment_preview.short_description = 'Comment'


@admin.register(DocumentAuditLog)
class DocumentAuditLogAdmin(admin.ModelAdmin):
    """Admin for document audit logs"""
    list_display = ['document', 'user', 'action', 'created_at', 'ip_address']
    list_filter = ['action', 'created_at']
    search_fields = ['document__title', 'user__username', 'user__first_name', 'user__last_name']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        """Disable adding audit logs manually"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable changing audit logs"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Disable deleting audit logs"""
        return False
