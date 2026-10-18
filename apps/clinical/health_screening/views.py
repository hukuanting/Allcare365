from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, parser_classes, permission_classes
from rest_framework.exceptions import APIException
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from services.disease_risk_engine import DiseaseRiskAssessmentService
from services.disease_risk_engine.algorithm_registry import public_algorithm_catalog
from apps.clinical.patients.access_policy import patient_clinical_access_policy, patient_risk_access_policy
from apps.clinical.patients.permissions import PatientScopedModelViewSetMixin
from apps.integration.fhir_integration.models import AuditLog
from apps.clinical.patients.clinical_scope import clinical_patients

from .cohort_service import CohortSummaryService
from .data_quality_service import DataQualitySummaryService
from .fhir_research_projection import CohortMeasureReportBuilder
from .ingestion_service import HealthScreeningIngestionService
from .fhir_import_formats import request_fhir_payload, summarize
from .models import HealthScreening, Immunization, Problem, Procedure, ResearchAggregateReport
from .patients_like_this_service import PatientsLikeThisService
from .research_report_service import ResearchAggregateReportService
from .sotera_report_service import SoteraResearchReportService
from .serializers import (
    HealthScreeningSerializer,
    ImmunizationSerializer,
    ProblemSerializer,
    ProcedureSerializer,
    ResearchAggregateReportSerializer,
)


class HasExplicitClinicalPermission(BasePermission):
    """Grant sensitive non-patient endpoints only through assigned permissions."""

    required_permission = ""

    def has_permission(self, request, view):
        return bool(
            patient_clinical_access_policy._is_active_user(request.user)
            and (request.user.is_superuser or request.user.has_perm(self.required_permission))
        )


class HasClinicalImportPermission(HasExplicitClinicalPermission):
    required_permission = "health_screening.import_clinical_records"


class HasResearchAggregatePermission(HasExplicitClinicalPermission):
    required_permission = "health_screening.view_research_aggregates"


class HasResearchAggregateApprovalPermission(HasExplicitClinicalPermission):
    required_permission = "health_screening.approve_research_aggregates"


class HealthScreeningViewSet(PatientScopedModelViewSetMixin, viewsets.ModelViewSet):
    serializer_class = HealthScreeningSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = (
            HealthScreening.objects.select_related("patient")
            .filter(patient__in=patient_clinical_access_policy.queryset(self.request.user))
            .prefetch_related("lab_results")
            .order_by("-screening_date", "-created_at", "-id")
        )
        patient = self.request.query_params.get("patient") or self.request.query_params.get("patient_id")
        if patient:
            queryset = queryset.filter(
                Q(patient_id=patient) | Q(patient__medical_record_number=str(patient))
            )
        return queryset

    def create(self, request, *args, **kwargs):
        try:
            patient_identifier = request.data.get("patient") or request.data.get("patient_id")
            patient = patient_clinical_access_policy.resolve_patient(patient_identifier)
            patient_clinical_access_policy.require_access(request.user, patient, operation="write")
            screening = HealthScreeningIngestionService().create_screening(dict(request.data))
            screening.created_by = request.user
            screening.updated_by = request.user
            screening.save(update_fields=["created_by", "updated_by", "updated_at"])
        except APIException:
            raise
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(screening)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"], url_path="calculate_comprehensive_risk")
    def calculate_comprehensive_risk(self, request, pk=None):
        screening = self.get_object()
        patient_risk_access_policy.require_access(request.user, screening.patient)
        result = DiseaseRiskAssessmentService().calculate_dynamic_risk(
            str(screening.patient_id),
            actor_user=request.user,
        )
        response_status = status.HTTP_400_BAD_REQUEST if result.get("error") else status.HTTP_200_OK
        return Response(result, status=response_status)

    @action(detail=True, methods=["get"], url_path="risk-analysis")
    def risk_analysis(self, request, pk=None):
        screening = self.get_object()
        patient_risk_access_policy.require_access(request.user, screening.patient)
        result = DiseaseRiskAssessmentService().calculate_dynamic_risk(
            str(screening.patient_id),
            actor_user=request.user,
        )
        response_status = status.HTTP_400_BAD_REQUEST if result.get("error") else status.HTTP_200_OK
        return Response(result, status=response_status)


class ImmunizationViewSet(PatientScopedModelViewSetMixin, viewsets.ModelViewSet):
    queryset = Immunization.objects.all()
    serializer_class = ImmunizationSerializer
    permission_classes = [IsAuthenticated]


class ProblemViewSet(PatientScopedModelViewSetMixin, viewsets.ModelViewSet):
    queryset = Problem.objects.all()
    serializer_class = ProblemSerializer
    permission_classes = [IsAuthenticated]


class ProcedureViewSet(PatientScopedModelViewSetMixin, viewsets.ModelViewSet):
    queryset = Procedure.objects.all()
    serializer_class = ProcedureSerializer
    permission_classes = [IsAuthenticated]


