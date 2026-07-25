"""Project source-backed HealthScreening/Encounter pairs to FHIR Encounter."""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ..fhir_search.query_translator import date_to_q
from ..meta_builder import MetaBuilder
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..resource_identity import identity
from ..uscore_templates import direct_encounter_for_source

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


FHIR_STATUSES = {
    "planned",
    "arrived",
    "triaged",
    "in-progress",
    "onleave",
    "finished",
    "cancelled",
    "entered-in-error",
    "unknown",
}


@ProjectorRegistry.register("Encounter")
class EncounterProjector(BaseProjector):
    resource_type = "Encounter"
    profile_key = "us-core-encounter"

    def query(self, patient_id, search_params, context):
        from apps.clinical.health_screening.models import HealthScreening

        qs = HealthScreening.objects.filter(
            is_active=True,
            product_encounters__is_active=True,
        ).select_related("patient").distinct()

        patient_scope = patient_id or search_params.get("patient")
        if patient_scope:
            resolved_patient_id = identity.resolve_patient_db_id(str(patient_scope))
            if resolved_patient_id is None:
                return []
            qs = qs.filter(patient_id=resolved_patient_id)

        if search_params.get("_id"):
            fhir_id = str(search_params["_id"]).rstrip("/").split("/")[-1]
            if not fhir_id.startswith("enc-"):
                return []
            qs = qs.filter(id=fhir_id[4:])
        if search_params.get("date"):
            qs = qs.filter(date_to_q("encounter_time__date", str(search_params["date"])))
        if search_params.get("identifier"):
            value = str(search_params["identifier"]).split("|", 1)[-1]
            qs = qs.filter(encounter_identifier=value)
        if search_params.get("_lastUpdated"):
            qs = qs.filter(date_to_q("updated_at__date", str(search_params["_lastUpdated"])))

        rows = []
        for screening in qs:
            encounter = direct_encounter_for_source(screening)
            if encounter is None:
                continue
            if not self._matches_linked_encounter(encounter, screening, search_params):
                continue
            rows.append(screening)
        return rows

    def optimize_queryset(self, qs):
        return qs.select_related("patient") if hasattr(qs, "select_related") else qs

    def project_batch(self, queryset_or_list, context):
        return [
            resource
            for screening in queryset_or_list
            if (resource := self.project(screening, context))
        ]

    def project(self, screening, context: "FHIRContext") -> dict | None:
        encounter = direct_encounter_for_source(screening)
        if encounter is None or not screening.encounter_time or not encounter.started_at:
            return None

        status = (encounter.status or "").strip().casefold()
        encounter_class = self._encounter_class(encounter.encounter_type)
        if status not in FHIR_STATUSES or encounter_class is None:
            return None

        ref = context.reference_builder
        pid = identity.patient_id(screening.patient)
        start = encounter.started_at.isoformat()
        resource = {
            "resourceType": "Encounter",
            "id": identity.encounter_id(screening),
            "meta": MetaBuilder.build(self.profile_key),
            "status": status,
            "class": {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": encounter_class,
            },
            "subject": ref.patient(pid),
            "period": {"start": start},
        }

        if encounter.ended_at:
            resource["period"]["end"] = encounter.ended_at.isoformat()
        if _usable_text(screening.encounter_identifier):
            resource["identifier"] = [{
                "value": screening.encounter_identifier.strip(),
            }]

        encounter_type = (screening.encounter_type or encounter.encounter_type or "").strip()
        if _usable_text(encounter_type):
            resource["type"] = [{"text": encounter_type}]

        practitioner = encounter.practitioner
        if practitioner is not None and _projectable_practitioner(practitioner):
            resource["participant"] = [{
                "individual": ref.practitioner(identity.practitioner_id(practitioner)),
            }]
            organization = practitioner.organization
            if organization is not None and _projectable_organization(organization):
                resource["serviceProvider"] = ref.organization(identity.organization_id(organization))

        if _usable_text(encounter.location):
            resource["location"] = [{
                "location": ref.location(identity.location_id(encounter.location.strip())),
            }]
        if _usable_text(encounter.reason):
            resource["reasonCode"] = [{"text": encounter.reason.strip()}]
        if _usable_text(screening.encounter_disposition):
            resource["hospitalization"] = {
                "dischargeDisposition": {"text": screening.encounter_disposition.strip()}
            }
        return resource

    @classmethod
    def _matches_linked_encounter(cls, encounter, screening, search_params) -> bool:
        requested_status = {
            value.strip().casefold()
            for value in str(search_params.get("status", "")).split(",")
            if value.strip()
        }
        if requested_status and (encounter.status or "").strip().casefold() not in requested_status:
            return False

        requested_class = str(search_params.get("class", "")).split("|")[-1].upper()
        if requested_class and cls._encounter_class(encounter.encounter_type) != requested_class:
            return False

        requested_type = str(search_params.get("type", "")).split("|")[-1].strip().casefold()
        actual_type = " ".join(filter(None, [screening.encounter_type, encounter.encounter_type])).casefold()
        if requested_type and requested_type not in actual_type:
            return False

        requested_location = str(search_params.get("location", "")).rstrip("/").split("/")[-1].strip()
        if requested_location:
            location = (encounter.location or "").strip()
            if not location or requested_location not in {location, identity.location_id(location)}:
                return False

        requested_disposition = str(search_params.get("discharge-disposition", "")).strip().casefold()
        if requested_disposition and requested_disposition not in (screening.encounter_disposition or "").casefold():
            return False
        return True

    @staticmethod
    def _encounter_class(encounter_type: str) -> str | None:
        value = (encounter_type or "").strip().casefold()
        words = set(re.findall(r"[a-z0-9]+", value))
        if words & {"inpatient", "admission", "hospitalized"}:
            return "IMP"
        if words & {"emergency", "er", "ed"}:
            return "EMER"
        if words & {"virtual", "telehealth", "remote"}:
            return "VR"
        if words & {"outpatient", "ambulatory", "clinic", "annual", "screening"}:
            return "AMB"
        return None

    def supported_search_params(self):
        return {
            "patient": "reference",
            "_id": "token",
            "identifier": "token",
            "date": "date",
            "class": "token",
            "type": "token",
            "_lastUpdated": "date",
            "status": "token",
            "location": "reference",
            "discharge-disposition": "token",
        }

    def supported_rev_includes(self):
        return ["Provenance:target"]


def _usable_text(value) -> bool:
    return bool(value and str(value).strip() and str(value).strip().casefold() != "unknown")


def _projectable_practitioner(practitioner) -> bool:
    return bool(
        practitioner.is_active
        and (practitioner.status or "").strip().casefold() == "active"
        and _usable_text(practitioner.first_name)
        and _usable_text(practitioner.last_name)
    )


def _projectable_organization(organization) -> bool:
    return bool(organization.is_active and _usable_text(organization.name))
