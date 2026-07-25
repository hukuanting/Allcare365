import math
import os

import pytest

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medical_system.settings")

import django

django.setup()

from services.disease_risk_engine.clinical_units import (
    canonical_unit_for,
    normalize_observation_quantity,
)


@pytest.mark.parametrize(
    ("field", "value", "unit", "expected", "canonical_unit"),
    [
        ("fasting_glucose", 5.5, "mmol/L", 99.085745, "mg/dL"),
        ("total_cholesterol", 5.0, "mmol/L", 193.3488, "mg/dL"),
        ("hdl_cholesterol", 1.2, "mmol/L", 46.403712, "mg/dL"),
        ("triglycerides", 2.0, "mmol/L", 177.14, "mg/dL"),
        ("creatinine", 88.4, "µmol/L", 1.0, "mg/dL"),
        ("albumin", 42.0, "g/L", 4.2, "g/dL"),
        ("body_height", 1.7, "m", 170.0, "cm"),
        ("waist_circumference", 0.9, "m", 90.0, "cm"),
        ("hip_circumference", 1.0, "m", 100.0, "cm"),
    ],
)
def test_proven_unit_conversions_are_deterministic(field, value, unit, expected, canonical_unit):
    quantity = normalize_observation_quantity(field, value, unit)

    assert quantity is not None
    assert quantity.value == pytest.approx(expected)
    assert quantity.normalized_unit == canonical_unit
    assert quantity.conversion != "identity"
    assert canonical_unit_for(field) == canonical_unit


@pytest.mark.parametrize(
    ("field", "value", "unit"),
    [
        ("fasting_glucose", 100, "kg"),
        ("fasting_glucose", 100, ""),
        ("systolic_bp", 120, "kPa"),
        ("systolic_bp", 120, None),
        ("body_height", 70, "in"),
        ("albumin", math.nan, "g/dL"),
        ("albumin", -1, "g/dL"),
    ],
)
def test_unknown_missing_incompatible_or_invalid_quantities_are_rejected(field, value, unit):
    assert normalize_observation_quantity(field, value, unit) is None


def test_registry_unit_is_the_canonical_output_when_contract_exists():
    assert canonical_unit_for("systolic_bp") == "mm[Hg]"
    assert canonical_unit_for("egfr") == "mL/min/{1.73_m2}"
    assert canonical_unit_for("platelet_count") == "10*9/L"


def test_ucum_count_per_week_is_accepted_for_alcohol_observation():
    normalized = normalize_observation_quantity("alcohol_drinks_per_week", 3, "1/wk")

    assert normalized is not None
    assert normalized.value == 3
