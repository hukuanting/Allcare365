"""Dependency-only planning for event-driven risk refreshes.

This module decides which governed runtime algorithms *may* need a refresh
after canonical clinical inputs change.  It deliberately does not dispatch
jobs, bypass data-quality checks, or emit alarms; those responsibilities need
an idempotent outbox, debounce policy, freshness policy, and clinical alert
governance at the application boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Iterable, Mapping

from .algorithm_registry import (
    CLINICAL_VARIABLES,
    RUNTIME_ALGORITHMS,
    RuntimeAlgorithmMetadata,
)


@dataclass(frozen=True, slots=True)
class RiskRefreshPlan:
    changed_inputs: tuple[str, ...]
    affected_algorithm_ids: tuple[str, ...]
    unknown_inputs: tuple[str, ...]

    @property
    def has_work(self) -> bool:
        return bool(self.affected_algorithm_ids)

    def to_dict(self) -> dict[str, object]:
        return {
            "changed_inputs": list(self.changed_inputs),
            "affected_algorithm_ids": list(self.affected_algorithm_ids),
            "unknown_inputs": list(self.unknown_inputs),
        }


class RiskRefreshPlanner:
    """Immutable reverse dependency index over runtime-approved algorithms."""

    def __init__(
        self,
        algorithms: tuple[RuntimeAlgorithmMetadata, ...] = RUNTIME_ALGORITHMS,
    ) -> None:
        enabled = tuple(item for item in algorithms if item.runtime_enabled)
        dependencies: dict[str, list[str]] = {}
        for algorithm in enabled:
            for field in algorithm.required_inputs:
                dependencies.setdefault(field, []).append(algorithm.algorithm_id)
        self._algorithm_order = {
            algorithm.algorithm_id: position
            for position, algorithm in enumerate(enabled)
        }
        self._dependencies: Mapping[str, tuple[str, ...]] = MappingProxyType(
            {field: tuple(ids) for field, ids in dependencies.items()}
        )

    @property
    def dependency_index(self) -> Mapping[str, tuple[str, ...]]:
        return self._dependencies

    def plan(self, changed_inputs: Iterable[str]) -> RiskRefreshPlan:
        normalized = tuple(
            dict.fromkeys(
                str(field).strip()
                for field in changed_inputs
                if str(field).strip()
            )
        )
        unknown = tuple(
            field for field in normalized if field not in CLINICAL_VARIABLES
        )
        affected = {
            algorithm_id
            for field in normalized
            for algorithm_id in self._dependencies.get(field, ())
        }
        ordered = tuple(
            sorted(affected, key=self._algorithm_order.__getitem__)
        )
        return RiskRefreshPlan(
            changed_inputs=normalized,
            affected_algorithm_ids=ordered,
            unknown_inputs=unknown,
        )


_DEFAULT_REFRESH_PLANNER = RiskRefreshPlanner()


def plan_runtime_refresh(changed_inputs: Iterable[str]) -> RiskRefreshPlan:
    return _DEFAULT_REFRESH_PLANNER.plan(changed_inputs)


__all__ = [
    "RiskRefreshPlan",
    "RiskRefreshPlanner",
    "plan_runtime_refresh",
]
