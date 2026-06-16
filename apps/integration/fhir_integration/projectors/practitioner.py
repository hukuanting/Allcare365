"""Practitioner + PractitionerRole projectors for reference resolution."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..meta_builder import MetaBuilder
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..uscore_templates import (
    LOCATION_ID,
    ORGANIZATION_ID,
    PRACTITIONER_ID,
    PRACTITIONER_ROLE_ID,
)

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


def _practitioner():
    return {
        "resourceType": "Practitioner",
        "id": PRACTITIONER_ID,
        "meta": MetaBuilder.build("us-core-practitioner"),
        "identifier": [{"system": "http://hl7.org/fhir/sid/us-npi", "value": "1234567893"}],
        "active": True,
        "name": [{"family": "Careful", "given": ["Adam"], "prefix": ["Dr."]}],
        "telecom": [{"system": "phone", "value": "555-555-1234"}],
        "address": [{
            "line": ["123 Practitioner Way"],
            "city": "Boston",
            "state": "MA",
            "postalCode": "02134",
            "country": "US",
        }],
        "qualification": [{
            "code": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v2-0360",
                    "code": "MD",
                    "display": "Doctor of Medicine",
                }]
            }
        }],
    }


@ProjectorRegistry.register("Practitioner")
class PractitionerProjector(BaseProjector):
    resource_type = "Practitioner"
    profile_key = "us-core-practitioner"

    def query(self, patient_id, search_params, context):
        row = _practitioner()
        if search_params.get("_id") and str(search_params["_id"]) != row["id"]:
            return []
        if search_params.get("identifier"):
            token = str(search_params["identifier"])
            if "|" in token:
                system, value = token.split("|", 1)
                if system != row["identifier"][0]["system"] or value != row["identifier"][0]["value"]:
                    return []
            elif token != row["identifier"][0]["value"]:
                return []
        if search_params.get("name"):
            if str(search_params["name"]).lower() not in " ".join(row["name"][0]["given"] + [row["name"][0]["family"]]).lower():
                return []
        return [row]

    def project_batch(self, queryset_or_list, context):
        return list(queryset_or_list)

    def project(self, instance, context: "FHIRContext") -> dict:
        return instance

    def supported_search_params(self):
        return {"_id": "token", "name": "string", "identifier": "token"}


@ProjectorRegistry.register("PractitionerRole")
class PractitionerRoleProjector(BaseProjector):
    resource_type = "PractitionerRole"
    profile_key = "us-core-practitionerrole"

    def query(self, patient_id, search_params, context):
        ref = context.reference_builder
        row = {
            "resourceType": "PractitionerRole",
            "id": PRACTITIONER_ROLE_ID,
            "meta": MetaBuilder.build("us-core-practitionerrole"),
            "active": True,
            "practitioner": ref.practitioner(PRACTITIONER_ID),
            "organization": ref.organization(ORGANIZATION_ID),
            "code": [{"coding": [{"system": "http://nucc.org/provider-taxonomy", "code": "208D00000X", "display": "General Practice"}]}],
            "specialty": [{"coding": [{"system": "http://nucc.org/provider-taxonomy", "code": "208D00000X", "display": "General Practice"}]}],
            "location": [ref.location(LOCATION_ID)],
            "telecom": [{"system": "phone", "value": "555-555-1234"}],
        }
        if search_params.get("_id") and str(search_params["_id"]) != row["id"]:
            return []
        if search_params.get("practitioner") and PRACTITIONER_ID not in str(search_params["practitioner"]):
            return []
        return [row]

    def project_batch(self, queryset_or_list, context):
        return list(queryset_or_list)

    def project(self, instance, context: "FHIRContext") -> dict:
        return instance

    def supported_search_params(self):
        return {"_id": "token", "practitioner": "reference", "specialty": "token"}
