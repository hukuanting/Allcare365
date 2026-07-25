"""Project persisted insurance rows to US Core Coverage."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..meta_builder import MetaBuilder
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..resource_identity import identity

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


FHIR_COVERAGE_STATUSES = {"active", "cancelled", "draft", "entered-in-error"}


@ProjectorRegistry.register("Coverage")
class CoverageProjector(BaseProjector):
    resource_type = "Coverage"
    profile_key = "us-core-coverage"

    def query(self, patient_id, search_params, context):
        from apps.clinical.patients.models import InsuranceData

        qs = InsuranceData.objects.filter(is_active=True).select_related("patient")
        if search_params.get("_id"):
            raw_id = str(search_params["_id"]).rstrip("/").split("/")[-1]
            if not raw_id.startswith("cov-"):
                return qs.none()
            qs = qs.filter(id=raw_id[4:])

        patient_scope = patient_id or search_params.get("patient")
        if patient_scope:
            resolved = identity.resolve_patient_db_id(str(patient_scope))
            if resolved is None:
                return qs.none()
            qs = qs.filter(patient_id=resolved)
        return qs

    def optimize_queryset(self, qs):
        return qs.select_related("patient")

    def project(self, insurance, context: "FHIRContext") -> dict | None:
        from apps.clinical.patients.models import Organization

        payer_identifier = (insurance.payer_identifier or "").strip()
        status = (insurance.coverage_status or "").strip().casefold()
        if not _usable_text(payer_identifier) or status not in FHIR_COVERAGE_STATUSES:
            return None

        payers = list(
            Organization.objects.filter(
                is_active=True,
                identifier=payer_identifier,
            ).exclude(name="").exclude(name__iexact="unknown")[:2]
        )
        if len(payers) != 1:
            return None

        ref = context.reference_builder
        resource = {
            "resourceType": "Coverage",
            "id": identity.coverage_id(insurance),
            "meta": MetaBuilder.build(self.profile_key),
            "status": status,
            "beneficiary": ref.patient(identity.patient_id(insurance.patient)),
            "payor": [ref.organization(identity.organization_id(payers[0]))],
        }

        if _usable_text(insurance.coverage_type):
            resource["type"] = {"text": insurance.coverage_type.strip()}
        if _usable_text(insurance.member_identifier):
            resource["identifier"] = [{"value": insurance.member_identifier.strip()}]
        if _usable_text(insurance.subscriber_identifier):
            resource["subscriberId"] = insurance.subscriber_identifier.strip()
        if _usable_text(insurance.relationship_to_subscriber):
            resource["relationship"] = {"text": insurance.relationship_to_subscriber.strip()}
        if _usable_text(insurance.group_identifier):
            resource["class"] = [{
                "type": {"coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/coverage-class",
                    "code": "group",
                }]},
                "value": insurance.group_identifier.strip(),
            }]
        return resource

    def supported_search_params(self):
        return {"patient": "reference", "_id": "token"}


def _usable_text(value) -> bool:
    return bool(value and str(value).strip() and str(value).strip().casefold() != "unknown")
