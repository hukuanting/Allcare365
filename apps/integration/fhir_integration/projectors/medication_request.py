"""
MedicationRequest Projector — Maps ``patients.PatientMedication`` → FHIR MedicationRequest.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from ..fhir_search.query_translator import date_to_q
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..meta_builder import MetaBuilder
from ..resource_identity import identity
from ..uscore_templates import PRACTITIONER_ID, encounter_ref_for_patient

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


@ProjectorRegistry.register("MedicationRequest")
class MedicationRequestProjector(BaseProjector):
    resource_type = "MedicationRequest"
    profile_key = "us-core-medicationrequest"

    def query(self, patient_id, search_params, context):
        from apps.clinical.patients.models import PatientMedication
        qs = PatientMedication.objects.filter(is_active=True)
        if search_params.get("_id"):
            raw_id = str(search_params["_id"])
            if raw_id.startswith("mreq-"):
                raw_id = raw_id[5:]
            qs = qs.filter(id=raw_id)
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        if search_params.get("patient"):
            qs = qs.filter(patient_id=search_params["patient"])
        if search_params.get("intent"):
            requested = {s.strip().lower() for s in str(search_params["intent"]).split(",") if s.strip()}
            if requested and "proposal" not in requested:
                return qs.none()
        if search_params.get("encounter"):
            from apps.clinical.health_screening.models import HealthScreening
            enc_id = str(search_params["encounter"]).split("/")[-1].replace("enc-", "")
            if not HealthScreening.objects.filter(id=enc_id).exists():
                return qs.none()
        if search_params.get("authoredon"):
            qs = qs.filter(date_to_q("start_date", str(search_params["authoredon"])))
        if search_params.get("status"):
            status_map = {"active": "active", "completed": "completed", "stopped": "stopped"}
            qs = qs.filter(dispense_status__in=[status_map.get(s, s) for s in search_params["status"].split(",")])
        return qs

    def optimize_queryset(self, qs):
        return qs.select_related("patient")

    def project(self, med, context: "FHIRContext") -> dict:
        mrid = identity.medication_request_id(med)
        mid = identity.medication_id(med)
        ref = context.reference_builder
        ts = context.terminology
        pid = identity.patient_id(med.patient)

        # Track the referenced Medication for _include
        context.include_tracker.add("Medication", mid)
        encounter_ref = encounter_ref_for_patient(str(med.patient_id), ref, identity)

        resource = {
            "resourceType": "MedicationRequest",
            "id": mrid,
            "meta": MetaBuilder.build(self.profile_key),
            "status": "active" if med.dispense_status == "active" else med.dispense_status,
            "intent": "proposal",
            "category": [
                ts.to_codeable_concept("medreq_outpatient"),
                ts.to_codeable_concept("medreq_discharge"),
            ],
            "reportedBoolean": False,
            "medicationReference": ref.medication(mid),
            "subject": ref.patient(pid),
            "encounter": encounter_ref,
            "authoredOn": med.start_date.isoformat() if med.start_date else med.created_at.isoformat(),
            "requester": ref.practitioner(PRACTITIONER_ID),
            "dosageInstruction": [{
                "text": med.medication_instructions or f"Take {med.medication} as directed",
                "timing": {"repeat": {"frequency": 1, "period": 1, "periodUnit": "d"}},
                "doseAndRate": [{"doseQuantity": {
                    "value": 1, "unit": "tablet",
                    "system": ts.resolve("unit_tablet").system,
                    "code": ts.resolve("unit_tablet").code,
                }}],
            }],
            "dispenseRequest": {
                "numberOfRepeatsAllowed": 3,
                "quantity": {"value": 30, "unit": "tab"},
            },
        }

        if med.indication:
            resource["reasonCode"] = [{"text": med.indication}]

        return resource

    def apply_extensions(self, resource, med, context):
        ts = context.terminology
        asserted_date = med.start_date.isoformat() if med.start_date else med.created_at.date().isoformat()
        resource.setdefault("extension", []).append({
            "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-medication-adherence",
            "extension": [
                {
                    "url": "medicationAdherence",
                    "valueCodeableConcept": ts.to_codeable_concept("treatment_compliant"),
                },
                {
                    "url": "dateAsserted",
                    "valueDateTime": asserted_date + "T00:00:00Z",
                },
            ],
        })
        return resource

    def supported_search_params(self):
        return {"patient": "reference", "intent": "token", "encounter": "reference", "authoredon": "date", "status": "token", "_id": "token"}

    def supported_includes(self):
        return ["MedicationRequest:medication"]

    def supported_rev_includes(self):
        return ["Provenance:target"]
