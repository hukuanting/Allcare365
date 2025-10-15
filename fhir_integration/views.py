"""
FHIR R4 API Views for ONC Certification
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.db import models
import json
import uuid
from datetime import datetime

from .models import FHIRResource, USCDIDataElement, FHIRPatientResource
from .serializers import (
    FHIRResourceSerializer, USCDIDataElementSerializer, 
    FHIRPatientSerializer, BulkHealthDataSerializer
)
from .services import FHIRService, BulkDataProcessor
from patients.models import Patient
from health_screening.models import HealthScreening


class FHIRResourceViewSet(viewsets.ModelViewSet):
    """
    FHIR Resource API ViewSet
    Supports FHIR R4 CRUD operations for ONC certification
    """
    queryset = FHIRResource.objects.all()
    serializer_class = FHIRResourceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter resources by type if specified"""
        queryset = super().get_queryset()
        resource_type = self.request.query_params.get('resourceType')
        if resource_type:
            queryset = queryset.filter(resource_type=resource_type)
        return queryset
    
    @action(detail=False, methods=['get'])
    def metadata(self, request):
        """
        FHIR Capability Statement for ONC certification
        """
        capability_statement = {
            "resourceType": "CapabilityStatement",
            "id": "allcare365-capability",
            "status": "active",
            "date": datetime.now().isoformat(),
            "publisher": "Allcare365",
            "kind": "instance",
            "software": {
                "name": "Allcare365 EMR",
                "version": "1.0.0"
            },
            "implementation": {
                "description": "Allcare365 FHIR R4 Server",
                "url": request.build_absolute_uri('/fhir/')
            },
            "fhirVersion": "4.0.1",
            "format": ["json"],
            "rest": [{
                "mode": "server",
                "resource": [
                    {
                        "type": "Patient",
                        "interaction": [
                            {"code": "read"},
                            {"code": "create"},
                            {"code": "update"},
                            {"code": "search-type"}
                        ],
                        "searchParam": [
                            {"name": "identifier", "type": "token"},
                            {"name": "name", "type": "string"},
                            {"name": "birthdate", "type": "date"}
                        ]
                    },
                    {
                        "type": "Observation",
                        "interaction": [
                            {"code": "read"},
                            {"code": "create"},
                            {"code": "search-type"}
                        ],
                        "searchParam": [
                            {"name": "patient", "type": "reference"},
                            {"name": "code", "type": "token"},
                            {"name": "date", "type": "date"}
                        ]
                    }
                ]
            }]
        }
        return Response(capability_statement)
    
    @action(detail=False, methods=['post'])
    def bulk_import(self, request):
        """
        Bulk import health data with FHIR conversion
        """
        serializer = BulkHealthDataSerializer(data=request.data)
        if serializer.is_valid():
            try:
                processor = BulkDataProcessor()
                result = processor.process_file(
                    serializer.validated_data['file'],
                    serializer.validated_data['data_format'],
                    patient_id=serializer.validated_data.get('patient_id'),
                    user=request.user
                )
                return Response(result, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response(
                    {"error": str(e)}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class USCDIDataElementViewSet(viewsets.ReadOnlyModelViewSet):
    """
    USCDI v6 Data Elements API
    """
    queryset = USCDIDataElement.objects.all()
    serializer_class = USCDIDataElementSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def compliance_report(self, request):
        """
        Generate USCDI compliance report
        """
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response(
                {"error": "patient_id parameter required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            patient = Patient.objects.get(id=patient_id)
            service = FHIRService()
            report = service.generate_uscdi_compliance_report(patient)
            return Response(report)
        except Patient.DoesNotExist:
            return Response(
                {"error": "Patient not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )


class FHIRPatientViewSet(viewsets.ModelViewSet):
    """
    FHIR Patient Resource API
    """
    queryset = FHIRPatientResource.objects.all()
    serializer_class = FHIRPatientSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=True, methods=['get'])
    def fhir_bundle(self, request, pk=None):
        """
        Generate complete FHIR bundle for patient
        """
        fhir_patient = self.get_object()
        service = FHIRService()
        bundle = service.create_patient_bundle(fhir_patient.patient)
        return Response(bundle.dict())


class FHIREndpointView(View):
    """
    Standard FHIR R4 endpoints for ONC certification
    """
    
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    def patient_search(self, request):
        """
        FHIR Patient search endpoint
        """
        # Implement FHIR search parameters
        identifier = request.GET.get('identifier')
        name = request.GET.get('name')
        birthdate = request.GET.get('birthdate')
        
        patients = Patient.objects.all()
        
        if identifier:
            patients = patients.filter(
                fhirpatientresource__identifier_value=identifier
            )
        if name:
            patients = patients.filter(
                models.Q(first_name__icontains=name) |
                models.Q(last_name__icontains=name)
            )
        if birthdate:
            patients = patients.filter(date_of_birth=birthdate)
        
        # Convert to FHIR Bundle
        service = FHIRService()
        bundle = service.create_search_bundle(patients, 'Patient')
        
        return JsonResponse(bundle.dict(), safe=False)
    
    def observation_search(self, request):
        """
        FHIR Observation search endpoint
        """
        patient_ref = request.GET.get('patient')
        code = request.GET.get('code')
        date = request.GET.get('date')
        
        observations = HealthScreening.objects.all()
        
        if patient_ref:
            patient_id = patient_ref.split('/')[-1]
            observations = observations.filter(patient__id=patient_id)
        
        # Convert to FHIR Bundle
        service = FHIRService()
        bundle = service.create_observation_bundle(observations)
        
        return JsonResponse(bundle.dict(), safe=False)