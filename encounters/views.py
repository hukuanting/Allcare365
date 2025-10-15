from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from .models import Encounter, EncounterForm, EncounterDiagnosis
from .serializers import (
    EncounterSerializer, EncounterListSerializer,
    EncounterFormSerializer, EncounterDiagnosisSerializer
)


class EncounterViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing patient encounters
    """
    queryset = Encounter.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['patient', 'provider', 'status', 'reason']
    search_fields = ['patient__first_name', 'patient__last_name', 'chief_complaint', 'assessment']
    ordering_fields = ['encounter_date', 'created_at']
    ordering = ['-encounter_date']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return EncounterListSerializer
        return EncounterSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        patient_id = self.request.query_params.get('patient_id')
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        return queryset.select_related('patient', 'provider').prefetch_related('diagnoses', 'forms')
    
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Get encounter summary with related data"""
        encounter = self.get_object()
        serializer = EncounterSerializer(encounter, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_diagnosis(self, request, pk=None):
        """Add a diagnosis to this encounter"""
        encounter = self.get_object()
        serializer = EncounterDiagnosisSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(encounter=encounter, created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def add_form(self, request, pk=None):
        """Add a form to this encounter"""
        encounter = self.get_object()
        serializer = EncounterFormSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(encounter=encounter, created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def by_patient(self, request):
        """Get encounters for a specific patient"""
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response({'error': 'patient_id parameter is required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        encounters = self.get_queryset().filter(patient_id=patient_id)
        serializer = EncounterListSerializer(encounters, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_provider(self, request):
        """Get encounters for a specific provider"""
        provider_id = request.query_params.get('provider_id')
        if not provider_id:
            return Response({'error': 'provider_id parameter is required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        encounters = self.get_queryset().filter(provider_id=provider_id)
        serializer = EncounterListSerializer(encounters, many=True, context={'request': request})
        return Response(serializer.data)


class EncounterFormViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing encounter forms
    """
    queryset = EncounterForm.objects.all()
    serializer_class = EncounterFormSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['encounter', 'form_type']
    search_fields = ['form_name', 'encounter__patient__first_name', 'encounter__patient__last_name']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        encounter_id = self.request.query_params.get('encounter_id')
        if encounter_id:
            queryset = queryset.filter(encounter_id=encounter_id)
        return queryset.select_related('encounter', 'encounter__patient')


class EncounterDiagnosisViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing encounter diagnoses
    """
    queryset = EncounterDiagnosis.objects.all()
    serializer_class = EncounterDiagnosisSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['encounter', 'diagnosis_type', 'is_confirmed']
    search_fields = ['icd_code', 'diagnosis_text', 'encounter__patient__first_name', 'encounter__patient__last_name']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        encounter_id = self.request.query_params.get('encounter_id')
        if encounter_id:
            queryset = queryset.filter(encounter_id=encounter_id)
        return queryset.select_related('encounter', 'encounter__patient')
