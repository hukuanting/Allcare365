"""Project persisted patient-practitioner links as FHIR CareTeam."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..meta_builder import MetaBuilder
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..resource_identity import identity

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


@ProjectorRegistry.register("CareTeam")
class CareTeamProjector(BaseProjector):
    resource_type = "CareTeam"
    profile_key = "us-core-careteam"

    def query(self, patient_id, search_params, context):
        from apps.clinical.patients.models import Patient

        qs = Patient.objects.filter(
            is_active=True,
            practitioner_links__is_active=True,
            practitioner_links__status__iexact="active",
            practitioner_links__practitioner__is_active=True,
            practitioner_links__practitioner__status__iexact="active",
        ).distinct()

        patient_scope = patient_id or search_params.get("patient")
        if patient_scope:
            resolved = identity.resolve_patient_db_id(str(patient_scope))
            if resolved is None:
                return qs.none()
            qs = qs.filter(id=resolved)
        if search_params.get("_id"):
            raw_id = str(search_params["_id"]).rstrip("/").split("/")[-1]
            if not raw_id.startswith("ct-"):
                return qs.none()
            qs = qs.filter(id=raw_id[3:])
        if search_params.get("status"):
            requested = {value.strip().casefold() for value in str(search_params["status"]).split(",") if value.strip()}
            if requested and "active" not in requested:
                return qs.none()
        return qs

    def optimize_queryset(self, qs):
        return qs.prefetch_related("practitioner_links__practitioner")

    def project(self, patient, context: "FHIRContext") -> dict | None:
        ref = context.reference_builder
        participants = []
        links = patient.practitioner_links.filter(
            is_active=True,
            status__iexact="active",
            practitioner__is_active=True,
            practitioner__status__iexact="active",
        ).select_related("practitioner").order_by("start_at", "id")
        for link in links:
            practitioner = link.practitioner
            if not _usable_text(practitioner.first_name) and not _usable_text(practitioner.last_name):
                continue
            participant = {
                "member": ref.practitioner_role(identity.practitioner_role_id(link)),
            }
            role = (link.role or link.link_type or "").strip()
            if _usable_text(role):
                participant["role"] = [{"text": role}]
            participants.append(participant)

        if not participants:
            return None
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


def _usable_text(value) -> bool:
    return bool(value and str(value).strip() and str(value).strip().casefold() != "unknown")
