"""CarePlan projector."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..meta_builder import MetaBuilder
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..resource_identity import identity

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


@ProjectorRegistry.register("CarePlan")
class CarePlanProjector(BaseProjector):
    resource_type = "CarePlan"
    profile_key = "us-core-careplan"

    def query(self, patient_id, search_params, context):
        from apps.clinical.patients.models import CarePlan

        qs = CarePlan.objects.filter(is_active=True)
        if search_params.get("_id"):
            raw_id = str(search_params["_id"])
            if raw_id.startswith("cp-"):
                raw_id = raw_id[3:]
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
        if search_params.get("category"):
            requested = {s.strip().split("|")[-1].lower() for s in str(search_params["category"]).split(",") if s.strip()}
            if requested and "assess-plan" not in requested:
                return qs.none()
        if search_params.get("status"):
            qs = qs.filter(status__in=str(search_params["status"]).split(","))
        return qs

    def optimize_queryset(self, qs):
        return qs.select_related("patient")

    def project(self, plan, context: "FHIRContext") -> dict:
        text = plan.care_plan or plan.assessment_and_plan or "Care plan details"
        return {
            "resourceType": "CarePlan",
            "id": identity.care_plan_id(plan),
            "meta": MetaBuilder.build(self.profile_key),
            "status": plan.status or "active",
            "intent": "plan",
            "category": [{
                "coding": [{
                    "system": "http://hl7.org/fhir/us/core/CodeSystem/careplan-category",
                    "code": "assess-plan",
                }]
            }],
            "subject": context.reference_builder.patient(identity.patient_id(plan.patient)),
            "text": {
                "status": "additional",
                "div": f"<div xmlns='http://www.w3.org/1999/xhtml'>{text}</div>",
            },
        }

    def supported_search_params(self):
        return {"patient": "reference", "category": "token", "status": "token", "_id": "token"}
