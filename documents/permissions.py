"""
Document Management Permissions

This module provides permission classes for document management functionality.
"""

from rest_framework import permissions
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils import timezone


class DocumentPermissions(permissions.BasePermission):
    """
    Custom permission class for document access control
    
    Permissions are based on:
    - Document ownership (uploader)
    - Document sharing (explicit shares)
    - Category access level
    - User roles and groups
    """
    
    def has_permission(self, request, view):
        """
        Check if user has permission to access document endpoints
        """
        # Require authentication for all document operations
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superusers have full access
        if request.user.is_superuser:
            return True
        
        # Check basic document management permissions
        if view.action in ['list', 'retrieve', 'my_documents', 'shared_with_me']:
            return request.user.has_perm('documents.view_document')
        
        if view.action in ['create', 'upload']:
            return request.user.has_perm('documents.add_document')
        
        if view.action in ['update', 'partial_update']:
            return request.user.has_perm('documents.change_document')
        
        if view.action in ['destroy', 'delete']:
            return request.user.has_perm('documents.delete_document')
        
        if view.action in ['sign']:
            return request.user.has_perm('documents.sign_document')
        
        if view.action in ['share']:
            return request.user.has_perm('documents.share_document')
        
        # Allow other actions if user has basic view permission
        return request.user.has_perm('documents.view_document')
    
    def has_object_permission(self, request, view, obj):
        """
        Check if user has permission to access specific document
        """
        # Superusers have full access
        if request.user.is_superuser:
            return True
        
        # Document owner has full access
        if hasattr(obj, 'uploaded_by') and obj.uploaded_by == request.user:
            return True
        
        # Check document sharing
        if hasattr(obj, 'shares'):
            shared_with_user = obj.shares.filter(
                shared_with=request.user,
                is_active=True
            ).exists()
            if shared_with_user:
                return self._check_share_permissions(request, view, obj)
        
        # Check category access level
        if hasattr(obj, 'category'):
            return self._check_category_access(request, view, obj)
        
        # For document versions, check parent document access
        if hasattr(obj, 'document'):
            return self.has_object_permission(request, view, obj.document)
        
        # Default deny
        return False
    
    def _check_share_permissions(self, request, view, obj):
        """
        Check permissions based on document sharing settings
        """
        share = obj.shares.filter(
            shared_with=request.user,
            is_active=True
        ).first()
        
        if not share:
            return False
        
        # Check if share has expired
        if share.expires_at and share.expires_at < timezone.now():
            return False
        
        # Check action permissions based on share settings
        if view.action in ['retrieve', 'list']:
            return True  # Read access always allowed for shared documents
        
        if view.action in ['download', 'preview']:
            return share.can_download
        
        if view.action in ['share']:
            return share.can_share
        
        if view.action in ['update', 'partial_update', 'destroy']:
            return share.access_level == 'edit'
        
        if view.action in ['sign']:
            return share.access_level in ['edit', 'sign']
        
        # Default to read-only access
        return view.action in ['retrieve', 'list']
    
    def _check_category_access(self, request, view, obj):
        """
        Check permissions based on category access level
        """
        if not hasattr(obj, 'category') or not obj.category:
            return False
        
        category = obj.category
        
        # Public documents - read-only access
        if category.access_level == 'public':
            return view.action in ['retrieve', 'list', 'download', 'preview']
        
        # Internal documents - require internal access
        if category.access_level == 'internal':
            if not request.user.groups.filter(name='Internal Users').exists():
                return False
            return view.action in ['retrieve', 'list', 'download', 'preview']
        
        # Restricted documents - require specific permissions
        if category.access_level == 'restricted':
            if not request.user.has_perm('documents.view_restricted'):
                return False
            return view.action in ['retrieve', 'list', 'download', 'preview']
        
        # Confidential documents - require confidential access
        if category.access_level == 'confidential':
            if not request.user.has_perm('documents.view_confidential'):
                return False
            return view.action in ['retrieve', 'list', 'download', 'preview']
        
        return False


