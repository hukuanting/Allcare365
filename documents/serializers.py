"""
Document Management Serializers

REST API serializers for document management functionality.
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    DocumentCategory, DocumentTemplate, Document, DocumentVersion,
    DocumentShare, DocumentSignature, DocumentComment, DocumentAuditLog
)


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user information for nested serialization"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'full_name', 'email']
        read_only_fields = ['id', 'username', 'full_name']


class DocumentCategorySerializer(serializers.ModelSerializer):
    """Document category serializer"""
    full_path = serializers.CharField(source='get_full_path', read_only=True)
    subcategories = serializers.SerializerMethodField()
    created_by = UserBasicSerializer(read_only=True)
    updated_by = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = DocumentCategory
        fields = [
            'id', 'name', 'description', 'parent_category', 'full_path',
            'requires_signature', 'auto_expire_days', 'allowed_file_types',
            'max_file_size_mb', 'access_level', 'subcategories',
            'created_at', 'updated_at', 'created_by', 'updated_by', 'is_active'
        ]
        read_only_fields = ['id', 'full_path', 'subcategories', 'created_at', 'updated_at']
    
    def get_subcategories(self, obj):
        """Get subcategories"""
        if hasattr(obj, 'subcategories'):
            return DocumentCategorySerializer(obj.subcategories.filter(is_active=True), many=True).data
        return []


class DocumentTemplateSerializer(serializers.ModelSerializer):
    """Document template serializer"""
    category = DocumentCategorySerializer(read_only=True)
    category_id = serializers.UUIDField(write_only=True)
    created_by = UserBasicSerializer(read_only=True)
    updated_by = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = DocumentTemplate
        fields = [
            'id', 'name', 'description', 'category', 'category_id',
            'template_file', 'template_type', 'is_default', 'version',
            'effective_date', 'expiration_date', 'form_fields',
            'created_at', 'updated_at', 'created_by', 'updated_by', 'is_active'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DocumentVersionSerializer(serializers.ModelSerializer):
    """Document version serializer"""
    created_by = UserBasicSerializer(read_only=True)
    file_size_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = DocumentVersion
        fields = [
            'id', 'version_number', 'file', 'file_size', 'file_size_mb',
            'file_hash', 'version_notes', 'is_current',
            'created_at', 'created_by'
        ]
        read_only_fields = ['id', 'file_hash', 'created_at']
    
    def get_file_size_mb(self, obj):
        """Get file size in MB"""
        return round(obj.file_size / (1024 * 1024), 2)


class DocumentShareSerializer(serializers.ModelSerializer):
    """Document sharing serializer"""
    shared_with_user = UserBasicSerializer(read_only=True)
    shared_with_user_id = serializers.IntegerField(write_only=True, required=False)
    created_by = UserBasicSerializer(read_only=True)
    is_access_valid = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = DocumentShare
        fields = [
            'id', 'document', 'shared_with_user', 'shared_with_user_id', 'shared_with_role',
            'can_view', 'can_download', 'can_edit', 'can_delete', 'can_share',
            'access_start_date', 'access_end_date', 'access_count', 'max_access_count',
            'notify_on_access', 'is_access_valid',
            'created_at', 'created_by'
        ]
        read_only_fields = ['id', 'access_count', 'is_access_valid', 'created_at']


class DocumentSignatureSerializer(serializers.ModelSerializer):
    """Document signature serializer"""
    signer = UserBasicSerializer(read_only=True)
    witness = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = DocumentSignature
        fields = [
            'id', 'signer', 'signature_type', 'signature_data', 'signature_hash',
            'signed_at', 'ip_address', 'user_agent', 'is_verified',
            'verification_method', 'verification_date', 'signature_intent', 'witness'
        ]
        read_only_fields = ['id', 'signature_hash', 'signed_at', 'is_verified', 'verification_date']
        extra_kwargs = {
            'signature_data': {'write_only': True},
            'ip_address': {'write_only': True},
            'user_agent': {'write_only': True},
        }


class DocumentCommentSerializer(serializers.ModelSerializer):
    """Document comment serializer"""
    author = UserBasicSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    
    class Meta:
        model = DocumentComment
        fields = [
            'id', 'author', 'comment', 'comment_type', 'page_number',
            'x_position', 'y_position', 'parent_comment', 'replies',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_replies(self, obj):
        """Get comment replies"""
        if hasattr(obj, 'replies'):
            return DocumentCommentSerializer(obj.replies.filter(is_active=True), many=True).data
        return []


class DocumentAuditLogSerializer(serializers.ModelSerializer):
    """Document audit log serializer"""
    user = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = DocumentAuditLog
        fields = [
            'id', 'user', 'action', 'ip_address', 'user_agent',
            'session_id', 'details', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class DocumentSerializer(serializers.ModelSerializer):
    """Main document serializer"""
    category = DocumentCategorySerializer(read_only=True)
    category_id = serializers.UUIDField(write_only=True)
    template = DocumentTemplateSerializer(read_only=True)
    template_id = serializers.UUIDField(write_only=True, required=False)
    created_by = UserBasicSerializer(read_only=True)
    updated_by = UserBasicSerializer(read_only=True)
    provider = serializers.SerializerMethodField()
    patient = serializers.SerializerMethodField()
    
    # File information
    file_size_mb = serializers.SerializerMethodField()
    file_extension = serializers.CharField(source='get_file_extension', read_only=True)
    is_image = serializers.BooleanField(source='is_image', read_only=True)
    is_pdf = serializers.BooleanField(source='is_pdf', read_only=True)
    
    # Related data
    versions = DocumentVersionSerializer(many=True, read_only=True)
    shares = DocumentShareSerializer(many=True, read_only=True)
    signatures = DocumentSignatureSerializer(many=True, read_only=True)
    comments = DocumentCommentSerializer(many=True, read_only=True)
    
    # Statistics
    view_count = serializers.SerializerMethodField()
    download_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = [
            'id', 'title', 'description', 'category', 'category_id',
            'template', 'template_id', 'file', 'original_filename',
            'file_size', 'file_size_mb', 'mime_type', 'file_hash',
            'file_extension', 'is_image', 'is_pdf',
            'document_date', 'document_type', 'patient', 'encounter',
            'provider', 'status', 'version', 'previous_version',
            'is_current_version', 'is_confidential', 'access_level',
            'retention_date', 'last_accessed', 'last_accessed_by',
            'versions', 'shares', 'signatures', 'comments',
            'view_count', 'download_count',
            'created_at', 'updated_at', 'created_by', 'updated_by', 'is_active'
        ]
        read_only_fields = [
            'id', 'file_size', 'mime_type', 'file_hash', 'file_extension',
            'is_image', 'is_pdf', 'file_size_mb', 'last_accessed',
            'last_accessed_by', 'view_count', 'download_count',
            'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'file': {'write_only': True},
        }
    
    def get_file_size_mb(self, obj):
        """Get file size in MB"""
        return round(obj.file_size / (1024 * 1024), 2)
    
    def get_provider(self, obj):
        """Get provider information"""
        if obj.provider:
            return {
                'id': obj.provider.id,
                'name': f"{obj.provider.first_name} {obj.provider.last_name}",
                'specialty': obj.provider.primary_specialty
            }
        return None
    
    def get_patient(self, obj):
        """Get patient information"""
        if obj.patient:
            return {
                'id': obj.patient.id,
                'name': obj.patient.full_name,
                'medical_record_number': obj.patient.medical_record_number
            }
        return None
    
    def get_view_count(self, obj):
        """Get document view count"""
        return obj.audit_logs.filter(action='view').count()
    
    def get_download_count(self, obj):
        """Get document download count"""
        return obj.audit_logs.filter(action='download').count()


class DocumentListSerializer(serializers.ModelSerializer):
    """Simplified document serializer for list views"""
    category = serializers.CharField(source='category.name', read_only=True)
    created_by = serializers.CharField(source='created_by.get_full_name', read_only=True)
    file_size_mb = serializers.SerializerMethodField()
    file_extension = serializers.CharField(source='get_file_extension', read_only=True)
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    provider_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = [
            'id', 'title', 'category', 'document_type', 'status',
            'document_date', 'file_size_mb', 'file_extension',
            'patient_name', 'provider_name', 'is_confidential',
            'created_by', 'created_at'
        ]
        read_only_fields = fields
    
    def get_file_size_mb(self, obj):
        """Get file size in MB"""
        return round(obj.file_size / (1024 * 1024), 2)
    
    def get_provider_name(self, obj):
        """Get provider name"""
        if obj.provider:
            return f"{obj.provider.first_name} {obj.provider.last_name}"
        return None


class DocumentUploadSerializer(serializers.ModelSerializer):
    """Document upload serializer"""
    category_id = serializers.UUIDField(write_only=True)
    patient_id = serializers.UUIDField(write_only=True, required=False)
    encounter_id = serializers.UUIDField(write_only=True, required=False)
    provider_id = serializers.UUIDField(write_only=True, required=False)
    
    class Meta:
        model = Document
        fields = [
            'title', 'description', 'category_id', 'file', 'document_type',
            'patient_id', 'encounter_id', 'provider_id', 'is_confidential',
            'access_level', 'retention_date'
        ]
    
    def validate_file(self, value):
        """Validate uploaded file"""
        # Check file size (50MB limit by default)
        max_size = 50 * 1024 * 1024  # 50MB
        if value.size > max_size:
            raise serializers.ValidationError(f"File size exceeds {max_size // (1024*1024)}MB limit")
        
        return value
