"""
Laboratory management views for web interface and REST API.

This module provides:
- REST API ViewSets for laboratory data
- Web views for laboratory dashboard
- Specialized views for critical results and pending orders
- HL7 message processing endpoints
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView, DetailView
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import (
    LabProvider, LabTestCategory, LabTestType, LabOrder, LabOrderItem,
    LabResult, LabMessage, QualityControlLog
)
from .serializers import (
    LabProviderSerializer, LabTestCategorySerializer, LabTestTypeSerializer,
    LabOrderSerializer, LabOrderCreateSerializer, LabOrderItemSerializer,
    LabResultSerializer, LabMessageSerializer, QualityControlLogSerializer,
    LabOrderSummarySerializer, CriticalResultSerializer, PendingOrderSerializer
)


# ============================================================================
# REST API ViewSets
# ============================================================================

class LabProviderViewSet(viewsets.ModelViewSet):
    """ViewSet for laboratory providers"""
    queryset = LabProvider.objects.all()
    serializer_class = LabProviderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['interface_type', 'is_preferred', 'is_active']
    search_fields = ['name', 'contact_name', 'clia_number']
    ordering_fields = ['name', 'average_turnaround_time', 'created_at']
    ordering = ['name']
    
    @action(detail=False, methods=['get'])
    def preferred(self, request):
        """Get preferred laboratory providers"""
        providers = self.queryset.filter(is_preferred=True, is_active=True)
        serializer = self.get_serializer(providers, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """Test connection to laboratory provider"""
        provider = self.get_object()
        # Implementation depends on provider interface type
        # This is a placeholder for actual connection testing
        return Response({
            'success': True,
            'message': f'Connection test for {provider.name} would be implemented here'
        })


class LabTestCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for laboratory test categories"""
    queryset = LabTestCategory.objects.all()
    serializer_class = LabTestCategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['parent_category', 'is_active']
    search_fields = ['name', 'code']
    ordering_fields = ['name', 'sort_order', 'created_at']
    ordering = ['sort_order', 'name']
    
    @action(detail=False, methods=['get'])
    def hierarchy(self, request):
        """Get category hierarchy"""
        categories = self.queryset.filter(parent_category=None, is_active=True)
        serializer = self.get_serializer(categories, many=True)
        return Response(serializer.data)


class LabTestTypeViewSet(viewsets.ModelViewSet):
    """ViewSet for laboratory test types"""
    queryset = LabTestType.objects.all()
    serializer_class = LabTestTypeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['category', 'specimen_type', 'result_type', 'requires_fasting', 'is_active']
    search_fields = ['name', 'short_name', 'loinc_code', 'cpt_code']
    ordering_fields = ['name', 'cost', 'average_tat', 'created_at']
    ordering = ['name']
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get test types by category"""
        category_id = request.query_params.get('category_id')
        if category_id:
            tests = self.queryset.filter(category_id=category_id, is_active=True)
        else:
            tests = self.queryset.filter(is_active=True)
        
        page = self.paginate_queryset(tests)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(tests, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search test types by various criteria"""
        query = request.query_params.get('q', '')
        if query:
            tests = self.queryset.filter(
                Q(name__icontains=query) |
                Q(short_name__icontains=query) |
                Q(loinc_code__icontains=query) |
                Q(cpt_code__icontains=query)
            ).filter(is_active=True)
        else:
            tests = self.queryset.filter(is_active=True)
        
        page = self.paginate_queryset(tests)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(tests, many=True)
        return Response(serializer.data)


