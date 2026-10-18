"""Reference cases for expert-source models and their runtime contracts."""
import math
import pytest
from services.disease_risk_engine import expert_adapters as adapters
from services.disease_risk_engine.algorithm_registry import RUNTIME_ALGORITHMS, FHIRResultType
from services.disease_risk_engine.clinical_units import normalize_observation_quantity


def test_prisq_published_table_extremes_and_bp_boundary():
    low = dict(age=18, sex="F", bmi=18.5, waist_circumference=79, systolic_bp=129, diastolic_bp=79)
    assert adapters.prisq(low)["score"] == 0
    assert adapters.prisq({**low, "diastolic_bp":80})["score"] == 6
    assert adapters.prisq(dict(age=55, sex="M", bmi=30, waist_circumference=103, systolic_bp=130, diastolic_bp=80))["score"] == 45


def test_gastric_score_table_maximum_and_assay_boundaries():
    base = dict(age=70, sex="M", regular_pickled_food=True, regular_fried_food=True,
                h_pylori_igg_eiu=34, pepsinogen_i_ii_ratio=3.88, gastrin_17_pmol_l=5.71)
    result = adapters.china_gastric(base)
    assert result["score"] == 25
    assert result["components"]["derivation_cohort_prevalence"] == 0.123
    assert adapters.china_gastric({**base, "h_pylori_igg_eiu":33.99, "pepsinogen_i_ii_ratio":3.89, "gastrin_17_pmol_l":5.70})["score"] == 20


def test_nelson_diabetes_centered_reference_and_applicability():
    base = dict(age=55, sex="M", has_diabetes=True, egfr=90, hba1c=7, bmi=27,
                urine_albumin_creatinine_ratio=10, race_black=False, cvd_history=False,
                ever_smoker=False, has_hypertension=False, diabetes_medication="oral")
    # eTable 11: age/HbA1c/BMI/log10(ACR) centered at zero; eGFR term = -3*0.268425.
    expected = -math.expm1(-5**1.212595 * math.exp(-5.372635))
    assert adapters.nelson_diabetes(base) == pytest.approx(expected, abs=1e-12)
    with pytest.raises(ValueError): adapters.nelson_diabetes({**base,"egfr":60})
    with pytest.raises(ValueError): adapters.nelson_diabetes({**base,"has_diabetes":False})


def test_new_scores_are_observations_and_nelson_is_probability():
    models = {m.algorithm_id:m for m in RUNTIME_ALGORITHMS}
    for model in ("prisq_prediabetes_screen", "china_gastric_cancer_prescreen_score"):
        assert models[model].output_resource == FHIRResultType.OBSERVATION
        assert not models[model].score_represents_probability
    assert models["nelson_ckd_egfr45_5y_diabetes"].output_resource == FHIRResultType.RISK_ASSESSMENT


def test_assay_specific_units_and_albumin_conversion():
    assert normalize_observation_quantity("h_pylori_igg_eiu",34,"{EIU}").value == 34
    assert normalize_observation_quantity("h_pylori_igg_eiu",34,"U/mL") is None
    assert normalize_observation_quantity("urine_albumin_creatinine_ratio",1,"mg/mmol").value == 8.84
