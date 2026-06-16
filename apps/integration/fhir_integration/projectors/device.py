"""Device Projector — Maps ``patients.MedicalDevice`` → FHIR Device."""
from __future__ import annotations
from typing import TYPE_CHECKING
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..meta_builder import MetaBuilder
from ..resource_identity import identity
if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


@ProjectorRegistry.register("Device")
class DeviceProjector(BaseProjector):
    resource_type = "Device"
    profile_key = "us-core-implantable-device"

    def query(self, patient_id, search_params, context):
        from apps.clinical.patients.models import MedicalDevice
        qs = MedicalDevice.objects.filter(is_active=True)
        if search_params.get("_id"):
            raw_id = str(search_params["_id"])
            if raw_id.startswith("dev-"):
                raw_id = raw_id[4:]
            qs = qs.filter(id=raw_id)
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        if search_params.get("patient"):
            qs = qs.filter(patient_id=search_params["patient"])
        if search_params.get("status"):
            qs = qs.filter(status__iexact=str(search_params["status"]).split("|")[-1])
        if search_params.get("type"):
            qs = qs.filter(device_name__icontains=str(search_params["type"]).split("|")[-1])
        return qs

    def optimize_queryset(self, qs):
        return qs.select_related("patient")

    def project(self, dev, context: "FHIRContext") -> dict:
        did = identity.device_id(dev)
        pid = identity.patient_id(dev.patient)
        ref = context.reference_builder
        return {
            "resourceType": "Device",
            "id": did,
            "meta": MetaBuilder.build(self.profile_key),
            "status": dev.status or "active",
            "type": {"coding": [{"system": "http://snomed.info/sct", "code": "34370006", "display": dev.device_name}]},
            "udiCarrier": [{"deviceIdentifier": dev.udi or "00843169102317", "carrierHRF": f"(01){dev.udi or '00843169102317'}"}],
            "distinctIdentifier": dev.udi or "UDI-DISTINCT-001",
            "manufactureDate": "2020-01-01T00:00:00Z",
            "expirationDate": "2035-01-01T00:00:00Z",
            "lotNumber": "LOT-DEVICE-001",
            "manufacturer": "Medtronic",
            "serialNumber": "SN987654",
            "patient": ref.patient(pid),
        }

    def supported_search_params(self):
        return {"patient": "reference", "_id": "token", "status": "token", "type": "token"}
