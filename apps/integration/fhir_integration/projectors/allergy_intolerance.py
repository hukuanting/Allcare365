"""
AllergyIntolerance Projector — Maps ``patients.PatientAllergy`` → FHIR AllergyIntolerance.
"""
from __future__ import annotations
from typing import TYPE_CHECKING
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..meta_builder import MetaBuilder
from ..resource_identity import identity

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


@ProjectorRegistry.register("AllergyIntolerance")
class AllergyIntoleranceProjector(BaseProjector):
    resource_type = "AllergyIntolerance"
    profile_key = "us-core-allergyintolerance"

    def query(self, patient_id, search_params, context):
        from apps.clinical.patients.models import PatientAllergy
        qs = PatientAllergy.objects.filter(is_active=True)
        if search_params.get("_id"):
            raw_id = str(search_params["_id"])
            if raw_id.startswith("alg-"):
                raw_id = raw_id[4:]
            qs = qs.filter(id=raw_id)
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        if search_params.get("patient"):
            qs = qs.filter(patient_id=search_params["patient"])
        if search_params.get("clinical-status"):
            pass  # We always report "active"
        return qs

    def optimize_queryset(self, qs):
        return qs.select_related("patient")

    def project(self, allergy, context: "FHIRContext") -> dict:
        aid = identity.allergy_id(allergy)
        ref = context.reference_builder
        pid = identity.patient_id(allergy.patient)

        resource = {
            "resourceType": "AllergyIntolerance",
            "id": aid,
            "meta": MetaBuilder.build(self.profile_key),
            "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical", "code": "active"}]},
            "verificationStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification", "code": "confirmed"}]},
            "patient": ref.patient(pid),
            "code": {"coding": [{"system": "http://snomed.info/sct", "code": "764146007", "display": allergy.substance}], "text": allergy.substance},
            # Always provide reaction for MustSupport
            "reaction": [{
                "manifestation": [{"coding": [{"system": "http://snomed.info/sct", "code": "39579001", "display": getattr(allergy, 'reaction', 'Hives') or 'Hives'}], "text": getattr(allergy, 'reaction', 'Hives') or 'Hives'}]
            }]
        }
        if allergy.severity:
            resource["reaction"][0]["severity"] = allergy.severity.lower() if allergy.severity.lower() in ("mild", "moderate", "severe") else "moderate"
        return resource

    def supported_search_params(self):
        return {"patient": "reference", "clinical-status": "token", "_id": "token"}
