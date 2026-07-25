"""Project persisted medication dispense state without guessed fulfillment data."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..meta_builder import MetaBuilder
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..resource_identity import identity

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


STATUS_MAP = {"active": "in-progress", "completed": "completed", "stopped": "stopped"}


@ProjectorRegistry.register("MedicationDispense")
class MedicationDispenseProjector(BaseProjector):
    resource_type = "MedicationDispense"
    profile_key = "us-core-medicationdispense"

    def query(self, patient_id, search_params, context):
        from apps.clinical.patients.models import PatientMedication

        qs = PatientMedication.objects.filter(is_active=True).select_related("patient")
        if search_params.get("_id"):
            raw_id = str(search_params["_id"]).rstrip("/").split("/")[-1]
            if not raw_id.startswith("mdisp-"):
                return qs.none()
            qs = qs.filter(id=raw_id[6:])
        patient_scope = patient_id or search_params.get("patient")
        if patient_scope:
            resolved = identity.resolve_patient_db_id(str(patient_scope))
            if resolved is None:
                return qs.none()
            qs = qs.filter(patient_id=resolved)
        if search_params.get("status"):
            requested = {value.strip().casefold() for value in str(search_params["status"]).split(",") if value.strip()}
            source_statuses = [source for source, target in STATUS_MAP.items() if target in requested]
            qs = qs.filter(dispense_status__in=source_statuses)
        if search_params.get("type"):
            return qs.none()
        return qs

    def project(self, medication, context: "FHIRContext") -> dict | None:
        name = (medication.medication or "").strip()
        status = STATUS_MAP.get((medication.dispense_status or "").strip().casefold())
        if not name or name.casefold() == "unknown" or status is None:
            return None

        ref = context.reference_builder
        medication_id = identity.medication_id(medication)
        context.include_tracker.add("Medication", medication_id)
        resource = {
            "resourceType": "MedicationDispense",
            "id": identity.medication_dispense_id(medication),
            "meta": MetaBuilder.build(self.profile_key),
            "status": status,
            "medicationReference": ref.medication(medication_id),
            "subject": ref.patient(identity.patient_id(medication.patient)),
        }
        if _usable_text(medication.medication_instructions):
            resource["dosageInstruction"] = [{"text": medication.medication_instructions.strip()}]
        return resource

    def supported_search_params(self):
        return {"patient": "reference", "status": "token", "type": "token", "_id": "token"}

    def supported_includes(self):
        return ["MedicationDispense:medication"]

    def supported_rev_includes(self):
        return ["Provenance:target"]


def _usable_text(value) -> bool:
    return bool(value and str(value).strip() and str(value).strip().casefold() != "unknown")