class LabOrderViewSet(viewsets.ModelViewSet):
    """ViewSet for laboratory orders"""
    queryset = LabOrder.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'priority', 'lab_provider', 'patient', 'provider']
    search_fields = ['order_number', 'patient__first_name', 'patient__last_name']
    ordering_fields = ['order_date', 'status', 'priority', 'total_cost']
    ordering = ['-order_date']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return LabOrderCreateSerializer
        elif self.action == 'list':
            return LabOrderSummarySerializer
        return LabOrderSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions"""
        queryset = super().get_queryset()
        
        # Filter by date range if provided
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(order_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(order_date__lte=end_date)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending orders"""
        orders = self.queryset.filter(status__in=['pending', 'collected', 'received'])
        serializer = PendingOrderSerializer(orders, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def urgent(self, request):
        """Get urgent orders"""
        orders = self.queryset.filter(priority='urgent')
        page = self.paginate_queryset(orders)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an order"""
        order = self.get_object()
        if order.status not in ['pending', 'collected']:
            return Response(
                {'error': 'Order cannot be cancelled in current status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = 'cancelled'
        order.save()
        return Response({'message': 'Order cancelled successfully'})
    
    @action(detail=True, methods=['post'])
    def collect(self, request, pk=None):
        """Mark order as collected"""
        order = self.get_object()
        if order.status != 'pending':
            return Response(
                {'error': 'Order cannot be collected in current status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = 'collected'
        order.collection_date = timezone.now()
        order.save()
        return Response({'message': 'Order marked as collected'})


class LabOrderItemViewSet(viewsets.ModelViewSet):
    """ViewSet for laboratory order items"""
    queryset = LabOrderItem.objects.all()
    serializer_class = LabOrderItemSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'test_type', 'lab_order']
    search_fields = ['specimen_id', 'test_type__name']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']


class LabResultViewSet(viewsets.ModelViewSet):
    """ViewSet for laboratory results"""
    queryset = LabResult.objects.all()
    serializer_class = LabResultSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['result_status', 'abnormal_flag', 'pathologist_review']
    search_fields = ['order_item__test_type__name', 'result_value']
    ordering_fields = ['result_date', 'verified_date', 'created_at']
    ordering = ['-result_date']
    
    @action(detail=False, methods=['get'])
    def critical(self, request):
        """Get critical results"""
        results = self.queryset.filter(abnormal_flag__in=['LL', 'HH', 'AA'])
        serializer = CriticalResultSerializer(results, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending_verification(self, request):
        """Get results pending verification"""
        results = self.queryset.filter(verified_date__isnull=True)
        serializer = self.get_serializer(results, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify a laboratory result"""
        result = self.get_object()
        result.verified_by = request.user
        result.verified_date = timezone.now()
        result.pathologist_notes = request.data.get('notes', '')
        result.save()
        return Response({'message': 'Result verified successfully'})


class LabMessageViewSet(viewsets.ModelViewSet):
    """ViewSet for HL7 messages"""
    queryset = LabMessage.objects.all()
    serializer_class = LabMessageSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['message_type', 'processing_status', 'lab_provider']
    search_fields = ['external_message_id']
    ordering_fields = ['created_at', 'processing_status']
    ordering = ['-created_at']
    
    @action(detail=False, methods=['get'])
    def failed(self, request):
        """Get failed messages"""
        messages = self.queryset.filter(processing_status='failed')
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reprocess(self, request, pk=None):
        """Reprocess a failed message"""
        message = self.get_object()
        if message.processing_status == 'failed':
            message.processing_status = 'pending'
            message.error_message = ''
            message.save()
            # Here you would trigger the actual reprocessing
            return Response({'message': 'Message queued for reprocessing'})
        else:
            return Response(
                {'error': 'Only failed messages can be reprocessed'},
                status=status.HTTP_400_BAD_REQUEST
            )


class QualityControlLogViewSet(viewsets.ModelViewSet):
    """ViewSet for quality control logs"""
    queryset = QualityControlLog.objects.all()
    serializer_class = QualityControlLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['qc_type', 'passed', 'test_type', 'lab_provider']
    search_fields = ['control_lot', 'performed_by']
    ordering_fields = ['created_at', 'passed']
    ordering = ['-created_at']
    
    @action(detail=False, methods=['get'])
    def failed(self, request):
        """Get failed QC logs"""
        logs = self.queryset.filter(passed=False)
        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)


# ============================================================================
# Web Views
# ============================================================================

