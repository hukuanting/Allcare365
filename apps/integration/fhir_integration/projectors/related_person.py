"""Project only persisted related-person demographics."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..meta_builder import MetaBuilder
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..resource_identity import identity

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


RELATIONSHIP_CODES = {
    "spouse": ("SPS", "Spouse"),
    "parent": ("PRN", "Parent"),
    "child": ("CHILD", "Child"),
    "friend": ("FRND", "Unrelated Friend"),
}


@ProjectorRegistry.register("RelatedPerson")
class RelatedPersonProjector(BaseProjector):
    resource_type = "RelatedPerson"
    profile_key = "us-core-relatedperson"

    def query(self, patient_id, search_params, context):
        from apps.clinical.patients.models import Patient

        qs = Patient.objects.filter(is_active=True).exclude(related_person_name="").exclude(related_person_name__iexact="unknown")
        if search_params.get("_id"):
            raw_id = str(search_params["_id"]).rstrip("/").split("/")[-1]
            if not raw_id.startswith("rp-"):
                return qs.none()
            qs = qs.filter(id=raw_id[3:])
        patient_scope = patient_id or search_params.get("patient")
        if patient_scope:
            resolved = identity.resolve_patient_db_id(str(patient_scope))
            if resolved is None:
                return qs.none()
            qs = qs.filter(id=resolved)
        return qs

    def project(self, patient, context: "FHIRContext") -> dict | None:
        name = (patient.related_person_name or "").strip()
        if not name or name.casefold() == "unknown":
            return None
        resource = {
            "resourceType": "RelatedPerson",
            "id": identity.related_person_id(patient),
            "meta": MetaBuilder.build(self.profile_key),
            "active": bool(patient.is_active),
            "patient": context.reference_builder.patient(identity.patient_id(patient)),
            "name": [{"text": name}],
        }
        relationship = (patient.relationship_type or "").strip()
        if relationship:
            code = RELATIONSHIP_CODES.get(relationship.casefold())
            concept = {"text": relationship}
            if code is not None:
                concept["coding"] = [{
                    "system": "http://terminology.hl7.org/CodeSystem/v3-RoleCode",
                    "code": code[0],
                    "display": code[1],
                }]
            resource["relationship"] = [concept]
        return resource

    def supported_search_params(self):
        return {"patient": "reference", "_id": "token"}
