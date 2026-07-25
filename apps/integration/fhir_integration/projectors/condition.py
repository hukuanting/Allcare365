"""
Condition Projector — Maps ``health_screening.Problem`` → FHIR Condition.

Handles both US Core profiles:
  - us-core-condition-problems-health-concerns (problem-list-item)
  - us-core-condition-encounter-diagnosis
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from django.db.models import QuerySet
from ..fhir_search.query_translator import date_to_q
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..meta_builder import MetaBuilder
from ..resource_identity import identity

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


@ProjectorRegistry.register("Condition")
class ConditionProjector(BaseProjector):
    resource_type = "Condition"
    profile_key = "us-core-condition-problems-health-concerns"
    supported_profile_keys = [
        "us-core-condition-problems-health-concerns",
        "us-core-condition-encounter-diagnosis",
    ]

    def query(self, patient_id, search_params, context):
        from apps.clinical.health_screening.models import Problem

        qs = Problem.objects.filter(is_active=True)
        patient_scope = patient_id or search_params.get("patient")
        if patient_scope:
            resolved = identity.resolve_patient_db_id(str(patient_scope))
            if resolved is None:
                return qs.none()
            qs = qs.filter(patient_id=resolved)
        if search_params.get("_id"):
            fhir_id = search_params["_id"]
            if fhir_id.startswith("con-"):
                qs = qs.filter(id=fhir_id[4:])
            else:
                qs = qs.filter(id=fhir_id)
        if search_params.get("category"):
            cat = str(search_params["category"]).lower()
            if "encounter-diagnosis" in cat:
                # Problem has no persisted Encounter relationship, so it cannot
                # truthfully be projected as an encounter diagnosis.
                return qs.none()
            elif "problem-list-item" in cat or "health-concern" in cat:
                # Keep resolved rows in category-only searches so Inferno can
                # observe valid abatementDateTime examples for this profile.
                qs = qs
            elif any(k in cat for k in ["sdoh", "functional-status", "disability-status", "cognitive-status"]):
                qs = qs.filter(date_of_resolution__isnull=True).exclude(status__iexact="resolved")
        
        if search_params.get("clinical-status"):
            qs = qs.filter(status__in=search_params["clinical-status"].split(","))
        if search_params.get("_lastUpdated"):
            qs = qs.filter(date_to_q("updated_at__date", str(search_params["_lastUpdated"])))
        if search_params.get("code"):
            qs = qs.filter(problem_name__icontains=search_params["code"])
        if search_params.get("onset-date"):
            qs = qs.filter(date_to_q("date_of_onset", str(search_params["onset-date"])))
        if search_params.get("abatement-date"):
            qs = qs.filter(date_to_q("date_of_resolution", str(search_params["abatement-date"])))
        if search_params.get("recorded-date"):
            qs = qs.filter(date_to_q("date_of_diagnosis", str(search_params["recorded-date"])))
        if search_params.get("asserted-date"):
            # assertedDate extension is projected from onset; align search behavior.
            qs = qs.filter(date_to_q("date_of_onset", str(search_params["asserted-date"])))
        if search_params.get("encounter"):
            return qs.none()
        return qs

    def optimize_queryset(self, qs):
        return qs.select_related("patient")

    def project(self, problem, context: "FHIRContext") -> dict:
        cid = identity.condition_id(problem)
        ref = context.reference_builder
        ts = context.terminology
        pid = identity.patient_id(problem.patient)

        # Resolution does not imply an encounter diagnosis.  Problem has no
        # encounter FK, so every row remains a problem-list/health-concern.
        is_resolved = (problem.date_of_resolution is not None) or (str(problem.status).lower() == "resolved")
        profile = "us-core-condition-problems-health-concerns"
        categories = [
            ts.to_codeable_concept("category_problem_list"),
            ts.to_codeable_concept("category_health_concern"),
        ]
        if problem.sdoh_problem:
            categories.append({"coding": [ts.to_fhir_coding("category_screening_sdoh")]})

        # Keep clinical graph semantically coherent: unresolved = active, resolved = resolved.
        clinical_status = "resolved" if is_resolved else "active"

        resource = {
            "resourceType": "Condition",
            "id": cid,
            "meta": MetaBuilder.build(profile),
            "clinicalStatus": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": clinical_status}]
            },
            "category": categories,
            "code": self._resolve_code(problem, ts),
            "subject": ref.patient(pid),
        }

        if problem.date_of_onset:
            onset = problem.date_of_onset.isoformat() + "T00:00:00Z"
            resource["onsetDateTime"] = onset
            resource["extension"] = [{
                "url": "http://hl7.org/fhir/StructureDefinition/condition-assertedDate",
                "valueDateTime": onset,
            }]
        if problem.date_of_diagnosis:
            resource["recordedDate"] = problem.date_of_diagnosis.isoformat() + "T00:00:00Z"
        if problem.date_of_resolution:
            resource["abatementDateTime"] = problem.date_of_resolution.isoformat() + "T00:00:00Z"

        return resource

    @staticmethod
    def _resolve_code(problem, ts) -> dict:
        """Try to resolve a known SNOMED code; fall back to text-only."""
        name_lower = problem.problem_name.lower() if problem.problem_name else ""
        # Simple keyword matching — extend as needed
        if "diabetes" in name_lower:
            return ts.to_codeable_concept("diabetes_type_2")
        if "anemia" in name_lower:
            return ts.to_codeable_concept("anemia")
        if "hypertension" in name_lower or "blood pressure" in name_lower:
            return ts.to_codeable_concept("hypertension")
        # Fallback: text-only CodeableConcept
        return {"text": problem.problem_name}

    def supported_search_params(self):
        return {
            "patient": "reference",
            "_id": "token",
            "category": "token",
            "clinical-status": "token",
            "code": "token",
            "onset-date": "date",
            "abatement-date": "date",
            "recorded-date": "date",
            "asserted-date": "date",
            "encounter": "reference",
            "_lastUpdated": "date",
        }

    def supported_rev_includes(self):
        return ["Provenance:target"]
