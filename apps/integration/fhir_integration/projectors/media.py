"""Media projection boundary.

There is no persisted media model in the relational clinical schema.  An
empty result is preferable to inventing a payload or a dangling reference.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..projectors.base import BaseProjector
from ..projectors.registry import ProjectorRegistry

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext


@ProjectorRegistry.register("Media")
class MediaProjector(BaseProjector):
    resource_type = "Media"
    profile_key = ""

    def query(self, patient_id, search_params, context):
        return []

    def project_batch(self, queryset_or_list, context):
        return []

    def project(self, instance, context: "FHIRContext") -> None:
        return None

    def supported_search_params(self):
        return {"_id": "token"}
