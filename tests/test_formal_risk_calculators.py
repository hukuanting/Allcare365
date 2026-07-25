import math

import pytest

from services.disease_risk_engine.algorithm_registry import (
    FHIRResultType,
    RUNTIME_ALGORITHMS,
    public_algorithm_catalog,
)
from services.disease_risk_engine.formula_catalog import (
    FORMULA_CALCULATION_STEPS,
    calculate_apri,
    calculate_dementia,
    calculate_fli,
    calculate_framingham_bmi,
    calculate_framingham_lipids,
    calculate_hsi,
    calculate_incident_steatosis,
    calculate_lfs,
    calculate_mayo,
    calculate_quicki,
)


def test_all_hospital_approved_algorithms_have_one_formula_binding():
    formula_ids = [
        algorithm_id
        for step in FORMULA_CALCULATION_STEPS
        for algorithm_id in step.algorithm_ids
    ]
    runtime_ids = [metadata.algorithm_id for metadata in RUNTIME_ALGORITHMS]
    assert formula_ids == runtime_ids
    assert len(formula_ids) == len(set(formula_ids)) == 42


def test_public_catalog_has_no_stale_review_cards_or_blocked_conflicts():
    catalog = public_algorithm_catalog()
    visible = {
        item["algorithm_id"]
        for group in catalog["systems"]
        for item in group["algorithms"]
    }
    assert catalog["counts"]["executable_models"] == 42
    assert catalog["counts"]["review_candidate_models"] == 0
    assert not {"new_zealand_dcs_cvd", "hunt_lung_cancer_6y", "china_nonobese_nafld_1y"} & visible


def test_formula_corrections_are_locked_by_vectors():
    hsi = calculate_hsi({"alt_gpt": 40, "ast_got": 20, "bmi": 25, "has_diabetes": True, "sex": "F"})
    assert hsi.score == 45

    fli = calculate_fli({"triglycerides": 150, "bmi": 28, "ggt": 50, "waist_circumference": 95})
    lp = .953 * math.log(150) + .139 * 28 + .718 * math.log(50) + .053 * 95 - 15.745
    assert fli.score == pytest.approx(100 * math.exp(lp) / (1 + math.exp(lp)))

    apri = calculate_apri({"ast_got": 80, "ast_uln": 40, "platelet_count": 100})
    assert apri.score == 2

    quicki = calculate_quicki({"insulin": 10, "fasting_glucose": 100})
    assert quicki.score == pytest.approx(1 / 3)


def test_published_verification_vectors_match():
    assert calculate_incident_steatosis({
        "sex": "M", "age": 33, "bmi": 35, "alcohol_drinks_per_week": 8, "triglycerides": 187,
    }).score == pytest.approx(0.3447787630795083)
    assert calculate_framingham_bmi({
        "sex": "F", "age": 30, "systolic_bp": 125, "anti_hypertensive_drugs": False,
        "bmi": 22.5, "is_smoker": False, "has_diabetes": False,
    }).score == pytest.approx(0.0108011676768296)
    assert calculate_framingham_lipids({
        "sex": "M", "age": 60, "systolic_bp": 118, "anti_hypertensive_drugs": False,
        "total_cholesterol": 149, "hdl_cholesterol": 40, "is_smoker": False, "has_diabetes": False,
    }).score == pytest.approx(0.106314054050157)


def test_nonpositive_log_or_denominator_inputs_are_never_executed():
    assert calculate_quicki({"insulin": 0, "fasting_glucose": 100}).missing_data == ["insulin"]
    assert calculate_apri({"ast_got": 80, "ast_uln": 0, "platelet_count": 100}).missing_data == ["ast_uln"]


def test_dementia_uses_positive_hypertension_coefficient_not_antihypertensive_proxy():
    base = {
        "age": 65, "bmi": 27.5, "sex": "M", "evaluation_year": 2026,
        "deprivation_quintile": 1, "is_smoker": False, "former_smoker": False,
        "heavy_alcohol": False, "depression_or_antidepressant": False, "aspirin_use": False,
        "stroke_tia_history": False, "atrial_fibrillation": False, "has_diabetes": False,
    }
    without_hypertension = calculate_dementia({**base, "has_hypertension": False})
    with_hypertension = calculate_dementia({**base, "has_hypertension": True})
    assert with_hypertension.score > without_hypertension.score


def test_fhir_result_semantics_distinguish_indices_from_predictions():
    by_id = {metadata.algorithm_id: metadata for metadata in RUNTIME_ALGORITHMS}
    assert by_id["fib4"].output_resource is FHIRResultType.OBSERVATION
    assert by_id["gad7"].output_resource is FHIRResultType.OBSERVATION
    assert by_id["mayo_pulmonary_nodule"].output_resource is FHIRResultType.RISK_ASSESSMENT


def test_special_source_encodings_are_not_silently_normalized():
    lfs_no_dm = calculate_lfs({"metabolic_syndrome": False, "has_diabetes": False, "insulin": 10, "ast_got": 30, "alt_gpt": 40})
    lfs_dm = calculate_lfs({"metabolic_syndrome": False, "has_diabetes": True, "insulin": 10, "ast_got": 30, "alt_gpt": 40})
    assert lfs_dm.score - lfs_no_dm.score == pytest.approx(.9)


def test_mayo_cancer_flag_means_extrathoracic_cancer_at_least_five_years_ago():
    base = {"age": 60, "ever_smoker": False, "pulmonary_nodule_diameter": 8, "nodule_spiculation": False, "nodule_upper_lobe": False}
    no_history = calculate_mayo({**base, "extrathoracic_cancer_over_5y": False})
    old_history = calculate_mayo({**base, "extrathoracic_cancer_over_5y": True})
    assert old_history.score > no_history.score
