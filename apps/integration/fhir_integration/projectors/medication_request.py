"""Project persisted PatientMedication rows as minimal MedicationRequest."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..fhir_search.query_translator import date_to_q
from ..meta_builder import MetaBuilder
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..resource_identity import identity

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


STATUS_MAP = {"active": "active", "completed": "completed", "stopped": "stopped"}


@ProjectorRegistry.register("MedicationRequest")
class MedicationRequestProjector(BaseProjector):
    resource_type = "MedicationRequest"
    profile_key = "us-core-medicationrequest"

    def query(self, patient_id, search_params, context):
        from apps.clinical.patients.models import PatientMedication

        qs = PatientMedication.objects.filter(is_active=True).select_related("patient")
        if search_params.get("_id"):
            raw_id = str(search_params["_id"]).rstrip("/").split("/")[-1]
            if not raw_id.startswith("mreq-"):
                return qs.none()
            qs = qs.filter(id=raw_id[5:])
        patient_scope = patient_id or search_params.get("patient")
        if patient_scope:
            resolved = identity.resolve_patient_db_id(str(patient_scope))
            if resolved is None:
                return qs.none()
            qs = qs.filter(patient_id=resolved)
        if search_params.get("intent"):
            requested = {value.strip().casefold() for value in str(search_params["intent"]).split(",") if value.strip()}
            if requested and "order" not in requested:
                return qs.none()
        if search_params.get("encounter"):
            return qs.none()
        if search_params.get("authoredon"):
            qs = qs.filter(date_to_q("created_at__date", str(search_params["authoredon"])))
        if search_params.get("status"):
            source_statuses = [
                source
                for source, fhir_status in STATUS_MAP.items()
                if fhir_status in {value.strip().casefold() for value in str(search_params["status"]).split(",")}
            ]
            qs = qs.filter(dispense_status__in=source_statuses)
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
            "resourceType": "MedicationRequest",
            "id": identity.medication_request_id(medication),
            "meta": MetaBuilder.build(self.profile_key),
            "status": status,
            "intent": "order",
            "medicationReference": ref.medication(medication_id),
            "subject": ref.patient(identity.patient_id(medication.patient)),
            "authoredOn": medication.created_at.isoformat(),
        }

        dosage = {}
        if _usable_text(medication.medication_instructions):
            dosage["text"] = medication.medication_instructions.strip()
        if _usable_text(medication.route_of_administration):
            dosage["route"] = {"text": medication.route_of_administration.strip()}
        if dosage:
            resource["dosageInstruction"] = [dosage]
        if _usable_text(medication.indication):
            resource["reasonCode"] = [{"text": medication.indication.strip()}]
        return resource

    def supported_search_params(self):
        return {"patient": "reference", "intent": "token", "encounter": "reference", "authoredon": "date", "status": "token", "_id": "token"}

    def supported_includes(self):
        return ["MedicationRequest:medication"]

    def supported_rev_includes(self):
        return ["Provenance:target"]


def _usable_text(value) -> bool:
    return bool(value and str(value).strip() and str(value).strip().casefold() != "unknown")
