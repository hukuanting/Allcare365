import uuid
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from django.db import transaction
from django.utils import timezone

from apps.clinical.health_screening.models import AIAnalysisJob, AIAnalysisResult
from apps.integration.fhir_integration.models import AuditLog, FHIRResource, FHIRResourceMapping

from .calculators import (
    DiseaseRiskResult,
    calculate_ausdrisk_diabetes,
    calculate_chinese_diabetes,
    calculate_fhs_diabetes,
    calculate_framingham_fatty_liver,
    calculate_metabolic_syndrome,
    calculate_nafld,
    calculate_vascular_caide,
)
from .repository import DiseaseRiskInputRepository


class DiseaseRiskAssessmentService:
    """Application service for CORE.xlsx based disease risk assessment."""

    MODEL_NAME = "core-xlsx-disease-risk"
    MODEL_VERSION = "core-xlsx-2024-12-24"

    def __init__(self, repository: Optional[DiseaseRiskInputRepository] = None):
        self.repository = repository or DiseaseRiskInputRepository()

    def calculate_dynamic_risk(self, patient_id: str, actor_user=None) -> Dict[str, Any]:
        return self.calculate_for_patient(patient_id, actor_user=actor_user)

    @transaction.atomic
    def calculate_for_patient(self, patient_id: str, actor_user=None) -> Dict[str, Any]:
        patient = self.repository.get_patient(patient_id)
        if not patient:
            return {"error": "Patient not found"}

        started_at = timezone.now()
        snapshot = self.repository.build_snapshot(patient)
        results = [
            calculate_fhs_diabetes(snapshot.data),
            calculate_chinese_diabetes(snapshot.data),
            calculate_metabolic_syndrome(snapshot.data),
            calculate_nafld(snapshot.data),
            calculate_framingham_fatty_liver(snapshot.data),
            calculate_ausdrisk_diabetes(snapshot.data),
            calculate_vascular_caide(snapshot.data),
        ]

        job = AIAnalysisJob.objects.create(
            patient=patient,
            requested_by_user=actor_user if getattr(actor_user, "is_authenticated", False) else None,
            job_type="disease_risk_assessment",
            status="completed",
            model_name=self.MODEL_NAME,
            model_version=self.MODEL_VERSION,
            input_json={
                "data": snapshot.data,
                "sources": snapshot.sources,
                "workbook": "CORE.xlsx",
            },
            started_at=started_at,
            completed_at=timezone.now(),
        )

        persisted_results = []
        for result in results:
            persisted = self._persist_result(job, patient, result)
            persisted_results.append((result, persisted))

        AuditLog.objects.create(
            actor_user=actor_user if getattr(actor_user, "is_authenticated", False) else None,
            patient=patient,
            action="disease_risk_assess",
            target_table="ai_analysis_jobs",
            target_id=job.id,
            metadata_json={
                "model_name": self.MODEL_NAME,
                "model_version": self.MODEL_VERSION,
                "result_ids": [str(saved.id) for _, saved in persisted_results],
            },
        )

        return self._build_response(job, snapshot.data, snapshot.sources, persisted_results)

    def _persist_result(self, job: AIAnalysisJob, patient, result: DiseaseRiskResult) -> AIAnalysisResult:
        saved = AIAnalysisResult.objects.create(
            job=job,
            patient=patient,
            result_type=result.algorithm_key,
            model_version=self.MODEL_VERSION,
            confidence_score=Decimal("0.7000") if result.missing_data else Decimal("0.9000"),
            risk_level=result.risk_level,
            result_json=result.to_api_payload(),
            explanation_json={
                "workbook": "CORE.xlsx",
                "source_sheet": self._sheet_name(result.algorithm_key),
                "missing_data": result.missing_data,
                "evidence": result.evidence,
            },
            recommendation_text=result.recommendation_text,
            requires_doctor_review=result.risk_level in {"moderate", "moderate_high", "high"} or bool(result.missing_data),
        )
        self._persist_risk_assessment_mapping(patient, saved, result)
        return saved

    def _persist_risk_assessment_mapping(self, patient, saved: AIAnalysisResult, result: DiseaseRiskResult) -> None:
        fhir_resource_id = f"risk-{str(saved.id).replace('-', '')[:24]}"
        fhir_json = {
            "resourceType": "RiskAssessment",
            "id": fhir_resource_id,
            "status": "final",
            "subject": {"reference": f"Patient/{patient.id}"},
            "occurrenceDateTime": timezone.now().isoformat(),
            "method": {
                "coding": [
                    {
                        "system": "https://allcare365.local/risk-models",
                        "code": result.algorithm_key,
                        "display": result.algorithm_name,
                    }
                ],
                "text": result.algorithm_name,
            },
            "prediction": [
                {
                    "outcome": {"text": result.outcome_key},
                    "qualitativeRisk": {"text": result.risk_category},
                    "probabilityString": result.risk_percentage,
                    "rationale": result.recommendation_text,
                }
            ],
            "note": [{"text": f"Generated by {self.MODEL_NAME} {self.MODEL_VERSION}"}],
        }
        probability = self._probability_decimal(result.risk_percentage)
        if probability is not None:
            fhir_json["prediction"][0]["probabilityDecimal"] = probability

        resource, _ = FHIRResource.objects.update_or_create(
            resource_type="RiskAssessment",
            resource_id=fhir_resource_id,
            defaults={"resource_data": fhir_json},
        )
        FHIRResourceMapping.objects.update_or_create(
            local_table="ai_analysis_results",
            local_id=saved.id,
            fhir_resource_type="RiskAssessment",
            defaults={
                "patient": patient,
                "fhir_resource_ref": resource,
                "fhir_resource_id": fhir_resource_id,
                "profile_url": "http://hl7.org/fhir/StructureDefinition/RiskAssessment",
                "fhir_json": fhir_json,
                "sync_status": "mapped",
                "last_synced_at": timezone.now(),
                "metadata_json": {
                    "algorithm": result.algorithm_key,
                    "model_version": self.MODEL_VERSION,
                },
            },
        )

    def _build_response(self, job, data: Dict[str, Any], sources: Dict[str, Any], results) -> Dict[str, Any]:
        response: Dict[str, Any] = {
            "risk_run_id": str(job.id),
            "disease_risk_job_id": str(job.id),
            "model_name": self.MODEL_NAME,
            "model_version": self.MODEL_VERSION,
            "data_summary": {
                "data": data,
                "sources": sources,
                "missing_data": sorted({field for result, _ in results for field in result.missing_data}),
            },
            "disease_risk_results": [self._result_payload(result, saved) for result, saved in results],
        }
        for result, _ in results:
            response.setdefault(result.algorithm_key, {})[result.outcome_key] = {
                "risk_percentage": result.risk_percentage,
                "risk_score": result.score,
                "risk_level": result.risk_level,
                "risk_category": result.risk_category,
                "missing_data": result.missing_data,
                "recommendation_text": result.recommendation_text,
            }
        return response

    def _result_payload(self, result: DiseaseRiskResult, saved: AIAnalysisResult) -> Dict[str, Any]:
        payload = result.to_api_payload()
        payload["id"] = str(saved.id)
        payload["requires_doctor_review"] = saved.requires_doctor_review
        return payload

    def _sheet_name(self, algorithm_key: str) -> str:
        return {
            "framingham_diabetes": "FHS DM",
            "chinese_diabetes": "CH DM",
            "metabolic_syndrome": "MetS",
            "nafld_fibrosis": "NAFLD",
            "framingham_fatty_liver": "FHSFLD",
            "ausdrisk_diabetes": "AusDM",
            "vascular_caide": "GVR CAIDE",
        }.get(algorithm_key, "CORE.xlsx")

    def _probability_decimal(self, value: str) -> Optional[float]:
        try:
            normalized = str(value).replace("%", "").replace(">", "").replace("<", "").strip()
            if "-" in normalized:
                parts = [Decimal(part) for part in normalized.split("-") if part]
                return float((sum(parts) / len(parts)) / Decimal("100"))
            return float(Decimal(normalized) / Decimal("100"))
        except (InvalidOperation, ValueError, ZeroDivisionError):
            return None
