from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from services.disease_risk_engine import DiseaseRiskAssessmentService
from apps.core.authentication.permissions import HasResearchAccess, HasResearchApprovalAccess
from apps.integration.fhir_integration.models import AuditLog

from .cohort_service import CohortSummaryService
from .data_quality_service import DataQualitySummaryService
from .fhir_research_projection import CohortMeasureReportBuilder
from .ingestion_service import HealthScreeningIngestionService
from .models import HealthScreening, Immunization, Problem, Procedure, ResearchAggregateReport
from .patients_like_this_service import PatientsLikeThisService
from .research_report_service import ResearchAggregateReportService
from .serializers import (
    HealthScreeningSerializer,
    ImmunizationSerializer,
    ProblemSerializer,
    ProcedureSerializer,
    ResearchAggregateReportSerializer,
)


class HealthScreeningViewSet(viewsets.ModelViewSet):
    serializer_class = HealthScreeningSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = (
            HealthScreening.objects.select_related("patient")
            .prefetch_related("lab_results")
            .order_by("-screening_date", "-created_at")
        )
        patient = self.request.query_params.get("patient") or self.request.query_params.get("patient_id")
        if patient:
            queryset = queryset.filter(
                Q(patient_id=patient) | Q(patient__medical_record_number=str(patient))
            )
        return queryset

    def create(self, request, *args, **kwargs):
        try:
            screening = HealthScreeningIngestionService().create_screening(dict(request.data))
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(screening)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"], url_path="calculate_comprehensive_risk")
    def calculate_comprehensive_risk(self, request, pk=None):
        screening = self.get_object()
        result = DiseaseRiskAssessmentService().calculate_dynamic_risk(
            str(screening.patient_id),
            actor_user=request.user,
        )
        response_status = status.HTTP_400_BAD_REQUEST if result.get("error") else status.HTTP_200_OK
        return Response(result, status=response_status)

    @action(detail=True, methods=["get"], url_path="risk-analysis")
    def risk_analysis(self, request, pk=None):
        screening = self.get_object()
        result = DiseaseRiskAssessmentService().calculate_dynamic_risk(
            str(screening.patient_id),
            actor_user=request.user,
        )
        response_status = status.HTTP_400_BAD_REQUEST if result.get("error") else status.HTTP_200_OK
        return Response(result, status=response_status)


class ImmunizationViewSet(viewsets.ModelViewSet):
    queryset = Immunization.objects.all()
    serializer_class = ImmunizationSerializer
    permission_classes = [IsAuthenticated]


class ProblemViewSet(viewsets.ModelViewSet):
    queryset = Problem.objects.all()
    serializer_class = ProblemSerializer
    permission_classes = [IsAuthenticated]


class ProcedureViewSet(viewsets.ModelViewSet):
    queryset = Procedure.objects.all()
    serializer_class = ProcedureSerializer
    permission_classes = [IsAuthenticated]


@api_view(["POST"])
@permission_classes([IsAuthenticated])
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
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def bulk_import(request):
    file_obj = request.FILES.get("file")
    if not file_obj:
        return Response({"detail": "file is required"}, status=status.HTTP_400_BAD_REQUEST)

    result = HealthScreeningIngestionService().bulk_import_file(file_obj)
    response_status = status.HTTP_207_MULTI_STATUS if result.get("error_count") else status.HTTP_201_CREATED
    return Response(result, status=response_status)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def fhir_import(request):
    fhir_data = request.data.get("fhir_data")
    if not fhir_data:
        return Response({"detail": "fhir_data is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        result = HealthScreeningIngestionService().import_fhir(
            fhir_data,
            request.data.get("format") or "json",
        )
    except Exception as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    response_status = status.HTTP_207_MULTI_STATUS if result.get("error_count") else status.HTTP_201_CREATED
    return Response(result, status=response_status)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def risk_analysis(request):
    patient_id = (
        request.query_params.get("patient")
        or request.query_params.get("patient_id")
        or request.data.get("patient")
        or request.data.get("patient_id")
    )
    if not patient_id:
        return Response({"detail": "patient or patient_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    result = DiseaseRiskAssessmentService().calculate_dynamic_risk(
        str(patient_id),
        actor_user=request.user,
    )
    response_status = status.HTTP_400_BAD_REQUEST if result.get("error") else status.HTTP_200_OK
    return Response(result, status=response_status)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def disease_risk_assessment(request):
    return risk_analysis(request)


@api_view(["GET"])
@permission_classes([HasResearchAccess])
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
@permission_classes([HasResearchAccess])
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
@permission_classes([HasResearchAccess])
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
@permission_classes([HasResearchAccess])
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
@permission_classes([HasResearchAccess])
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
@permission_classes([HasResearchAccess])
def research_report_detail(request, report_id):
    report = ResearchAggregateReport.objects.filter(id=report_id, is_active=True).first()
    if not report:
        return Response({"detail": "Report not found"}, status=status.HTTP_404_NOT_FOUND)
    return Response(ResearchAggregateReportSerializer(report).data)


@api_view(["POST"])
@permission_classes([HasResearchApprovalAccess])
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
@permission_classes([HasResearchApprovalAccess])
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
@permission_classes([HasResearchAccess])
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
