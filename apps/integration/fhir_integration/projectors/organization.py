"""Project persisted organization master data as FHIR Organization."""
from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Q

from ..meta_builder import MetaBuilder
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..resource_identity import identity

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


@ProjectorRegistry.register("Organization")
class OrganizationProjector(BaseProjector):
    resource_type = "Organization"
    profile_key = "us-core-organization"

    def query(self, patient_id, search_params, context):
        from apps.clinical.patients.models import Organization

        qs = Organization.objects.filter(is_active=True).exclude(name="").exclude(
            name__iexact="unknown"
        )
        if search_params.get("_id"):
            raw_id = str(search_params["_id"])
            if raw_id.startswith("org-"):
                raw_id = raw_id[4:]
            qs = qs.filter(id=raw_id)
        if search_params.get("identifier"):
            value = str(search_params["identifier"]).split("|", 1)[-1]
            qs = qs.filter(identifier=value)
        if search_params.get("name"):
            qs = qs.filter(name__icontains=str(search_params["name"]))
        if search_params.get("address"):
            value = str(search_params["address"])
            qs = qs.filter(
                Q(address_line1__icontains=value)
                | Q(address_line2__icontains=value)
                | Q(city__icontains=value)
                | Q(state__icontains=value)
                | Q(postal_code__icontains=value)
                | Q(country__icontains=value)
            )
        return qs

    def project(self, organization, context: "FHIRContext") -> dict:
        name = str(organization.name or "").strip()
        if not name or name.lower() == "unknown":
            return None

        resource = {
            "resourceType": "Organization",
            "id": identity.organization_id(organization),
            "meta": MetaBuilder.build(self.profile_key),
            "active": bool(organization.is_active),
            "name": name,
        }
        identifier = str(organization.identifier or "").strip()
        if identifier:
            resource["identifier"] = [{"value": identifier}]
        organization_type = str(organization.type or "").strip()
        if organization_type:
            resource["type"] = [{"text": organization_type}]

        address = {}
        lines = [
            value
            for value in (
                str(organization.address_line1 or "").strip(),
                str(organization.address_line2 or "").strip(),
            )
            if value
        ]
        if lines:
            address["line"] = lines
        for field_name, fhir_name in (
            ("city", "city"),
            ("state", "state"),
            ("postal_code", "postalCode"),
            ("country", "country"),
        ):
            value = str(getattr(organization, field_name, "") or "").strip()
            if value:
                address[fhir_name] = value
        if address:
            resource["address"] = [address]
        return resource

    def supported_search_params(self):
        return {
            "_id": "token",
            "identifier": "token",
            "name": "string",
            "address": "string",
        }
