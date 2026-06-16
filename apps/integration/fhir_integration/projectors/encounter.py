"""
Encounter Projector — Maps ``health_screening.HealthScreening`` → FHIR Encounter.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from ..fhir_search.query_translator import date_to_q
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..meta_builder import MetaBuilder
from ..resource_identity import identity
from ..uscore_templates import LOCATION_ID, ORGANIZATION_ID, PRACTITIONER_ID

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


@ProjectorRegistry.register("Encounter")
class EncounterProjector(BaseProjector):
    resource_type = "Encounter"
    profile_key = "us-core-encounter"

    def query(self, patient_id, search_params, context):
        from apps.clinical.health_screening.models import HealthScreening
        qs = HealthScreening.objects.filter(is_active=True)
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        if search_params.get("patient"):
            qs = qs.filter(patient_id=search_params["patient"])
        if search_params.get("_id"):
            fid = str(search_params["_id"])
            if fid == "example-encounter":
                first = qs.order_by("encounter_time", "screening_date", "id").first()
                return qs.filter(id=first.id) if first else qs.none()
            if fid.startswith("enc-"):
                qs = qs.filter(id=fid[4:])
            else:
                qs = qs.filter(id=fid)
        if search_params.get("date"):
            qs = qs.filter(date_to_q("screening_date", str(search_params["date"])))
        if search_params.get("identifier"):
            token = str(search_params["identifier"])
            value = token.split("|", 1)[-1]
            qs = qs.filter(encounter_identifier=value)
        if search_params.get("class"):
            cls = str(search_params["class"]).split("|")[-1].upper()
            if cls == "IMP":
                qs = qs.filter(encounter_type__icontains="inpatient")
            elif cls == "AMB":
                qs = qs.exclude(encounter_type__icontains="inpatient")
        if search_params.get("type"):
            qs = qs.filter(encounter_type__icontains=str(search_params["type"]).split("|")[-1])
        if search_params.get("_lastUpdated"):
            qs = qs.filter(date_to_q("updated_at__date", str(search_params["_lastUpdated"])))
        if search_params.get("status"):
            requested = {s.strip().lower() for s in str(search_params["status"]).split(",") if s.strip()}
            if requested and "finished" not in requested:
                return qs.none()
        if search_params.get("location"):
            if LOCATION_ID not in str(search_params["location"]):
                return qs.none()
        if search_params.get("discharge-disposition"):
            if "home" not in str(search_params["discharge-disposition"]).lower():
                return qs.none()
        return qs

    def optimize_queryset(self, qs):
        return qs.select_related("patient").prefetch_related("patient__problems")

    def project(self, screening, context: "FHIRContext") -> dict:
        eid = identity.encounter_id(screening)
        ref = context.reference_builder
        ts = context.terminology
        pid = identity.patient_id(screening.patient)
        dt_start = screening.encounter_time.isoformat() if screening.encounter_time else "2025-01-01T10:00:00Z"
        enc_type = (screening.encounter_type or "").lower()
        enc_class = "IMP" if "inpatient" in enc_type else "AMB"

        resource = {
            "resourceType": "Encounter",
            "id": eid,
            "meta": MetaBuilder.build(self.profile_key),
            "status": "finished",
            "statusHistory": [{
                "status": "finished",
                "period": {"start": dt_start, "end": dt_start},
            }],
            "identifier": [{
                "system": "http://allcare365.example/encounter-id",
                "value": screening.encounter_identifier or f"ENC-{screening.id}",
            }],
            "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": enc_class},
            "classHistory": [{
                "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": enc_class},
                "period": {"start": dt_start, "end": dt_start},
            }],
            "type": [{"coding": [{"system": "http://snomed.info/sct", "code": "185345009"}]}],
            "subject": ref.patient(pid),
            "period": {"start": dt_start, "end": dt_start},
            "participant": [{
                "type": [{"coding": [ts.to_fhir_coding("participant_attender")]}],
                "period": {"start": dt_start},
                "individual": ref.practitioner(PRACTITIONER_ID),
            }],
            "location": [{
                "location": ref.location(LOCATION_ID),
                "status": "completed",
            }],
            "serviceProvider": ref.organization(ORGANIZATION_ID),
            "hospitalization": {
                "dischargeDisposition": {"coding": [ts.to_fhir_coding("discharge_home")]}
            },
        }

        # reasonReference — link to patient's conditions
        problems = list(
            screening.patient.problems.filter(is_active=True)
            .order_by("-date_of_resolution", "-updated_at")[:3]
        )
        if problems:
            resource["reasonReference"] = [ref.condition(identity.condition_id(p)) for p in problems]
            resource["reasonCode"] = [ts.to_codeable_concept("anemia")]
            resource["diagnosis"] = [{
                "condition": ref.condition(identity.condition_id(problems[0])),
                "use": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/diagnosis-role", "code": "AD"}]},
            }]

        return resource

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
