"""
Document Management Views

REST API views and web views for document management functionality.
"""

import hashlib
import mimetypes
import os
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, FileResponse, Http404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView, DetailView
from django.utils import timezone
from django.db.models import Q, Count
from django.core.files.storage import default_storage
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q, Count
from .models import (
    DocumentCategory, DocumentTemplate, Document, DocumentVersion,
    DocumentShare, DocumentSignature, DocumentComment, DocumentAuditLog
)
from .serializers import (
    DocumentCategorySerializer, DocumentTemplateSerializer, DocumentSerializer,
    DocumentVersionSerializer, DocumentShareSerializer, DocumentSignatureSerializer,
    DocumentCommentSerializer, DocumentAuditLogSerializer, DocumentListSerializer,
    DocumentUploadSerializer
)


# REST API ViewSets

class DocumentCategoryViewSet(viewsets.ModelViewSet):
    """Document Category ViewSet"""
    queryset = DocumentCategory.objects.filter(is_active=True)
    serializer_class = DocumentCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['parent_category', 'access_level', 'requires_signature']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get statistics for a category"""
        category = self.get_object()
        
        # Get document counts
        total_docs = category.documents.filter(is_active=True).count()
        docs_by_status = category.documents.filter(is_active=True).values('status').annotate(count=Count('id'))
        
        stats = {
            'total_documents': total_docs,
            'documents_by_status': {item['status']: item['count'] for item in docs_by_status},
            'subcategories_count': category.subcategories.filter(is_active=True).count(),
        }
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def tree(self, request):
        """Get category hierarchy tree"""
        root_categories = self.get_queryset().filter(parent_category__isnull=True)
        serializer = self.get_serializer(root_categories, many=True)
        return Response(serializer.data)


class DocumentTemplateViewSet(viewsets.ModelViewSet):
    """Document Template ViewSet"""
    queryset = DocumentTemplate.objects.filter(is_active=True)
    serializer_class = DocumentTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'template_type', 'is_default']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class DocumentViewSet(viewsets.ModelViewSet):
    """Document ViewSet"""
    queryset = Document.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'document_type', 'status', 'patient', 'provider', 'is_confidential']
    search_fields = ['title', 'description', 'original_filename']
    ordering_fields = ['title', 'document_date', 'created_at']
    ordering = ['-document_date', '-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return DocumentListSerializer
        elif self.action == 'create':
            return DocumentUploadSerializer
        return DocumentSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.select_related('category', 'patient', 'provider', 'created_by')
    
    def get_object(self):
        """Get object and check permissions"""
        obj = get_object_or_404(Document, pk=self.kwargs['pk'], is_active=True)
        
        # Check permissions
        if not self._check_permission(obj, 'view'):
            raise PermissionDenied("You don't have permission to access this document.")
        
        return obj
    
    def perform_create(self, serializer):
        # Calculate file hash and metadata
        file = serializer.validated_data['file']
        file_content = file.read()
        file_hash = hashlib.sha256(file_content).hexdigest()
        file.seek(0)  # Reset file pointer
        
        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(file.name)
        if not mime_type:
            mime_type = 'application/octet-stream'
        
        document = serializer.save(
            created_by=self.request.user,
            original_filename=file.name,
            file_size=file.size,
            mime_type=mime_type,
            file_hash=file_hash,
            is_current_version=True
        )
        
        # Log the upload action
        self._log_action(document, 'upload')
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
        self._log_action(serializer.instance, 'edit')
    
    def retrieve(self, request, *args, **kwargs):
        """Override retrieve to log view action"""
        instance = self.get_object()
        self._log_action(instance, 'view')
        
        # Update last accessed info
        instance.last_accessed = timezone.now()
        instance.last_accessed_by = request.user
        instance.save(update_fields=['last_accessed', 'last_accessed_by'])
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download document file"""
        document = self.get_object()
        
        # Check download permissions
        if not self._check_permission(document, 'download'):
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Log download action
        self._log_action(document, 'download')
        
        try:
            if default_storage.exists(document.file.name):
                response = FileResponse(
                    document.file.open('rb'),
                    content_type=document.mime_type,
                    as_attachment=True,
                    filename=document.original_filename
                )
                return response
            else:
                return Response(
                    {'error': 'File not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def my_documents(self, request):
        """Get documents uploaded by current user"""
        documents = self.get_queryset().filter(created_by=request.user)
        
        page = self.paginate_queryset(documents)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(documents, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def shared_with_me(self, request):
        """Get documents shared with current user"""
        # This would need proper DocumentShare model implementation
        documents = self.get_queryset().none()  # Empty queryset for now
        
        serializer = self.get_serializer(documents, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending_signatures(self, request):
        """Get documents pending signature from current user"""
        # This would need to be implemented based on signature model
        documents = self.get_queryset().filter(
            status='pending_review'  # Use existing status field
        )
        
        serializer = self.get_serializer(documents, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get document statistics"""
        queryset = self.get_queryset()
        
        # Basic counts
        total_documents = queryset.count()
        
        # Documents by category
        docs_by_category = queryset.values('category__name').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Documents by status
        docs_by_status = queryset.values('status').annotate(
            count=Count('id')
        )
        
        # Recent uploads (last 7 days)
        from django.utils import timezone
        from datetime import timedelta
        recent_uploads = queryset.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        stats = {
            'total_documents': total_documents,
            'documents_by_category': {item['category__name']: item['count'] for item in docs_by_category},
            'documents_by_status': {item['status']: item['count'] for item in docs_by_status},
            'recent_uploads': recent_uploads,
        }
        
        return Response(stats)
    
    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        """Share document with another user"""
        document = self.get_object()
        
        # Basic implementation - would need proper share model
        return Response({'message': 'Sharing functionality not fully implemented'}, 
                      status=status.HTTP_501_NOT_IMPLEMENTED)
    
    @action(detail=True, methods=['post'])
    def sign(self, request, pk=None):
        """Sign document"""
        document = self.get_object()
        
        # Basic implementation - would need proper signature model
        return Response({'message': 'Signing functionality not fully implemented'}, 
                      status=status.HTTP_501_NOT_IMPLEMENTED)
    
    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """Preview document"""
        document = self.get_object()
        
        # Check preview permissions
        if not self._check_permission(document, 'view'):
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Only allow preview for certain file types
        if document.mime_type:
            supported_types = ['image/', 'application/pdf', 'text/']
            if not any(document.mime_type.startswith(t) for t in supported_types):
                return Response(
                    {'error': 'File type not supported for preview'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Log preview action
        self._log_action(document, 'preview')
        
        try:
            if default_storage.exists(document.file.name):
                response = FileResponse(
                    document.file.open('rb'),
                    content_type=document.mime_type,
                )
                return response
            else:
                return Response(
                    {'error': 'File not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            return Response(
                {'error': f'Error accessing file: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _check_permission(self, document, action):
        """Check if user has permission for action"""
        user = self.request.user
        
        # Owner always has access
        if document.created_by == user:
            return True
        
        # Superuser has access
        if user.is_superuser:
            return True
        
        # Check shared permissions
        try:
            share = document.shares.get(shared_with_user=user)
            if action == 'view' and share.can_view:
                return True
            elif action == 'download' and share.can_download:
                return True
            elif action == 'edit' and share.can_edit:
                return True
        except DocumentShare.DoesNotExist:
            pass
        
        # Check public access
        if document.access_level == 'public' and action == 'view':
            return True
        
        return False
    
    def _log_action(self, document, action):
        """Log document action"""
        DocumentAuditLog.objects.create(
            document=document,
            user=self.request.user,
            action=action,
            ip_address=self._get_client_ip(self.request),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
            details={'timestamp': timezone.now().isoformat()}
        )
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class DocumentVersionViewSet(viewsets.ModelViewSet):
    """Document Version ViewSet"""
    queryset = DocumentVersion.objects.all()
    serializer_class = DocumentVersionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['document', 'is_current']
    ordering_fields = ['version_number', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return super().get_queryset().filter(
            Q(document__created_by=self.request.user)
        ).select_related('document', 'created_by')
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
        
        # Log the version creation
        DocumentAuditLog.objects.create(
            document=serializer.instance.document,
            user=self.request.user,
            action='version_created',
            details={'version': serializer.instance.version_number}
        )


class DocumentShareViewSet(viewsets.ModelViewSet):
    """Document Share ViewSet"""
    queryset = DocumentShare.objects.all()
    serializer_class = DocumentShareSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['document', 'shared_with_user', 'can_view', 'can_edit']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return super().get_queryset().filter(
            Q(document__created_by=self.request.user) |
            Q(shared_with_user=self.request.user)
        ).select_related('document', 'shared_with_user', 'created_by')
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class DocumentSignatureViewSet(viewsets.ModelViewSet):
    """Document Signature ViewSet"""
    queryset = DocumentSignature.objects.all()
    serializer_class = DocumentSignatureSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['document', 'signer', 'signature_type', 'is_verified']
    ordering_fields = ['signed_at']
    ordering = ['-signed_at']
    
    def get_queryset(self):
        return super().get_queryset().filter(
            Q(document__created_by=self.request.user) |
            Q(signer=self.request.user)
        ).select_related('document', 'signer')
    
    def perform_create(self, serializer):
        serializer.save(signer=self.request.user, signed_at=timezone.now())


class DocumentCommentViewSet(viewsets.ModelViewSet):
    """Document Comment ViewSet"""
    queryset = DocumentComment.objects.all()
    serializer_class = DocumentCommentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['document', 'author']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return super().get_queryset().filter(
            Q(document__created_by=self.request.user) |
            Q(document__shares__shared_with_user=self.request.user)
        ).select_related('document', 'author')
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class DocumentAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Document Audit Log ViewSet - Read Only"""
    queryset = DocumentAuditLog.objects.all()
    serializer_class = DocumentAuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['document', 'user', 'action']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return super().get_queryset().filter(
            Q(document__created_by=self.request.user) |
            Q(document__shares__shared_with_user=self.request.user)
        ).select_related('document', 'user')


# Web Views

class DocumentListView(LoginRequiredMixin, ListView):
    """Document list view"""
    model = Document
    template_name = 'documents/document_list.html'
    context_object_name = 'documents'
    paginate_by = 25
    
    def get_queryset(self):
        return Document.objects.filter(
            Q(created_by=self.request.user) |
            Q(shares__shared_with_user=self.request.user) |
            Q(access_level='public'),
            is_active=True
        ).select_related('category', 'created_by').distinct()


class DocumentDetailView(LoginRequiredMixin, DetailView):
    """Document detail view"""
    model = Document
    template_name = 'documents/document_detail.html'
    context_object_name = 'document'
    
    def get_object(self):
        obj = get_object_or_404(Document, pk=self.kwargs['pk'], is_active=True)
        
        # Check permissions
        if not self._check_permission(obj):
            raise Http404("Document not found")
        
        return obj
    
    def _check_permission(self, document):
        """Check if user has permission to view document"""
        user = self.request.user
        
        # Owner always has access
        if document.created_by == user:
            return True
        
        # Check shared permissions
        if document.shares.filter(shared_with_user=user, can_view=True).exists():
            return True
        
        # Check public access
        if document.access_level == 'public':
            return True
        
        return False


@login_required
def document_download(request, pk):
    """Download document file"""
    document = get_object_or_404(Document, pk=pk, is_active=True)
    
    # Check permissions
    if not _check_document_permission(request.user, document, 'download'):
        raise Http404("Document not found")
    
    # Log download
    DocumentAuditLog.objects.create(
        document=document,
        user=request.user,
        action='download',
        ip_address=_get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        details={'timestamp': timezone.now().isoformat()}
    )
    
    try:
        if default_storage.exists(document.file.name):
            response = FileResponse(
                document.file.open('rb'),
                content_type=document.mime_type,
                as_attachment=True,
                filename=document.original_filename
            )
            return response
        else:
            raise Http404("File not found")
    except Exception:
        raise Http404("File not found")


def _check_document_permission(user, document, action):
    """Check if user has permission for action on document"""
    # Owner always has access
    if document.created_by == user:
        return True
    
    # Check shared permissions
    try:
        share = document.shares.get(shared_with_user=user)
        if action == 'view' and share.can_view:
            return True
        elif action == 'download' and share.can_download:
            return True
        elif action == 'edit' and share.can_edit:
            return True
    except DocumentShare.DoesNotExist:
        pass
    
    # Check public access
    if document.access_level == 'public' and action == 'view':
        return True
    
    return False


def _get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# Additional web view functions

@login_required
def document_dashboard(request):
    """Document dashboard view"""
    return render(request, 'documents/dashboard.html', {
        'recent_documents': Document.objects.filter(
            Q(created_by=request.user) |
            Q(shares__shared_with_user=request.user)
        ).order_by('-created_at')[:10],
        'categories': DocumentCategory.objects.filter(is_active=True),
    })

@login_required
def document_list(request):
    """Document list view"""
    documents = Document.objects.filter(
        Q(created_by=request.user) |
        Q(shares__shared_with_user=request.user) |
        Q(access_level='public'),
        is_active=True
    ).select_related('category', 'created_by')
    
    # Handle search query
    query = request.GET.get('q', '')
    if query:
        documents = documents.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(original_filename__icontains=query)
        )
    
    return render(request, 'documents/document_list.html', {
        'documents': documents,
        'query': query
    })

@login_required
def document_detail(request, pk):
    """Document detail view"""
    document = get_object_or_404(Document, pk=pk, is_active=True)
    
    # Check permissions
    if not _check_document_permission(request.user, document, 'view'):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("You don't have permission to access this document.")
    
    # Log the view action
    DocumentAuditLog.objects.create(
        document=document,
        user=request.user,
        action='view',
        ip_address=_get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        details={'timestamp': timezone.now().isoformat()}
    )
    
    return render(request, 'documents/document_detail.html', {
        'document': document
    })

@login_required
def document_upload(request):
    """Document upload view"""
    if request.method == 'POST':
        # Handle file upload
        pass
    
    return render(request, 'documents/document_upload.html', {
        'categories': DocumentCategory.objects.filter(is_active=True)
    })

@login_required
def document_share_view(request, pk):
    """Document share view"""
    document = get_object_or_404(Document, pk=pk, is_active=True)
    
    # Check permissions
    if not _check_document_permission(request.user, document, 'edit'):
        raise Http404("Document not found")
    
    return render(request, 'documents/document_share.html', {
        'document': document
    })

@login_required
def document_sign_view(request, pk):
    """Document sign view"""
    document = get_object_or_404(Document, pk=pk, is_active=True)
    
    # Check permissions
    if not _check_document_permission(request.user, document, 'view'):
        raise Http404("Document not found")
    
    return render(request, 'documents/document_sign.html', {
        'document': document
    })

@login_required
def document_comment_view(request, pk):
    """Document comment view"""
    document = get_object_or_404(Document, pk=pk, is_active=True)
    
    # Check permissions
    if not _check_document_permission(request.user, document, 'view'):
        raise Http404("Document not found")
    
    return render(request, 'documents/document_comment.html', {
        'document': document
    })

@login_required
def document_audit_view(request, pk):
    """Document audit view"""
    document = get_object_or_404(Document, pk=pk, is_active=True)
    
    # Check permissions
    if not _check_document_permission(request.user, document, 'view'):
        raise Http404("Document not found")
    
    return render(request, 'documents/document_audit.html', {
        'document': document,
        'audit_logs': document.audit_logs.order_by('-created_at')
    })

@login_required
def document_by_category(request, category_id):
    """Documents by category view"""
    category = get_object_or_404(DocumentCategory, pk=category_id, is_active=True)
    documents = Document.objects.filter(
        category=category,
        is_active=True
    ).filter(
        Q(created_by=request.user) |
        Q(shares__shared_with_user=request.user) |
        Q(access_level='public')
    )
    
    return render(request, 'documents/document_by_category.html', {
        'category': category,
        'documents': documents
    })

@login_required
def document_search(request):
    """Document search view"""
    return render(request, 'documents/document_search.html')

@login_required
def document_analytics(request):
    """Document analytics view"""
    return render(request, 'documents/document_analytics.html')

@login_required
def my_documents(request):
    """My documents view"""
    documents = Document.objects.filter(
        created_by=request.user,
        is_active=True
    ).select_related('category')
    
    return render(request, 'documents/my_documents.html', {
        'documents': documents
    })

@login_required
def shared_with_me(request):
    """Documents shared with me view"""
    documents = Document.objects.filter(
        shares__shared_with_user=request.user,
        is_active=True
    ).select_related('category', 'created_by')
    
    return render(request, 'documents/shared_with_me.html', {
        'documents': documents
    })

@login_required
def pending_signatures(request):
    """Pending signatures view"""
    documents = Document.objects.filter(
        signatures__signer=request.user,
        signatures__signed_at__isnull=True,
        is_active=True
    ).select_related('category', 'created_by')
    
    return render(request, 'documents/pending_signatures.html', {
        'documents': documents
    })

@login_required
def document_bulk_action(request):
    """Document bulk action view"""
    if request.method == 'POST':
        # Handle bulk actions
        pass
    
    return render(request, 'documents/document_bulk_action.html')
