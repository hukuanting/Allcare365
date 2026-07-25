"""Expose only Provenance resources persisted in the FHIR store."""
from __future__ import annotations

import copy
from typing import TYPE_CHECKING

from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..resource_identity import identity

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


@ProjectorRegistry.register("Provenance")
class ProvenanceProjector(BaseProjector):
    resource_type = "Provenance"
    profile_key = "us-core-provenance"

    def query(self, patient_id, search_params, context):
        from ..models import FHIRResource, FHIRResourceMapping

        qs = FHIRResource.objects.filter(resource_type="Provenance", is_active=True)
        if search_params.get("_id"):
            resource_id = str(search_params["_id"]).rstrip("/").split("/")[-1]
            qs = qs.filter(resource_id=resource_id)

        allowed_resource_pks = None
        direct_patient_reference = None
        if patient_id:
            resolved_patient_id = identity.resolve_patient_db_id(str(patient_id))
            if resolved_patient_id is None:
                return []
            allowed_resource_pks = set(
                FHIRResourceMapping.objects.filter(
                    patient_id=resolved_patient_id,
                    fhir_resource_ref__resource_type="Provenance",
                    fhir_resource_ref__is_active=True,
                ).values_list("fhir_resource_ref_id", flat=True)
            )
            from apps.clinical.patients.models import Patient

            patient = Patient.objects.filter(id=resolved_patient_id, is_active=True).first()
            if patient is None:
                return []
            direct_patient_reference = f"Patient/{identity.patient_id(patient)}"

        requested_target = str(search_params.get("target", "")).strip()
        requested_target_tail = requested_target.rstrip("/").split("/")[-1] if requested_target else ""
        rows = []
        for row in qs.order_by("resource_id"):
            targets = self._target_references(row.resource_data)
            if requested_target and not any(
                target == requested_target
                or target.rstrip("/").split("/")[-1] == requested_target_tail
                for target in targets
            ):
                continue
            if allowed_resource_pks is not None:
                mapped = row.pk in allowed_resource_pks
                directly_targets_patient = direct_patient_reference in targets
                if not mapped and not directly_targets_patient:
                    continue
            rows.append(row)
        return rows

    def project(self, persisted, context: "FHIRContext") -> dict | None:
        data = copy.deepcopy(getattr(persisted, "resource_data", None))
        if not isinstance(data, dict):
            return None
        if data.get("resourceType") not in (None, "Provenance"):
            return None

        resource_id = str(getattr(persisted, "resource_id", "") or data.get("id", "")).strip()
        if not resource_id:
            return None
        data["resourceType"] = "Provenance"
        data["id"] = resource_id
        if not self._target_references(data) or not data.get("recorded") or not data.get("agent"):
            return None
        return data

    @classmethod
    def for_resource(cls, resource: dict, context: "FHIRContext") -> dict | None:
        if not isinstance(resource, dict) or not resource.get("resourceType") or not resource.get("id"):
            return None
        target = f"{resource['resourceType']}/{resource['id']}"
        projector = ProjectorRegistry.get("Provenance")
        rows = projector.query(getattr(context, "patient_id", None), {"target": target}, context)
        projected = projector.project_batch(rows, context)
        return projected[0] if len(projected) == 1 else None

    @staticmethod
    def _target_references(resource_data) -> list[str]:
        if not isinstance(resource_data, dict):
            return []
        references = []
        for target in resource_data.get("target", []):
            if isinstance(target, dict) and isinstance(target.get("reference"), str):
                reference = target["reference"].strip()
                if reference:
                    references.append(reference)
        return references

    def supported_search_params(self):
        return {"_id": "token", "target": "reference"}
