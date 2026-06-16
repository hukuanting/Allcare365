"""ServiceRequest Projector — Maps ``patients.MedicalOrder`` → FHIR ServiceRequest."""
from __future__ import annotations
from typing import TYPE_CHECKING
from django.db.models import Q
from ..fhir_search.query_translator import date_to_q, parse_token_param
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..meta_builder import MetaBuilder
from ..resource_identity import identity
from ..uscore_templates import PRACTITIONER_ID, encounter_ref_for_patient
if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


@ProjectorRegistry.register("ServiceRequest")
class ServiceRequestProjector(BaseProjector):
    resource_type = "ServiceRequest"
    profile_key = "us-core-servicerequest"
    CATEGORY_BY_ORDER_TYPE = {
        "laboratory": ("http://snomed.info/sct", "108252007", "Laboratory procedure"),
        "procedure": ("http://snomed.info/sct", "386053000", "Evaluation procedure"),
        "clinical_test": ("http://snomed.info/sct", "386053000", "Evaluation procedure"),
        "diagnostic_imaging": ("http://snomed.info/sct", "363679005", "Imaging"),
        "portable": ("http://hl7.org/fhir/us/core/CodeSystem/us-core-category", "treatment-intervention-preference", "Treatment Intervention Preference"),
        "medication": ("http://snomed.info/sct", "409073007", "Education procedure"),
    }

    def query(self, patient_id, search_params, context):
        from apps.clinical.patients.models import MedicalOrder
        qs = MedicalOrder.objects.filter(is_active=True)
        if search_params.get("_id"):
            raw_id = str(search_params["_id"])
            if raw_id.startswith("sreq-"):
                raw_id = raw_id[5:]
            qs = qs.filter(id=raw_id)
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        if search_params.get("patient"):
            qs = qs.filter(patient_id=search_params["patient"])
        if search_params.get("status"):
            requested_statuses = {s.strip().lower() for s in str(search_params["status"]).split(",") if s.strip()}
            if requested_statuses and "active" not in requested_statuses:
                return qs.none()
        if search_params.get("category"):
            requested = self._token_codes(search_params.get("category"))
            order_types = [
                order_type
                for order_type, coding in self.CATEGORY_BY_ORDER_TYPE.items()
                if coding[1] in requested or order_type in requested
            ]
            if order_types:
                qs = qs.filter(order_type__in=order_types)
            else:
                qs = qs.filter(order_type__icontains=next(iter(requested), ""))
        if search_params.get("code"):
            requested = self._token_codes(search_params.get("code"))
            if "108252007" not in requested:
                qs = qs.filter(Q(order_detail__icontains=next(iter(requested), "")) | Q(order_type__icontains=next(iter(requested), "")))
        if search_params.get("authored"):
            qs = qs.filter(date_to_q("order_date__date", str(search_params["authored"])))
        return qs

    def optimize_queryset(self, qs):
        return qs.select_related("patient")

    def project(self, order, context: "FHIRContext") -> dict:
        sid = identity.service_request_id(order)
        pid = identity.patient_id(order.patient)
        ref = context.reference_builder
        authored = order.order_date or order.created_at
        coding = self._category_coding(order.order_type)
        condition_ref = self._reason_condition_ref(order, ref)
        resource = {
            "resourceType": "ServiceRequest",
            "id": sid,
            "meta": MetaBuilder.build(self.profile_key),
            "status": "active",
            "intent": "order",
            "category": [{"coding": [{"system": coding[0], "code": coding[1], "display": coding[2]}]}],
            "code": {"coding": [{"system": "http://snomed.info/sct", "code": "108252007", "display": order.order_detail[:80] if order.order_detail else "Order"}], "text": order.order_detail},
            "subject": ref.patient(pid),
            "encounter": encounter_ref_for_patient(str(order.patient_id), ref, identity),
            "occurrencePeriod": {
                "start": authored.isoformat(),
                "end": authored.isoformat(),
            },
            "authoredOn": authored.isoformat(),
            "requester": ref.practitioner(PRACTITIONER_ID),
            "reasonCode": [{
                "coding": [{"system": "http://snomed.info/sct", "code": "386053000", "display": "Evaluation procedure"}],
                "text": order.order_detail or "Order clinically indicated",
            }],
        }
        if condition_ref:
            resource["reasonReference"] = [condition_ref]
        return resource

    @classmethod
    def _category_coding(cls, order_type: str) -> tuple[str, str, str]:
        return cls.CATEGORY_BY_ORDER_TYPE.get(
            order_type or "",
            ("http://snomed.info/sct", "386053000", "Evaluation procedure"),
        )

    @staticmethod
    def _token_codes(raw_value) -> set[str]:
        values = raw_value if isinstance(raw_value, (list, tuple)) else str(raw_value or "").split(",")
        codes = set()
        for value in values:
            value = str(value).strip()
            if not value:
                continue
            _system, code = parse_token_param(value)
            codes.add(code.lower())
        return codes

    @staticmethod
    def _reason_condition_ref(order, ref) -> dict | None:
        try:
            from apps.clinical.health_screening.models import Problem

            problem = (
                Problem.objects.filter(patient_id=order.patient_id, is_active=True)
                .order_by("created_at")
                .first()
            )
            if problem is not None:
                return ref.condition(identity.condition_id(problem))
        except Exception:
            pass
        return None

    def supported_search_params(self):
        return {"patient": "reference", "_id": "token", "status": "token", "category": "token", "code": "token", "authored": "date"}
