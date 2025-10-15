"""
Electronic Signature System API Views

This module provides REST API views for managing electronic signatures,
including signature creation, verification, audit logs, and configuration.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from datetime import datetime
import logging

from .models import ESignSignature, ESignConfiguration, ESignAuditLog, ESignTemplate
from .serializers import (
    ESignSignatureSerializer, ESignConfigurationSerializer,
    ESignAuditLogSerializer, ESignTemplateSerializer,
    ESignCreateSerializer, ESignStatusSerializer
)
from .services import ESignService

logger = logging.getLogger(__name__)


class ESignSignatureViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing electronic signatures
    
    Provides CRUD operations for signatures with additional
    actions for signing, verifying, and locking/unlocking.
    """
    queryset = ESignSignature.objects.all()
    serializer_class = ESignSignatureSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter signatures based on user permissions"""
        queryset = super().get_queryset()
        
        # Filter by content type and object ID if provided
        content_type = self.request.query_params.get('content_type')
        object_id = self.request.query_params.get('object_id')
        
        if content_type:
            queryset = queryset.filter(content_type__model=content_type)
        if object_id:
            queryset = queryset.filter(object_id=object_id)
            
        # Filter by user if not admin
        if not self.request.user.is_superuser:
            queryset = queryset.filter(signer=self.request.user)
            
        return queryset.order_by('-datetime_signed')
    
    @action(detail=False, methods=['post'])
    def create_signature(self, request):
        """
        Create a new electronic signature
        
        Required fields:
        - content_type_id: ID of the content type for the document
        - object_id: ID of the object being signed
        - signature_type: Type of signature (default: 'signature')
        - amendment_note: Optional note for the signature
        - password_confirmation: User's password for verification
        """
        serializer = ESignCreateSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                signature = serializer.save()
                
                response_serializer = ESignSignatureSerializer(signature)
                return Response(
                    response_serializer.data,
                    status=status.HTTP_201_CREATED
                )
                
        except ValueError as e:
            logger.error(f"Signature creation failed: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unexpected error during signature creation: {str(e)}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def verify_signature(self, request, pk=None):
        """
        Verify an electronic signature
        
        Returns signature validity and verification details.
        """
        signature = get_object_or_404(ESignSignature, pk=pk)
        
        try:
            service = ESignService()
            verification_result = service.verify_signature(signature)
            
            return Response({
                'is_valid': verification_result['is_valid'],
                'signature_id': signature.id,
                'content_type': signature.content_type.name if signature.content_type else None,
                'object_id': signature.object_id,
                'signed_by': signature.signer_full_name,
                'signed_at': signature.datetime_signed,
                'verification_timestamp': timezone.now(),
                'errors': verification_result.get('errors', [])
            })
            
        except Exception as e:
            logger.error(f"Signature verification failed: {str(e)}")
            return Response(
                {'error': 'Verification failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def lock_signature(self, request, pk=None):
        """
        Lock a signature to prevent modifications
        
        Requires admin permissions or signature owner.
        """
        signature = get_object_or_404(ESignSignature, pk=pk)
        
        # Check permissions
        if not (request.user.is_superuser or signature.user == request.user):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            service = ESignService()
            content_object = signature.content_object
            if content_object:
                service.lock_object(content_object, request.user)
            
            return Response({
                'message': 'Signature locked successfully',
                'signature_id': signature.id,
                'locked_at': timezone.now()
            })
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Lock operation failed: {str(e)}")
            return Response(
                {'error': 'Lock operation failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def unlock_signature(self, request, pk=None):
        """
        Unlock a signature
        
        Requires admin permissions or signature owner.
        """
        signature = get_object_or_404(ESignSignature, pk=pk)
        
        # Check permissions
        if not (request.user.is_superuser or signature.user == request.user):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            service = ESignService()
            content_object = signature.content_object
            if content_object:
                service.unlock_object(content_object, request.user)
            
            return Response({
                'message': 'Signature unlocked successfully',
                'signature_id': signature.id,
                'unlocked_at': timezone.now()
            })
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unlock operation failed: {str(e)}")
            return Response(
                {'error': 'Unlock operation failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """
        Get signature status and details
        """
        signature = get_object_or_404(ESignSignature, pk=pk)
        
        serializer = ESignStatusSerializer(signature)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def audit_log(self, request, pk=None):
        """
        Get audit log for a specific signature
        """
        signature = get_object_or_404(ESignSignature, pk=pk)
        
        # Check permissions
        if not (request.user.is_superuser or signature.user == request.user):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        audit_logs = ESignAuditLog.objects.filter(
            signature=signature
        ).order_by('-created_at')
        
        serializer = ESignAuditLogSerializer(audit_logs, many=True)
        return Response(serializer.data)


class ESignConfigurationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing electronic signature configuration
    
    Provides CRUD operations for system-wide signature settings.
    """
    queryset = ESignConfiguration.objects.all()
    serializer_class = ESignConfigurationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """
        Only allow admins to modify configuration
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated]
            # Add admin check
            return [permission() for permission in permission_classes]
        return super().get_permissions()
    
    def create(self, request, *args, **kwargs):
        """Override create to check admin permissions"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Admin permissions required'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """Override update to check admin permissions"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Admin permissions required'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Override destroy to check admin permissions"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Admin permissions required'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)


class ESignTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing electronic signature templates
    
    Provides CRUD operations for signature templates and rendering.
    """
    queryset = ESignTemplate.objects.all()
    serializer_class = ESignTemplateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter templates based on user permissions"""
        queryset = super().get_queryset()
        
        # Filter by module if provided
        module = self.request.query_params.get('module')
        if module:
            queryset = queryset.filter(module=module)
        
        # Only show active templates to non-admin users
        if not self.request.user.is_superuser:
            queryset = queryset.filter(is_active=True)
            
        return queryset.order_by('name')
    
    @action(detail=True, methods=['post'])
    def render(self, request, pk=None):
        """
        Render a template with provided context data
        
        Expected data:
        - context: Dictionary of template variables
        """
        template = get_object_or_404(ESignTemplate, pk=pk)
        
        context = request.data.get('context', {})
        
        try:
            # Simple template rendering using Django's template engine
            from django.template import Context, Template
            
            django_template = Template(template.template_content)
            rendered_content = django_template.render(Context(context))
            
            return Response({
                'template_id': template.id,
                'rendered_content': rendered_content,
                'rendered_at': timezone.now()
            })
            
        except Exception as e:
            logger.error(f"Template rendering failed: {str(e)}")
            return Response(
                {'error': 'Template rendering failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ESignAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing electronic signature audit logs
    
    Provides read-only access to audit trail records.
    """
    queryset = ESignAuditLog.objects.all()
    serializer_class = ESignAuditLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter audit logs based on user permissions"""
        queryset = super().get_queryset()
        
        # Filter by signature ID if provided
        signature_id = self.request.query_params.get('signature_id')
        if signature_id:
            queryset = queryset.filter(signature_id=signature_id)
        
        # Filter by content type if provided
        content_type = self.request.query_params.get('content_type')
        if content_type:
            queryset = queryset.filter(signature__content_type__model=content_type)
        
        # Filter by date range if provided
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__gte=date_from)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__date__lte=date_to)
            except ValueError:
                pass
        
        # Non-admin users can only see their own audit logs
        if not self.request.user.is_superuser:
            queryset = queryset.filter(signature__user=self.request.user)
            
        return queryset.order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Get audit log summary statistics
        """
        queryset = self.get_queryset()
        
        # Count by action type
        action_counts = {}
        for log in queryset:
            action = log.action
            action_counts[action] = action_counts.get(action, 0) + 1
        
        # Count by date (last 30 days)
        from django.utils import timezone
        from datetime import timedelta
        
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_logs = queryset.filter(created_at__gte=thirty_days_ago)
        
        return Response({
            'total_logs': queryset.count(),
            'recent_logs': recent_logs.count(),
            'action_counts': action_counts,
            'date_range': {
                'from': thirty_days_ago.date(),
                'to': timezone.now().date()
            }
        })
