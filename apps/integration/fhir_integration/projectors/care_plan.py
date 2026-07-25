"""Project persisted care-plan content without placeholder narrative."""
from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.html import escape

from ..meta_builder import MetaBuilder
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..resource_identity import identity

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


FHIR_CAREPLAN_STATUSES = {"draft", "active", "on-hold", "revoked", "completed", "entered-in-error", "unknown"}
FHIR_CAREPLAN_INTENTS = {"proposal", "plan", "order", "option"}


@ProjectorRegistry.register("CarePlan")
class CarePlanProjector(BaseProjector):
    resource_type = "CarePlan"
    profile_key = "us-core-careplan"

    def query(self, patient_id, search_params, context):
        from apps.clinical.patients.models import CarePlan

        qs = CarePlan.objects.filter(is_active=True).select_related("patient")
        if search_params.get("_id"):
            raw_id = str(search_params["_id"]).rstrip("/").split("/")[-1]
            if not raw_id.startswith("cp-"):
                return qs.none()
            qs = qs.filter(id=raw_id[3:])
        patient_scope = patient_id or search_params.get("patient")
        if patient_scope:
            resolved = identity.resolve_patient_db_id(str(patient_scope))
            if resolved is None:
                return qs.none()
            qs = qs.filter(patient_id=resolved)
        if search_params.get("category"):
            requested = {value.strip().split("|")[-1].casefold() for value in str(search_params["category"]).split(",") if value.strip()}
            qs = qs.filter(category__in=requested)
        if search_params.get("status"):
            qs = qs.filter(status__in=str(search_params["status"]).split(","))
        return qs

    def project(self, plan, context: "FHIRContext") -> dict | None:
        narrative = (plan.care_plan or plan.assessment_and_plan or "").strip()
        status = (plan.status or "").strip().casefold()
        intent = (plan.intent or "").strip().casefold()
        if not narrative or status not in FHIR_CAREPLAN_STATUSES or intent not in FHIR_CAREPLAN_INTENTS:
            return None

        resource = {
            "resourceType": "CarePlan",
            "id": identity.care_plan_id(plan),
            "meta": MetaBuilder.build(self.profile_key),
            "status": status,
            "intent": intent,
            "subject": context.reference_builder.patient(identity.patient_id(plan.patient)),
            "text": {
                "status": "additional",
                "div": f"<div xmlns='http://www.w3.org/1999/xhtml'>{escape(narrative)}</div>",
            },
        }
        if (plan.title or "").strip():
            resource["title"] = plan.title.strip()
        if (plan.category or "").strip():
            category = plan.category.strip()
            if category == "assess-plan":
                resource["category"] = [{"coding": [{
                    "system": "http://hl7.org/fhir/us/core/CodeSystem/careplan-category",
                    "code": category,
                }]}]
            else:
                resource["category"] = [{"text": category}]
        period = {}
        if plan.period_start:
            period["start"] = plan.period_start.isoformat()
        if plan.period_end:
            period["end"] = plan.period_end.isoformat()
        if period:
            resource["period"] = period
        return resource

    def supported_search_params(self):
        return {"patient": "reference", "category": "token", "status": "token", "_id": "token"}
