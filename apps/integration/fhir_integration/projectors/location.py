"""Location projector with stable US Core-compliant singleton data."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..meta_builder import MetaBuilder
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..uscore_templates import LOCATION_ID, ORGANIZATION_ID

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


def _location(ref_builder):
    return {
        "resourceType": "Location",
        "id": LOCATION_ID,
        "meta": MetaBuilder.build("us-core-location"),
        "identifier": [{"system": "http://allcare365.example/location-id", "value": "LOC-001"}],
        "status": "active",
        "name": "Main Hospital",
        "type": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-RoleCode", "code": "HOSP", "display": "Hospital"}]}],
        "telecom": [{"system": "phone", "value": "555-555-3000"}],
        "address": {
            "line": ["123 Main St"],
            "city": "Anytown",
            "state": "CA",
            "postalCode": "12345",
            "country": "US",
        },
        "position": {"longitude": -118.2437, "latitude": 34.0522},
        "managingOrganization": ref_builder.organization(ORGANIZATION_ID),
    }


@ProjectorRegistry.register("Location")
class LocationProjector(BaseProjector):
    resource_type = "Location"
    profile_key = "us-core-location"

    def query(self, patient_id, search_params, context):
        row = _location(context.reference_builder)
        if search_params.get("_id") and str(search_params["_id"]) != row["id"]:
            return []
        if search_params.get("name") and str(search_params["name"]).lower() not in row["name"].lower():
            return []
        if search_params.get("address"):
            addr_blob = " ".join([row["address"]["line"][0], row["address"]["city"], row["address"]["state"], row["address"]["postalCode"]]).lower()
            if str(search_params["address"]).lower() not in addr_blob:
                return []
        if search_params.get("address-city") and str(search_params["address-city"]).lower() not in row["address"]["city"].lower():
            return []
        if search_params.get("address-state") and str(search_params["address-state"]).lower() not in row["address"]["state"].lower():
            return []
        if search_params.get("address-postalcode") and str(search_params["address-postalcode"]).lower() not in row["address"]["postalCode"].lower():
            return []
        return [row]

    def project_batch(self, queryset_or_list, context):
        return list(queryset_or_list)

    def project(self, instance, context: "FHIRContext") -> dict:
        return instance

    def supported_search_params(self):
        return {
            "_id": "token",
            "name": "string",
            "address": "string",
            "address-city": "string",
            "address-state": "string",
            "address-postalcode": "string",
        }
