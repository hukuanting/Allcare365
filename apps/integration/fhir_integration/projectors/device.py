"""Project persisted implantable-device facts without synthetic UDI details."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..meta_builder import MetaBuilder
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..resource_identity import identity

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


FHIR_DEVICE_STATUSES = {"active", "inactive", "entered-in-error", "unknown"}


@ProjectorRegistry.register("Device")
class DeviceProjector(BaseProjector):
    resource_type = "Device"
    profile_key = "us-core-implantable-device"

    def query(self, patient_id, search_params, context):
        from apps.clinical.patients.models import MedicalDevice

        qs = MedicalDevice.objects.filter(is_active=True).select_related("patient")
        if search_params.get("_id"):
            raw_id = str(search_params["_id"]).rstrip("/").split("/")[-1]
            if not raw_id.startswith("dev-"):
                return qs.none()
            qs = qs.filter(id=raw_id[4:])
        patient_scope = patient_id or search_params.get("patient")
        if patient_scope:
            resolved = identity.resolve_patient_db_id(str(patient_scope))
            if resolved is None:
                return qs.none()
            qs = qs.filter(patient_id=resolved)
        if search_params.get("status"):
            qs = qs.filter(status__iexact=str(search_params["status"]).split("|")[-1])
        if search_params.get("type"):
            qs = qs.filter(device_name__icontains=str(search_params["type"]).split("|")[-1])
        return qs

    def project(self, device, context: "FHIRContext") -> dict | None:
        name = (device.device_name or "").strip()
        udi = (device.udi or "").strip()
        status = (device.status or "").strip().casefold()
        if not name or not udi or status not in FHIR_DEVICE_STATUSES:
            return None
        return {
            "resourceType": "Device",
            "id": identity.device_id(device),
            "meta": MetaBuilder.build(self.profile_key),
            "status": status,
            "type": {"text": name},
            "udiCarrier": [{"deviceIdentifier": udi}],
            "patient": context.reference_builder.patient(identity.patient_id(device.patient)),
        }

    def supported_search_params(self):
        return {"patient": "reference", "_id": "token", "status": "token", "type": "token"}
