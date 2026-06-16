"""Minimal Media projector to support DiagnosticReport.media.link references."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..meta_builder import MetaBuilder
from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry
from ..uscore_templates import MEDIA_ID

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


@ProjectorRegistry.register("Media")
class MediaProjector(BaseProjector):
    resource_type = "Media"
    profile_key = "us-core-documentreference"

    def query(self, patient_id, search_params, context):
        media_id = str(search_params.get("_id", MEDIA_ID))
        if media_id not in {MEDIA_ID}:
            return []
        return [media_id]

    def project_batch(self, queryset_or_list, context):
        return [self.project(item, context) for item in queryset_or_list]

    def project(self, media_id, context: "FHIRContext") -> dict:
        return {
            "resourceType": "Media",
            "id": media_id if isinstance(media_id, str) else MEDIA_ID,
            "status": "completed",
            "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/media-type", "code": "image"}]},
            "content": {"contentType": "text/plain", "data": "bWVkaWE="},
        }

    def supported_search_params(self):
        return {"_id": "token"}
