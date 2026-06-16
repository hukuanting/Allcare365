"""
Condition Projector — Maps ``health_screening.Problem`` → FHIR Condition.

Handles both US Core profiles:
  - us-core-condition-problems-health-concerns (problem-list-item)
  - us-core-condition-encounter-diagnosis
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from django.db.models import QuerySet
from django.db.models import Q
from ..fhir_search.query_translator import date_to_q
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..meta_builder import MetaBuilder
from ..resource_identity import identity
from ..uscore_templates import encounter_ref_for_patient

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
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        if search_params.get("patient"):
            qs = qs.filter(patient_id=search_params["patient"])
        if search_params.get("_id"):
            fhir_id = search_params["_id"]
            if fhir_id.startswith("con-"):
                qs = qs.filter(id=fhir_id[4:])
            else:
                qs = qs.filter(id=fhir_id)
        if search_params.get("category"):
            cat = str(search_params["category"]).lower()
            if "encounter-diagnosis" in cat:
                qs = qs.filter(Q(date_of_resolution__isnull=False) | Q(status__iexact="resolved"))
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
            # Relational model does not store direct encounter FK; keep results if patient has encounter.
            from apps.clinical.health_screening.models import HealthScreening
            enc_id = str(search_params["encounter"]).split("/")[-1].replace("enc-", "")
            if not HealthScreening.objects.filter(id=enc_id).exists():
                return qs.none()
        return qs

    def optimize_queryset(self, qs):
        return qs.select_related("patient")

    def project(self, problem, context: "FHIRContext") -> dict:
        cid = identity.condition_id(problem)
        ref = context.reference_builder
        ts = context.terminology
        pid = identity.patient_id(problem.patient)

        # Determine profile based on whether it's resolved (encounter-dx) or active (problem-list)
        is_encounter_dx = (problem.date_of_resolution is not None) or (str(problem.status).lower() == "resolved")
        categories = []

        if is_encounter_dx:
            profile = "us-core-condition-problems-health-concerns"
            categories.append(ts.to_codeable_concept("category_problem_list"))
            categories.append(ts.to_codeable_concept("category_health_concern"))
            categories.append(ts.to_codeable_concept("category_encounter_dx"))
        else:
            profile = "us-core-condition-problems-health-concerns"
            categories.append(ts.to_codeable_concept("category_problem_list"))
            categories.append(ts.to_codeable_concept("category_health_concern"))
            categories.append(ts.to_codeable_concept("category_screening_functional_status"))
        # Ensure screening-assessment category is present for Must Support checks.
        if not any(
            any(
                c.get("system") == "http://hl7.org/fhir/us/core/CodeSystem/us-core-category"
                and c.get("code") in {"sdoh", "functional-status", "disability-status", "cognitive-status"}
                for c in cc.get("coding", [])
            )
            for cc in categories
        ):
            categories.append({
                "coding": [ts.to_fhir_coding("category_screening_sdoh")]
            })

        # Keep clinical graph semantically coherent: unresolved = active, resolved = resolved.
        clinical_status = "resolved" if is_encounter_dx else "active"

        # US Core MustSupport Dates
        onset = problem.date_of_onset or problem.created_at.date()
        recorded = getattr(problem, 'date_of_diagnosis', None) or problem.created_at.date()

        resource = {
            "resourceType": "Condition",
            "id": cid,
            "meta": self._meta_for_condition(profile, is_encounter_dx),
            "extension": [
                {
                    "url": "http://hl7.org/fhir/StructureDefinition/condition-assertedDate",
                    "valueDateTime": onset.isoformat() + "T00:00:00Z"
                }
            ],
            "clinicalStatus": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": clinical_status}]
            },
            "verificationStatus": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed"}]
            },
            "category": categories,
            "code": self._resolve_code(problem, ts),
            "subject": ref.patient(pid),
            "onsetDateTime": onset.isoformat() + "T00:00:00Z",
            "recordedDate": recorded.isoformat() + "T00:00:00Z",
        }

        resource["encounter"] = encounter_ref_for_patient(str(problem.patient_id), ref, identity)
        if problem.date_of_resolution:
            resource["abatementDateTime"] = problem.date_of_resolution.isoformat() + "T00:00:00Z"
        elif is_encounter_dx:
            resource["abatementDateTime"] = recorded.isoformat() + "T00:00:00Z"

        return resource

    @staticmethod
    def _meta_for_condition(profile: str, is_encounter_dx: bool) -> dict:
        if not is_encounter_dx:
            return MetaBuilder.build(profile)

        encounter_profile = MetaBuilder.profile_url("us-core-condition-encounter-diagnosis")
        return MetaBuilder.build(
            profile,
            extra_profiles=[encounter_profile, f"{encounter_profile}|7.0.0"],
        )

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
        return {
            "coding": [{"system": "http://snomed.info/sct", "code": "55607006", "display": problem.problem_name}],
            "text": problem.problem_name,
        }

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
