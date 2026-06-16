from __future__ import annotations

from typing import Any, Dict

from django.db import transaction
from django.utils import timezone

from .cohort_service import CohortSummaryService
from .fhir_research_projection import CohortMeasureReportBuilder
from .models import ResearchAggregateReport
from .patients_like_this_service import PatientsLikeThisService


SUPPORTED_REPORT_TYPES = {"cohort_summary", "cohort_measure_report", "patients_like_this"}


class ResearchAggregateReportService:
    """Governed aggregate report snapshots for approved research outputs."""

    def request_report(self, payload: Dict[str, Any], *, actor_user=None, minimum_cell_count: int = 10) -> ResearchAggregateReport:
        report_type = str(payload.get("report_type") or "cohort_summary")
        if report_type not in SUPPORTED_REPORT_TYPES:
            raise ValueError(f"Unsupported report_type: {report_type}")

        query_params = dict(payload.get("query_params") or {})
        dataset = str(query_params.get("dataset") or payload.get("dataset") or "h2u_cvd_csv")
        query_params["dataset"] = dataset
        title = str(payload.get("title") or self._default_title(report_type, dataset))

        result, fhir_json = self._generate(report_type, query_params, minimum_cell_count=minimum_cell_count)
        privacy = result.get("privacy", {})
        if privacy.get("line_level_data_returned") is not False:
            raise ValueError("Research aggregate reports must not contain line-level data")

        with transaction.atomic():
            report = ResearchAggregateReport.objects.create(
                requested_by_user=actor_user if getattr(actor_user, "is_authenticated", False) else None,
                created_by=actor_user if getattr(actor_user, "is_authenticated", False) else None,
                title=title,
                report_type=report_type,
                status="requested",
                dataset=dataset,
                query_params_json=query_params,
                privacy_json=privacy,
                result_json=result,
                fhir_json=fhir_json,
                metadata_json={
                    "minimum_cell_count": minimum_cell_count,
                    "artifact_locked_until_approved": True,
                },
            )
        return report

    def approve(self, report: ResearchAggregateReport, *, actor_user=None, note: str = "") -> ResearchAggregateReport:
        if report.status != "requested":
            raise ValueError(f"Only requested reports can be approved; current status is {report.status}")
        report.status = "approved"
        report.approved_by_user = actor_user if getattr(actor_user, "is_authenticated", False) else None
        report.updated_by = actor_user if getattr(actor_user, "is_authenticated", False) else None
        report.approved_at = timezone.now()
        report.approval_note = note or report.approval_note
        report.save(update_fields=["status", "approved_by_user", "updated_by", "approved_at", "approval_note", "updated_at"])
        return report

    def reject(self, report: ResearchAggregateReport, *, actor_user=None, note: str = "") -> ResearchAggregateReport:
        if report.status != "requested":
            raise ValueError(f"Only requested reports can be rejected; current status is {report.status}")
        report.status = "rejected"
        report.updated_by = actor_user if getattr(actor_user, "is_authenticated", False) else None
        report.rejected_at = timezone.now()
        report.approval_note = note or report.approval_note
        report.save(update_fields=["status", "updated_by", "rejected_at", "approval_note", "updated_at"])
        return report

    def artifact(self, report: ResearchAggregateReport) -> Dict[str, Any]:
        if report.status != "approved":
            raise PermissionError("Report artifact is locked until approval")
        if report.report_type == "cohort_measure_report":
            return report.fhir_json
        return report.result_json

    def _generate(self, report_type: str, query_params: Dict[str, Any], *, minimum_cell_count: int) -> tuple[Dict[str, Any], Dict[str, Any]]:
        if report_type == "patients_like_this":
            result = PatientsLikeThisService().find(query_params, minimum_cell_count=minimum_cell_count)
            if result.get("error"):
                raise ValueError(result["error"])
            return result, {}

        cohort_result = CohortSummaryService().summarize(query_params, minimum_cell_count=minimum_cell_count)
        if report_type == "cohort_measure_report":
            return cohort_result, CohortMeasureReportBuilder().build(cohort_result)
        return cohort_result, {}

    def _default_title(self, report_type: str, dataset: str) -> str:
        return f"{report_type.replace('_', ' ').title()} - {dataset}"
