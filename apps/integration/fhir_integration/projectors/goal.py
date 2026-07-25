"""Project persisted patient goals and preferences."""
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

        qs = AdvanceDirective.objects.filter(is_active=True).select_related("patient")
        if search_params.get("_id"):
            raw_id = str(search_params["_id"]).rstrip("/").split("/")[-1]
            if not raw_id.startswith("goal-"):
                return qs.none()
            qs = qs.filter(id=raw_id[5:])
        patient_scope = patient_id or search_params.get("patient")
        if patient_scope:
            resolved = identity.resolve_patient_db_id(str(patient_scope))
            if resolved is None:
                return qs.none()
            qs = qs.filter(patient_id=resolved)
        if search_params.get("lifecycle-status"):
            requested = {value.strip().casefold() for value in str(search_params["lifecycle-status"]).split(",") if value.strip()}
            if requested and "active" not in requested:
                return qs.none()
        return qs

    def project(self, directive, context: "FHIRContext") -> dict | None:
        description = next(
            (
                str(value).strip()
                for value in (
                    directive.patient_goals,
                    directive.sdoh_goals,
                    directive.treatment_intervention_preference,
                )
                if value and str(value).strip()
            ),
            None,
        )
        if description is None:
            return None
        return {
            "resourceType": "Goal",
            "id": identity.goal_id(directive),
            "meta": MetaBuilder.build(self.profile_key),
            "lifecycleStatus": "active",
            "description": {"text": description},
            "subject": context.reference_builder.patient(identity.patient_id(directive.patient)),
            "startDate": directive.created_at.date().isoformat(),
        }

    def supported_search_params(self):
        return {"patient": "reference", "_id": "token", "lifecycle-status": "token"}
