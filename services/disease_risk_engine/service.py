import uuid
import re
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.db import transaction
from django.utils import timezone

from apps.clinical.health_screening.models import AIAnalysisJob, AIAnalysisResult
from apps.integration.fhir_integration.models import AuditLog, FHIRResource, FHIRResourceMapping
from apps.integration.fhir_integration.resource_identity import identity

from .algorithm_registry import (
    CORE_MODEL_VERSION,
    FHIRResultType,
    RUNTIME_CATALOG_VERSION,
    public_algorithm_catalog,
    runtime_registry,
)
from .formula_catalog import DiseaseRiskResult
from .repository import DiseaseRiskInputRepository
from .runtime_calculators import calculate_catalog_risks


_RUNTIME_ALGORITHM_REGISTRY = runtime_registry()
RISK_OUTPUT_ORIGIN_NAMESPACE = "allcare365:disease-risk-engine:v1"


class DiseaseRiskAssessmentService:
    """Application service for CORE.xlsx based disease risk assessment."""

    MODEL_NAME = "allcare365-deterministic-risk-catalog"
    MODEL_VERSION = CORE_MODEL_VERSION

    def __init__(self, repository: Optional[DiseaseRiskInputRepository] = None):
        self.repository = repository or DiseaseRiskInputRepository()

    def calculate_dynamic_risk(self, patient_id: str, actor_user=None) -> Dict[str, Any]:
        return self.calculate_for_patient(patient_id, actor_user=actor_user)

    @transaction.atomic
    def calculate_for_patient(
        self,
        patient_id: str,
        actor_user=None,
        *,
        evaluation_as_of: Optional[date] = None,
    ) -> Dict[str, Any]:
        patient = self.repository.get_patient(patient_id)
        if not patient:
            return {"error": "Patient not found"}

        started_at = timezone.now()
        snapshot = self.repository.build_snapshot(
            patient,
            evaluation_as_of=evaluation_as_of,
        )
        # The catalog response includes explicit governance cards for models
        # that are visible in the product but not approved for execution.
        results = calculate_catalog_risks(snapshot.data)

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
                "clinical_models": [
                    "Hospital-approved risk catalog 2026-07",
                    "CORE.xlsx legacy governed models",
                    "AHA PREVENT base equations",
                ],
                "algorithm_catalog_version": RUNTIME_CATALOG_VERSION,
                "evaluation_as_of": (
                    evaluation_as_of.isoformat() if evaluation_as_of is not None else None
                ),
            },
            started_at=started_at,
            completed_at=timezone.now(),
        )

        persisted_results = []
        for result in results:
            persisted = self._persist_result(job, patient, result, snapshot.sources)
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
                "algorithm_catalog_version": RUNTIME_CATALOG_VERSION,
                "result_ids": [str(saved.id) for _, saved in persisted_results],
                "algorithm_versions": {
                    result.algorithm_key: self._model_version(result)
                    for result, _ in persisted_results
                },
            },
        )

        return self._build_response(job, snapshot.data, snapshot.sources, persisted_results)

    def _persist_result(
        self,
        job: AIAnalysisJob,
        patient,
        result: DiseaseRiskResult,
        sources: Dict[str, Any],
    ) -> AIAnalysisResult:
        metadata = _RUNTIME_ALGORITHM_REGISTRY.get_runtime(result.algorithm_key)
        if metadata is None:
            raise ValueError(f"Unregistered runtime algorithm: {result.algorithm_key!r}")
        effective_model_version = result.model_version or metadata.model_version
        effective_method_uri = result.method_uri or metadata.method_uri
        saved = AIAnalysisResult.objects.create(
            job=job,
            patient=patient,
            result_type=result.algorithm_key,
            model_version=effective_model_version,
            # Deterministic clinical equations do not produce a calibrated
            # model-confidence measure. Keep this null instead of inventing a
            # percentage that could be mistaken for clinical evidence.
            confidence_score=None,
            risk_level=result.risk_level,
            result_json=result.to_api_payload(),
            explanation_json={
                "source_document": metadata.source_label,
                "missing_data": result.missing_data,
                "evidence": result.evidence,
                "applicability": result.applicability,
                "limitations": result.limitations,
                "method_uri": effective_method_uri,
            },
            recommendation_text=result.recommendation_text,
            requires_doctor_review=(
                result.risk_level in {"moderate", "moderate_high", "high"}
                or bool(result.missing_data)
                or result.applicability != "applicable"
            ),
        )
        if metadata.output_resource is FHIRResultType.OBSERVATION:
            self._persist_observation_mapping(patient, saved, result, sources)
        else:
            self._persist_risk_assessment_mapping(patient, saved, result, sources)
        return saved

    def _persist_observation_mapping(self, patient, saved, result, sources) -> None:
        observation_id = f"risk-observation-{str(saved.id).replace('-', '')[:20]}"
        metadata = _RUNTIME_ALGORITHM_REGISTRY.get_runtime(result.algorithm_key)
        basis_references = self._basis_references(result, sources)
        model_version = result.model_version or metadata.model_version
        category = "survey" if result.algorithm_key == "gad7" else (
            "vital-signs" if result.algorithm_key == "bmi" else "laboratory"
        )
        unit = "kg/m2" if result.algorithm_key == "bmi" else "1"
        fhir_json = {
            "resourceType": "Observation",
            "id": observation_id,
            "status": "final",
            "category": [{"coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": category,
            }]}],
            "code": {"coding": [{
                "system": "https://allcare365.local/fhir/CodeSystem/risk-algorithm-output",
                "code": result.algorithm_key,
                "display": result.algorithm_name,
                "version": model_version,
            }], "text": result.algorithm_name},
            "subject": {"reference": f"Patient/{identity.patient_id(patient)}"},
            "effectiveDateTime": timezone.now().isoformat(),
            "interpretation": [{"text": result.risk_category}],
            "note": [{"text": result.recommendation_text}],
        }
        if result.score is not None:
            fhir_json["valueQuantity"] = {
                "value": float(result.score),
                "unit": unit,
                "system": "http://unitsofmeasure.org",
                "code": unit,
            }
        else:
            fhir_json["dataAbsentReason"] = {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/data-absent-reason",
                    "code": "unknown",
                }]
            }
        if basis_references:
            fhir_json["derivedFrom"] = [{"reference": reference} for reference in basis_references]
        if metadata.method_uri:
            fhir_json["extension"] = [{
                "url": "https://allcare365.local/fhir/StructureDefinition/risk-algorithm-source",
                "valueUri": metadata.method_uri,
            }]
        resource = self._upsert_owned_fhir_resource(
            resource_type="Observation", resource_id=observation_id, resource_data=fhir_json
        )
        FHIRResourceMapping.objects.update_or_create(
            local_table="ai_analysis_results",
            local_id=saved.id,
            fhir_resource_type="Observation",
            defaults={
                "patient": patient,
                "fhir_resource_ref": resource,
                "fhir_resource_id": observation_id,
                "profile_url": "http://hl7.org/fhir/StructureDefinition/Observation",
                "fhir_json": fhir_json,
                "sync_status": "mapped",
                "last_synced_at": timezone.now(),
                "metadata_json": {
                    "algorithm": result.algorithm_key,
                    "model_version": model_version,
                    "method_uri": metadata.method_uri,
                    "provenance_resource_id": f"provenance-{observation_id}",
                },
            },
        )
        self._persist_provenance(
            patient=patient,
            saved=saved,
            target_resource_type="Observation",
            target_resource_id=observation_id,
            result=result,
            basis_references=basis_references,
            model_version=model_version,
        )

    def _persist_risk_assessment_mapping(
        self,
        patient,
        saved: AIAnalysisResult,
        result: DiseaseRiskResult,
        sources: Dict[str, Any],
    ) -> None:
        fhir_resource_id = f"risk-{str(saved.id).replace('-', '')[:24]}"
        metadata = _RUNTIME_ALGORITHM_REGISTRY.get_runtime(result.algorithm_key)
        if metadata is None:
            raise ValueError(f"Unregistered runtime algorithm: {result.algorithm_key!r}")
        effective_model_version = result.model_version or metadata.model_version
        effective_method_uri = result.method_uri or metadata.method_uri
        basis_references = self._basis_references(result, sources)
        patient_fhir_id = identity.patient_id(patient)
        fhir_json = {
            "resourceType": "RiskAssessment",
            "id": fhir_resource_id,
            # Executed workflows are final even when inputs are insufficient.
            # A governance-only catalog entry is registered but not performed.
            "status": "final" if metadata.runtime_enabled else "registered",
            "subject": {"reference": f"Patient/{patient_fhir_id}"},
            "occurrenceDateTime": timezone.now().isoformat(),
            "method": {
                "coding": [
                    {
                        "system": "https://allcare365.local/risk-models",
                        "code": result.algorithm_key,
                        "display": result.algorithm_name,
                        "version": effective_model_version,
                    }
                ],
                "text": result.algorithm_name,
            },
            "prediction": [
                {
                    "outcome": {"text": result.outcome_key},
                    "qualitativeRisk": {"text": result.risk_category},
                    "rationale": f"{result.risk_percentage}. {result.recommendation_text}",
                }
            ],
            "note": [
                {
                    "text": (
                        f"Generated by {self.MODEL_NAME}; algorithm version {effective_model_version}; "
                        f"applicability={result.applicability}."
                    )
                }
            ],
        }
        if effective_method_uri:
            fhir_json["extension"] = [
                {
                    "url": "https://allcare365.local/fhir/StructureDefinition/risk-algorithm-source",
                    "valueUri": effective_method_uri,
                }
            ]
        if basis_references:
            fhir_json["basis"] = [{"reference": reference} for reference in basis_references]
        probability = self._probability_representation(result)
        if probability is not None:
            probability_key, probability_value = probability
            fhir_json["prediction"][0][probability_key] = probability_value

        resource = self._upsert_owned_fhir_resource(
            resource_type="RiskAssessment",
            resource_id=fhir_resource_id,
            resource_data=fhir_json,
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
                    "model_version": effective_model_version,
                    "method_uri": effective_method_uri,
                    "provenance_resource_id": f"provenance-{fhir_resource_id}",
                },
            },
        )
        self._persist_provenance(
            patient=patient,
            saved=saved,
            target_resource_type="RiskAssessment",
            target_resource_id=fhir_resource_id,
            result=result,
            basis_references=basis_references,
            model_version=effective_model_version,
        )

    def _persist_provenance(
        self,
        *,
        patient,
        saved: AIAnalysisResult,
        target_resource_type: str,
        target_resource_id: str,
        result: DiseaseRiskResult,
        basis_references: List[str],
        model_version: str,
    ) -> None:
        provenance_id = f"provenance-{target_resource_id}"
        provenance_json = {
            "resourceType": "Provenance",
            "id": provenance_id,
            "target": [{"reference": f"{target_resource_type}/{target_resource_id}"}],
            "recorded": timezone.now().isoformat(),
            "activity": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-DataOperation",
                        "code": "CREATE",
                        "display": "create",
                    }
                ],
                "text": (
                    f"{result.algorithm_name} deterministic risk calculation"
                    if _RUNTIME_ALGORITHM_REGISTRY.get_runtime(result.algorithm_key).runtime_enabled
                    else f"{result.algorithm_name} governance gate evaluation; calculation not executed"
                ),
            },
            "agent": [
                {
                    "type": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/provenance-participant-type",
                                "code": "assembler",
                                "display": "Assembler",
                            }
                        ]
                    },
                    "who": {"display": f"{self.MODEL_NAME} {model_version}"},
                }
            ],
            "entity": [
                {"role": "source", "what": {"reference": reference}}
                for reference in basis_references
            ],
        }
        method_uri = result.method_uri or (
            _RUNTIME_ALGORITHM_REGISTRY.get_runtime(result.algorithm_key).method_uri
            if _RUNTIME_ALGORITHM_REGISTRY.get_runtime(result.algorithm_key)
            else None
        )
        if method_uri:
            provenance_json["policy"] = [method_uri]
        resource = self._upsert_owned_fhir_resource(
            resource_type="Provenance",
            resource_id=provenance_id,
            resource_data=provenance_json,
        )
        FHIRResourceMapping.objects.update_or_create(
            local_table="ai_analysis_results",
            local_id=saved.id,
            fhir_resource_type="Provenance",
            defaults={
                "patient": patient,
                "fhir_resource_ref": resource,
                "fhir_resource_id": provenance_id,
                "profile_url": "http://hl7.org/fhir/StructureDefinition/Provenance",
                "fhir_json": provenance_json,
                "sync_status": "mapped",
                "last_synced_at": timezone.now(),
                "metadata_json": {
                    "target": f"{target_resource_type}/{target_resource_id}",
                    "algorithm": result.algorithm_key,
                },
            },
        )

    def _upsert_owned_fhir_resource(
        self,
        *,
        resource_type: str,
        resource_id: str,
        resource_data: Dict[str, Any],
    ) -> FHIRResource:
        """Persist an internally generated FHIR resource without source takeover."""

        resource, created = FHIRResource.objects.select_for_update().get_or_create(
            resource_type=resource_type,
            resource_id=resource_id,
            defaults={
                "origin_namespace": RISK_OUTPUT_ORIGIN_NAMESPACE,
                "resource_data": resource_data,
            },
        )
        if not created:
            if resource.origin_namespace != RISK_OUTPUT_ORIGIN_NAMESPACE:
                raise ValueError(
                    f"FHIR {resource_type}/{resource_id} is owned by "
                    f"{resource.origin_namespace}, not the disease-risk engine"
                )
            resource.resource_data = resource_data
            resource.save(update_fields=["resource_data", "last_updated"])
        return resource

    def _basis_references(self, result: DiseaseRiskResult, sources: Dict[str, Any]) -> List[str]:
        metadata = _RUNTIME_ALGORITHM_REGISTRY.get_runtime(result.algorithm_key)
        if metadata is None:
            raise ValueError(f"Unregistered runtime algorithm: {result.algorithm_key!r}")
        references = []
        for field in metadata.required_inputs:
            self._collect_fhir_references(sources.get(field), references)
        return list(dict.fromkeys(references))

    def _collect_fhir_references(self, source: Any, references: List[str]) -> None:
        if isinstance(source, dict):
            reference = source.get("fhir_reference")
            if reference:
                references.append(str(reference))
            for item in source.get("fhir_references") or []:
                if item:
                    references.append(str(item))
            for value in source.values():
                self._collect_fhir_references(value, references)
        elif isinstance(source, list):
            for value in source:
                self._collect_fhir_references(value, references)

    def _build_response(self, job, data: Dict[str, Any], sources: Dict[str, Any], results) -> Dict[str, Any]:
        executable_results = [
            (result, saved)
            for result, saved in results
            if _RUNTIME_ALGORITHM_REGISTRY.get_runtime(result.algorithm_key).runtime_enabled
        ]
        calculated_algorithm_ids = [
            result.algorithm_key
            for result, _ in executable_results
            if result.score is not None
            and not result.missing_data
            and result.applicability == "applicable"
        ]
        insufficient_data_algorithm_ids = [
            result.algorithm_key
            for result, _ in executable_results
            if result.missing_data
        ]
        not_applicable_algorithm_ids = [
            result.algorithm_key
            for result, _ in executable_results
            if not result.missing_data and result.applicability != "applicable"
        ]
        governance_gated_algorithm_ids = [
            result.algorithm_key
            for result, _ in results
            if not _RUNTIME_ALGORITHM_REGISTRY.get_runtime(result.algorithm_key).runtime_enabled
        ]
        executable_model_count = len(executable_results)
        resolved_model_count = len(calculated_algorithm_ids) + len(not_applicable_algorithm_ids)
        response: Dict[str, Any] = {
            "risk_run_id": str(job.id),
            "disease_risk_job_id": str(job.id),
            "model_name": self.MODEL_NAME,
            "model_version": self.MODEL_VERSION,
            "algorithm_catalog_version": RUNTIME_CATALOG_VERSION,
            "algorithm_catalog": public_algorithm_catalog(),
            "execution_summary": {
                "runtime_catalog_models": len(results),
                "executable_models": executable_model_count,
                "calculated_models": len(calculated_algorithm_ids),
                "insufficient_data_models": len(insufficient_data_algorithm_ids),
                "not_applicable_models": len(not_applicable_algorithm_ids),
                "governance_gated_models": len(governance_gated_algorithm_ids),
                "resolved_models": resolved_model_count,
                "all_executable_models_calculated": (
                    len(calculated_algorithm_ids) == executable_model_count
                ),
                "all_executable_models_resolved": (
                    resolved_model_count == executable_model_count
                    and not insufficient_data_algorithm_ids
                ),
                "calculated_algorithm_ids": calculated_algorithm_ids,
                "insufficient_data_algorithm_ids": insufficient_data_algorithm_ids,
                "not_applicable_algorithm_ids": not_applicable_algorithm_ids,
                "governance_gated_algorithm_ids": governance_gated_algorithm_ids,
            },
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

    def _model_version(self, result: DiseaseRiskResult) -> str:
        metadata = _RUNTIME_ALGORITHM_REGISTRY.get_runtime(result.algorithm_key)
        if metadata is None:
            raise ValueError(f"Unregistered runtime algorithm: {result.algorithm_key!r}")
        return result.model_version or metadata.model_version

    def _probability_representation(self, result: DiseaseRiskResult):
        metadata = _RUNTIME_ALGORITHM_REGISTRY.get_runtime(result.algorithm_key)
        if metadata is None:
            raise ValueError(f"Unregistered runtime algorithm: {result.algorithm_key!r}")

        if metadata.score_represents_probability and result.score is not None:
            probability = float(result.score)
            if 0 <= probability <= 1:
                return "probabilityDecimal", probability
            return None

        text = str(result.risk_percentage or "").strip()
        exact = re.fullmatch(r"(\d+(?:\.\d+)?)%", text)
        if exact:
            return "probabilityDecimal", float(Decimal(exact.group(1)) / Decimal("100"))

        bounded = re.fullmatch(r"([<>])\s*(\d+(?:\.\d+)?)%", text)
        if bounded:
            boundary = float(Decimal(bounded.group(2)) / Decimal("100"))
            edge = "high" if bounded.group(1) == "<" else "low"
            return "probabilityRange", {
                edge: {
                    "value": boundary,
                    "system": "http://unitsofmeasure.org",
                    "code": "1",
                }
            }

        interval = re.fullmatch(r"(\d+(?:\.\d+)?)\s*[-~]\s*(\d+(?:\.\d+)?)%", text)
        if interval:
            low = Decimal(interval.group(1)) / Decimal("100")
            high = Decimal(interval.group(2)) / Decimal("100")
            if low > high:
                return None
            return "probabilityRange", {
                "low": {
                    "value": float(low),
                    "system": "http://unitsofmeasure.org",
                    "code": "1",
                },
                "high": {
                    "value": float(high),
                    "system": "http://unitsofmeasure.org",
                    "code": "1",
                },
            }
        return None
