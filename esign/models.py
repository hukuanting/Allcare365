"""
Electronic Signature Models

Provides models for managing electronic signatures on medical documents,
forms, and encounters with full audit trail capabilities.
"""

import hashlib
import json
from datetime import datetime
from typing import Dict, Any, Optional, List

from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from patients.models import Patient


class ESignManager(models.Manager):
    """Custom manager for electronic signatures"""
    
    def for_object(self, obj):
        """Get all signatures for a specific object"""
        content_type = ContentType.objects.get_for_model(obj)
        return self.filter(
            content_type=content_type,
            object_id=obj.pk
        )
    
    def signed_objects(self, model_class):
        """Get all objects of a type that have signatures"""
        content_type = ContentType.objects.get_for_model(model_class)
        return self.filter(content_type=content_type).values_list('object_id', flat=True).distinct()
    
    def locked_objects(self, model_class):
        """Get all objects of a type that are locked"""
        content_type = ContentType.objects.get_for_model(model_class)
        return self.filter(
            content_type=content_type,
            is_lock=True
        ).values_list('object_id', flat=True).distinct()


class ESignSignature(models.Model):
    """
    Electronic signature model for medical documents and forms
    
    Stores cryptographic signatures with full audit trail and 
    supports locking of signed documents.
    """
    
    SIGNATURE_TYPES = [
        ('signature', _('Signature')),
        ('lock', _('Lock')),
        ('amendment', _('Amendment')),
        ('approval', _('Approval')),
        ('review', _('Review')),
    ]
    
    # Generic foreign key to any signable object
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        help_text=_("The type of object being signed")
    )
    object_id = models.PositiveIntegerField(
        help_text=_("The ID of the object being signed")
    )
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Signature metadata
    signer = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='esign_signatures',
        help_text=_("User who created the signature")
    )
    
    signature_type = models.CharField(
        max_length=20,
        choices=SIGNATURE_TYPES,
        default='signature',
        help_text=_("Type of signature action")
    )
    
    is_lock = models.BooleanField(
        default=False,
        help_text=_("Whether this signature locks the object from editing")
    )
    
    datetime_signed = models.DateTimeField(
        default=timezone.now,
        help_text=_("When the signature was created")
    )
    
    # Cryptographic data
    content_hash = models.CharField(
        max_length=64,
        help_text=_("SHA-256 hash of the signed content")
    )
    
    signature_hash = models.CharField(
        max_length=64,
        help_text=_("SHA-256 hash of the signature data")
    )
    
    # Additional data
    amendment_note = models.TextField(
        blank=True,
        help_text=_("Amendment or signature notes")
    )
    
    signature_data = models.JSONField(
        default=dict,
        help_text=_("Additional signature metadata")
    )
    
    # Audit fields
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text=_("IP address from which signature was created")
    )
    
    user_agent = models.TextField(
        blank=True,
        help_text=_("Browser user agent string")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = ESignManager()
    
    class Meta:
        db_table = 'esign_signatures'
        verbose_name = _('Electronic Signature')
        verbose_name_plural = _('Electronic Signatures')
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['signer', 'datetime_signed']),
            models.Index(fields=['is_lock']),
            models.Index(fields=['signature_type']),
        ]
        ordering = ['-datetime_signed']
    
    def __str__(self):
        signer_name = self.signer.get_full_name() or self.signer.username
        return f"Signature by {signer_name} on {self.datetime_signed}"
    
    def save(self, *args, **kwargs):
        """Override save to generate signature hash"""
        if not self.signature_hash:
            self.signature_hash = self.generate_signature_hash()
        super().save(*args, **kwargs)
    
    def generate_signature_hash(self) -> str:
        """Generate cryptographic hash of signature data"""
        signature_data = {
            'content_type': self.content_type.pk,
            'object_id': self.object_id,
            'signer_id': self.signer.pk,
            'signature_type': self.signature_type,
            'datetime_signed': self.datetime_signed.isoformat(),
            'content_hash': self.content_hash,
            'amendment_note': self.amendment_note,
        }
        
        signature_string = json.dumps(signature_data, sort_keys=True)
        return hashlib.sha256(signature_string.encode()).hexdigest()
    
    def verify_signature(self) -> bool:
        """Verify the integrity of the signature"""
        return self.signature_hash == self.generate_signature_hash()
    
    @classmethod
    def generate_content_hash(cls, content_data: Any) -> str:
        """Generate SHA-256 hash of content being signed"""
        if isinstance(content_data, str):
            content_bytes = content_data.encode()
        elif isinstance(content_data, dict):
            content_bytes = json.dumps(content_data, sort_keys=True).encode()
        else:
            content_bytes = str(content_data).encode()
        
        return hashlib.sha256(content_bytes).hexdigest()
    
    @property
    def signer_full_name(self) -> str:
        """Get the full name of the signer"""
        return self.signer.get_full_name() or self.signer.username
    
    @property
    def signer_credentials(self) -> str:
        """Get signer credentials from user profile"""
        if hasattr(self.signer, 'userprofile'):
            return getattr(self.signer.userprofile, 'credentials', '')
        return ''


