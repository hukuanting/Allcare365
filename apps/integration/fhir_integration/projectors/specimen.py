"""Specimen Projector — Maps ``health_screening.LaboratoryResults`` → FHIR Specimen."""
from __future__ import annotations
from typing import TYPE_CHECKING
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..meta_builder import MetaBuilder
from ..resource_identity import identity
if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


@ProjectorRegistry.register("Specimen")
class SpecimenProjector(BaseProjector):
    resource_type = "Specimen"
    profile_key = "us-core-specimen"

    def query(self, patient_id, search_params, context):
        from apps.clinical.health_screening.models import LaboratoryResults
        qs = LaboratoryResults.objects.filter(is_active=True)
        if search_params.get("_id"):
            raw_id = str(search_params["_id"])
            if raw_id.startswith("spm-"):
                raw_id = raw_id[4:]
            qs = qs.filter(id=raw_id)
        if patient_id:
            qs = qs.filter(health_screening__patient_id=patient_id)
        if search_params.get("patient"):
            qs = qs.filter(health_screening__patient_id=search_params["patient"])
        return qs

    def optimize_queryset(self, qs):
        return qs.select_related("health_screening", "health_screening__patient")

    def project(self, lab, context: "FHIRContext") -> dict:
        sid = identity.specimen_id(lab)
        pid = identity.patient_id(lab.health_screening.patient)
        ref = context.reference_builder
        dt = lab.health_screening.screening_date.isoformat() if lab.health_screening.screening_date else "2025-01-01"
        specimen_identifier = lab.specimen_identifier or f"SP-{lab.id}"
        body_site_text = lab.specimen_source_site or "venous blood"
        return {
            "resourceType": "Specimen",
            "id": sid,
            "meta": MetaBuilder.build(self.profile_key),
            "identifier": [{
                "system": "http://allcare365.example/specimen",
                "value": specimen_identifier,
            }],
            "accessionIdentifier": {
                "system": "http://allcare365.example/specimen-accession",
                "value": f"ACC-{specimen_identifier}",
            },
            "status": "available",
            "type": {"coding": [{"system": "http://snomed.info/sct", "code": "119297000", "display": lab.specimen_type or "Blood specimen"}]},
            "subject": ref.patient(pid),
            "collection": {
                "collectedDateTime": dt,
                "bodySite": {
                    "coding": [{"system": "http://snomed.info/sct", "code": "49852007", "display": "Structure of vein"}],
                    "text": body_site_text,
                },
            },
            "condition": [{
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0493", "code": "A", "display": "Accepted"}],
                "text": lab.specimen_condition or "acceptable",
            }],
        }

    def supported_search_params(self):
        return {"patient": "reference", "_id": "token"}
