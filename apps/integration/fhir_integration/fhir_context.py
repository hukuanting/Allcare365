"""
FHIR Context — Request-scoped state container.

Passed to every projector call so they have access to:
  - base_url (for fullUrl / absolute references)
  - patient scope
  - _include / _revinclude tracking
  - shared services (terminology, reference builder, identity)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple

if TYPE_CHECKING:
    from django.http import HttpRequest

from .terminology import TerminologyService
from .resource_identity import ResourceIdentityService, identity as _default_identity


class IncludeTracker:
    """
    Lazy collector for _include / _revinclude resources.

    During projection, projectors call ``tracker.add(resource_type, resource_id)``
    to register references that need to be included in the Bundle.
    The BundleBuilder resolves them all at the end — preventing recursive explosion.
    """

    def __init__(self):
        self._pending: List[Tuple[str, str]] = []  # (resource_type, resource_id)
        self._resolved: List[dict] = []

    def add(self, resource_type: str, resource_id: str) -> None:
        """Register a resource for lazy inclusion."""
        self._pending.append((resource_type, resource_id))

    @property
    def pending(self) -> List[Tuple[str, str]]:
        return list(self._pending)

    @property
    def resolved(self) -> List[dict]:
        return self._resolved

    def mark_resolved(self, resources: List[dict]) -> None:
        """Called by IncludeResolver after batch-resolving all pending items."""
        self._resolved = resources
        self._pending.clear()


@dataclass
class FHIRContext:
    """
    Immutable-ish context object threaded through the projection pipeline.

    Created once per HTTP request in the view layer.
    """

    # ── Request info ─────────────────────────────────────────
    base_url: str = ""
    patient_id: Optional[str] = None
    request: Optional["HttpRequest"] = None

    # ── Include tracking ─────────────────────────────────────
    includes: Set[str] = field(default_factory=set)       # e.g. {"MedicationRequest:medication"}
    rev_includes: Set[str] = field(default_factory=set)   # e.g. {"Provenance:target"}
    include_tracker: IncludeTracker = field(default_factory=IncludeTracker)

    # ── Shared services ──────────────────────────────────────
    terminology: TerminologyService = field(default_factory=TerminologyService)
    identity: ResourceIdentityService = field(default_factory=lambda: _default_identity)

    # ── Convenience helpers built from services ──────────────
    # reference_builder is injected after construction (circular dep avoidance)
    _reference_builder: object = field(default=None, repr=False)

    @property
    def reference_builder(self):
        if self._reference_builder is None:
            from .reference_builder import ReferenceBuilder
            self._reference_builder = ReferenceBuilder(self.base_url)
        return self._reference_builder

    # ── Factory ──────────────────────────────────────────────

    @classmethod
    def from_request(cls, request, patient_id: Optional[str] = None) -> "FHIRContext":
        """Build a FHIRContext from a Django HttpRequest."""
        base_url = ""
        if hasattr(request, "build_absolute_uri"):
            base_url = request.build_absolute_uri("/").rstrip("/")

        # Parse _include and _revinclude from query params
        includes: Set[str] = set()
        rev_includes: Set[str] = set()
        
        # Handle both list (standard) and single values if provided manually
        def get_list(key):
            if hasattr(request, "GET"):
                return request.GET.getlist(key, [])
            return []

        for val in get_list("_include"):
            for token in val.split(","):
                includes.add(token.strip())
        for val in get_list("_revinclude"):
            for token in val.split(","):
                rev_includes.add(token.strip())

        return cls(
            base_url=base_url,
            patient_id=patient_id,
            request=request,
            includes=includes,
            rev_includes=rev_includes,
        )
