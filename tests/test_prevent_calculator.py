import os
import sys

import pytest


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medical_system.settings")

import django


django.setup()

from services.disease_risk_engine.clinical_math import calculate_egfr_2021
from services.disease_risk_engine.formula_catalog import PREVENT_MODEL_VERSION, calculate_prevent_risks


BASE_INPUT = {
    "age": 50,
    "sex": "F",
    "systolic_bp": 160,
    "anti_hypertensive_drugs": True,
    "total_cholesterol": 200,
    "hdl_cholesterol": 45,
    "statin_use": False,
    "has_diabetes": True,
    "is_smoker": False,
    "egfr": 90,
    "bmi": 35,
    "chd_history": False,
    "cvd_history": False,
    "pvd_history": False,
    "ascvd_history": False,
    "stroke_tia_history": False,
    "heart_failure_history": False,
}


@pytest.mark.parametrize(
    ("sex", "expected"),
    [
        ("F", [0.147, 0.092, 0.081]),
        ("M", [0.163, 0.102, 0.106]),
    ],
)
def test_prevent_base_equations_match_published_reference_values(sex, expected):
    data = {**BASE_INPUT, "sex": sex}
    results = calculate_prevent_risks(data)

    assert [round(result.score, 3) for result in results] == expected
    assert [result.model_version for result in results] == [PREVENT_MODEL_VERSION] * 3
    assert all(result.applicability == "applicable" for result in results)


def test_prevent_does_not_estimate_when_required_data_is_missing():
    results = calculate_prevent_risks({key: value for key, value in BASE_INPUT.items() if key != "egfr"})

    assert all(result.score is None for result in results)
    assert all(result.risk_percentage == "資料不足" for result in results)
    assert all(result.missing_data == ["egfr"] for result in results)


def test_prevent_does_not_clamp_or_estimate_outside_validated_population():
    results = calculate_prevent_risks({**BASE_INPUT, "age": 80})

    assert all(result.score is None for result in results)
    assert all(result.risk_percentage == "不適用" for result in results)
    assert all(result.risk_level == "not_applicable" for result in results)
    assert all(result.limitations for result in results)


def test_prevent_treats_unknown_sex_as_missing_instead_of_a_reference_category():
    results = calculate_prevent_risks({**BASE_INPUT, "sex": "U"})

    assert all(result.score is None for result in results)
    assert all(result.missing_data == ["sex"] for result in results)


def test_prevent_treats_invalid_required_boolean_as_missing_not_false():
    results = calculate_prevent_risks({**BASE_INPUT, "has_diabetes": "false"})

    assert all(result.score is None for result in results)
    assert all(result.missing_data == ["has_diabetes"] for result in results)


def test_ckd_epi_2021_egfr_is_deterministic_and_race_free():
    assert calculate_egfr_2021(1.0, 50, "F") == 69.0
    assert calculate_egfr_2021(1.0, 50, "M") == 92.0
