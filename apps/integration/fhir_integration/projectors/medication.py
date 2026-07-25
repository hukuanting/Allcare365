"""Project medication master text from persisted patient medication rows."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..meta_builder import MetaBuilder
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..resource_identity import identity

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


@ProjectorRegistry.register("Medication")
class MedicationProjector(BaseProjector):
    resource_type = "Medication"
    profile_key = "us-core-medication"

    def query(self, patient_id, search_params, context):
        from apps.clinical.patients.models import PatientMedication

        qs = PatientMedication.objects.filter(is_active=True)
        if search_params.get("_id"):
            raw_id = str(search_params["_id"]).rstrip("/").split("/")[-1]
            if not raw_id.startswith("med-"):
                return qs.none()
            qs = qs.filter(id=raw_id[4:])
        patient_scope = patient_id or search_params.get("patient")
        if patient_scope:
            resolved = identity.resolve_patient_db_id(str(patient_scope))
            if resolved is None:
                return qs.none()
            qs = qs.filter(patient_id=resolved)
        return qs

    def project(self, medication, context: "FHIRContext") -> dict | None:
        name = (medication.medication or "").strip()
        if not name or name.casefold() == "unknown":
            return None
        return {
            "resourceType": "Medication",
            "id": identity.medication_id(medication),
            "meta": MetaBuilder.build(self.profile_key),
            "code": {"text": name},
        }

    def supported_search_params(self):
        return {"_id": "token", "patient": "reference"}
