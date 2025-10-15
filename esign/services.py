"""
ESign Services

Business logic for electronic signature operations including
signing, verification, locking, and audit trail management.
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import (
    ESignSignature,
    ESignConfiguration,
    ESignAuditLog,
    ESignTemplate
)


class ESignService:
    """
    Service class for electronic signature operations
    """
    
    def __init__(self):
        self.audit_service = ESignAuditService()
    
    def sign_object(
        self,
        obj: Any,
        user: User,
        signature_type: str = 'signature',
        amendment_note: str = '',
        request_meta: Optional[Dict] = None
    ) -> ESignSignature:
        """
        Create an electronic signature for an object
        
        Args:
            obj: The object being signed
            user: The user creating the signature
            signature_type: Type of signature (signature, lock, amendment, etc.)
            amendment_note: Optional note for amendments
            request_meta: Request metadata (IP, user agent, etc.)
        
        Returns:
            ESignSignature: The created signature
        
        Raises:
            ValidationError: If signing requirements are not met
            PermissionDenied: If user lacks permission to sign
        """
        content_type = ContentType.objects.get_for_model(obj)
        config = self._get_configuration(content_type.model)
        
        # Check permissions
        if not self._can_user_sign(user, config):
            raise PermissionDenied(_("User not authorized to sign this type of object"))
        
        # Check if object is already locked
        if self.is_locked(obj):
            if signature_type != 'amendment':
                raise ValidationError(_("Object is locked and cannot be modified"))
            
            if not config.allow_amendments:
                raise ValidationError(_("Amendments are not allowed for this type of object"))
        
        # Generate content hash
        content_data = self._extract_signable_content(obj)
        content_hash = ESignSignature.generate_content_hash(content_data)
        
        # Create signature
        with transaction.atomic():
            signature = ESignSignature.objects.create(
                content_type=content_type,
                object_id=obj.pk,
                signer=user,
                signature_type=signature_type,
                is_lock=config.auto_lock_on_sign and signature_type == 'signature',
                content_hash=content_hash,
                amendment_note=amendment_note,
                ip_address=request_meta.get('ip_address') if request_meta else None,
                user_agent=request_meta.get('user_agent') if request_meta else None
            )
            
            # Log the action
            self.audit_service.log_action(
                user=user,
                action='sign',
                obj=obj,
                signature=signature,
                details={
                    'signature_type': signature_type,
                    'is_lock': signature.is_lock,
                    'amendment_note': amendment_note
                },
                request_meta=request_meta
            )
        
        return signature
    
    def lock_object(
        self,
        obj: Any,
        user: User,
        request_meta: Optional[Dict] = None
    ) -> ESignSignature:
        """
        Lock an object to prevent further modifications
        
        Args:
            obj: The object to lock
            user: The user creating the lock
            request_meta: Request metadata
        
        Returns:
            ESignSignature: The lock signature
        """
        return self.sign_object(
            obj=obj,
            user=user,
            signature_type='lock',
            request_meta=request_meta
        )
    
    def unlock_object(
        self,
        obj: Any,
        user: User,
        reason: str = '',
        request_meta: Optional[Dict] = None
    ) -> None:
        """
        Unlock an object by marking lock signatures as inactive
        
        Args:
            obj: The object to unlock
            user: The user performing the unlock
            reason: Reason for unlocking
            request_meta: Request metadata
        """
        content_type = ContentType.objects.get_for_model(obj)
        
        # Check permissions (only admins or original signers can unlock)
        if not (user.is_superuser or user.has_perm('esign.can_unlock')):
            raise PermissionDenied(_("User not authorized to unlock objects"))
        
        with transaction.atomic():
            # Find active lock signatures
            lock_signatures = ESignSignature.objects.filter(
                content_type=content_type,
                object_id=obj.pk,
                signature_type='lock',
                is_lock=True
            )
            
            # Create unlock record for each lock
            for lock_sig in lock_signatures:
                ESignSignature.objects.create(
                    content_type=content_type,
                    object_id=obj.pk,
                    signer=user,
                    signature_type='unlock',
                    is_lock=False,
                    content_hash=lock_sig.content_hash,
                    amendment_note=f"Unlocked: {reason}",
                    ip_address=request_meta.get('ip_address') if request_meta else None,
                    user_agent=request_meta.get('user_agent') if request_meta else None
                )
            
            # Deactivate locks
            lock_signatures.update(is_lock=False)
            
            # Log the action
            self.audit_service.log_action(
                user=user,
                action='unlock',
                obj=obj,
                details={
                    'reason': reason,
                    'locks_removed': lock_signatures.count()
                },
                request_meta=request_meta
            )
    
    def is_signed(self, obj: Any) -> bool:
        """Check if an object has any signatures"""
        content_type = ContentType.objects.get_for_model(obj)
        return ESignSignature.objects.filter(
            content_type=content_type,
            object_id=obj.pk
        ).exists()
    
    def is_locked(self, obj: Any) -> bool:
        """Check if an object is locked"""
        content_type = ContentType.objects.get_for_model(obj)
        return ESignSignature.objects.filter(
            content_type=content_type,
            object_id=obj.pk,
            is_lock=True
        ).exists()
    
    def get_signatures(self, obj: Any) -> List[ESignSignature]:
        """Get all signatures for an object"""
        return list(ESignSignature.objects.for_object(obj))
    
    def get_latest_signature(self, obj: Any) -> Optional[ESignSignature]:
        """Get the most recent signature for an object"""
        signatures = ESignSignature.objects.for_object(obj).first()
        return signatures
    
    def verify_signature(self, signature: ESignSignature) -> Dict[str, Any]:
        """
        Verify the integrity of a signature
        
        Returns:
            Dict with verification results
        """
        result = {
            'is_valid': False,
            'signature_valid': False,
            'content_valid': False,
            'signer_valid': False,
            'timestamp_valid': False,
            'errors': []
        }
        
        try:
            # Verify signature hash
            result['signature_valid'] = signature.verify_signature()
            if not result['signature_valid']:
                result['errors'].append('Signature hash verification failed')
            
            # Verify signer still exists and is active
            result['signer_valid'] = signature.signer.is_active
            if not result['signer_valid']:
                result['errors'].append('Signer account is inactive')
            
            # Verify timestamp is reasonable
            config = self._get_configuration(signature.content_type.model)
            validity_period = timedelta(days=config.signature_validity_days)
            result['timestamp_valid'] = (
                timezone.now() - signature.datetime_signed <= validity_period
            )
            if not result['timestamp_valid']:
                result['errors'].append('Signature has expired')
            
            # Overall validity
            result['is_valid'] = all([
                result['signature_valid'],
                result['signer_valid'],
                result['timestamp_valid']
            ])
            
        except Exception as e:
            result['errors'].append(f'Verification error: {str(e)}')
        
        return result
    
    def _can_user_sign(self, user: User, config: ESignConfiguration) -> bool:
        """Check if user can sign with given configuration"""
        if not config.require_signature:
            return False
        
        return config.can_user_sign(user)
    
    def _get_configuration(self, model_name: str) -> ESignConfiguration:
        """Get configuration for a model type"""
        try:
            return ESignConfiguration.objects.get(module=model_name.lower())
        except ESignConfiguration.DoesNotExist:
            # Create default configuration
            return ESignConfiguration.objects.create(
                module=model_name.lower(),
                require_signature=False,
                auto_lock_on_sign=True,
                allow_amendments=True
            )
    
    def _extract_signable_content(self, obj: Any) -> Dict[str, Any]:
        """Extract content from object for signature generation"""
        content = {
            'model': obj._meta.label,
            'pk': obj.pk,
            'timestamp': timezone.now().isoformat()
        }
        
        # Add specific fields based on object type
        if hasattr(obj, 'get_signable_content'):
            content.update(obj.get_signable_content())
        else:
            # Default: include all non-system fields
            for field in obj._meta.fields:
                if not field.name.startswith('_') and field.name not in ['created_at', 'updated_at']:
                    value = getattr(obj, field.name)
                    if value is not None:
                        content[field.name] = str(value)
        
        return content


class ESignAuditService:
    """
    Service for managing electronic signature audit trails
    """
    
    def log_action(
        self,
        user: User,
        action: str,
        obj: Any,
        signature: Optional[ESignSignature] = None,
        details: Optional[Dict] = None,
        request_meta: Optional[Dict] = None
    ) -> ESignAuditLog:
        """
        Log an electronic signature action
        
        Args:
            user: User performing the action
            action: Action type (view, sign, lock, etc.)
            obj: Object being acted upon
            signature: Related signature (if any)
            details: Additional action details
            request_meta: Request metadata
        
        Returns:
            ESignAuditLog: The created audit log entry
        """
        content_type = ContentType.objects.get_for_model(obj)
        
        audit_log = ESignAuditLog.objects.create(
            signature=signature,
            user=user,
            action=action,
            content_type=content_type,
            object_id=obj.pk,
            action_details=details or {},
            ip_address=request_meta.get('ip_address') if request_meta else None,
            user_agent=request_meta.get('user_agent') if request_meta else None
        )
        
        return audit_log
    
    def get_audit_trail(self, obj: Any) -> List[ESignAuditLog]:
        """Get complete audit trail for an object"""
        content_type = ContentType.objects.get_for_model(obj)
        return list(
            ESignAuditLog.objects.filter(
                content_type=content_type,
                object_id=obj.pk
            ).select_related('user', 'signature')
        )
    
    def get_user_activity(
        self,
        user: User,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[ESignAuditLog]:
        """Get signature activity for a specific user"""
        queryset = ESignAuditLog.objects.filter(user=user)
        
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
        
        return list(queryset.select_related('signature'))


class ESignTemplateService:
    """
    Service for managing electronic signature templates
    """
    
    def create_template(
        self,
        name: str,
        module: str,
        created_by: User,
        description: str = '',
        template_data: Optional[Dict] = None,
        required_fields: Optional[List] = None,
        workflow: Optional[Dict] = None
    ) -> ESignTemplate:
        """
        Create a new signature template
        
        Args:
            name: Template name
            module: Module this template applies to
            created_by: User creating the template
            description: Template description
            template_data: Template configuration data
            required_fields: Required fields for signing
            workflow: Signature workflow configuration
        
        Returns:
            ESignTemplate: The created template
        """
        template = ESignTemplate.objects.create(
            name=name,
            description=description,
            module=module,
            template_data=template_data or {},
            required_fields=required_fields or [],
            signature_workflow=workflow or {},
            created_by=created_by
        )
        
        return template
    
    def get_template_for_object(self, obj: Any) -> Optional[ESignTemplate]:
        """Get the appropriate template for an object"""
        model_name = obj._meta.label.lower()
        
        try:
            return ESignTemplate.objects.filter(
                module=model_name,
                is_active=True
            ).first()
        except ESignTemplate.DoesNotExist:
            return None
    
    def validate_signature_requirements(
        self,
        obj: Any,
        template: ESignTemplate,
        user_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate that signature requirements are met
        
        Args:
            obj: Object being signed
            template: Signature template
            user_data: Data provided by user
        
        Returns:
            Dict with validation results
        """
        result = {
            'is_valid': True,
            'missing_fields': [],
            'errors': []
        }
        
        # Check required fields
        for field in template.required_fields:
            if field not in user_data or not user_data[field]:
                result['missing_fields'].append(field)
                result['is_valid'] = False
        
        # Additional validation based on workflow
        workflow = template.signature_workflow
        if 'validation_rules' in workflow:
            for rule in workflow['validation_rules']:
                if not self._validate_rule(obj, user_data, rule):
                    result['errors'].append(f"Validation failed: {rule.get('message', 'Unknown rule')}")
                    result['is_valid'] = False
        
        return result
    
    def _validate_rule(self, obj: Any, data: Dict[str, Any], rule: Dict[str, Any]) -> bool:
        """Validate a specific rule against data"""
        rule_type = rule.get('type')
        
        if rule_type == 'required':
            field = rule.get('field')
            return field in data and bool(data[field])
        
        elif rule_type == 'min_length':
            field = rule.get('field')
            min_length = rule.get('value', 0)
            return len(str(data.get(field, ''))) >= min_length
        
        elif rule_type == 'custom':
            # Custom validation logic
            condition = rule.get('condition')
            return self._evaluate_condition(obj, data, condition)
        
        return True
    
    def _evaluate_condition(self, obj: Any, data: Dict[str, Any], condition: str) -> bool:
        """Evaluate a custom condition"""
        # Implement custom condition evaluation logic
        # This could involve parsing condition strings and evaluating them
        # For safety, this should be implemented carefully to avoid code injection
        return True
