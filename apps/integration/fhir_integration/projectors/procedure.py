"""Project persisted clinical procedures without inferred relationships."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..fhir_search.query_translator import date_to_q
from ..meta_builder import MetaBuilder
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..resource_identity import identity

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


@ProjectorRegistry.register("Procedure")
class ProcedureProjector(BaseProjector):
    resource_type = "Procedure"
    profile_key = "us-core-procedure"

    def query(self, patient_id, search_params, context):
        from apps.clinical.health_screening.models import Procedure

        qs = Procedure.objects.filter(is_active=True).select_related("patient")
        if search_params.get("_id"):
            raw_id = str(search_params["_id"]).rstrip("/").split("/")[-1]
            if not raw_id.startswith("proc-"):
                return qs.none()
            qs = qs.filter(id=raw_id[5:])
        patient_scope = patient_id or search_params.get("patient")
        if patient_scope:
            resolved = identity.resolve_patient_db_id(str(patient_scope))
            if resolved is None:
                return qs.none()
            qs = qs.filter(patient_id=resolved)
        if search_params.get("date"):
            qs = qs.filter(date_to_q("performance_time__date", str(search_params["date"])))
        if search_params.get("code"):
            qs = qs.filter(procedure_name__icontains=str(search_params["code"]).split("|")[-1])
        if search_params.get("status"):
            requested = {value.strip().casefold() for value in str(search_params["status"]).split(",") if value.strip()}
            if requested and "completed" not in requested:
                return qs.none()
        return qs

    def project(self, procedure, context: "FHIRContext") -> dict | None:
        if not _usable_text(procedure.procedure_name) or not procedure.performance_time:
            return None
        resource = {
            "resourceType": "Procedure",
            "id": identity.procedure_id(procedure),
            "meta": MetaBuilder.build(self.profile_key),
            "status": "completed",
            "code": {"text": procedure.procedure_name.strip()},
            "subject": context.reference_builder.patient(identity.patient_id(procedure.patient)),
            "performedDateTime": procedure.performance_time.isoformat(),
        }
        if _usable_text(procedure.reason_for_referral):
            resource["reasonCode"] = [{"text": procedure.reason_for_referral.strip()}]
        return resource

    def supported_search_params(self):
        return {"patient": "reference", "date": "date", "code": "token", "status": "token", "_id": "token"}


def _usable_text(value) -> bool:
    return bool(value and str(value).strip() and str(value).strip().casefold() != "unknown")
