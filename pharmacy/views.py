"""
Views for pharmacy management.
"""
from datetime import datetime, timedelta
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q, Count, Sum, F
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import (
    DrugCategory, Drug, DrugInteraction, DrugAllergy,
    DrugInventory, Prescription, PrescriptionRefill, InventoryTransaction
)
from .serializers import (
    DrugCategorySerializer, DrugSerializer, DrugInteractionSerializer,
    DrugAllergySerializer, DrugInventorySerializer, PrescriptionSerializer,
    PrescriptionCreateSerializer, PrescriptionRefillSerializer,
    InventoryTransactionSerializer
)


class DrugCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for drug categories"""
    queryset = DrugCategory.objects.filter(is_active=True)
    serializer_class = DrugCategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['parent_category', 'is_active']
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['name', 'code', 'created_at']
    ordering = ['name']

    @action(detail=True, methods=['get'])
    def subcategories(self, request, pk=None):
        """Get all subcategories of a category"""
        category = self.get_object()
        subcategories = category.subcategories.filter(is_active=True)
        serializer = DrugCategorySerializer(subcategories, many=True)
        return Response(serializer.data)


class DrugViewSet(viewsets.ModelViewSet):
    """ViewSet for drugs"""
    queryset = Drug.objects.filter(is_active=True).select_related('category')
    serializer_class = DrugSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'category', 'dosage_form', 'is_active', 'controlled_substance'
    ]
    search_fields = [
        'name', 'generic_name', 'brand_name', 'ndc_number', 'manufacturer'
    ]
    ordering_fields = ['name', 'generic_name', 'brand_name', 'created_at']
    ordering = ['name']

    @action(detail=True, methods=['get'])
    def interactions(self, request, pk=None):
        """Get all interactions for a drug"""
        drug = self.get_object()
        interactions = DrugInteraction.objects.filter(
            Q(drug1=drug) | Q(drug2=drug),
            is_active=True
        )
        serializer = DrugInteractionSerializer(interactions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def inventory(self, request, pk=None):
        """Get inventory information for a drug"""
        drug = self.get_object()
        inventory = DrugInventory.objects.filter(drug=drug)
        serializer = DrugInventorySerializer(inventory, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def search_by_ndc(self, request):
        """Search drugs by NDC code"""
        ndc_code = request.query_params.get('ndc_number')
        if not ndc_code:
            return Response(
                {'error': 'NDC number is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        drugs = Drug.objects.filter(ndc_number__icontains=ndc_code, is_active=True)
        serializer = DrugSerializer(drugs, many=True)
        return Response(serializer.data)


class DrugInteractionViewSet(viewsets.ModelViewSet):
    """ViewSet for drug interactions"""
    queryset = DrugInteraction.objects.filter(is_active=True).select_related('drug1', 'drug2')
    serializer_class = DrugInteractionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['severity', 'interaction_type', 'is_active']
    search_fields = ['drug1__name', 'drug2__name', 'description']
    ordering_fields = ['severity', 'drug1__name', 'drug2__name']
    ordering = ['severity', 'drug1__name']

    @action(detail=False, methods=['post'])
    def check_interaction(self, request):
        """Check for interactions between two drugs"""
        drug1_id = request.data.get('drug1_id')
        drug2_id = request.data.get('drug2_id')
        
        if not drug1_id or not drug2_id:
            return Response(
                {'error': 'Both drug IDs are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        interactions = DrugInteraction.objects.filter(
            Q(drug1_id=drug1_id, drug2_id=drug2_id) |
            Q(drug1_id=drug2_id, drug2_id=drug1_id),
            is_active=True
        )
        
        serializer = DrugInteractionSerializer(interactions, many=True)
        return Response({
            'has_interaction': interactions.exists(),
            'interactions': serializer.data
        })


class DrugAllergyViewSet(viewsets.ModelViewSet):
    """ViewSet for drug allergies"""
    queryset = DrugAllergy.objects.all().select_related('patient', 'drug', 'verified_by')
    serializer_class = DrugAllergySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['patient', 'drug', 'severity', 'reaction_type']
    search_fields = ['patient__first_name', 'patient__last_name', 'drug__name']
    ordering_fields = ['onset_date', 'severity']
    ordering = ['-onset_date']

    @action(detail=False, methods=['get'])
    def by_patient(self, request):
        """Get all allergies for a specific patient"""
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response(
                {'error': 'Patient ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        allergies = self.queryset.filter(patient_id=patient_id)
        serializer = DrugAllergySerializer(allergies, many=True)
        return Response(serializer.data)


class DrugInventoryViewSet(viewsets.ModelViewSet):
    """ViewSet for drug inventory"""
    queryset = DrugInventory.objects.all().select_related('drug')
    serializer_class = DrugInventorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['drug', 'facility', 'warehouse']
    search_fields = ['drug__name', 'lot_number', 'warehouse']
    ordering_fields = ['expiration_date', 'quantity_on_hand']
    ordering = ['expiration_date']

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get drugs with low stock levels"""
        # Since we don't have reorder_level field, return items with quantity < 10
        low_stock_items = self.queryset.filter(
            quantity_on_hand__lt=10
        )
        serializer = DrugInventorySerializer(low_stock_items, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        """Get drugs expiring within 30 days"""
        expiry_date = timezone.now().date() + timedelta(days=30)
        expiring_items = self.queryset.filter(
            expiration_date__lte=expiry_date
        )
        serializer = DrugInventorySerializer(expiring_items, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def adjust_quantity(self, request, pk=None):
        """Adjust inventory quantity"""
        inventory = self.get_object()
        adjustment = request.data.get('adjustment', 0)
        reason = request.data.get('reason', 'Manual adjustment')
        
        if not adjustment:
            return Response(
                {'error': 'Adjustment amount is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create transaction record
        transaction = InventoryTransaction.objects.create(
            drug_inventory=inventory,
            transaction_type='ADJUSTMENT',
            quantity=adjustment,
            transaction_date=timezone.now(),
            performed_by=request.user,
            notes=reason
        )
        
        # Update inventory
        inventory.quantity_on_hand += adjustment
        inventory.save()
        
        return Response({
            'message': 'Inventory adjusted successfully',
            'new_quantity': inventory.quantity_on_hand,
            'transaction_id': transaction.id
        })


class PrescriptionViewSet(viewsets.ModelViewSet):
    """ViewSet for prescriptions"""
    queryset = Prescription.objects.all().select_related('patient', 'drug', 'provider')
    serializer_class = PrescriptionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['patient', 'drug', 'provider', 'status']
    search_fields = [
        'patient__first_name', 'patient__last_name',
        'drug__name', 'provider__first_name', 'provider__last_name'
    ]
    ordering_fields = ['prescribed_date', 'status']
    ordering = ['-prescribed_date']

    def get_serializer_class(self):
        """Use different serializers for create vs other actions"""
        if self.action == 'create':
            return PrescriptionCreateSerializer
        return PrescriptionSerializer

    @action(detail=False, methods=['get'])
    def by_patient(self, request):
        """Get all prescriptions for a specific patient"""
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response(
                {'error': 'Patient ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        prescriptions = self.queryset.filter(patient_id=patient_id)
        serializer = PrescriptionSerializer(prescriptions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get all active prescriptions"""
        active_prescriptions = self.queryset.filter(
            status__in=['ACTIVE', 'PENDING']
        )
        serializer = PrescriptionSerializer(active_prescriptions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def fill(self, request, pk=None):
        """Fill a prescription"""
        prescription = self.get_object()
        
        if prescription.status != 'ACTIVE':
            return Response(
                {'error': 'Prescription is not active'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if prescription.refills_remaining <= 0:
            return Response(
                {'error': 'No refills remaining'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create refill record
        refill = PrescriptionRefill.objects.create(
            prescription=prescription,
            refill_number=prescription.refills_authorized - prescription.refills_remaining + 1,
            refill_date=timezone.now().date(),
            quantity_dispensed=prescription.quantity,
            pharmacist=request.user
        )
        
        # Update prescription
        prescription.refills_remaining -= 1
        prescription.filled_date = timezone.now().date()
        if prescription.refills_remaining == 0:
            prescription.status = 'COMPLETED'
        prescription.save()
        
        return Response({
            'message': 'Prescription filled successfully',
            'refill_id': refill.id,
            'refills_remaining': prescription.refills_remaining
        })


class PrescriptionRefillViewSet(viewsets.ModelViewSet):
    """ViewSet for prescription refills"""
    queryset = PrescriptionRefill.objects.all().select_related(
        'prescription', 'prescription__patient', 'prescription__drug', 'pharmacist'
    )
    serializer_class = PrescriptionRefillSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['prescription', 'pharmacist']
    search_fields = [
        'prescription__patient__first_name',
        'prescription__patient__last_name',
        'prescription__drug__name'
    ]
    ordering_fields = ['refill_date']
    ordering = ['-refill_date']


class InventoryTransactionViewSet(viewsets.ModelViewSet):
    """ViewSet for inventory transactions"""
    queryset = InventoryTransaction.objects.all().select_related(
        'drug_inventory', 'drug_inventory__drug', 'performed_by'
    )
    serializer_class = InventoryTransactionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['drug_inventory', 'transaction_type', 'performed_by']
    search_fields = ['drug_inventory__drug__name', 'reference_number']
    ordering_fields = ['transaction_date']
    ordering = ['-transaction_date']

    @action(detail=False, methods=['get'])
    def by_drug(self, request):
        """Get all transactions for a specific drug"""
        drug_id = request.query_params.get('drug_id')
        if not drug_id:
            return Response(
                {'error': 'Drug ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        transactions = self.queryset.filter(drug_inventory__drug_id=drug_id)
        serializer = InventoryTransactionSerializer(transactions, many=True)
        return Response(serializer.data)


# Dashboard views
@login_required
def pharmacy_dashboard(request):
    """Pharmacy dashboard view"""
    # Get summary statistics
    total_drugs = Drug.objects.filter(is_active=True).count()
    active_prescriptions = Prescription.objects.filter(status='active').count()
    low_stock_count = DrugInventory.objects.filter(
        quantity_on_hand__lte=F('drug__reorder_level')
    ).count()
    
    # Get drugs expiring within 30 days
    expiry_date = timezone.now().date() + timedelta(days=30)
    expiring_drugs = DrugInventory.objects.filter(
        expiration_date__lte=expiry_date
    ).count()
    
    context = {
        'total_drugs': total_drugs,
        'active_prescriptions': active_prescriptions,
        'low_stock_count': low_stock_count,
        'expiring_drugs': expiring_drugs,
    }
    
    return render(request, 'pharmacy/dashboard.html', context)


@login_required
def inventory_alerts(request):
    """View for inventory alerts"""
    # Low stock items - using quantity_on_hand < 10 as threshold
    low_stock_items = DrugInventory.objects.filter(
        quantity_on_hand__lt=10
    ).select_related('drug')
    
    # Expiring items
    expiry_date = timezone.now().date() + timedelta(days=30)
    expiring_items = DrugInventory.objects.filter(
        expiration_date__lte=expiry_date
    ).select_related('drug')
    
    context = {
        'low_stock_items': low_stock_items,
        'expiring_items': expiring_items,
    }
    
    return render(request, 'pharmacy/inventory_alerts.html', context)
