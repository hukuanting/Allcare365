"""Goal projector for patient goals and preferences."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..meta_builder import MetaBuilder
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..resource_identity import identity

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


@ProjectorRegistry.register("Goal")
class GoalProjector(BaseProjector):
    resource_type = "Goal"
    profile_key = "us-core-goal"

    def query(self, patient_id, search_params, context):
        from apps.clinical.patients.models import AdvanceDirective

        qs = AdvanceDirective.objects.filter(is_active=True)
        if search_params.get("_id"):
            raw_id = str(search_params["_id"])
            if raw_id.startswith("goal-"):
                raw_id = raw_id[5:]
            qs = qs.filter(id=raw_id)
        if patient_id:
            resolved = identity.resolve_patient_db_id(patient_id) or patient_id
            qs = qs.filter(patient_id=resolved)
        if search_params.get("patient"):
            patient_ref = str(search_params["patient"]).split("/")[-1]
            resolved = identity.resolve_patient_db_id(patient_ref)
            if not resolved:
                return qs.none()
            qs = qs.filter(patient_id=resolved)
        if search_params.get("lifecycle-status"):
            requested = {s.strip().lower() for s in str(search_params["lifecycle-status"]).split(",") if s.strip()}
            if requested and "active" not in requested:
                return qs.none()
        return qs

    def optimize_queryset(self, qs):
        return qs.select_related("patient")

    def project(self, directive, context: "FHIRContext") -> dict:
        return {
            "resourceType": "Goal",
            "id": identity.goal_id(directive),
            "meta": MetaBuilder.build(self.profile_key),
            "lifecycleStatus": "active",
            "description": {
                "text": directive.patient_goals
                or directive.sdoh_goals
                or directive.treatment_intervention_preference
                or "Maintain health"
            },
            "subject": context.reference_builder.patient(identity.patient_id(directive.patient)),
            "startDate": directive.created_at.date().isoformat(),
            "target": [{"dueDate": "2026-12-31"}],
        }

    def supported_search_params(self):
        return {"patient": "reference", "_id": "token", "lifecycle-status": "token"}
