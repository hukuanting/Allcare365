"""
Document Management Models

This module provides comprehensive document management functionality including:
- Document storage and versioning
- Electronic signatures (eSign)
- Document categories and templates
- Access control and sharing
- Audit trails for compliance
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
import uuid
import os


class BaseModel(models.Model):
    """Base model with common fields for all models"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='%(class)s_created')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='%(class)s_updated')
    is_active = models.BooleanField(default=True)
    
    class Meta:
        abstract = True


class DocumentCategory(BaseModel):
    """Document categories for organization and classification"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    parent_category = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    
    # Category settings
    requires_signature = models.BooleanField(default=False)
    auto_expire_days = models.IntegerField(null=True, blank=True, help_text="Auto-expire documents after N days")
    allowed_file_types = models.JSONField(default=list, help_text="Allowed file extensions")
    max_file_size_mb = models.IntegerField(default=50, help_text="Maximum file size in MB")
    
    # Access control
    access_level = models.CharField(max_length=20, choices=[
        ('public', 'Public'),
        ('internal', 'Internal Only'),
        ('restricted', 'Restricted'),
        ('confidential', 'Confidential'),
    ], default='internal')
    
    class Meta:
        verbose_name_plural = "Document Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_full_path(self):
        """Get the full category path"""
        if self.parent_category:
            return f"{self.parent_category.get_full_path()} > {self.name}"
        return self.name


class DocumentTemplate(BaseModel):
    """Document templates for standardized documents"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    category = models.ForeignKey(DocumentCategory, on_delete=models.CASCADE, related_name='templates')
    
    # Template content
    template_file = models.FileField(upload_to='document_templates/', validators=[
        FileExtensionValidator(allowed_extensions=['pdf', 'docx', 'xlsx', 'html'])
    ])
    template_type = models.CharField(max_length=20, choices=[
        ('form', 'Form Template'),
        ('letter', 'Letter Template'),
        ('report', 'Report Template'),
        ('consent', 'Consent Form'),
        ('other', 'Other'),
    ])
    
    # Template settings
    is_default = models.BooleanField(default=False)
    version = models.CharField(max_length=20, default='1.0')
    effective_date = models.DateField(default=timezone.localdate)
    expiration_date = models.DateField(null=True, blank=True)
    
    # Form fields for dynamic templates
    form_fields = models.JSONField(default=dict, help_text="Field definitions for dynamic forms")
    
    class Meta:
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.name} (v{self.version})"