class DocumentCategoryPermissions(permissions.BasePermission):
    """
    Permission class for document category management
    """
    
    def has_permission(self, request, view):
        """Check category management permissions"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        if view.action in ['list', 'retrieve']:
            return request.user.has_perm('documents.view_documentcategory')
        
        if view.action in ['create']:
            return request.user.has_perm('documents.add_documentcategory')
        
        if view.action in ['update', 'partial_update']:
            return request.user.has_perm('documents.change_documentcategory')
        
        if view.action in ['destroy']:
            return request.user.has_perm('documents.delete_documentcategory')
        
        return False


class DocumentTemplatePermissions(permissions.BasePermission):
    """
    Permission class for document template management
    """
    
    def has_permission(self, request, view):
        """Check template management permissions"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        if view.action in ['list', 'retrieve', 'download']:
            return request.user.has_perm('documents.view_documenttemplate')
        
        if view.action in ['create']:
            return request.user.has_perm('documents.add_documenttemplate')
        
        if view.action in ['update', 'partial_update', 'set_default']:
            return request.user.has_perm('documents.change_documenttemplate')
        
        if view.action in ['destroy']:
            return request.user.has_perm('documents.delete_documenttemplate')
        
        return False


class ElectronicSignaturePermissions(permissions.BasePermission):
    """
    Permission class for electronic signature management
    """
    
    def has_permission(self, request, view):
        """Check signature permissions"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        if view.action in ['list', 'retrieve']:
            return request.user.has_perm('documents.view_electronicsignature')
        
        if view.action in ['create', 'sign']:
            return request.user.has_perm('documents.add_electronicsignature')
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """Check object-level signature permissions"""
        if request.user.is_superuser:
            return True
        
        # Users can view their own signatures
        if hasattr(obj, 'signer') and obj.signer == request.user:
            return True
        
        # Document owner can view all signatures on their documents
        if hasattr(obj, 'document') and obj.document.uploaded_by == request.user:
            return True
        
        return False


def check_document_access(user, document, action='view'):
    """
    Utility function to check if user can perform action on document
    
    Args:
        user: Django User instance
        document: Document instance
        action: Action to perform ('view', 'edit', 'delete', 'share', 'sign')
    
    Returns:
        bool: True if user has permission, False otherwise
    """
    if not user or not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    # Document owner has full access
    if document.uploaded_by == user:
        return True
    
    # Check sharing permissions
    share = document.shares.filter(
        shared_with=user,
        is_active=True
    ).first()
    
    if share:
        # Check if share has expired
        if share.expires_at and share.expires_at < timezone.now():
            return False
        
        if action == 'view':
            return True
        elif action == 'download':
            return share.can_download
        elif action == 'share':
            return share.can_share
        elif action in ['edit', 'update']:
            return share.access_level == 'edit'
        elif action == 'sign':
            return share.access_level in ['edit', 'sign']
        elif action == 'delete':
            return share.access_level == 'edit' and user.has_perm('documents.delete_document')
    
    # Check category access level
    if document.category:
        if document.category.access_level == 'public':
            return action in ['view', 'download']
        elif document.category.access_level == 'internal':
            if user.groups.filter(name='Internal Users').exists():
                return action in ['view', 'download']
        elif document.category.access_level == 'restricted':
            if user.has_perm('documents.view_restricted'):
                return action in ['view', 'download']
        elif document.category.access_level == 'confidential':
            if user.has_perm('documents.view_confidential'):
                return action in ['view', 'download']
    
    return False


def get_user_accessible_documents(user, queryset=None):
    """
    Get documents that user has access to
    
    Args:
        user: Django User instance
        queryset: Optional base queryset to filter
    
    Returns:
        QuerySet: Filtered document queryset
    """
    if queryset is None:
        from .models import Document
        queryset = Document.objects.filter(is_active=True)
    
    if not user or not user.is_authenticated:
        return queryset.none()
    
    if user.is_superuser:
        return queryset
    
    # Build filter for accessible documents
    q_filters = Q()
    
    # Documents uploaded by user
    q_filters |= Q(uploaded_by=user)
    
    # Documents shared with user
    q_filters |= Q(
        shares__shared_with=user,
        shares__is_active=True
    )
    
    # Public documents
    q_filters |= Q(category__access_level='public')
    
    # Internal documents (if user is internal)
    if user.groups.filter(name='Internal Users').exists():
        q_filters |= Q(category__access_level='internal')
    
    # Restricted documents (if user has permission)
    if user.has_perm('documents.view_restricted'):
        q_filters |= Q(category__access_level='restricted')
    
    # Confidential documents (if user has permission)
    if user.has_perm('documents.view_confidential'):
        q_filters |= Q(category__access_level='confidential')
    
    return queryset.filter(q_filters).distinct()
