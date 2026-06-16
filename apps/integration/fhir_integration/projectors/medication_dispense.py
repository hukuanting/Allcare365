"""
MedicationDispense Projector — Maps ``patients.PatientMedication`` → FHIR MedicationDispense.

Uses the same PatientMedication model but filters by dispense_status == 'completed'.
"""
from __future__ import annotations
from typing import Any, Dict, TYPE_CHECKING
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..meta_builder import MetaBuilder
from ..resource_identity import identity
from ..uscore_templates import ORGANIZATION_ID, encounter_ref_for_patient

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


@ProjectorRegistry.register("MedicationDispense")
class MedicationDispenseProjector(BaseProjector):
    resource_type = "MedicationDispense"
    profile_key = "us-core-medicationdispense"

    def query(self, patient_id, search_params, context):
        from apps.clinical.patients.models import PatientMedication
        qs = PatientMedication.objects.filter(is_active=True)
        if search_params.get("_id"):
            raw_id = str(search_params["_id"])
            if raw_id.startswith("mdisp-"):
                raw_id = raw_id[6:]
            qs = qs.filter(id=raw_id)
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        if search_params.get("patient"):
            qs = qs.filter(patient_id=search_params["patient"])
        if search_params.get("status"):
            qs = qs.filter(dispense_status__in=search_params["status"].split(","))
        if search_params.get("type"):
            token = str(search_params["type"]).split("|")[-1].upper()
            if token != "FFP":
                return qs.none()
        return qs

    def optimize_queryset(self, qs):
        return qs.select_related("patient")

    def project(self, med, context: "FHIRContext") -> dict:
        did = identity.medication_dispense_id(med)
        mid = identity.medication_id(med)
        mrid = identity.medication_request_id(med)
        ref = context.reference_builder
        ts = context.terminology
        pid = identity.patient_id(med.patient)
        status_map = {
            "active": "in-progress",
            "completed": "completed",
            "stopped": "stopped",
        }
        fhir_status = status_map.get((med.dispense_status or "").lower(), "completed")

        context.include_tracker.add("Medication", mid)
        encounter_ref = encounter_ref_for_patient(str(med.patient_id), ref, identity)

        return {
            "resourceType": "MedicationDispense",
            "id": did,
            "meta": MetaBuilder.build(self.profile_key),
            "status": fhir_status,
            "medicationReference": ref.medication(mid),
            "subject": ref.patient(pid),
            "context": encounter_ref,
            "performer": [
                {"actor": ref.organization(ORGANIZATION_ID)},
            ],
            "authorizingPrescription": [ref.medication_request(mrid)],
            "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "FFP"}]},
            "whenHandedOver": med.end_date.isoformat() if med.end_date else med.created_at.isoformat(),
            "quantity": {"value": 30, "unit": "tab"},
            "dosageInstruction": [{
                "text": med.medication_instructions or f"Take {med.medication} as directed",
                "timing": {"repeat": {"frequency": 1, "period": 1, "periodUnit": "d"}},
                "doseAndRate": [{"doseQuantity": {
                    "value": 1, "unit": "tablet",
                    "system": ts.resolve("unit_tablet").system,
                    "code": ts.resolve("unit_tablet").code,
                }}],
            }],
        }

    def supported_search_params(self):
        return {"patient": "reference", "status": "token", "type": "token", "_id": "token"}

    def supported_includes(self):
        return ["MedicationDispense:medication"]

    def supported_rev_includes(self):
        return ["Provenance:target"]
