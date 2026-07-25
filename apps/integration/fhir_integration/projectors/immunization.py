"""Project persisted immunization administrations without guessed context."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..fhir_search.query_translator import date_to_q
from ..meta_builder import MetaBuilder
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..resource_identity import identity

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


@ProjectorRegistry.register("Immunization")
class ImmunizationProjector(BaseProjector):
    resource_type = "Immunization"
    profile_key = "us-core-immunization"

    def query(self, patient_id, search_params, context):
        from apps.clinical.health_screening.models import Immunization

        qs = Immunization.objects.filter(is_active=True).select_related("patient")
        if search_params.get("_id"):
            raw_id = str(search_params["_id"]).rstrip("/").split("/")[-1]
            if not raw_id.startswith("imm-"):
                return qs.none()
            qs = qs.filter(id=raw_id[4:])
        patient_scope = patient_id or search_params.get("patient")
        if patient_scope:
            resolved = identity.resolve_patient_db_id(str(patient_scope))
            if resolved is None:
                return qs.none()
            qs = qs.filter(patient_id=resolved)
        if search_params.get("status"):
            requested = {value.strip().casefold() for value in str(search_params["status"]).split(",") if value.strip()}
            if requested and "completed" not in requested:
                return qs.none()
        if search_params.get("date"):
            qs = qs.filter(date_to_q("administration_date__date", str(search_params["date"])))
        return qs

    def project(self, immunization, context: "FHIRContext") -> dict | None:
        if not _usable_text(immunization.vaccine_name) or not immunization.administration_date:
            return None
        resource = {
            "resourceType": "Immunization",
            "id": identity.immunization_id(immunization),
            "meta": MetaBuilder.build(self.profile_key),
            "status": "completed",
            "vaccineCode": {"text": immunization.vaccine_name.strip()},
            "patient": context.reference_builder.patient(identity.patient_id(immunization.patient)),
            "occurrenceDateTime": immunization.administration_date.isoformat(),
        }
        if _usable_text(immunization.lot_number):
            resource["lotNumber"] = immunization.lot_number.strip()
        return resource

    def supported_search_params(self):
        return {"patient": "reference", "status": "token", "date": "date", "_id": "token"}


def _usable_text(value) -> bool:
    return bool(value and str(value).strip() and str(value).strip().casefold() != "unknown")
