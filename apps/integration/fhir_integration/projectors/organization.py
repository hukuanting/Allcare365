"""Organization projector with stable US Core-compliant singleton data."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..meta_builder import MetaBuilder
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..uscore_templates import ORGANIZATION_ID

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


def _default_org():
    return {
        "resourceType": "Organization",
        "id": ORGANIZATION_ID,
        "meta": MetaBuilder.build("us-core-organization"),
        "identifier": [{
            "system": "http://hl7.org/fhir/sid/us-npi",
            "value": "1000000004",
        }, {
            "system": "urn:oid:2.16.840.1.113883.6.300",
            "value": "12345",
        }],
        "active": True,
        "type": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/organization-type",
                "code": "ins",
                "display": "Insurance Company",
            }]
        }],
        "name": "Allcare365 Health System",
        "telecom": [{"system": "phone", "value": "555-555-2000"}],
        "address": [{
            "line": ["123 Main St"],
            "city": "Anytown",
            "state": "CA",
            "postalCode": "12345",
            "country": "US",
        }],
    }


@ProjectorRegistry.register("Organization")
class OrganizationProjector(BaseProjector):
    resource_type = "Organization"
    profile_key = "us-core-organization"

    def query(self, patient_id, search_params, context):
        org = _default_org()
        rows = [org]

        if search_params.get("_id"):
            rid = str(search_params["_id"])
            if rid != org["id"]:
                return []
        if search_params.get("name"):
            if str(search_params["name"]).lower() not in org["name"].lower():
                return []
        if search_params.get("address"):
            address_text = " ".join(org["address"][0].values()).lower()
            if str(search_params["address"]).lower() not in address_text:
                return []
        return rows

    def project_batch(self, queryset_or_list, context):
        return list(queryset_or_list)

    def project(self, instance, context: "FHIRContext") -> dict:
        return instance

    def supported_search_params(self):
        return {"_id": "token", "name": "string", "address": "string"}
