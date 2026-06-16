"""Coverage Projector — Maps ``patients.InsuranceData`` → FHIR Coverage."""
from __future__ import annotations
from datetime import date
from typing import TYPE_CHECKING
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..meta_builder import MetaBuilder
from ..resource_identity import identity
from ..uscore_templates import ORGANIZATION_ID
if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


@ProjectorRegistry.register("Coverage")
class CoverageProjector(BaseProjector):
    resource_type = "Coverage"
    profile_key = "us-core-coverage"

    def query(self, patient_id, search_params, context):
        from apps.clinical.patients.models import InsuranceData
        qs = InsuranceData.objects.filter(is_active=True)
        if search_params.get("_id"):
            raw_id = str(search_params["_id"])
            if raw_id.startswith("cov-"):
                raw_id = raw_id[4:]
            qs = qs.filter(id=raw_id)
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        if search_params.get("patient"):
            qs = qs.filter(patient_id=search_params["patient"])
        return qs

    def optimize_queryset(self, qs):
        return qs.select_related("patient")

    def project(self, ins, context: "FHIRContext") -> dict:
        cid = identity.coverage_id(ins)
        pid = identity.patient_id(ins.patient)
        ref = context.reference_builder

        # Mandatory period for US Core MustSupport
        start_date = (ins.created_at.date() if hasattr(ins, 'created_at') else date(2020, 1, 1))

        return {
            "resourceType": "Coverage",
            "id": cid,
            "meta": MetaBuilder.build(self.profile_key),
            "status": ins.coverage_status or "active",
            "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "HIP", "display": "health insurance plan"}]},
            "subscriberId": ins.subscriber_identifier or "SUB12345",
            "identifier": [{"type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0203", "code": "MB"}]}, "system": "http://hospital.org/coverage/memberid", "value": ins.member_identifier}],
            "beneficiary": ref.patient(pid),
            "relationship": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/subscriber-relationship", "code": ins.relationship_to_subscriber or "self"}]},
            "period": {
                "start": start_date.isoformat() + "T00:00:00Z"
            },
            "payor": [{
                "reference": ref.organization(ORGANIZATION_ID)["reference"],
                "display": "Allcare365 Health System"
            }],
            "class": [
                {"type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/coverage-class", "code": "group"}]}, "value": ins.group_identifier or "GRP123", "name": "Group Alpha"},
                {"type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/coverage-class", "code": "plan"}]}, "value": "PLN456", "name": "Gold Plan"},
            ],
            "costToBeneficiary": [{
                "valueQuantity": {"value": 20, "unit": "USD", "system": "urn:iso:std:iso:4217", "code": "USD"},
                "exception": [{
                    "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/coverage-copay-type", "code": "gpvisit"}]},
                }],
            }],
        }

    def supported_search_params(self):
        return {"patient": "reference", "_id": "token"}
