"""Project persisted allergy facts without guessed codes or reactions."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..meta_builder import MetaBuilder
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..resource_identity import identity

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


@ProjectorRegistry.register("AllergyIntolerance")
class AllergyIntoleranceProjector(BaseProjector):
    resource_type = "AllergyIntolerance"
    profile_key = "us-core-allergyintolerance"

    def query(self, patient_id, search_params, context):
        from apps.clinical.patients.models import PatientAllergy

        qs = PatientAllergy.objects.filter(is_active=True).select_related("patient")
        if search_params.get("_id"):
            raw_id = str(search_params["_id"]).rstrip("/").split("/")[-1]
            if not raw_id.startswith("alg-"):
                return qs.none()
            qs = qs.filter(id=raw_id[4:])
        patient_scope = patient_id or search_params.get("patient")
        if patient_scope:
            resolved = identity.resolve_patient_db_id(str(patient_scope))
            if resolved is None:
                return qs.none()
            qs = qs.filter(patient_id=resolved)
        if search_params.get("clinical-status"):
            requested = {value.strip().split("|")[-1].casefold() for value in str(search_params["clinical-status"]).split(",") if value.strip()}
            if requested and "active" not in requested:
                return qs.none()
        return qs

    def project(self, allergy, context: "FHIRContext") -> dict | None:
        substance = (allergy.substance or "").strip()
        if not substance or substance.casefold() == "unknown":
            return None
        resource = {
            "resourceType": "AllergyIntolerance",
            "id": identity.allergy_id(allergy),
            "meta": MetaBuilder.build(self.profile_key),
            "clinicalStatus": {"coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                "code": "active",
            }]},
            "patient": context.reference_builder.patient(identity.patient_id(allergy.patient)),
            "code": {"text": substance},
        }
        if (allergy.reaction or "").strip():
            reaction = {"manifestation": [{"text": allergy.reaction.strip()}]}
            severity = (allergy.severity or "").strip().casefold()
            if severity in {"mild", "moderate", "severe"}:
                reaction["severity"] = severity
            resource["reaction"] = [reaction]
        return resource

    def supported_search_params(self):
        return {"patient": "reference", "clinical-status": "token", "_id": "token"}
