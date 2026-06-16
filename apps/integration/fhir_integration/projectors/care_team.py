"""CareTeam projector driven from relational care team membership."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..meta_builder import MetaBuilder
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..resource_identity import identity
from ..uscore_templates import PRACTITIONER_ROLE_ID

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


@ProjectorRegistry.register("CareTeam")
class CareTeamProjector(BaseProjector):
    resource_type = "CareTeam"
    profile_key = "us-core-careteam"

    def query(self, patient_id, search_params, context):
        from apps.clinical.patients.models import Patient

        qs = Patient.objects.filter(is_active=True, care_team__is_active=True).distinct()
        if search_params.get("_id"):
            raw_id = str(search_params["_id"])
            if raw_id.startswith("ct-"):
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
        if search_params.get("status"):
            requested = {s.strip().lower() for s in str(search_params["status"]).split(",") if s.strip()}
            if requested and "active" not in requested:
                return qs.none()
        return qs

    def optimize_queryset(self, qs):
        return qs.prefetch_related("care_team")

    def project(self, patient, context: "FHIRContext") -> dict:
        ref = context.reference_builder
        participants = []

        for member in patient.care_team.filter(is_active=True).order_by("created_at", "id"):
            role_lower = (member.role or "").lower()
            if "related person" in role_lower:
                member_ref = ref.related_person(identity.related_person_id(patient))
                member_ref["display"] = member.name or "Jordan Smith"
            else:
                member_ref = ref.practitioner_role(PRACTITIONER_ROLE_ID)
                member_ref["display"] = member.name or "Dr. Adam Careful"

            participants.append(
                {
                    "role": [{
                        "coding": [{
                            "system": "http://snomed.info/sct",
                            "code": "158974003",
                            "display": member.role or "Care team member",
                        }]
                    }],
                    "member": member_ref,
                }
            )

        return {
            "resourceType": "CareTeam",
            "id": identity.care_team_id(patient),
            "meta": MetaBuilder.build(self.profile_key),
            "status": "active",
            "subject": ref.patient(identity.patient_id(patient)),
            "participant": participants,
        }

    def supported_search_params(self):
        return {"patient": "reference", "status": "token", "_id": "token"}
