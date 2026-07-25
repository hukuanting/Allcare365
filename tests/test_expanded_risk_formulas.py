import pytest

from services.disease_risk_engine.formula_catalog import (
    calculate_anu_adri,
    calculate_bdsi_dementia_6y,
    calculate_brock_pancan_nodule,
    calculate_caide_dementia_20y,
    calculate_cardiometabolic_index,
    calculate_ggt_platelet_ratio,
    calculate_ipag_copd_questionnaire,
    calculate_lipid_accumulation_product,
    calculate_mci_to_ad_3y,
    calculate_pooled_cohort_ascvd_10y,
    calculate_reynolds_men_10y,
    calculate_reynolds_women_10y,
    calculate_va_pulmonary_nodule,
)


PUBLISHED_REFERENCE_VECTORS = (
    (calculate_reynolds_women_10y, {
        "age": 55, "sex": "F", "systolic_bp": 120, "hs_crp": 2,
        "total_cholesterol": 213, "hdl_cholesterol": 50, "hba1c": 5.5,
        "has_diabetes": False, "is_smoker": False, "parental_mi_before_60": False,
    }, 0.014171824970328206),
    (calculate_reynolds_men_10y, {
        "age": 55, "sex": "M", "systolic_bp": 120, "hs_crp": 2,
        "total_cholesterol": 213, "hdl_cholesterol": 50,
        "is_smoker": False, "parental_mi_before_60": False,
    }, 0.04535218232899574),
    (calculate_pooled_cohort_ascvd_10y, {
        "age": 55, "sex": "F", "pce_race": "white", "total_cholesterol": 213,
        "hdl_cholesterol": 50, "systolic_bp": 120,
        "anti_hypertensive_drugs": False, "is_smoker": False, "has_diabetes": False,
    }, 0.02052229820249485),
    (calculate_cardiometabolic_index, {
        "triglycerides": 150, "hdl_cholesterol": 50,
        "waist_circumference": 90, "body_height": 180,
    }, 1.5),
    (calculate_lipid_accumulation_product, {
        "sex": "M", "waist_circumference": 90, "triglycerides": 150,
    }, 42.3375),
    (calculate_ggt_platelet_ratio, {
        "ggt": 50, "ggt_uln": 50, "platelet_count": 200,
    }, 0.5),
    (calculate_ipag_copd_questionnaire, {
        "age": 65, "pack_years": 30, "bmi": 24,
        "weather_affected_cough": True, "sputum_without_cold": True,
        "morning_sputum": False, "wheeze_sometimes_or_often": True,
        "allergy_history": False,
    }, 32.0),
    (calculate_mci_to_ad_3y, {
        "has_amnestic_mci": True, "sex": "F", "stubborn_or_resistive": True,
        "upset_when_separated_from_caregiver": True, "difficulty_shopping_alone": True,
        "forgets_appointments": True, "mean_words_recalled": 4,
        "orientation_correct": 6, "clock_drawing_score": 3,
    }, 16.0),
    (calculate_anu_adri, {
        "age": 70, "sex": "M", "education_years": 12, "bmi": 25,
        "has_diabetes": False, "depressive_symptoms": False,
        "high_cholesterol": False, "traumatic_brain_injury": False,
        "smoking_status": "never", "alcohol_category": "light_moderate",
        "social_engagement_level": "high", "physical_activity_level": "high",
        "cognitive_activity_level": "high", "fish_servings_per_week": 3,
        "pesticide_exposure": False,
    }, -5.0),
    (calculate_brock_pancan_nodule, {
        "age": 62, "sex": "M", "family_history_lung_cancer": False,
        "has_emphysema": False, "pulmonary_nodule_diameter": 10,
        "nodule_type": "solid", "nodule_upper_lobe": False,
        "nodule_count": 4, "nodule_spiculation": False,
    }, 0.025098338800117814),
    (calculate_va_pulmonary_nodule, {
        "age": 60, "ever_smoker": False, "pulmonary_nodule_diameter": 10,
        "years_since_quitting": 0,
    }, 0.06849760372432612),
    (calculate_caide_dementia_20y, {
        "age": 54, "sex": "M", "education_years": 12, "systolic_bp": 141,
        "bmi": 31, "total_cholesterol": 260, "physical_activity_active": False,
    }, 12.0),
    (calculate_bdsi_dementia_6y, {
        "age": 70, "education_years": 11, "bmi": 18, "has_diabetes": True,
        "stroke_tia_history": True, "needs_help_money_or_medications": True,
        "depressive_symptoms": True,
    }, 47.0),
)


@pytest.mark.parametrize(("calculator", "inputs", "expected"), PUBLISHED_REFERENCE_VECTORS)
def test_expanded_formula_reference_vectors(calculator, inputs, expected):
    result = calculator(inputs)
    assert result.applicability == "applicable"
    assert result.missing_data == []
    assert result.score == pytest.approx(expected, abs=1e-12)


def test_expanded_formula_missing_data_is_not_silently_substituted():
    result = calculate_cardiometabolic_index({
        "triglycerides": 150,
        "hdl_cholesterol": 50,
        "waist_circumference": 90,
    })
    assert result.score is None
    assert result.applicability == "insufficient_data"
    assert result.missing_data == ["body_height"]


def test_sex_specific_formula_reports_not_applicable_instead_of_a_score():
    result = calculate_reynolds_women_10y({
        "age": 55, "sex": "M", "systolic_bp": 120, "hs_crp": 2,
        "total_cholesterol": 213, "hdl_cholesterol": 50, "hba1c": 5.5,
        "has_diabetes": False, "is_smoker": False, "parental_mi_before_60": False,
    })
    assert result.score is None
    assert result.applicability == "not_applicable"
    assert result.missing_data == []