class ESignConfiguration(models.Model):
    """
    Configuration settings for the electronic signature system
    """
    
    MODULES = [
        ('forms', _('Forms')),
        ('encounters', _('Encounters')),
        ('documents', _('Documents')),
        ('prescriptions', _('Prescriptions')),
        ('lab_results', _('Lab Results')),
    ]
    
    module = models.CharField(
        max_length=50,
        choices=MODULES,
        unique=True,
        help_text=_("Module this configuration applies to")
    )
    
    # Signature requirements
    require_signature = models.BooleanField(
        default=False,
        help_text=_("Whether signatures are required for this module")
    )
    
    auto_lock_on_sign = models.BooleanField(
        default=True,
        help_text=_("Whether to automatically lock objects when signed")
    )
    
    allow_amendments = models.BooleanField(
        default=True,
        help_text=_("Whether amendments are allowed after signing")
    )
    
    # Access control
    allowed_signers = models.ManyToManyField(
        User,
        blank=True,
        related_name='esign_configurations',
        help_text=_("Users allowed to sign in this module")
    )
    
    # Validation settings
    signature_validity_days = models.PositiveIntegerField(
        default=365,
        help_text=_("Number of days signatures remain valid")
    )
    
    require_reason_for_amendment = models.BooleanField(
        default=True,
        help_text=_("Whether amendment reason is required")
    )
    
    # Notification settings
    notify_on_signature = models.BooleanField(
        default=False,
        help_text=_("Send notifications when objects are signed")
    )
    
    notify_on_amendment = models.BooleanField(
        default=True,
        help_text=_("Send notifications when amendments are made")
    )
    
    # Additional settings
    configuration_data = models.JSONField(
        default=dict,
        help_text=_("Additional configuration parameters")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'esign_configurations'
        verbose_name = _('ESign Configuration')
        verbose_name_plural = _('ESign Configurations')
    
    def __str__(self):
        return f"ESign Config: {self.get_module_display()}"
    
    def can_user_sign(self, user: User) -> bool:
        """Check if user is allowed to sign in this module"""
        if not self.require_signature:
            return False
        
        if not self.allowed_signers.exists():
            return True  # No restrictions
        
        return self.allowed_signers.filter(pk=user.pk).exists()


class ESignAuditLog(models.Model):
    """
    Audit log for electronic signature activities
    """
    
    ACTIONS = [
        ('view', _('View')),
        ('sign', _('Sign')),
        ('lock', _('Lock')),
        ('unlock', _('Unlock')),
        ('amend', _('Amend')),
        ('verify', _('Verify')),
        ('export', _('Export')),
    ]
    
    signature = models.ForeignKey(
        ESignSignature,
        on_delete=models.CASCADE,
        related_name='audit_logs',
        null=True,
        blank=True,
        help_text=_("Related signature (if any)")
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='esign_audit_logs',
        help_text=_("User who performed the action")
    )
    
    action = models.CharField(
        max_length=20,
        choices=ACTIONS,
        help_text=_("Action performed")
    )
    
    # Object being acted upon
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        help_text=_("Type of object")
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Action details
    action_details = models.JSONField(
        default=dict,
        help_text=_("Detailed information about the action")
    )
    
    # Request metadata
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text=_("IP address of the request")
    )
    
    user_agent = models.TextField(
        blank=True,
        help_text=_("Browser user agent string")
    )
    
    timestamp = models.DateTimeField(
        default=timezone.now,
        help_text=_("When the action occurred")
    )
    
    class Meta:
        db_table = 'esign_audit_logs'
        verbose_name = _('ESign Audit Log')
        verbose_name_plural = _('ESign Audit Logs')
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['content_type', 'object_id']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user.username} {self.action} on {self.timestamp}"


class ESignTemplate(models.Model):
    """
    Templates for electronic signature forms and workflows
    """
    
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text=_("Template name")
    )
    
    description = models.TextField(
        blank=True,
        help_text=_("Template description")
    )
    
    # Template configuration
    module = models.CharField(
        max_length=50,
        choices=ESignConfiguration.MODULES,
        help_text=_("Module this template applies to")
    )
    
    template_data = models.JSONField(
        default=dict,
        help_text=_("Template configuration data")
    )
    
    # Signature requirements
    required_fields = models.JSONField(
        default=list,
        help_text=_("List of required fields for signing")
    )
    
    signature_workflow = models.JSONField(
        default=dict,
        help_text=_("Workflow configuration for signatures")
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this template is active")
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='created_esign_templates',
        help_text=_("User who created the template")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'esign_templates'
        verbose_name = _('ESign Template')
        verbose_name_plural = _('ESign Templates')
        ordering = ['name']
    
    def __str__(self):
        return self.name
