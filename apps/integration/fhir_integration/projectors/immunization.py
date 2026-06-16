"""Immunization Projector — Maps ``health_screening.Immunization`` → FHIR Immunization."""
from __future__ import annotations
from typing import TYPE_CHECKING
from ..fhir_search.query_translator import date_to_q
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..meta_builder import MetaBuilder
from ..resource_identity import identity
from ..uscore_templates import LOCATION_ID, PRACTITIONER_ID, encounter_ref_for_patient
if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


@ProjectorRegistry.register("Immunization")
class ImmunizationProjector(BaseProjector):
    resource_type = "Immunization"
    profile_key = "us-core-immunization"

    def query(self, patient_id, search_params, context):
        from apps.clinical.health_screening.models import Immunization
        qs = Immunization.objects.filter(is_active=True)
        if search_params.get("_id"):
            raw_id = str(search_params["_id"])
            if raw_id.startswith("imm-"):
                raw_id = raw_id[4:]
            qs = qs.filter(id=raw_id)
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        if search_params.get("patient"):
            qs = qs.filter(patient_id=search_params["patient"])
        if search_params.get("status"):
            status = str(search_params["status"]).lower()
            if status != "completed":
                return qs.none()
        if search_params.get("date"):
            qs = qs.filter(date_to_q("administration_date__date", str(search_params["date"])))
        return qs

    def optimize_queryset(self, qs):
        return qs.select_related("patient")

    def project(self, imm, context: "FHIRContext") -> dict:
        iid = identity.immunization_id(imm)
        pid = identity.patient_id(imm.patient)
        ref = context.reference_builder
        ts = context.terminology
        encounter_ref = encounter_ref_for_patient(str(imm.patient_id), ref, identity)
        return {
            "resourceType": "Immunization",
            "id": iid,
            "meta": MetaBuilder.build(self.profile_key),
            "status": "completed",
            "statusReason": {"coding": [ts.to_fhir_coding("immunization_status_reason_immune")]},
            "vaccineCode": {"coding": [{"system": "http://hl7.org/fhir/sid/cvx", "code": "207", "display": imm.vaccine_name}], "text": imm.vaccine_name},
            "patient": ref.patient(pid),
            "encounter": encounter_ref,
            "occurrenceDateTime": imm.administration_date.isoformat() if imm.administration_date else imm.created_at.isoformat(),
            "primarySource": True,
            "location": ref.location(LOCATION_ID),
            "performer": [{"actor": ref.practitioner(PRACTITIONER_ID)}],
            "protocolApplied": [{"doseNumberPositiveInt": 1}],
        }

    def supported_search_params(self):
        return {"patient": "reference", "status": "token", "date": "date", "_id": "token"}