class Document(BaseModel):
    """Main document model"""
    # Basic document information
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(DocumentCategory, on_delete=models.CASCADE, related_name='documents')
    template = models.ForeignKey(DocumentTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    
    # File information
    file = models.FileField(upload_to='documents/%Y/%m/%d/')
    original_filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    mime_type = models.CharField(max_length=100)
    file_hash = models.CharField(max_length=64, unique=True, help_text="SHA-256 hash for integrity")
    
    # Document metadata
    document_date = models.DateTimeField(default=timezone.now)
    document_type = models.CharField(max_length=50, choices=[
        ('clinical_note', 'Clinical Note'),
        ('lab_result', 'Lab Result'),
        ('image', 'Medical Image'),
        ('consent', 'Consent Form'),
        ('insurance', 'Insurance Document'),
        ('correspondence', 'Correspondence'),
        ('administrative', 'Administrative'),
        ('other', 'Other'),
    ])
    
    # Patient and encounter linking
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='documents', null=True, blank=True)
    encounter = models.ForeignKey('medical_records.MedicalRecord', on_delete=models.SET_NULL, null=True, blank=True)
    provider = models.ForeignKey('administration.Provider', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Document status and lifecycle
    status = models.CharField(max_length=20, choices=[
        ('draft', 'Draft'),
        ('pending_review', 'Pending Review'),
        ('active', 'Active'),
        ('archived', 'Archived'),
        ('deleted', 'Deleted'),
    ], default='draft')
    
    # Version control
    version = models.CharField(max_length=20, default='1.0')
    previous_version = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='newer_versions')
    is_current_version = models.BooleanField(default=True)
    
    # Access control
    is_confidential = models.BooleanField(default=False)
    access_level = models.CharField(max_length=20, choices=[
        ('public', 'Public'),
        ('internal', 'Internal Only'),
        ('restricted', 'Restricted'),
        ('confidential', 'Confidential'),
    ], default='internal')
    
    # Compliance and audit
    retention_date = models.DateField(null=True, blank=True, help_text="Date when document can be destroyed")
    last_accessed = models.DateTimeField(null=True, blank=True)
    last_accessed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='last_accessed_documents')
    
    class Meta:
        ordering = ['-document_date', '-created_at']
        indexes = [
            models.Index(fields=['patient', 'document_date']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['file_hash']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.document_date.strftime('%Y-%m-%d')}"
    
    def get_file_extension(self):
        """Get file extension"""
        return os.path.splitext(self.original_filename)[1].lower()
    
    def is_image(self):
        """Check if document is an image"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.dcm']
        return self.get_file_extension() in image_extensions
    
    def is_pdf(self):
        """Check if document is a PDF"""
        return self.get_file_extension() == '.pdf'


class DocumentVersion(BaseModel):
    """Document version history"""
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='versions')
    version_number = models.CharField(max_length=20)
    file = models.FileField(upload_to='document_versions/%Y/%m/%d/')
    file_size = models.BigIntegerField()
    file_hash = models.CharField(max_length=64)
    
    # Version metadata
    version_notes = models.TextField(blank=True)
    is_current = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['document', 'version_number']
    
    def __str__(self):
        return f"{self.document.title} v{self.version_number}"


class DocumentShare(BaseModel):
    """Document sharing and access permissions"""
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='shares')
    shared_with_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    shared_with_role = models.CharField(max_length=50, blank=True, help_text="Role-based sharing")
    
    # Permission settings
    can_view = models.BooleanField(default=True)
    can_download = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    can_share = models.BooleanField(default=False)
    
    # Access control
    access_start_date = models.DateTimeField(default=timezone.now)
    access_end_date = models.DateTimeField(null=True, blank=True)
    access_count = models.IntegerField(default=0)
    max_access_count = models.IntegerField(null=True, blank=True)
    
    # Notification settings
    notify_on_access = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['document', 'shared_with_user']
    
    def __str__(self):
        return f"{self.document.title} shared with {self.shared_with_user}"
    
    def is_access_valid(self):
        """Check if access is still valid"""
        now = timezone.now()
        if self.access_end_date and now > self.access_end_date:
            return False
        if self.max_access_count and self.access_count >= self.max_access_count:
            return False
        return True


class DocumentSignature(BaseModel):
    """Electronic signatures for documents"""
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='signatures')
    signer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='document_signatures')
    
    # Signature data
    signature_type = models.CharField(max_length=20, choices=[
        ('electronic', 'Electronic Signature'),
        ('digital', 'Digital Signature'),
        ('biometric', 'Biometric Signature'),
    ], default='electronic')
    
    signature_data = models.TextField(help_text="Base64 encoded signature image or digital certificate")
    signature_hash = models.CharField(max_length=64, help_text="Hash of signature for verification")
    
    # Signature metadata
    signed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    
    # Verification
    is_verified = models.BooleanField(default=False)
    verification_method = models.CharField(max_length=50, blank=True)
    verification_date = models.DateTimeField(null=True, blank=True)
    
    # Legal compliance
    signature_intent = models.CharField(max_length=100, help_text="Purpose of signature")
    witness = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='witnessed_signatures')
    
    class Meta:
        ordering = ['-signed_at']
        unique_together = ['document', 'signer', 'signature_intent']
    
    def __str__(self):
        return f"{self.document.title} signed by {self.signer.get_full_name()}"


class DocumentComment(BaseModel):
    """Comments and annotations on documents"""
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='document_comments')
    
    # Comment content
    comment = models.TextField()
    comment_type = models.CharField(max_length=20, choices=[
        ('note', 'Note'),
        ('review', 'Review Comment'),
        ('approval', 'Approval'),
        ('rejection', 'Rejection'),
        ('question', 'Question'),
    ], default='note')
    
    # Position information for annotations
    page_number = models.IntegerField(null=True, blank=True)
    x_position = models.FloatField(null=True, blank=True)
    y_position = models.FloatField(null=True, blank=True)
    
    # Threading
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment on {self.document.title} by {self.author.get_full_name()}"


class DocumentAuditLog(BaseModel):
    """Audit log for document access and modifications"""
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Action details
    action = models.CharField(max_length=20, choices=[
        ('created', 'Created'),
        ('view', 'Viewed'),
        ('download', 'Downloaded'),
        ('upload', 'Uploaded'),
        ('edit', 'Edited'),
        ('delete', 'Deleted'),
        ('share', 'Shared'),
        ('sign', 'Signed'),
        ('comment', 'Commented'),
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
    ])
    
    # Context information
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    session_id = models.CharField(max_length=100, blank=True)
    
    # Additional details
    details = models.JSONField(default=dict, help_text="Additional action details")
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['document', 'action']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        user_name = self.user.get_full_name() if self.user else "System"
        return f"{user_name} {self.action} {self.document.title}"


# Signal handlers for audit logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=Document)
def create_document_audit_log(sender, instance, created, **kwargs):
    """Create audit log entry when document is created or updated"""
    if created:
        action = 'created'
    else:
        action = 'edit'
    
    DocumentAuditLog.objects.create(
        document=instance,
        user=instance.created_by if created else instance.updated_by,
        action=action,
        details={'timestamp': timezone.now().isoformat()}
    )

@receiver(post_delete, sender=Document)
def delete_document_audit_log(sender, instance, **kwargs):
    """Create audit log entry when document is deleted"""
    DocumentAuditLog.objects.create(
        document=instance,
        user=instance.updated_by,
        action='delete',
        details={'timestamp': timezone.now().isoformat()}
    )
