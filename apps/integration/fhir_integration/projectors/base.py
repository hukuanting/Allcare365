"""
Base Projector — Abstract base class for all FHIR Resource Projectors.

Implements the Projection Pipeline:

    query() → optimize_queryset() → project_batch()
                                        ├─ normalize()
                                        ├─ project()
                                        ├─ apply_profiles()
                                        └─ apply_extensions()

Every concrete projector overrides the abstract methods it needs.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from django.db.models import QuerySet

if TYPE_CHECKING:
    from ..fhir_context import FHIRContext

from ..projection_contracts import get_projection_contract
from ..reference_resolution import ProjectionContractValidator


_contract_validator = ProjectionContractValidator()
logger = logging.getLogger("medical_system")


class BaseProjector(ABC):
    """
    Abstract base for resource-type-based projectors.

    Subclasses MUST implement:
        - ``resource_type``  (class attribute)
        - ``project(instance, context) -> dict``

    Subclasses SHOULD override:
        - ``query(patient_id, search_params, context) -> QuerySet``
        - ``optimize_queryset(qs) -> QuerySet``
        - ``supported_search_params() -> dict``

    Subclasses MAY override:
        - ``normalize(instance) -> Any``
        - ``apply_extensions(resource, instance, context) -> dict``
    """

    # ── Class-level metadata (override in subclasses) ────────

    resource_type: str = ""  # e.g. "Observation", "Condition"
    profile_key: str = ""    # e.g. "us-core-vital-signs", used by MetaBuilder

    # ── Query Phase ──────────────────────────────────────────

    def query(
        self,
        patient_id: Optional[str],
        search_params: Dict[str, Any],
        context: "FHIRContext",
    ) -> QuerySet:
        """
        Translate FHIR search parameters into a Django QuerySet.

        Override in each projector to map FHIR param names to ORM fields.
        Default implementation returns an empty queryset.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__}.query() must be implemented"
        )

    def optimize_queryset(self, qs: QuerySet) -> QuerySet:
        """
        Hook for adding ``select_related()``, ``prefetch_related()``,
        or annotations to avoid N+1 queries.

        Default: pass-through (no optimization).
        Override in projectors that touch related tables.
        """
        return qs

    # ── Projection Pipeline ──────────────────────────────────

    def project_batch(
        self,
        queryset: QuerySet,
        context: "FHIRContext",
    ) -> List[dict]:
        """
        Full pipeline: optimize → iterate → normalize → project → extensions.

        Returns a list of FHIR resource dicts ready for BundleBuilder.
        """
        optimized = self.optimize_queryset(queryset)
        results = []
        contract = get_projection_contract(self.resource_type)
        for instance in optimized:
            normalized = self.normalize(instance)
            resource = self.project(normalized, context)
            resource = self.apply_extensions(resource, normalized, context)
            if contract is not None:
                try:
                    _contract_validator.validate(resource, context, contract)
                except ValueError as exc:
                    logger.warning(
                        "Projection contract warning for %s/%s: %s",
                        self.resource_type,
                        resource.get("id"),
                        exc,
                    )
            results.append(resource)
        return results

    def normalize(self, instance: Any) -> Any:
        """
        Optional data normalization before projection.
        Override to unify different source models into a common shape.
        Default: pass-through.
        """
        return instance

    @abstractmethod
    def project(self, instance: Any, context: "FHIRContext") -> dict:
        """
        Map a single ORM instance to a FHIR resource dict.
        This is the core mapping logic every projector MUST implement.
        """
        ...

    def apply_extensions(
        self,
        resource: dict,
        instance: Any,
        context: "FHIRContext",
    ) -> dict:
        """
        Inject FHIR extensions into the resource after base projection.
        Override to add US Core extensions (e.g., medication adherence).
        Default: no-op.
        """
        return resource

    # ── Metadata for CapabilityStatement / Search ────────────

    def supported_search_params(self) -> Dict[str, str]:
        """
        Return a dict of ``{fhir_param_name: type}`` supported by this projector.
        Used by CapabilityStatement generator and search parameter validation.

        Example::

            {"patient": "reference", "code": "token", "date": "date"}
        """
        return {}

    def supported_includes(self) -> List[str]:
        """
        Return list of supported ``_include`` values.
        Example: ``["MedicationRequest:medication"]``
        """
        return []

    def supported_rev_includes(self) -> List[str]:
        """
        Return list of supported ``_revinclude`` values.
        Example: ``["Provenance:target"]``
        """
        return []

    def projection_contract(self):
        return get_projection_contract(self.resource_type)
