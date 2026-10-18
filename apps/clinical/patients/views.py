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
from .clinical_scope import (
    GOLDEN_DEMO_FIXTURE_KEY,
    GOLDEN_DEMO_MRN,
    GOLDEN_DEMO_SOURCE_SYSTEM,
    clinical_patients,
    risk_selectable_patients,
)
from .access_policy import patient_clinical_access_policy
from .permissions import PatientScopedModelViewSetMixin

class PatientViewSet(viewsets.ModelViewSet):
    """患者管理 REST API ViewSet - USCDI v6 兼容版"""
    queryset = clinical_patients()
    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = patient_clinical_access_policy.queryset(self.request.user)
        include_demo = (
            self.action == 'list'
            and str(self.request.query_params.get('include_demo', '')).strip().lower()
            in {'1', 'true', 'yes'}
        )
        if include_demo and patient_clinical_access_policy._is_active_user(self.request.user):
            authorized_ids = queryset.values('id')
            queryset = risk_selectable_patients(include_golden_demo=True).filter(
                Q(id__in=authorized_ids)
                | Q(
                    medical_record_number=GOLDEN_DEMO_MRN,
                    source_system=GOLDEN_DEMO_SOURCE_SYSTEM,
                    metadata_json__conformance_fixture=GOLDEN_DEMO_FIXTURE_KEY,
                    metadata_json__synthetic=True,
                    metadata_json__clinical_use_prohibited=True,
                )
            )
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(medical_record_number__icontains=search)
            )
        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        if (
            not patient_clinical_access_policy._is_active_user(self.request.user)
            or (
                not self.request.user.has_perm('patients.create_patient_records')
                and not self.request.user.is_superuser
            )
        ):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('You do not have permission to create patient records.')
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        patient_clinical_access_policy.require_access(self.request.user, serializer.instance, operation='write')
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance):
        patient_clinical_access_policy.require_access(self.request.user, instance, operation='write')
        instance.delete()

class FamilyHealthHistoryViewSet(PatientScopedModelViewSetMixin, viewsets.ModelViewSet):
    queryset = FamilyHealthHistory.objects.all()
    serializer_class = FamilyHealthHistorySerializer
    permission_classes = [IsAuthenticated]

class MedicalDeviceViewSet(PatientScopedModelViewSetMixin, viewsets.ModelViewSet):
    queryset = MedicalDevice.objects.all()
    serializer_class = MedicalDeviceSerializer
    permission_classes = [IsAuthenticated]

class CareTeamMemberViewSet(PatientScopedModelViewSetMixin, viewsets.ModelViewSet):
    queryset = CareTeamMember.objects.all()
    serializer_class = CareTeamMemberSerializer
    permission_classes = [IsAuthenticated]

class PatientAllergyViewSet(PatientScopedModelViewSetMixin, viewsets.ModelViewSet):
    queryset = PatientAllergy.objects.all()
    serializer_class = PatientAllergySerializer
    permission_classes = [IsAuthenticated]

class CarePlanViewSet(PatientScopedModelViewSetMixin, viewsets.ModelViewSet):
    queryset = CarePlan.objects.all()
    serializer_class = CarePlanSerializer
    permission_classes = [IsAuthenticated]

class PatientMedicationViewSet(PatientScopedModelViewSetMixin, viewsets.ModelViewSet):
    queryset = PatientMedication.objects.all()
    serializer_class = PatientMedicationSerializer
    permission_classes = [IsAuthenticated]

class MedicalOrderViewSet(PatientScopedModelViewSetMixin, viewsets.ModelViewSet):
    queryset = MedicalOrder.objects.all()
    serializer_class = MedicalOrderSerializer
    permission_classes = [IsAuthenticated]

class InsuranceDataViewSet(PatientScopedModelViewSetMixin, viewsets.ModelViewSet):
    queryset = InsuranceData.objects.all()
    serializer_class = InsuranceDataSerializer
    permission_classes = [IsAuthenticated]

class AdvanceDirectiveViewSet(PatientScopedModelViewSetMixin, viewsets.ModelViewSet):
    queryset = AdvanceDirective.objects.all()
    serializer_class = AdvanceDirectiveSerializer
    permission_classes = [IsAuthenticated]

class PatientDocumentViewSet(PatientScopedModelViewSetMixin, viewsets.ModelViewSet):
    queryset = PatientDocument.objects.all()
    serializer_class = PatientDocumentSerializer
    permission_classes = [IsAuthenticated]

@login_required
def patient_list_view(request):
    return render(request, 'patients/patient_list.html')

@login_required
def patient_detail_view(request, patient_id):
    patient = get_object_or_404(patient_clinical_access_policy.queryset(request.user), id=patient_id)
    return render(request, 'patients/patient_detail.html', {'patient': patient})