@api_view(["POST"])
@permission_classes([HasClinicalImportPermission])
@parser_classes([MultiPartParser, FormParser])
def parse_file(request):
    file_obj = request.FILES.get("file")
    if not file_obj:
        return Response({"detail": "file is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        result = HealthScreeningIngestionService().parse_file_preview(file_obj)
    except Exception as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(result)


@api_view(["POST"])
@permission_classes([HasClinicalImportPermission])
@parser_classes([MultiPartParser, FormParser])
def bulk_import(request):
    file_obj = request.FILES.get("file")
    if not file_obj:
        return Response({"detail": "file is required"}, status=status.HTTP_400_BAD_REQUEST)

    result = HealthScreeningIngestionService().bulk_import_file(file_obj)
    response_status = status.HTTP_207_MULTI_STATUS if result.get("error_count") else status.HTTP_201_CREATED
    return Response(result, status=response_status)


@api_view(["POST"])
@permission_classes([HasClinicalImportPermission])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def fhir_preview(request):
    """Normalize and summarize inputs without persisting clinical records."""
    try:
        bundle = request_fhir_payload(request)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response({"fhir_data": bundle, **summarize(bundle)})


@api_view(["POST"])
@permission_classes([HasClinicalImportPermission])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def fhir_import(request):
    try:
        bundle = request_fhir_payload(request)
        result = HealthScreeningIngestionService().import_fhir(bundle)
    except Exception as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    response_status = status.HTTP_207_MULTI_STATUS if result.get("error_count") else status.HTTP_201_CREATED
    return Response(result, status=response_status)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def risk_analysis(request):
    return _risk_analysis_response(request)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def risk_algorithm_catalog(request):
    """Expose every non-conflicted model without exposing candidate formulas."""

    return Response(public_algorithm_catalog())


def _risk_analysis_response(request):
    """Run the shared risk workflow from an already initialized DRF request."""

    patient_id = (
        request.query_params.get("patient")
        or request.query_params.get("patient_id")
        or request.data.get("patient")
        or request.data.get("patient_id")
    )
    if not patient_id:
        return Response({"detail": "patient or patient_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    patient = patient_risk_access_policy.resolve_patient(patient_id)
    patient_risk_access_policy.require_access(request.user, patient)
    result = DiseaseRiskAssessmentService().calculate_dynamic_risk(
        str(patient.id),
        actor_user=request.user,
    )
    response_status = status.HTTP_400_BAD_REQUEST if result.get("error") else status.HTTP_200_OK
    return Response(result, status=response_status)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def disease_risk_assessment(request):
    return _risk_analysis_response(request)


@api_view(["GET"])
@permission_classes([HasResearchAggregatePermission])
def cohort_summary(request):
    minimum_cell_count = 10
    result = CohortSummaryService().summarize(
        request.query_params,
        minimum_cell_count=minimum_cell_count,
    )
    AuditLog.objects.create(
        actor_user=request.user if getattr(request.user, "is_authenticated", False) else None,
        action="cohort_summary",
        target_table="health_screening_cohort",
        metadata_json={
            "filters": result.get("filters", {}),
            "privacy": result.get("privacy", {}),
            "cohort_count_returned": result.get("cohort_count"),
        },
    )
    return Response(result)


@api_view(["GET"])
@permission_classes([HasResearchAggregatePermission])
def cohort_summary_fhir(request):
    minimum_cell_count = 10
    result = CohortSummaryService().summarize(
        request.query_params,
        minimum_cell_count=minimum_cell_count,
    )
    measure_report = CohortMeasureReportBuilder().build(result)
    AuditLog.objects.create(
        actor_user=request.user if getattr(request.user, "is_authenticated", False) else None,
        action="cohort_summary_fhir",
        target_table="health_screening_cohort",
        metadata_json={
            "filters": result.get("filters", {}),
            "privacy": result.get("privacy", {}),
            "cohort_count_returned": result.get("cohort_count"),
            "fhir_resource_type": "MeasureReport",
        },
    )
    return JsonResponse(measure_report, content_type="application/fhir+json")


@api_view(["GET"])
@permission_classes([HasResearchAggregatePermission])
def data_quality_summary(request):
    dataset = request.query_params.get("dataset") or "h2u_cvd_csv"
    result = DataQualitySummaryService().summarize(dataset=dataset)
    AuditLog.objects.create(
        actor_user=request.user if getattr(request.user, "is_authenticated", False) else None,
        action="data_quality_summary",
        target_table="health_screening_dataset",
        metadata_json={
            "dataset": dataset,
            "readiness": result.get("readiness", {}),
            "record_counts": result.get("record_counts", {}),
        },
    )
    return Response(result)


@api_view(["GET"])
@permission_classes([HasResearchAggregatePermission])
def sotera_continuous_signal_report(request):
    """Return the latest deidentified continuous-signal import report."""

    result = SoteraResearchReportService().latest()
    AuditLog.objects.create(
        actor_user=request.user if getattr(request.user, "is_authenticated", False) else None,
        action="continuous_signal_report_viewed",
        target_table="ai_analysis_results",
        metadata_json={
            "dataset": result.get("dataset"),
            "available": result.get("available", False),
            "quality_status": result.get("quality", {}).get("status"),
            "ao_status": result.get("ao_readiness", {}).get("status"),
        },
    )
    return Response(result)


@api_view(["GET"])
@permission_classes([HasResearchAggregatePermission])
def patients_like_this(request):
    minimum_cell_count = 10
    result = PatientsLikeThisService().find(
        request.query_params,
        minimum_cell_count=minimum_cell_count,
    )
    if result.get("error"):
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    AuditLog.objects.create(
        actor_user=request.user if getattr(request.user, "is_authenticated", False) else None,
        action="patients_like_this",
        target_table="health_screening_similarity",
        metadata_json={
            "dataset": result.get("dataset"),
            "reference_source": result.get("reference_source"),
            "privacy": result.get("privacy", {}),
            "matched_count_returned": result.get("matched_count"),
            "matching_model": result.get("matching_model", {}).get("version"),
        },
    )
    return Response(result)


@api_view(["GET", "POST"])
@permission_classes([HasResearchAggregatePermission])
def research_reports(request):
    service = ResearchAggregateReportService()
    if request.method == "GET":
        queryset = ResearchAggregateReport.objects.filter(is_active=True).order_by("-requested_at")
        status_filter = request.query_params.get("status")
        report_type = request.query_params.get("report_type")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if report_type:
            queryset = queryset.filter(report_type=report_type)
        return Response(ResearchAggregateReportSerializer(queryset[:100], many=True).data)

    try:
        report = service.request_report(request.data, actor_user=request.user)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    AuditLog.objects.create(
        actor_user=request.user if getattr(request.user, "is_authenticated", False) else None,
        action="research_report_requested",
        target_table="research_aggregate_reports",
        target_id=report.id,
        metadata_json={
            "report_type": report.report_type,
            "dataset": report.dataset,
            "privacy": report.privacy_json,
            "status": report.status,
        },
    )
    return Response(ResearchAggregateReportSerializer(report).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([HasResearchAggregatePermission])
def research_report_detail(request, report_id):
    report = ResearchAggregateReport.objects.filter(id=report_id, is_active=True).first()
    if not report:
        return Response({"detail": "Report not found"}, status=status.HTTP_404_NOT_FOUND)
    return Response(ResearchAggregateReportSerializer(report).data)


@api_view(["POST"])
@permission_classes([HasResearchAggregateApprovalPermission])
def approve_research_report(request, report_id):
    report = ResearchAggregateReport.objects.filter(id=report_id, is_active=True).first()
    if not report:
        return Response({"detail": "Report not found"}, status=status.HTTP_404_NOT_FOUND)
    try:
        report = ResearchAggregateReportService().approve(
            report,
            actor_user=request.user,
            note=str(request.data.get("approval_note") or ""),
        )
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    AuditLog.objects.create(
        actor_user=request.user if getattr(request.user, "is_authenticated", False) else None,
        action="research_report_approved",
        target_table="research_aggregate_reports",
        target_id=report.id,
        metadata_json={"report_type": report.report_type, "dataset": report.dataset},
    )
    return Response(ResearchAggregateReportSerializer(report).data)


@api_view(["POST"])
@permission_classes([HasResearchAggregateApprovalPermission])
def reject_research_report(request, report_id):
    report = ResearchAggregateReport.objects.filter(id=report_id, is_active=True).first()
    if not report:
        return Response({"detail": "Report not found"}, status=status.HTTP_404_NOT_FOUND)
    try:
        report = ResearchAggregateReportService().reject(
            report,
            actor_user=request.user,
            note=str(request.data.get("approval_note") or ""),
        )
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    AuditLog.objects.create(
        actor_user=request.user if getattr(request.user, "is_authenticated", False) else None,
        action="research_report_rejected",
        target_table="research_aggregate_reports",
        target_id=report.id,
        metadata_json={"report_type": report.report_type, "dataset": report.dataset},
    )
    return Response(ResearchAggregateReportSerializer(report).data)


@api_view(["GET"])
@permission_classes([HasResearchAggregatePermission])
def research_report_artifact(request, report_id):
    report = ResearchAggregateReport.objects.filter(id=report_id, is_active=True).first()
    if not report:
        return Response({"detail": "Report not found"}, status=status.HTTP_404_NOT_FOUND)
    try:
        artifact = ResearchAggregateReportService().artifact(report)
    except PermissionError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)

    AuditLog.objects.create(
        actor_user=request.user if getattr(request.user, "is_authenticated", False) else None,
        action="research_report_artifact_viewed",
        target_table="research_aggregate_reports",
        target_id=report.id,
        metadata_json={"report_type": report.report_type, "dataset": report.dataset},
    )
    if report.report_type == "cohort_measure_report":
        return JsonResponse(artifact, content_type="application/fhir+json")
    return Response(artifact)


def screening_list_view(request):
    return render(request, "health_screening/screening_list.html")
