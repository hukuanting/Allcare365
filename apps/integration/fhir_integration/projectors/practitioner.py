"""Project persisted practitioner master data and patient-practitioner roles."""
from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Q

from ..meta_builder import MetaBuilder
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..resource_identity import identity

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


def practitioner_role_id(link) -> str:
    return identity.practitioner_role_id(link)


@ProjectorRegistry.register("Practitioner")
class PractitionerProjector(BaseProjector):
    resource_type = "Practitioner"
    profile_key = "us-core-practitioner"

    def query(self, patient_id, search_params, context):
        from apps.clinical.patients.models import Practitioner

        qs = Practitioner.objects.filter(is_active=True).exclude(
            Q(first_name="") & Q(last_name="")
        )
        if patient_id:
            resolved = identity.resolve_patient_db_id(str(patient_id))
            if resolved is None:
                return qs.none()
            qs = qs.filter(patient_links__patient_id=resolved, patient_links__is_active=True).distinct()
        if search_params.get("_id"):
            raw_id = str(search_params["_id"])
            if raw_id.startswith("pract-"):
                raw_id = raw_id[6:]
            qs = qs.filter(id=raw_id)
        if search_params.get("identifier"):
            value = str(search_params["identifier"]).split("|", 1)[-1]
            qs = qs.filter(
                Q(identifier=value) | Q(npi=value) | Q(license_number=value)
            )
        if search_params.get("name"):
            value = str(search_params["name"])
            qs = qs.filter(Q(first_name__icontains=value) | Q(last_name__icontains=value))
        return qs.select_related("organization")

    def project(self, practitioner, context: "FHIRContext") -> dict:
        first_name = str(practitioner.first_name or "").strip()
        last_name = str(practitioner.last_name or "").strip()
        if not first_name and not last_name:
            return None

        name = {}
        if last_name:
            name["family"] = last_name
        if first_name:
            name["given"] = [first_name]
        resource = {
            "resourceType": "Practitioner",
            "id": identity.practitioner_id(practitioner),
            "meta": MetaBuilder.build(self.profile_key),
            "active": bool(
                practitioner.is_active
                and str(practitioner.status or "").strip().lower() == "active"
            ),
            "name": [name],
        }

        identifiers = []
        if practitioner.npi:
            identifiers.append({
                "system": "http://hl7.org/fhir/sid/us-npi",
                "value": str(practitioner.npi),
            })
        if practitioner.identifier:
            identifiers.append({"value": str(practitioner.identifier)})
        if practitioner.license_number:
            identifiers.append({
                "type": {"text": "Professional license"},
                "value": str(practitioner.license_number),
            })
        if identifiers:
            resource["identifier"] = identifiers

        telecom = []
        if practitioner.phone:
            telecom.append({"system": "phone", "value": str(practitioner.phone)})
        if practitioner.email:
            telecom.append({"system": "email", "value": str(practitioner.email)})
        if telecom:
            resource["telecom"] = telecom
        return resource

    def supported_search_params(self):
        return {"_id": "token", "name": "string", "identifier": "token"}


@ProjectorRegistry.register("PractitionerRole")
class PractitionerRoleProjector(BaseProjector):
    resource_type = "PractitionerRole"
    profile_key = "us-core-practitionerrole"

    def query(self, patient_id, search_params, context):
        from apps.clinical.patients.models import PatientPractitionerLink

        qs = PatientPractitionerLink.objects.filter(
            is_active=True,
            status__iexact="active",
            practitioner__is_active=True,
            practitioner__status__iexact="active",
        ).select_related("patient", "practitioner", "practitioner__organization")
        if patient_id:
            resolved = identity.resolve_patient_db_id(str(patient_id))
            if resolved is None:
                return qs.none()
            qs = qs.filter(patient_id=resolved)
        if search_params.get("_id"):
            raw_id = str(search_params["_id"])
            if raw_id.startswith("prrole-"):
                raw_id = raw_id[7:]
            qs = qs.filter(id=raw_id)
        if search_params.get("practitioner"):
            raw_id = str(search_params["practitioner"]).rstrip("/").split("/")[-1]
            if raw_id.startswith("pract-"):
                raw_id = raw_id[6:]
            qs = qs.filter(practitioner_id=raw_id)
        if search_params.get("organization"):
            raw_id = str(search_params["organization"]).rstrip("/").split("/")[-1]
            if raw_id.startswith("org-"):
                raw_id = raw_id[4:]
            qs = qs.filter(practitioner__organization_id=raw_id)
        if search_params.get("specialty"):
            value = str(search_params["specialty"]).split("|", 1)[-1]
            qs = qs.filter(
                Q(practitioner__specialty__icontains=value) | Q(role__icontains=value)
            )
        return qs

    def project(self, link, context: "FHIRContext") -> dict:
        practitioner = link.practitioner
        if (
            not link.is_active
            or str(link.status or "").strip().casefold() != "active"
            or not practitioner.is_active
            or str(practitioner.status or "").strip().casefold() != "active"
            or not (str(practitioner.first_name or "").strip() or str(practitioner.last_name or "").strip())
        ):
            return None
        ref = context.reference_builder
        resource = {
            "resourceType": "PractitionerRole",
            "id": practitioner_role_id(link),
            "meta": MetaBuilder.build(self.profile_key),
            "active": bool(
                link.is_active
                and str(link.status or "").strip().lower() == "active"
                and practitioner.is_active
            ),
            "practitioner": ref.practitioner(identity.practitioner_id(practitioner)),
            "period": {"start": link.start_at.isoformat()},
        }
        if link.end_at:
            resource["period"]["end"] = link.end_at.isoformat()
        if (
            practitioner.organization_id
            and practitioner.organization.is_active
            and str(practitioner.organization.name or "").strip()
            and str(practitioner.organization.name).strip().casefold() != "unknown"
        ):
            resource["organization"] = ref.organization(
                identity.organization_id(practitioner.organization)
            )

        role = str(link.role or link.link_type or "").strip()
        if role:
            resource["code"] = [{"text": role}]
        specialty = str(practitioner.specialty or "").strip()
        if specialty:
            resource["specialty"] = [{"text": specialty}]

        telecom = []
        if practitioner.phone:
            telecom.append({"system": "phone", "value": str(practitioner.phone)})
        if practitioner.email:
            telecom.append({"system": "email", "value": str(practitioner.email)})
        if telecom:
            resource["telecom"] = telecom
        return resource

    def supported_search_params(self):
        return {
            "_id": "token",
            "practitioner": "reference",
            "organization": "reference",
            "specialty": "token",
        }
