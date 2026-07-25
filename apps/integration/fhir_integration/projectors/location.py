"""Project persisted encounter locations as FHIR Location resources."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..meta_builder import MetaBuilder
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..resource_identity import identity

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


@ProjectorRegistry.register("Location")
class LocationProjector(BaseProjector):
    resource_type = "Location"
    profile_key = "us-core-location"

    def query(self, patient_id, search_params, context):
        from apps.clinical.health_screening.models import Encounter

        qs = Encounter.objects.filter(is_active=True).exclude(location="")
        if patient_id:
            resolved_patient_id = identity.resolve_patient_db_id(str(patient_id))
            if resolved_patient_id is None:
                return []
            qs = qs.filter(patient_id=resolved_patient_id)

        names = list(qs.values_list("location", flat=True).distinct())
        names = [name.strip() for name in names if _usable_text(name)]

        requested_id = str(search_params.get("_id", "")).strip()
        if requested_id:
            names = [name for name in names if identity.location_id(name) == requested_id]

        requested_name = str(search_params.get("name", "")).strip().casefold()
        if requested_name:
            names = [name for name in names if requested_name in name.casefold()]

        requested_address = str(search_params.get("address", "")).strip().casefold()
        if requested_address:
            names = [name for name in names if requested_address in name.casefold()]

        return sorted(set(names), key=str.casefold)

    def project_batch(self, queryset_or_list, context):
        return [resource for name in queryset_or_list if (resource := self.project(name, context))]

    def project(self, location_name, context: "FHIRContext") -> dict | None:
        if not _usable_text(location_name):
            return None
        name = str(location_name).strip()
        return {
            "resourceType": "Location",
            "id": identity.location_id(name),
            "meta": MetaBuilder.build(self.profile_key),
            "status": "active",
            "name": name,
        }

    def supported_search_params(self):
        return {"_id": "token", "name": "string", "address": "string"}


def _usable_text(value) -> bool:
    return bool(value and str(value).strip() and str(value).strip().casefold() != "unknown")
