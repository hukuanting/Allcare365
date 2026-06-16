"""Provenance Projector - auto-generates FHIR Provenance for target resources."""
from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from ..meta_builder import MetaBuilder
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..uscore_templates import ORGANIZATION_ID

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


@ProjectorRegistry.register("Provenance")
class ProvenanceProjector(BaseProjector):
    resource_type = "Provenance"
    profile_key = "us-core-provenance"

    def query(self, patient_id, search_params, context):
        if search_params.get("_id"):
            prov_id = str(search_params["_id"])
            return self._find_targets_by_provenance_id(prov_id, context)
        if search_params.get("target"):
            target_id = str(search_params["target"]).split("/")[-1]
            return self._find_targets_by_id(target_id, context)
        return []

    def project(self, target_resource: dict, context: "FHIRContext") -> dict:
        ref = context.reference_builder
        target_type = target_resource.get("resourceType", "Unknown")
        target_id = target_resource.get("id", "unknown")
        provenance_id = self._provenance_id(target_type, target_id)
        recorded = target_resource.get("meta", {}).get(
            "lastUpdated",
            MetaBuilder.build(self.profile_key)["lastUpdated"],
        )

        return {
            "resourceType": "Provenance",
            "id": provenance_id,
            "meta": MetaBuilder.build(self.profile_key),
            "target": [{"reference": f"{target_type}/{target_id}"}],
            "recorded": recorded,
            "agent": [
                {
                    "type": {
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/provenance-participant-type",
                            "code": "author",
                            "display": "Author",
                        }]
                    },
                    "who": ref.organization(ORGANIZATION_ID),
                    "onBehalfOf": ref.organization(ORGANIZATION_ID),
                },
                {
                    "type": {
                        "coding": [{
                            "system": "http://hl7.org/fhir/us/core/CodeSystem/us-core-provenance-participant-type",
                            "code": "transmitter",
                            "display": "Transmitter",
                        }]
                    },
                    "who": ref.organization(ORGANIZATION_ID),
                    "onBehalfOf": ref.organization(ORGANIZATION_ID),
                },
            ],
            "entity": [{
                "role": "source",
                "what": {"reference": f"{target_type}/{target_id}"},
            }],
        }

    @staticmethod
    def for_resource(resource: dict, context: "FHIRContext") -> dict:
        projector = ProjectorRegistry.get("Provenance")
        return projector.project(resource, context)

    @staticmethod
    def _find_targets_by_id(target_id: str, context: "FHIRContext") -> list[dict]:
        matches = []
        for resource_type, projector in ProjectorRegistry.all_projectors().items():
            if resource_type == "Provenance":
                continue
            try:
                items = projector.query(
                    patient_id=None,
                    search_params={"_id": target_id},
                    context=context,
                )
                resources = projector.project_batch(items, context)
            except Exception:
                continue
            matches.extend(res for res in resources if str(res.get("id")) == target_id)
        return matches

    @classmethod
    def _find_targets_by_provenance_id(cls, provenance_id: str, context: "FHIRContext") -> list[dict]:
        matches = []
        for resource_type, projector in ProjectorRegistry.all_projectors().items():
            if resource_type == "Provenance":
                continue
            try:
                resources = projector.project_batch(
                    projector.query(patient_id=None, search_params={}, context=context),
                    context,
                )
            except Exception:
                continue
            matches.extend(
                res
                for res in resources
                if cls._provenance_id(res.get("resourceType", ""), res.get("id", "")) == provenance_id
            )
        return matches

    @staticmethod
    def _provenance_id(target_type: str, target_id: str) -> str:
        digest = hashlib.sha1(f"{target_type}/{target_id}".encode("utf-8")).hexdigest()[:24]
        type_prefix = "".join(ch for ch in str(target_type).lower() if ch.isalnum())[:8] or "resource"
        return f"prov-{type_prefix}-{digest}"

    def supported_search_params(self):
        return {"_id": "token", "target": "reference"}
