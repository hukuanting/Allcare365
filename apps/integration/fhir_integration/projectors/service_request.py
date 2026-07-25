"""Project persisted medical orders without inferred encounter or requester."""
from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Q

from ..fhir_search.query_translator import date_to_q, parse_token_param
from ..meta_builder import MetaBuilder
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..resource_identity import identity

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
        "portable": (
            "http://hl7.org/fhir/us/core/CodeSystem/us-core-category",
            "treatment-intervention-preference",
            "Treatment Intervention Preference",
        ),
    }

    def query(self, patient_id, search_params, context):
        from apps.clinical.patients.models import MedicalOrder

        qs = MedicalOrder.objects.filter(is_active=True).select_related("patient")
        if search_params.get("_id"):
            raw_id = str(search_params["_id"]).rstrip("/").split("/")[-1]
            if not raw_id.startswith("sreq-"):
                return qs.none()
            qs = qs.filter(id=raw_id[5:])
        patient_scope = patient_id or search_params.get("patient")
        if patient_scope:
            resolved = identity.resolve_patient_db_id(str(patient_scope))
            if resolved is None:
                return qs.none()
            qs = qs.filter(patient_id=resolved)
        if search_params.get("status"):
            requested = {value.strip().casefold() for value in str(search_params["status"]).split(",") if value.strip()}
            if requested and "active" not in requested:
                return qs.none()
        if search_params.get("category"):
            requested = self._token_codes(search_params["category"])
            order_types = [
                order_type
                for order_type, coding in self.CATEGORY_BY_ORDER_TYPE.items()
                if order_type in requested or coding[1].casefold() in requested
            ]
            if not order_types:
                return qs.none()
            qs = qs.filter(order_type__in=order_types)
        if search_params.get("code"):
            requested = self._token_codes(search_params["code"])
            if not requested:
                return qs.none()
            predicate = Q()
            for value in requested:
                predicate |= Q(order_detail__icontains=value)
            qs = qs.filter(predicate)
        if search_params.get("authored"):
            qs = qs.filter(date_to_q("order_date__date", str(search_params["authored"])))
        return qs

    def project(self, order, context: "FHIRContext") -> dict | None:
        detail = (order.order_detail or "").strip()
        if not detail or not order.order_date:
            return None
        resource = {
            "resourceType": "ServiceRequest",
            "id": identity.service_request_id(order),
            "meta": MetaBuilder.build(self.profile_key),
            "status": "active",
            "intent": "order",
            "code": {"text": detail},
            "subject": context.reference_builder.patient(identity.patient_id(order.patient)),
            "authoredOn": order.order_date.isoformat(),
        }
        coding = self.CATEGORY_BY_ORDER_TYPE.get((order.order_type or "").strip())
        if coding is not None:
            resource["category"] = [{"coding": [{
                "system": coding[0],
                "code": coding[1],
                "display": coding[2],
            }]}]
        return resource

    @staticmethod
    def _token_codes(raw_value) -> set[str]:
        values = raw_value if isinstance(raw_value, (list, tuple)) else str(raw_value or "").split(",")
        codes = set()
        for value in values:
            value = str(value).strip()
            if value:
                _system, code = parse_token_param(value)
                codes.add(code.casefold())
        return codes

    def supported_search_params(self):
        return {"patient": "reference", "_id": "token", "status": "token", "category": "token", "code": "token", "authored": "date"}
