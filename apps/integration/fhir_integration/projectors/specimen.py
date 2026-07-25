"""Project only specimen facts explicitly stored with a lab result."""
from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Q

from ..meta_builder import MetaBuilder
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..resource_identity import identity

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


@ProjectorRegistry.register("Specimen")
class SpecimenProjector(BaseProjector):
    resource_type = "Specimen"
    profile_key = "us-core-specimen"

    def query(self, patient_id, search_params, context):
        from apps.clinical.health_screening.models import LaboratoryResults

        qs = LaboratoryResults.objects.filter(is_active=True).filter(
            Q(specimen_type__gt="")
            | Q(specimen_source_site__gt="")
            | Q(specimen_identifier__gt="")
            | Q(specimen_condition__gt="")
        ).select_related("health_screening", "health_screening__patient")
        if search_params.get("_id"):
            raw_id = str(search_params["_id"]).rstrip("/").split("/")[-1]
            if not raw_id.startswith("spm-"):
                return qs.none()
            qs = qs.filter(id=raw_id[4:])
        patient_scope = patient_id or search_params.get("patient")
        if patient_scope:
            resolved = identity.resolve_patient_db_id(str(patient_scope))
            if resolved is None:
                return qs.none()
            qs = qs.filter(health_screening__patient_id=resolved)
        return qs

    def project(self, lab, context: "FHIRContext") -> dict | None:
        if not any(_usable_text(value) for value in (
            lab.specimen_type,
            lab.specimen_source_site,
            lab.specimen_identifier,
            lab.specimen_condition,
        )):
            return None
        resource = {
            "resourceType": "Specimen",
            "id": identity.specimen_id(lab),
            "meta": MetaBuilder.build(self.profile_key),
            "subject": context.reference_builder.patient(identity.patient_id(lab.health_screening.patient)),
        }
        if _usable_text(lab.specimen_identifier):
            resource["identifier"] = [{"value": lab.specimen_identifier.strip()}]
        if _usable_text(lab.specimen_type):
            resource["type"] = {"text": lab.specimen_type.strip()}

        collection = {}
        if lab.health_screening.screening_date:
            collection["collectedDateTime"] = lab.health_screening.screening_date.isoformat()
        if _usable_text(lab.specimen_source_site):
            collection["bodySite"] = {"text": lab.specimen_source_site.strip()}
        if collection:
            resource["collection"] = collection
        if _usable_text(lab.specimen_condition):
            resource["condition"] = [{"text": lab.specimen_condition.strip()}]
        return resource

    def supported_search_params(self):
        return {"patient": "reference", "_id": "token"}


def _usable_text(value) -> bool:
    return bool(value and str(value).strip() and str(value).strip().casefold() != "unknown")
