"""
Projector Registry — Decorator-based auto-discovery.

Every projector file registers itself with:

    @ProjectorRegistry.register("Observation")
    class ObservationProjector(BaseProjector):
        ...

Views simply call ``ProjectorRegistry.get("Observation")``.
Adding a new resource type = one new file + one decorator. Zero view changes.
"""
from __future__ import annotations

from typing import Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseProjector


class ProjectorRegistry:
    """Singleton registry mapping FHIR resource type name → Projector instance."""

    _registry: Dict[str, "BaseProjector"] = {}

    @classmethod
    def register(cls, resource_type: str):
        """
        Class decorator.  Usage::

            @ProjectorRegistry.register("Patient")
            class PatientProjector(BaseProjector):
                ...
        """
        def decorator(projector_cls):
            cls._registry[resource_type] = projector_cls()
            return projector_cls
        return decorator

    @classmethod
    def get(cls, resource_type: str) -> "BaseProjector":
        """Return the projector for *resource_type*; raise KeyError if none."""
        try:
            return cls._registry[resource_type]
        except KeyError:
            raise KeyError(
                f"No projector registered for resource type {resource_type!r}. "
                f"Available: {sorted(cls._registry.keys())}"
            )

    @classmethod
    def has(cls, resource_type: str) -> bool:
        return resource_type in cls._registry

    @classmethod
    def all_types(cls) -> list[str]:
        """Return sorted list of all registered FHIR resource types."""
        return sorted(cls._registry.keys())

    @classmethod
    def all_projectors(cls) -> Dict[str, "BaseProjector"]:
        """Return the full registry dict (for CapabilityStatement generation)."""
        return dict(cls._registry)
