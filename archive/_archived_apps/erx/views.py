"""
Electronic Prescription (eRx) Views

This module provides REST API views for the electronic prescription system
including prescription management, drug interactions, formulary checks,
and pharmacy directory.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
import logging

from .models import (
    ElectronicPrescription,
    PrescriptionRefill,
    PrescriptionHistory,
    DrugFormulary,
    DrugInteraction,
    PharmacyDirectory
)
from .serializers import (
    ElectronicPrescriptionSerializer,
    ElectronicPrescriptionCreateSerializer,
    PrescriptionStatusUpdateSerializer,
    PrescriptionRefillSerializer,
    PrescriptionHistorySerializer,
    DrugFormularySerializer,
    DrugInteractionSerializer,
    PharmacyDirectorySerializer,
    DrugInteractionCheckSerializer,
    FormularyCheckSerializer,
    PharmacySearchSerializer
)
from .services import ErxService
from patients.models import Patient

logger = logging.getLogger(__name__)


class ElectronicPrescriptionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing electronic prescriptions
    """
    queryset = ElectronicPrescription.objects.all()
    serializer_class = ElectronicPrescriptionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter prescriptions based on user permissions"""
        queryset = super().get_queryset()
        user = self.request.user
        
        # Filter by patient if provided
        patient_id = self.request.query_params.get('patient')
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        
        # Filter by status if provided
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by date range if provided
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(date_prescribed__gte=start_date)
        if end_date:
            queryset = queryset.filter(date_prescribed__lte=end_date)
        
        # Non-admin users can only see their own prescriptions
        if not user.is_superuser:
            queryset = queryset.filter(prescriber=user)
        
        return queryset.order_by('-date_prescribed')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return ElectronicPrescriptionCreateSerializer
        elif self.action == 'update_status':
            return PrescriptionStatusUpdateSerializer
        return ElectronicPrescriptionSerializer
    
    @action(detail=True, methods=['post'])
    def send_prescription(self, request, pk=None):
        """
        Send prescription to pharmacy
        """
        prescription = self.get_object()
        
        # Check permissions
        if prescription.prescriber != request.user and not request.user.is_superuser:
            return Response(
                {'error': 'You can only send your own prescriptions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if prescription can be sent
        if prescription.status != 'draft':
            return Response(
                {'error': 'Only draft prescriptions can be sent'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Send prescription
        success = ErxService.send_prescription(prescription, request.user)
        
        if success:
            serializer = self.get_serializer(prescription)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'Failed to send prescription'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def cancel_prescription(self, request, pk=None):
        """
        Cancel a prescription
        """
        prescription = self.get_object()
        
        # Check permissions
        if prescription.prescriber != request.user and not request.user.is_superuser:
            return Response(
                {'error': 'You can only cancel your own prescriptions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        reason = request.data.get('reason', '')
        
        success = ErxService.cancel_prescription(prescription, request.user, reason)
        
        if success:
            serializer = self.get_serializer(prescription)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'Failed to cancel prescription'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """
        Update prescription status (for external systems)
        """
        prescription = self.get_object()
        
        serializer = PrescriptionStatusUpdateSerializer(
            prescription,
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def check_interactions(self, request):
        """
        Check for drug interactions
        """
        serializer = DrugInteractionCheckSerializer(data=request.data)
        
        if serializer.is_valid():
            drugs = serializer.validated_data['drugs']
            interactions = []
            
            # Check all combinations
            for i, drug1 in enumerate(drugs):
                for drug2 in drugs[i+1:]:
                    drug_interactions = DrugInteraction.objects.filter(
                        Q(drug1_name__icontains=drug1, drug2_name__icontains=drug2) |
                        Q(drug1_name__icontains=drug2, drug2_name__icontains=drug1)
                    )
                    
                    for interaction in drug_interactions:
                        interactions.append({
                            'drug1': interaction.drug1_name,
                            'drug2': interaction.drug2_name,
                            'severity': interaction.interaction_severity,
                            'description': interaction.interaction_description,
                            'management': interaction.clinical_management
                        })
            
            return Response({
                'interactions': interactions,
                'interaction_count': len(interactions)
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def check_formulary(self, request):
        """
        Check drug formulary status
        """
        serializer = FormularyCheckSerializer(data=request.data)
        
        if serializer.is_valid():
            drug_name = serializer.validated_data['drug_name']
            patient_id = serializer.validated_data['patient_id']
            
            try:
                patient = Patient.objects.get(id=patient_id)
                formulary_info = ErxService.check_formulary(drug_name, patient)
                
                return Response({
                    'formulary_info': formulary_info,
                    'covered': formulary_info is not None
                }, status=status.HTTP_200_OK)
                
            except Patient.DoesNotExist:
                return Response(
                    {'error': 'Patient not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """
        Get prescription analytics
        """
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Parse dates
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        
        analytics = ErxService.get_prescription_analytics(
            request.user,
            start_date,
            end_date
        )
        
        return Response(analytics, status=status.HTTP_200_OK)


class PrescriptionRefillViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing prescription refills
    """
    queryset = PrescriptionRefill.objects.all()
    serializer_class = PrescriptionRefillSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter refills based on user permissions"""
        queryset = super().get_queryset()
        user = self.request.user
        
        # Filter by prescription if provided
        prescription_id = self.request.query_params.get('prescription')
        if prescription_id:
            queryset = queryset.filter(prescription_id=prescription_id)
        
        # Non-admin users can only see refills for their prescriptions
        if not user.is_superuser:
            queryset = queryset.filter(prescription__prescriber=user)
        
        return queryset.order_by('-date_filled')


class PrescriptionHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing prescription history
    """
    queryset = PrescriptionHistory.objects.all()
    serializer_class = PrescriptionHistorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter history based on user permissions"""
        queryset = super().get_queryset()
        user = self.request.user
        
        # Filter by prescription if provided
        prescription_id = self.request.query_params.get('prescription')
        if prescription_id:
            queryset = queryset.filter(prescription_id=prescription_id)
        
        # Non-admin users can only see history for their prescriptions
        if not user.is_superuser:
            queryset = queryset.filter(prescription__prescriber=user)
        
        return queryset.order_by('-timestamp')


class DrugFormularyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing drug formulary information
    """
    queryset = DrugFormulary.objects.all()
    serializer_class = DrugFormularySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter formulary based on search parameters"""
        queryset = super().get_queryset()
        
        # Filter by drug name if provided
        drug_name = self.request.query_params.get('drug_name')
        if drug_name:
            queryset = queryset.filter(drug_name__icontains=drug_name)
        
        # Filter by formulary status if provided
        formulary_status = self.request.query_params.get('formulary_status')
        if formulary_status:
            queryset = queryset.filter(formulary_status=formulary_status)
        
        return queryset.order_by('drug_name')


class DrugInteractionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing drug interaction information
    """
    queryset = DrugInteraction.objects.all()
    serializer_class = DrugInteractionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter interactions based on search parameters"""
        queryset = super().get_queryset()
        
        # Filter by drug name if provided
        drug_name = self.request.query_params.get('drug_name')
        if drug_name:
            queryset = queryset.filter(
                Q(drug1_name__icontains=drug_name) |
                Q(drug2_name__icontains=drug_name)
            )
        
        # Filter by severity if provided
        severity = self.request.query_params.get('severity')
        if severity:
            queryset = queryset.filter(interaction_severity=severity)
        
        return queryset.order_by('-interaction_severity', 'drug1_name')


class PharmacyDirectoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing pharmacy directory
    """
    queryset = PharmacyDirectory.objects.filter(is_active=True)
    serializer_class = PharmacyDirectorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter pharmacies based on search parameters"""
        queryset = super().get_queryset()
        
        # Filter by search term if provided
        search_term = self.request.query_params.get('search')
        if search_term:
            queryset = queryset.filter(
                Q(name__icontains=search_term) |
                Q(address_line1__icontains=search_term) |
                Q(city__icontains=search_term)
            )
        
        # Filter by city if provided
        city = self.request.query_params.get('city')
        if city:
            queryset = queryset.filter(city__icontains=city)
        
        # Filter by state if provided
        state = self.request.query_params.get('state')
        if state:
            queryset = queryset.filter(state__iexact=state)
        
        # Filter by zip code if provided
        zip_code = self.request.query_params.get('zip_code')
        if zip_code:
            queryset = queryset.filter(zip_code__startswith=zip_code)
        
        # Filter by capabilities
        accepts_erx = self.request.query_params.get('accepts_erx')
        if accepts_erx and accepts_erx.lower() == 'true':
            queryset = queryset.filter(accepts_erx=True)
        
        accepts_controlled = self.request.query_params.get('accepts_controlled_substances')
        if accepts_controlled and accepts_controlled.lower() == 'true':
            queryset = queryset.filter(accepts_controlled_substances=True)
        
        return queryset.order_by('name')[:50]  # Limit results
    
    @action(detail=False, methods=['post'])
    def search(self, request):
        """
        Advanced pharmacy search
        """
        serializer = PharmacySearchSerializer(data=request.data)
        
        if serializer.is_valid():
            search_criteria = serializer.validated_data
            pharmacies = ErxService.search_pharmacies(search_criteria)
            
            serializer = PharmacyDirectorySerializer(pharmacies, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
