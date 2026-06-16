"""Medication Projector — Generates FHIR Medication from ``patients.PatientMedication``."""
from __future__ import annotations
from typing import TYPE_CHECKING
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..meta_builder import MetaBuilder
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
            raw_id = str(search_params["_id"])
            if raw_id.startswith("med-"):
                raw_id = raw_id[4:]
            qs = qs.filter(id=raw_id)
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        if search_params.get("patient"):
            qs = qs.filter(patient_id=search_params["patient"])
        return qs

    def optimize_queryset(self, qs):
        return qs.select_related("patient")

    def project(self, med, context: "FHIRContext") -> dict:
        mid = identity.medication_id(med)
        return {
            "resourceType": "Medication",
            "id": mid,
            "meta": MetaBuilder.build(self.profile_key),
            "code": {
                "coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "582620", "display": med.medication}],
                "text": med.medication,
            },
        }

    def supported_search_params(self):
        return {"_id": "token", "patient": "reference"}
