"""
Django REST Framework Serializers for ESign Module

Serializers for electronic signature API endpoints including
signature creation, verification, and audit trail data.
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from .models import (
    ESignSignature,
    ESignConfiguration,
    ESignAuditLog,
    ESignTemplate
)
from .services import ESignService


class ESignSignatureSerializer(serializers.ModelSerializer):
    """Serializer for electronic signatures"""
    
    signer_name = serializers.CharField(source='signer_full_name', read_only=True)
    signer_credentials = serializers.CharField(read_only=True)
    content_type_name = serializers.CharField(source='content_type.name', read_only=True)
    verification_status = serializers.SerializerMethodField()
    
    class Meta:
        model = ESignSignature
        fields = [
            'id',
            'content_type',
            'content_type_name',
            'object_id',
            'signer',
            'signer_name',
            'signer_credentials',
            'signature_type',
            'is_lock',
            'datetime_signed',
            'content_hash',
            'signature_hash',
            'amendment_note',
            'signature_data',
            'verification_status',
            'created_at'
        ]
        read_only_fields = [
            'id',
            'content_hash',
            'signature_hash',
            'datetime_signed',
            'created_at'
        ]
    
    def get_verification_status(self, obj):
        """Get signature verification status"""
        service = ESignService()
        verification = service.verify_signature(obj)
        return {
            'is_valid': verification['is_valid'],
            'errors': verification['errors']
        }


class ESignCreateSerializer(serializers.Serializer):
    """Serializer for creating electronic signatures"""
    
    content_type_id = serializers.IntegerField()
    object_id = serializers.IntegerField()
    signature_type = serializers.ChoiceField(
        choices=ESignSignature.SIGNATURE_TYPES,
        default='signature'
    )
    amendment_note = serializers.CharField(required=False, allow_blank=True, max_length=1000)
    password_confirmation = serializers.CharField(write_only=True, required=False)
    
    def validate(self, attrs):
        """Validate signature creation data"""
        content_type_id = attrs['content_type_id']
        object_id = attrs['object_id']
        
        try:
            content_type = ContentType.objects.get(id=content_type_id)
            model_class = content_type.model_class()
            obj = model_class.objects.get(pk=object_id)
            attrs['content_object'] = obj
        except (ContentType.DoesNotExist, model_class.DoesNotExist):
            raise serializers.ValidationError("Invalid content type or object ID")
        
        return attrs
    
    def create(self, validated_data):
        """Create electronic signature using service"""
        request = self.context['request']
        obj = validated_data['content_object']
        
        service = ESignService()
        signature = service.sign_object(
            obj=obj,
            user=request.user,
            signature_type=validated_data['signature_type'],
            amendment_note=validated_data.get('amendment_note', ''),
            request_meta={
                'ip_address': self._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')
            }
        )
        
        return signature
    
    def _get_client_ip(self, request):
        """Extract client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class ESignConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for ESign configurations"""
    
    allowed_signers_count = serializers.SerializerMethodField()
    module_display = serializers.CharField(source='get_module_display', read_only=True)
    
    class Meta:
        model = ESignConfiguration
        fields = [
            'id',
            'module',
            'module_display',
            'require_signature',
            'auto_lock_on_sign',
            'allow_amendments',
            'allowed_signers',
            'allowed_signers_count',
            'signature_validity_days',
            'require_reason_for_amendment',
            'notify_on_signature',
            'notify_on_amendment',
            'configuration_data',
            'created_at',
            'updated_at'
        ]
    
    def get_allowed_signers_count(self, obj):
        """Get count of allowed signers"""
        count = obj.allowed_signers.count()
        return count if count > 0 else "All users"


class ESignAuditLogSerializer(serializers.ModelSerializer):
    """Serializer for ESign audit logs"""
    
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    content_type_name = serializers.CharField(source='content_type.name', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    signature_info = serializers.SerializerMethodField()
    
    class Meta:
        model = ESignAuditLog
        fields = [
            'id',
            'signature',
            'signature_info',
            'user',
            'user_name',
            'action',
            'action_display',
            'content_type',
            'content_type_name',
            'object_id',
            'action_details',
            'ip_address',
            'user_agent',
            'timestamp'
        ]
    
    def get_signature_info(self, obj):
        """Get basic signature information if available"""
        if obj.signature:
            return {
                'id': obj.signature.id,
                'type': obj.signature.signature_type,
                'datetime_signed': obj.signature.datetime_signed
            }
        return None


class ESignTemplateSerializer(serializers.ModelSerializer):
    """Serializer for ESign templates"""
    
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    module_display = serializers.CharField(source='get_module_display', read_only=True)
    
    class Meta:
        model = ESignTemplate
        fields = [
            'id',
            'name',
            'description',
            'module',
            'module_display',
            'template_data',
            'required_fields',
            'signature_workflow',
            'is_active',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_by']
    
    def create(self, validated_data):
        """Set created_by to current user"""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class ESignStatusSerializer(serializers.Serializer):
    """Serializer for checking signature status of objects"""
    
    content_type_id = serializers.IntegerField()
    object_id = serializers.IntegerField()
    
    def validate(self, attrs):
        """Validate object exists"""
        content_type_id = attrs['content_type_id']
        object_id = attrs['object_id']
        
        try:
            content_type = ContentType.objects.get(id=content_type_id)
            model_class = content_type.model_class()
            obj = model_class.objects.get(pk=object_id)
            attrs['content_object'] = obj
        except (ContentType.DoesNotExist, model_class.DoesNotExist):
            raise serializers.ValidationError("Invalid content type or object ID")
        
        return attrs
    
    def to_representation(self, instance):
        """Return signature status for object"""
        obj = instance['content_object']
        service = ESignService()
        
        signatures = service.get_signatures(obj)
        latest_signature = service.get_latest_signature(obj)
        
        return {
            'is_signed': service.is_signed(obj),
            'is_locked': service.is_locked(obj),
            'signature_count': len(signatures),
            'latest_signature': ESignSignatureSerializer(latest_signature).data if latest_signature else None,
            'signatures': ESignSignatureSerializer(signatures, many=True).data
        }


class UserSerializer(serializers.ModelSerializer):
    """Simple user serializer for ESign purposes"""
    
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'full_name', 'email']
        read_only_fields = fields
