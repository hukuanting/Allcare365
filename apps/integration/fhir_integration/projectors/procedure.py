"""Procedure Projector — Maps ``health_screening.Procedure`` → FHIR Procedure."""
from __future__ import annotations
from typing import TYPE_CHECKING
from ..fhir_search.query_translator import date_to_q
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..meta_builder import MetaBuilder
from ..resource_identity import identity
from ..uscore_templates import encounter_ref_for_patient
if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


@ProjectorRegistry.register("Procedure")
class ProcedureProjector(BaseProjector):
    resource_type = "Procedure"
    profile_key = "us-core-procedure"

    def query(self, patient_id, search_params, context):
        from apps.clinical.health_screening.models import Procedure
        qs = Procedure.objects.filter(is_active=True)
        if search_params.get("_id"):
            raw_id = str(search_params["_id"])
            if raw_id.startswith("proc-"):
                raw_id = raw_id[5:]
            qs = qs.filter(id=raw_id)
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        if search_params.get("patient"):
            qs = qs.filter(patient_id=search_params["patient"])
        if search_params.get("date"):
            qs = qs.filter(date_to_q("performance_time__date", str(search_params["date"])))
        if search_params.get("code"):
            code = str(search_params["code"]).split("|")[-1]
            if code != "430193006":
                qs = qs.filter(procedure_name__icontains=code)
        if search_params.get("status"):
            requested = {s.strip().lower() for s in str(search_params["status"]).split(",") if s.strip()}
            if requested and "completed" not in requested:
                return qs.none()
        return qs

    def optimize_queryset(self, qs):
        return qs.select_related("patient")

    def project(self, proc, context: "FHIRContext") -> dict:
        prid = identity.procedure_id(proc)
        pid = identity.patient_id(proc.patient)
        ref = context.reference_builder
        encounter_ref = encounter_ref_for_patient(str(proc.patient_id), ref, identity)
        service_request_ref = self._service_request_ref(proc, ref)
        condition_ref = self._reason_condition_ref(proc, ref)
        resource = {
            "resourceType": "Procedure",
            "id": prid,
            "meta": MetaBuilder.build(self.profile_key),
            "status": "completed",
            "code": {"coding": [{"system": "http://snomed.info/sct", "code": "430193006", "display": proc.procedure_name}], "text": proc.procedure_name},
            "subject": ref.patient(pid),
            "encounter": encounter_ref,
            "performedDateTime": proc.performance_time.isoformat() if proc.performance_time else proc.created_at.isoformat(),
            "basedOn": [service_request_ref],
            "reasonCode": [{
                "coding": [{"system": "http://snomed.info/sct", "code": "386053000", "display": "Evaluation procedure"}],
                "text": proc.reason_for_referral or "Procedure clinically indicated",
            }],
        }
        if condition_ref:
            resource["reasonReference"] = [condition_ref]
        return resource

    @staticmethod
    def _service_request_ref(proc, ref) -> dict:
        try:
            from apps.clinical.patients.models import MedicalOrder

            order = (
                MedicalOrder.objects.filter(patient_id=proc.patient_id, is_active=True, order_type="procedure")
                .order_by("order_date", "created_at")
                .first()
            )
            if order is None:
                order = (
                    MedicalOrder.objects.filter(patient_id=proc.patient_id, is_active=True)
                    .order_by("order_date", "created_at")
                    .first()
                )
            if order is not None:
                return ref.service_request(identity.service_request_id(order))
        except Exception:
            pass
        return ref.service_request("sreq-placeholder")

    @staticmethod
    def _reason_condition_ref(proc, ref) -> dict | None:
        try:
            from apps.clinical.health_screening.models import Problem

            problem = (
                Problem.objects.filter(patient_id=proc.patient_id, is_active=True)
                .order_by("created_at")
                .first()
            )
            if problem is not None:
                return ref.condition(identity.condition_id(problem))
        except Exception:
            pass
        return None

    def supported_search_params(self):
        return {"patient": "reference", "date": "date", "code": "token", "status": "token", "_id": "token"}
