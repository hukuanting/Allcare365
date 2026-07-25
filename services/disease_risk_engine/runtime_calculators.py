"""Registry-locked execution plan for governed disease-risk calculators.

Metadata and executable functions intentionally remain separate trust
boundaries.  This module is the single composition point and verifies at
import time and at execution time that every enabled algorithm is produced
exactly once.  Disabled catalog entries are represented by explicit governance
cards; their formulas are never called.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from .algorithm_registry import CatalogInvariantError, runtime_registry
from .formula_catalog import (
    DiseaseRiskResult,
    FORMULA_CALCULATION_STEPS,
    FormulaCalculationStep,
)


# Public compatibility name for callers that inspect the execution plan. The
# authoritative bindings now live beside all executable formulas.
RuntimeCalculationStep = FormulaCalculationStep
RUNTIME_CALCULATION_STEPS = FORMULA_CALCULATION_STEPS


def _catalog_algorithm_ids() -> Tuple[str, ...]:
    return tuple(item.algorithm_id for item in runtime_registry().runtime_algorithms)


def _executable_algorithm_ids() -> Tuple[str, ...]:
    return tuple(
        item.algorithm_id
        for item in runtime_registry().runtime_algorithms
        if item.runtime_enabled
    )


def _declared_algorithm_ids() -> Tuple[str, ...]:
    return tuple(
        algorithm_id
        for step in RUNTIME_CALCULATION_STEPS
        for algorithm_id in step.algorithm_ids
    )


if _declared_algorithm_ids() != _executable_algorithm_ids():
    raise CatalogInvariantError(
        "Runtime calculation plan must match the executable algorithm registry exactly"
    )


def calculate_runtime_risks(data: Dict[str, Any]) -> list[DiseaseRiskResult]:
    results: list[DiseaseRiskResult] = []
    for step in RUNTIME_CALCULATION_STEPS:
        calculated = step.calculator(data)
        step_results = [calculated] if isinstance(calculated, DiseaseRiskResult) else list(calculated)
        returned_ids = tuple(result.algorithm_key for result in step_results)
        if returned_ids != step.algorithm_ids:
            raise CatalogInvariantError(
                f"Runtime calculator returned {returned_ids!r}; expected {step.algorithm_ids!r}"
            )
        results.extend(step_results)

    returned_ids = tuple(result.algorithm_key for result in results)
    if returned_ids != _executable_algorithm_ids():
        raise CatalogInvariantError("Runtime calculation did not produce every enabled algorithm exactly once")
    return results


def calculate_catalog_risks(data: Dict[str, Any]) -> list[DiseaseRiskResult]:
    """Return every product catalog entry without executing a gated formula."""

    calculated = {result.algorithm_key: result for result in calculate_runtime_risks(data)}
    results: list[DiseaseRiskResult] = []
    for metadata in runtime_registry().runtime_algorithms:
        if metadata.runtime_enabled:
            result = calculated.get(metadata.algorithm_id)
            if result is None:
                raise CatalogInvariantError(
                    f"Enabled algorithm {metadata.algorithm_id!r} produced no result"
                )
            results.append(result)
            continue

        results.append(
            DiseaseRiskResult(
                algorithm_key=metadata.algorithm_id,
                outcome_key=metadata.outcome_key,
                algorithm_name=metadata.display_name,
                score=None,
                risk_percentage="待臨床審核",
                risk_level="review_required",
                risk_category="尚未啟用",
                missing_data=[],
                evidence={"calculation_executed": False},
                recommendation_text="此模型尚未通過醫院端臨床治理審核，系統未執行公式或產生風險分數。",
                model_version=metadata.model_version,
                method_uri=metadata.method_uri,
                applicability="clinical_review_required",
                limitations=[metadata.clinical_review_reason] if metadata.clinical_review_reason else [],
            )
        )

    returned_ids = tuple(result.algorithm_key for result in results)
    if returned_ids != _catalog_algorithm_ids():
        raise CatalogInvariantError("Catalog response did not represent every algorithm exactly once")
    return results


__all__ = [
    "RUNTIME_CALCULATION_STEPS",
    "RuntimeCalculationStep",
    "calculate_catalog_risks",
    "calculate_runtime_risks",
]
