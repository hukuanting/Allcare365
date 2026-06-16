from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import (
    Patient, PatientAllergy, PatientMedication, PatientDocument,
    FamilyHealthHistory, MedicalDevice, CareTeamMember, CarePlan,
    MedicalOrder, InsuranceData, AdvanceDirective
)
from .serializers import (
    PatientSerializer, PatientAllergySerializer, PatientMedicationSerializer,
    PatientDocumentSerializer, FamilyHealthHistorySerializer, 
    MedicalDeviceSerializer, CareTeamMemberSerializer, CarePlanSerializer,
    MedicalOrderSerializer, InsuranceDataSerializer, AdvanceDirectiveSerializer
)

class PatientViewSet(viewsets.ModelViewSet):
    """患者管理 REST API ViewSet - USCDI v6 兼容版"""
    queryset = Patient.objects.filter(is_active=True)
    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Patient.objects.filter(is_active=True)
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(medical_record_number__icontains=search)
            )
        return queryset.order_by('-created_at')

class FamilyHealthHistoryViewSet(viewsets.ModelViewSet):
    queryset = FamilyHealthHistory.objects.all()
    serializer_class = FamilyHealthHistorySerializer
    permission_classes = [IsAuthenticated]

class MedicalDeviceViewSet(viewsets.ModelViewSet):
    queryset = MedicalDevice.objects.all()
    serializer_class = MedicalDeviceSerializer
    permission_classes = [IsAuthenticated]

class CareTeamMemberViewSet(viewsets.ModelViewSet):
    queryset = CareTeamMember.objects.all()
    serializer_class = CareTeamMemberSerializer
    permission_classes = [IsAuthenticated]

class PatientAllergyViewSet(viewsets.ModelViewSet):
    queryset = PatientAllergy.objects.all()
    serializer_class = PatientAllergySerializer
    permission_classes = [IsAuthenticated]

class CarePlanViewSet(viewsets.ModelViewSet):
    queryset = CarePlan.objects.all()
    serializer_class = CarePlanSerializer
    permission_classes = [IsAuthenticated]

class PatientMedicationViewSet(viewsets.ModelViewSet):
    queryset = PatientMedication.objects.all()
    serializer_class = PatientMedicationSerializer
    permission_classes = [IsAuthenticated]

class MedicalOrderViewSet(viewsets.ModelViewSet):
    queryset = MedicalOrder.objects.all()
    serializer_class = MedicalOrderSerializer
    permission_classes = [IsAuthenticated]

class InsuranceDataViewSet(viewsets.ModelViewSet):
    queryset = InsuranceData.objects.all()
    serializer_class = InsuranceDataSerializer
    permission_classes = [IsAuthenticated]

class AdvanceDirectiveViewSet(viewsets.ModelViewSet):
    queryset = AdvanceDirective.objects.all()
    serializer_class = AdvanceDirectiveSerializer
    permission_classes = [IsAuthenticated]

class PatientDocumentViewSet(viewsets.ModelViewSet):
    queryset = PatientDocument.objects.all()
    serializer_class = PatientDocumentSerializer
    permission_classes = [IsAuthenticated]

@login_required
def patient_list_view(request):
    return render(request, 'patients/patient_list.html')

@login_required
def patient_detail_view(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    return render(request, 'patients/patient_detail.html', {'patient': patient})
