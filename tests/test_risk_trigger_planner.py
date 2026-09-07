from services.disease_risk_engine.algorithm_registry import RUNTIME_ALGORITHMS
from services.disease_risk_engine.trigger_planner import (
    RiskRefreshPlanner,
    plan_runtime_refresh,
)


def test_refresh_planner_returns_only_algorithms_dependent_on_changed_inputs():
    changed = {"systolic_bp", "heart_rate"}
    expected = tuple(
        item.algorithm_id
        for item in RUNTIME_ALGORITHMS
        if item.runtime_enabled and changed.intersection(item.required_inputs)
    )

    plan = plan_runtime_refresh(["heart_rate", "systolic_bp", "heart_rate"])

    assert plan.changed_inputs == ("heart_rate", "systolic_bp")
    assert plan.affected_algorithm_ids == expected
    assert len(plan.affected_algorithm_ids) == len(set(plan.affected_algorithm_ids))
    assert plan.has_work is bool(expected)


def test_refresh_planner_exposes_unknown_canonical_inputs_without_scheduling_work():
    planner = RiskRefreshPlanner()

    plan = planner.plan(["unmapped-sotera-channel"])

    assert plan.unknown_inputs == ("unmapped-sotera-channel",)
    assert plan.affected_algorithm_ids == ()
    assert plan.has_work is False
