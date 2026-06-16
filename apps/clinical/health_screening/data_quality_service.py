from __future__ import annotations

from typing import Any, Dict

from django.db.models import Count, Max, Min

from .cohort_service import CANONICAL_NUMERIC_FEATURES, CohortSummaryService
from .models import DataImportBatch, HealthScreening, QuestionnaireResponse


class DataQualitySummaryService:
    """Dataset-level quality metrics for research readiness."""

    def summarize(self, *, dataset: str = "h2u_cvd_csv") -> Dict[str, Any]:
        screenings = (
            HealthScreening.objects.filter(is_active=True, product_encounters__source_type=dataset)
            .select_related("patient")
            .distinct()
        )
        screening_ids = list(screenings.values_list("id", flat=True))
        total = len(screening_ids)
        date_bounds = screenings.aggregate(first=Min("screening_date"), last=Max("screening_date"))
        feature_values = CohortSummaryService()._feature_values(screening_ids)
        questionnaire_ids = set(
            QuestionnaireResponse.objects.filter(
                encounter__source_screening_id__in=screening_ids,
                status="completed",
            ).values_list("encounter__source_screening_id", flat=True)
        )

        latest_batch = (
            DataImportBatch.objects.filter(source_type=dataset)
            .order_by("-created_at")
            .values("id", "status", "total_rows", "success_rows", "failed_rows", "summary_json", "created_at")
            .first()
        )

        duplicate_identifiers = (
            screenings.exclude(encounter_identifier="")
            .values("encounter_identifier")
            .annotate(n=Count("id"))
            .filter(n__gt=1)
            .count()
        )

        feature_coverage = {}
        for key, spec in CANONICAL_NUMERIC_FEATURES.items():
            present = sum(1 for values in feature_values.values() if key in values)
            feature_coverage[key] = {
                "label": spec["label"],
                "unit": spec["unit"],
                "present": present,
                "missing": max(total - present, 0),
                "coverage": self._ratio(present, total),
            }

        questionnaire_present = len(questionnaire_ids)
        coverage_values = [item["coverage"] for item in feature_coverage.values()]
        coverage_values.append(self._ratio(questionnaire_present, total))
        readiness_score = round(sum(coverage_values) / len(coverage_values), 4) if coverage_values else 0

        return {
            "dataset": dataset,
            "record_counts": {
                "patients": screenings.values("patient_id").distinct().count(),
                "screenings": total,
                "questionnaire_responses": questionnaire_present,
            },
            "date_range": {
                "first": date_bounds["first"].isoformat() if date_bounds["first"] else None,
                "last": date_bounds["last"].isoformat() if date_bounds["last"] else None,
            },
            "import_batch": self._serialize_batch(latest_batch),
            "duplicates": {
                "duplicate_encounter_identifiers": duplicate_identifiers,
            },
            "feature_coverage": feature_coverage,
            "questionnaire_coverage": {
                "present": questionnaire_present,
                "missing": max(total - questionnaire_present, 0),
                "coverage": self._ratio(questionnaire_present, total),
            },
            "readiness": {
                "score": readiness_score,
                "label": self._readiness_label(readiness_score, duplicate_identifiers),
            },
        }

    def _serialize_batch(self, batch: Dict[str, Any] | None) -> Dict[str, Any]:
        if not batch:
            return {}
        return {
            "id": str(batch["id"]),
            "status": batch["status"],
            "total_rows": batch["total_rows"],
            "success_rows": batch["success_rows"],
            "failed_rows": batch["failed_rows"],
            "summary": batch["summary_json"] or {},
            "created_at": batch["created_at"].isoformat() if batch["created_at"] else None,
        }

    def _ratio(self, numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0
        return round(numerator / denominator, 4)

    def _readiness_label(self, score: float, duplicate_count: int) -> str:
        if duplicate_count:
            return "needs_review"
        if score >= 0.9:
            return "research_ready"
        if score >= 0.75:
            return "usable_with_caveats"
        return "needs_data_work"
