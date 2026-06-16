"""
FHIR Bundle Builder — Assembles search results into a valid FHIR Bundle.

Handles: fullUrl, entry ordering, search.mode, link.self, pagination cursor.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .fhir_context import FHIRContext


class FHIRBundleBuilder:
    """
    Build a FHIR ``searchset`` Bundle from projected resources.

    Usage::

        builder = FHIRBundleBuilder(context)
        bundle = builder.build_searchset(
            primary_resources=resources,
            included_resources=includes,
            total=len(resources),
        )
    """

    def __init__(self, context: "FHIRContext"):
        self.context = context

    def build_searchset(
        self,
        primary_resources: List[dict],
        included_resources: Optional[List[dict]] = None,
        total: Optional[int] = None,
        request_url: str = "",
    ) -> dict:
        """
        Assemble a complete FHIR searchset Bundle.

        Parameters
        ----------
        primary_resources : list[dict]
            Resources matching the search (search.mode = "match").
        included_resources : list[dict], optional
            Resources from _include / _revinclude (search.mode = "include").
        total : int, optional
            Total count. Defaults to len(primary_resources).
        request_url : str
            The original request URL for ``link.self``.
        """
        entries = []

        # Primary results
        for r in primary_resources:
            entries.append(self._make_entry(r, mode="match"))

        # Included resources
        for r in (included_resources or []):
            entries.append(self._make_entry(r, mode="include"))

        bundle = {
            "resourceType": "Bundle",
            "id": str(uuid.uuid4()),
            "type": "searchset",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total": total if total is not None else len(primary_resources),
            "entry": entries,
        }

        # link.self
        if request_url:
            bundle["link"] = [{"relation": "self", "url": request_url}]

        return bundle

    def build_read_response(self, resource: dict) -> dict:
        """Wrap a single resource read (no Bundle, just the resource)."""
        return resource

    def _make_entry(self, resource: dict, mode: str = "match") -> dict:
        """Create a Bundle entry with fullUrl and search.mode."""
        resource_type = resource.get("resourceType", "Unknown")
        resource_id = resource.get("id", "unknown")
        ref_builder = self.context.reference_builder
        full_url = ref_builder.full_url(resource_type, resource_id)

        return {
            "fullUrl": full_url,
            "resource": resource,
            "search": {"mode": mode},
        }