class LaboratoryDashboardView(LoginRequiredMixin, TemplateView):
    """Laboratory dashboard view"""
    template_name = 'laboratory/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get dashboard statistics
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        
        context.update({
            'total_orders': LabOrder.objects.count(),
            'pending_orders': LabOrder.objects.filter(status='pending').count(),
            'urgent_orders': LabOrder.objects.filter(
                priority__in=['urgent', 'stat', 'asap'],
                status__in=['pending', 'collected', 'received', 'in_progress']
            ).count(),
            'critical_results': LabResult.objects.filter(
                abnormal_flag__in=['LL', 'HH', 'AA'],
                verified_date__isnull=True
            ).count(),
            'recent_orders': LabOrder.objects.filter(
                order_date__gte=week_ago
            ).order_by('-order_date')[:10],
            'failed_messages': LabMessage.objects.filter(
                processing_status='failed'
            ).count(),
        })
        
        return context


class CriticalResultsView(LoginRequiredMixin, ListView):
    """View for critical laboratory results"""
    model = LabResult
    template_name = 'laboratory/critical_results.html'
    context_object_name = 'results'
    paginate_by = 25
    
    def get_queryset(self):
        return LabResult.objects.filter(
            abnormal_flag__in=['LL', 'HH', 'AA']
        ).order_by('-result_date')


class PendingOrdersView(LoginRequiredMixin, ListView):
    """View for pending laboratory orders"""
    model = LabOrder
    template_name = 'laboratory/pending_orders.html'
    context_object_name = 'orders'
    paginate_by = 25
    
    def get_queryset(self):
        return LabOrder.objects.filter(
            status__in=['pending', 'collected', 'received']
        ).order_by('order_date')


class LabOrderDetailView(LoginRequiredMixin, DetailView):
    """Detailed view for laboratory order"""
    model = LabOrder
    template_name = 'laboratory/order_detail.html'
    context_object_name = 'order'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['order_items'] = self.object.order_items.all()
        return context


@login_required
def laboratory_dashboard(request):
    """Laboratory dashboard view function"""
    return render(request, 'laboratory/dashboard.html')


@login_required
def lab_order_search(request):
    """Search laboratory orders"""
    query = request.GET.get('q', '')
    orders = []
    
    if query:
        orders = LabOrder.objects.filter(
            Q(order_number__icontains=query) |
            Q(patient__first_name__icontains=query) |
            Q(patient__last_name__icontains=query)
        ).order_by('-order_date')[:20]
    
    return render(request, 'laboratory/order_search.html', {
        'orders': orders,
        'query': query
    })


# ============================================================================
# API Helper Functions
# ============================================================================

def get_lab_statistics(request):
    """Get laboratory statistics for dashboard"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    stats = {
        'orders': {
            'total': LabOrder.objects.count(),
            'pending': LabOrder.objects.filter(status='pending').count(),
            'this_week': LabOrder.objects.filter(order_date__gte=week_ago).count(),
            'this_month': LabOrder.objects.filter(order_date__gte=month_ago).count(),
        },
        'results': {
            'total': LabResult.objects.count(),
            'critical': LabResult.objects.filter(abnormal_flag__in=['LL', 'HH', 'AA']).count(),
            'pending_verification': LabResult.objects.filter(verified_date__isnull=True).count(),
        },
        'providers': {
            'total': LabProvider.objects.filter(is_active=True).count(),
            'preferred': LabProvider.objects.filter(is_preferred=True, is_active=True).count(),
        }
    }
    
    return JsonResponse(stats)


def process_hl7_message(request):
    """Process incoming HL7 message"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        raw_message = request.body.decode('utf-8')
        provider_id = request.GET.get('provider_id')
        
        if not provider_id:
            return JsonResponse({'error': 'Provider ID required'}, status=400)
        
        # Create HL7 message record
        message = LabMessage.objects.create(
            lab_provider_id=provider_id,
            message_type='ORU',  # Assume result message
            raw_message=raw_message,
            processing_status='pending'
        )
        
        # Here you would implement actual HL7 parsing and processing
        # For now, just mark as processed
        message.processing_status = 'processed'
        message.save()
        
        return JsonResponse({
            'message_id': str(message.id),
            'status': 'processed'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
