"""Typed execution adapter for complete equations from the expert collection."""
import math
from .expert_sources import DEFINITIONS


def calculate_source_model(algorithm_id, data):
    from .algorithm_registry import runtime_registry
    from .formula_catalog import DiseaseRiskResult
    definition = next(item for item in DEFINITIONS if item["id"] == algorithm_id)
    registry = runtime_registry()
    metadata = registry.get_runtime(algorithm_id)
    validated = registry.validate_required_inputs(algorithm_id, data)
    inputs = dict(validated.values)
    missing = list(validated.missing_fields)
    score = None
    components = {}
    applicability = "applicable"
    limitations = list(definition.get("limitations", ()))
    if not missing:
        try:
            calculated = definition["calculator"](inputs)
            components = calculated.get("components", {}) if isinstance(calculated, dict) else {}
            score = float(calculated["score"] if isinstance(calculated, dict) else calculated)
            if not math.isfinite(score):
                raise ValueError("The equation returned a non-finite value")
            if definition.get("probability") and not 0 <= score <= 1:
                raise ValueError("Probability falls outside [0, 1]")
        except (ValueError, OverflowError, ZeroDivisionError) as exc:
            score = None
            applicability = "not_applicable"
            limitations.append(str(exc))
    display = "資料不足" if missing else "不適用" if score is None else (
        f"{score*100:.2f}%" if definition.get("probability") else f"{score:.3f}"
    )
    if score is not None and not definition.get("probability") and metadata.output_unit != "1":
        display += f" {metadata.output_unit}"
    # No shared arbitrary disease thresholds are assigned to derived measures.
    level, category = "informational", "已計算"
    if score is not None and definition.get("interpret"):
        level, category = definition["interpret"](score)
    return DiseaseRiskResult(
        algorithm_key=algorithm_id, outcome_key=metadata.outcome_key,
        algorithm_name=metadata.display_name, score=score,
        risk_percentage=display, risk_level=level, risk_category=category,
        missing_data=missing,
        evidence={"inputs": inputs, "source_document": metadata.source_label,
                  "reference": metadata.method_uri, "time_horizon": metadata.time_horizon,
                  "components": components, "output_unit": metadata.output_unit, "source_acceptance": metadata.source_acceptance},
        recommendation_text="補齊必要資料後重新計算。" if missing else "依模型適用族群與臨床資料判讀。",
        model_version=metadata.model_version, method_uri=metadata.method_uri,
        applicability=applicability, limitations=limitations,
    )
