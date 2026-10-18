"""Expert-source cardiovascular calculators recovered from the source archive.

This module intentionally has no dependency on the registry.  It is a small,
pure calculation boundary so the catalogue integration can validate input
contracts and attach the appropriate FHIR provenance separately.

Only equations whose *complete* numerical form was recovered from a primary
source are executable here.  Other archive models remain represented in the
catalogue with their source and required inputs until their baseline survival
or supplied worksheet dependency is recovered; a hazard ratio table alone is
not sufficient to make an absolute-risk calculator.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Optional


UKPDS_STROKE_URI = "https://www.rdm.ox.ac.uk/files/clinical-studies-and-and-trials/ukpds-risk-engine-equations"
UKPDS_STROKE_VERSION = "UKPDS-Risk-Engine-2.0"
NZDCS_URI = "https://pmc.ncbi.nlm.nih.gov/articles/PMC2875452/"
NELSON_CKD_URI = "https://jamanetwork.com/journals/jama/fullarticle/2755299"


def _number(data: Mapping[str, Any], key: str) -> Optional[float]:
    value = data.get(key)
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _boolean(data: Mapping[str, Any], key: str) -> Optional[bool]:
    value = data.get(key)
    return value if isinstance(value, bool) else None


def _required_number(data: Mapping[str, Any], key: str, *, positive: bool = False) -> float:
    value = _number(data, key)
    if value is None or value < 0 or (positive and value <= 0):
        raise ValueError(f"{key} must be a finite {'positive' if positive else 'non-negative'} number")
    return value


def _required_boolean(data: Mapping[str, Any], key: str) -> bool:
    value = _boolean(data, key)
    if value is None:
        raise ValueError(f"{key} must be a boolean")
    return value


def calculate_ukpds_stroke(data: Mapping[str, Any]) -> float:
    """Return the UKPDS Risk Engine 2.0 10-year stroke probability (0 to 1).

    This is the first-stroke equation for a person with type 2 diabetes.  The
    required inputs are ``age`` and ``diabetes_duration_years`` (years),
    ``sex`` (``male`` or ``female``), ``is_smoker``,
    ``atrial_fibrillation``, ``systolic_bp``
    (mm[Hg]), ``total_cholesterol`` and ``hdl_cholesterol`` (both mg/dL), and
    ``diabetes_duration_years``.  Lipids are converted only to form their
    ratio, so matched units are required; the product boundary supplies both
    in canonical mg/dL.

    Equation values are the exact UKPDS 2.0 published estimates.  In
    particular, atrial fibrillation is a real input.  The archived workbook
    hard-coded this term as ``8.554^0``; doing that would erase a documented
    predictor and is a material formula error.
    """

    age = _required_number(data, "age")
    sbp = _required_number(data, "systolic_bp", positive=True)
    total_cholesterol = _required_number(data, "total_cholesterol", positive=True)
    hdl = _required_number(data, "hdl_cholesterol", positive=True)
    duration = _required_number(data, "diabetes_duration_years")
    sex = str(data.get("sex") or "").strip().casefold()
    if sex not in {"male", "female"}:
        raise ValueError("sex must be 'male' or 'female'")
    female = sex == "female"
    smoker = _required_boolean(data, "is_smoker")
    af = _required_boolean(data, "atrial_fibrillation")
    age_at_diagnosis = age - duration
    if age_at_diagnosis < 0:
        raise ValueError("diabetes_duration_years cannot exceed age")

    lipid_ratio = total_cholesterol / hdl
    if not math.isfinite(lipid_ratio) or lipid_ratio <= 0:
        raise ValueError("total_cholesterol/hdl_cholesterol must be positive")

    q = (
        0.001854749
        * math.pow(1.091797834, age_at_diagnosis - 55.0)
        * math.pow(0.700038749, int(female))
        * math.pow(1.546546697, int(smoker))
        * math.pow(8.553988106, int(af))
        * math.pow(1.122089348, (sbp - 135.549791) / 10.0)
        * math.pow(1.138088189, math.log(lipid_ratio) - 1.593026)
    )
    duration_ratio = 1.145004121
    horizon_years = 10.0
    cumulative_hazard = q * math.pow(duration_ratio, duration) * (
        (1.0 - math.pow(duration_ratio, horizon_years)) / (1.0 - duration_ratio)
    )
    probability = 1.0 - math.exp(-cumulative_hazard)
    if not math.isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError("UKPDS equation produced an invalid probability")
    return probability


def _nzdcs_covariates(
    data: Mapping[str, Any],
) -> tuple[float, bool, bool, bool, float, float, float, bool, float, bool, bool]:
    """Return the covariates shared by archived NZDCS CVD and MI equations."""

    age_at_diagnosis = _required_number(data, "age_at_diabetes_diagnosis")
    hba1c = _required_number(data, "hba1c")
    sbp = _required_number(data, "systolic_bp", positive=True)
    total_cholesterol = _required_number(data, "total_cholesterol", positive=True)
    hdl = _required_number(data, "hdl_cholesterol", positive=True)
    duration = _required_number(data, "diabetes_duration_years")
    sex = str(data.get("sex") or "").strip().casefold()
    if sex not in {"male", "female"}:
        raise ValueError("sex must be 'male' or 'female'")
    former_smoker = _required_boolean(data, "former_smoker")
    is_smoker = _required_boolean(data, "is_smoker")
    east_asian = _required_boolean(data, "east_asian")
    microalbuminuria = _required_boolean(data, "microalbuminuria")
    macroalbuminuria = _required_boolean(data, "macroalbuminuria")
    if former_smoker and is_smoker:
        raise ValueError("former_smoker and is_smoker cannot both be true")
    if microalbuminuria and macroalbuminuria:
        raise ValueError("microalbuminuria and macroalbuminuria cannot both be true")
    return (
        age_at_diagnosis,
        sex == "female",
        former_smoker,
        is_smoker,
        hba1c,
        sbp,
        total_cholesterol / hdl,
        east_asian,
        duration,
        microalbuminuria,
        macroalbuminuria,
    )


def _nzdcs_probability(baseline_survival: float, linear_predictor: float) -> float:
    probability = 1.0 - math.pow(baseline_survival, math.exp(linear_predictor))
    if not math.isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError("NZDCS equation produced an invalid probability")
    return probability


def calculate_nzdcs_cvd_5y(data: Mapping[str, Any]) -> float:
    """Return archived NZDCS five-year first-CVD probability (0 to 1).

    The formula was preserved verbatim in ``NZ DM Heart.docx``.  Its compact
    East-Asian indicator is the exact local expert artefact, rather than a
    claim that it is a replacement for the broader ethnicity coding published
    in the NZDCS derivation paper.
    """

    age_dx, female, former, smoker, hba1c, sbp, ratio, east_asian, duration, micro, macro = _nzdcs_covariates(data)
    linear = (
        age_dx * 0.04093
        + int(female) * -0.16542
        + int(former) * 0.10296
        + int(smoker) * 0.23131
        + hba1c * 0.05874
        + sbp * 0.00290
        + int(east_asian) * -0.09536
        + ratio * 0.02015
        + int(micro) * 0.21857
        + int(macro) * 0.69659
        + duration * 0.05795
        - 3.62948747
    )
    return _nzdcs_probability(0.8156, linear)


def calculate_nzdcs_mi_5y(data: Mapping[str, Any]) -> float:
    """Return archived NZDCS five-year myocardial-infarction probability."""

    age_dx, female, former, smoker, hba1c, sbp, ratio, east_asian, duration, micro, macro = _nzdcs_covariates(data)
    linear = (
        age_dx * 0.05251
        + int(female) * -0.25276
        + int(former) * 0.08549
        + int(smoker) * 0.35338
        + hba1c * 0.06457
        + sbp * 0.00153
        + int(east_asian) * -0.17086
        + ratio * 0.03762
        + int(micro) * 0.21629
        + int(macro) * 0.66917
        + duration * 0.06905
        - 4.23497
    )
    return _nzdcs_probability(0.9248, linear)


def calculate_nelson_ckd_egfr45_5y_diabetes(data: Mapping[str, Any]) -> float:
    """Return CKD-PC/Nelson 5-year incident eGFR <45 probability in diabetes.

    This is the diabetes branch from Nelson et al. JAMA 2019 eTable 11 for
    *all* (confirmed and unconfirmed) events.  It applies only where baseline
    eGFR is over 60 mL/min/1.73 m2.  The non-diabetes branch deliberately is
    not substituted here: it requires the eTable 2 expected-log10(ACR) patch.
    """

    age = _required_number(data, "age")
    egfr = _required_number(data, "egfr", positive=True)
    hba1c = _required_number(data, "hba1c")
    bmi = _required_number(data, "bmi", positive=True)
    acr = _required_number(data, "urine_albumin_creatinine_ratio", positive=True)
    female = str(data.get("sex") or "").strip().casefold() == "female"
    if str(data.get("sex") or "").strip().casefold() not in {"male", "female"}:
        raise ValueError("sex must be 'male' or 'female'")
    black = _required_boolean(data, "black_race")
    history_cvd = _required_boolean(data, "history_cvd")
    ever_smoker = _required_boolean(data, "ever_smoker")
    hypertension = _required_boolean(data, "hypertension")
    medication = str(data.get("diabetes_medication") or "").strip().casefold()
    if medication not in {"oral", "insulin", "none"}:
        raise ValueError("diabetes_medication must be 'oral', 'insulin', or 'none'")
    if egfr <= 60:
        raise ValueError("Nelson incident-CKD equation requires baseline egfr > 60")

    insulin = medication == "insulin"
    no_medication = medication == "none"
    linear = (
        -4.56736
        + 0.1086255 * (age / 5.0 - 11.0)
        + 0.1130331 * int(female)
        + 0.1475446 * int(black)
        + 0.268425 * (15.0 - min(egfr, 90.0) / 5.0)
        - 0.1160029 * max(0.0, egfr - 90.0) / 5.0
        + 0.3073098 * int(history_cvd)
        + 0.0841638 * (hba1c - 7.0)
        + 0.0909167 * int(insulin)
        - 0.1855329 * int(no_medication)
        + 0.035993 * (hba1c - 7.0) * int(insulin)
        + 0.0610776 * (hba1c - 7.0) * int(no_medication)
        + 0.0310965 * int(ever_smoker)
        + 0.4748296 * int(hypertension)
        + 0.0645142 * (bmi / 5.0 - 5.4)
        + 0.5715969 * (math.log10(acr) - 1.0)
    )
    probability = 1.0 - math.exp(-math.pow(5.0, 1.212595) * math.exp(linear))
    if not math.isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError("Nelson CKD equation produced an invalid probability")
    return probability


DEFINITIONS = (
    {
        "id": "ukpds_stroke_10y",
        "name": "UKPDS Risk Engine 2.0 stroke",
        "name_zh": "UKPDS 第二型糖尿病十年中風風險",
        "system": "cardiovascular",
        "outcome": "First fatal or non-fatal stroke",
        "probability": True,
        "horizon": "10 years",
        "source": "UKPDS Risk Engine 2.0 equations",
        "uri": UKPDS_STROKE_URI,
        "calculator": "calculate_ukpds_stroke",
        "inputs": (
            {"key": "age", "unit": "a", "type": "number"},
            {"key": "sex", "type": "enum", "values": ("male", "female")},
            {"key": "is_smoker", "type": "boolean"},
            {"key": "atrial_fibrillation", "type": "boolean"},
            {"key": "systolic_bp", "unit": "mm[Hg]", "type": "number"},
            {"key": "total_cholesterol", "unit": "mg/dL", "type": "number"},
            {"key": "hdl_cholesterol", "unit": "mg/dL", "type": "number"},
            {"key": "diabetes_duration_years", "unit": "a", "type": "number"},
        ),
    },
    {
        "id": "nelson_ckd_egfr45_5y_diabetes",
        "name": "CKD-PC/Nelson incident eGFR <45 in diabetes",
        "name_zh": "CKD-PC／Nelson 糖尿病者五年 eGFR 小於 45 風險",
        "system": "renal",
        "outcome": "Incident eGFR <45 mL/min/1.73m2 (all events)",
        "probability": True,
        "horizon": "5 years",
        "source": "Nelson et al., JAMA 2019, eTable 11 (diabetes branch)",
        "uri": NELSON_CKD_URI,
        "calculator": "calculate_nelson_ckd_egfr45_5y_diabetes",
        "inputs": (
            {"key": "age", "unit": "a", "type": "number"},
            {"key": "sex", "type": "enum", "values": ("male", "female")},
            {"key": "black_race", "type": "boolean"},
            {"key": "egfr", "unit": "mL/min/{1.73_m2}", "type": "number"},
            {"key": "history_cvd", "type": "boolean"},
            {"key": "hba1c", "unit": "%", "type": "number"},
            {"key": "diabetes_medication", "type": "enum", "values": ("oral", "insulin", "none")},
            {"key": "ever_smoker", "type": "boolean"},
            {"key": "hypertension", "type": "boolean"},
            {"key": "bmi", "unit": "kg/m2", "type": "number"},
            {"key": "urine_albumin_creatinine_ratio", "unit": "mg/g", "type": "number"},
        ),
    },
    {
        "id": "nzdcs_cvd_5y",
        "name": "New Zealand Diabetes Cohort Study CVD",
        "name_zh": "紐西蘭糖尿病世代五年心血管疾病風險",
        "system": "cardiovascular",
        "outcome": "First fatal or non-fatal cardiovascular disease event",
        "probability": True,
        "horizon": "5 years",
        "source": "NZ DM Heart.docx; Elley et al., Diabetes Care 2010",
        "uri": NZDCS_URI,
        "calculator": "calculate_nzdcs_cvd_5y",
        "inputs": (
            {"key": "age_at_diabetes_diagnosis", "unit": "a", "type": "number"},
            {"key": "sex", "type": "enum", "values": ("male", "female")},
            {"key": "former_smoker", "type": "boolean"},
            {"key": "is_smoker", "type": "boolean"},
            {"key": "hba1c", "unit": "%", "type": "number"},
            {"key": "systolic_bp", "unit": "mm[Hg]", "type": "number"},
            {"key": "total_cholesterol", "unit": "mg/dL", "type": "number"},
            {"key": "hdl_cholesterol", "unit": "mg/dL", "type": "number"},
            {"key": "east_asian", "type": "boolean"},
            {"key": "microalbuminuria", "type": "boolean"},
            {"key": "macroalbuminuria", "type": "boolean"},
            {"key": "diabetes_duration_years", "unit": "a", "type": "number"},
        ),
    },
    {
        "id": "nzdcs_mi_5y",
        "name": "New Zealand Diabetes Cohort Study MI",
        "name_zh": "紐西蘭糖尿病世代五年心肌梗塞風險",
        "system": "cardiovascular",
        "outcome": "Myocardial infarction",
        "probability": True,
        "horizon": "5 years",
        "source": "NZ DM Heart.docx; Elley et al., Diabetes Care 2010",
        "uri": NZDCS_URI,
        "calculator": "calculate_nzdcs_mi_5y",
        "inputs": (
            {"key": "age_at_diabetes_diagnosis", "unit": "a", "type": "number"},
            {"key": "sex", "type": "enum", "values": ("male", "female")},
            {"key": "former_smoker", "type": "boolean"},
            {"key": "is_smoker", "type": "boolean"},
            {"key": "hba1c", "unit": "%", "type": "number"},
            {"key": "systolic_bp", "unit": "mm[Hg]", "type": "number"},
            {"key": "total_cholesterol", "unit": "mg/dL", "type": "number"},
            {"key": "hdl_cholesterol", "unit": "mg/dL", "type": "number"},
            {"key": "east_asian", "type": "boolean"},
            {"key": "microalbuminuria", "type": "boolean"},
            {"key": "macroalbuminuria", "type": "boolean"},
            {"key": "diabetes_duration_years", "unit": "a", "type": "number"},
        ),
    },
)


__all__ = [
    "DEFINITIONS",
    "calculate_nzdcs_cvd_5y",
    "calculate_nzdcs_mi_5y",
    "calculate_nelson_ckd_egfr45_5y_diabetes",
    "calculate_ukpds_stroke",
]
