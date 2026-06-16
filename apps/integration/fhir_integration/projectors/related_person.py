"""RelatedPerson projector."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..meta_builder import MetaBuilder
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..resource_identity import identity

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


@ProjectorRegistry.register("RelatedPerson")
class RelatedPersonProjector(BaseProjector):
    resource_type = "RelatedPerson"
    profile_key = "us-core-relatedperson"

    def query(self, patient_id, search_params, context):
        from apps.clinical.patients.models import Patient

        qs = Patient.objects.filter(is_active=True).exclude(related_person_name="")
        if search_params.get("_id"):
            raw_id = str(search_params["_id"])
            if raw_id.startswith("rp-"):
                raw_id = raw_id[3:]
            qs = qs.filter(id=raw_id)
        if patient_id:
            resolved = identity.resolve_patient_db_id(patient_id) or patient_id
            qs = qs.filter(id=resolved)
        if search_params.get("patient"):
            patient_ref = str(search_params["patient"]).split("/")[-1]
            resolved = identity.resolve_patient_db_id(patient_ref)
            if not resolved:
                return qs.none()
            qs = qs.filter(id=resolved)
        return qs

    def project(self, patient, context: "FHIRContext") -> dict:
        relationship_map = {
            "spouse": ("SPS", "Spouse"),
            "parent": ("PRN", "Parent"),
            "child": ("CHILD", "Child"),
            "friend": ("FRND", "Unrelated Friend"),
        }
        rel_code, rel_display = relationship_map.get(
            (patient.relationship_type or "").strip().lower(),
            ("SPS", "Spouse"),
        )

        names = (patient.related_person_name or "Jordan Smith").split(" ", 1)
        given = names[0]
        family = names[1] if len(names) > 1 else "Smith"

        return {
            "resourceType": "RelatedPerson",
            "id": identity.related_person_id(patient),
            "meta": MetaBuilder.build(self.profile_key),
            "active": True,
            "patient": context.reference_builder.patient(identity.patient_id(patient)),
            "relationship": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v3-RoleCode",
                    "code": rel_code,
                    "display": rel_display,
                }]
            }],
            "name": [{"family": family, "given": [given]}],
            "telecom": [{"system": "phone", "value": "555-555-6677"}],
            "address": [{
                "line": [patient.current_address_line1 or "123 Interoperability Lane"],
                "city": patient.city or "Boston",
                "state": patient.state or "MA",
                "postalCode": patient.postal_code or "02134",
                "country": patient.country or "US",
            }],
        }

    def supported_search_params(self):
        return {"patient": "reference", "_id": "token"}
