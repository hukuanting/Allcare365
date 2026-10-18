"""Deterministic calculators recovered from the expert source collection.

This module deliberately has no registry or Django dependency.  The product
catalog can import individual functions only after it has declared matching
clinical input contracts.  Formula inputs are explicit and units are recorded
in :data:`DEFINITIONS`; invalid or missing inputs raise ``ValueError`` rather
than being silently treated as zero.
"""

from __future__ import annotations

import math
from typing import Any, Mapping


DEFINITIONS = {
    "plala_cirrhosis": {
        "name_zh": "PLALA 肝硬化篩檢分數",
        "name_en": "PLALA score",
        "system": "hepatic",
        "outcome": "cirrhosis in people with NAFLD",
        "probability": False,
        "time": None,
        "inputs": {
            "platelet_count": "10^9/L",
            "albumin": "g/dL",
            "ast_got": "U/L",
            "alt_gpt": "U/L",
        },
        "method_uri": "https://mhlw-grants.niph.go.jp/system/files/2014/143151/201423005A/201423005A0014.pdf",
        "version": "PLALA-source-workbook-thresholds",
    },
    "nafic_nash": {
        "name_zh": "NAFIC NASH 分數",
        "name_en": "NAFIC score",
        "system": "hepatic",
        "outcome": "NASH in Japanese patients with biopsy-proven NAFLD",
        "probability": False,
        "time": None,
        "inputs": {
            "sex": "M or F",
            "ferritin": "ng/mL",
            "fasting_insulin": "uIU/mL",
            "type_iv_collagen_7s": "ng/mL",
        },
        "method_uri": "https://pubmed.ncbi.nlm.nih.gov/20842510/",
        "version": "Sumida-2011-original",
    },
    "modified_nafic_nash": {
        "name_zh": "修正版 NAFIC NASH 分數",
        "name_en": "Modified NAFIC score",
        "system": "hepatic",
        "outcome": "NASH in Japanese patients with biopsy-proven NAFLD",
        "probability": False,
        "time": None,
        "inputs": {
            "sex": "M or F",
            "ferritin": "ng/mL",
            "fasting_insulin": "uIU/mL",
            "type_iv_collagen_7s": "ng/mL",
        },
        "method_uri": "https://pmc.ncbi.nlm.nih.gov/articles/PMC4020262/",
        "version": "Sumida-2014-modified",
    },
    "fibroindex_hcv": {
        "name_zh": "FibroIndex 肝纖維化指數",
        "name_en": "FibroIndex",
        "system": "hepatic",
        "outcome": "significant fibrosis in chronic hepatitis C",
        "probability": False,
        "time": None,
        "inputs": {
            "platelet_count_10e4_per_mm3": "10^4/mm3",
            "ast_got": "U/L",
            "gamma_globulin": "g/dL",
        },
        "method_uri": "https://doi.org/10.1002/hep.21520",
        "version": "Koda-2007",
    },
    "thin_dementia_60_79_5y": {
        "name_zh": "UK THIN 5 年失智症風險（60–79 歲）",
        "name_en": "Dementia Risk Score (UK THIN, age 60–79)",
        "system": "neurocognitive",
        "outcome": "first recorded dementia diagnosis",
        "probability": True,
        "time": "5 years",
        "inputs": {
            "age": "years", "sex": "M or F", "bmi": "kg/m2",
            "deprivation_quintile": "1..5", "calendar_year": "year",
            "anti_hypertensive_drugs": "boolean", "former_smoker": "boolean",
            "current_smoker": "boolean", "heavy_drinking": "boolean",
            "depression_or_antidepressants": "boolean", "aspirin_use": "boolean",
            "stroke_or_tia_history": "boolean", "atrial_fibrillation_history": "boolean",
            "has_diabetes": "boolean",
        },
        "method_uri": "https://pubmed.ncbi.nlm.nih.gov/26797096/",
        "version": "Walters-2016-60-79",
    },
    "load_probable_4y_score": {
        "name_zh": "晚發型阿茲海默症血管風險分數（probable LOAD）",
        "name_en": "Probable late-onset Alzheimer disease vascular risk score",
        "system": "neurocognitive",
        "outcome": "probable late-onset Alzheimer disease risk stratification",
        "probability": False,
        "time": "mean follow-up 4.2 years in the derivation cohort",
        "inputs": {
            "age": "years", "sex": "M or F", "has_diabetes": "boolean",
            "has_hypertension": "boolean", "current_smoker": "boolean",
            "load_low_hdl_c": "boolean", "load_high_whr": "boolean",
            "education_years": "years", "ethnicity": "white, black, or hispanic",
            "apoe_e4": "allele count",
        },
        "method_uri": "https://jamanetwork.com/journals/jamaneurology/fullarticle/800692",
        "version": "Reitz-2010-probable-LOAD",
    },
    "expert_epwv_reference": {
        "name_zh": "估算脈波傳導速度參考值",
        "name_en": "Expert-workbook estimated pulse wave velocity",
        "system": "cardiovascular",
        "outcome": "arterial stiffness reference measure",
        "probability": False,
        "time": None,
        "inputs": {"age": "years", "systolic_bp": "mm[Hg]", "diastolic_bp": "mm[Hg]"},
        "method_uri": "https://academic.oup.com/eurheartj/article/31/19/2338/441416",
        "version": "CORE-20220414-PWV-WK",
    },
    "cimt_age_percentile": {
        "name_zh": "年齡與性別校正 CIMT 百分位",
        "name_en": "Age- and sex-specific CIMT percentile",
        "system": "cardiovascular",
        "outcome": "CIMT reference percentile",
        "probability": False,
        "time": None,
        "inputs": {"sex": "M or F", "age": "years", "cimt_um": "um"},
        "method_uri": "expert-source:AgeCIMY table.docx",
        "version": "AgeCIMY-table-linear-interpolation",
    },
    "expert_fvc_reference": {
        "name_zh": "FVC 參考預測值",
        "name_en": "Expert-workbook predicted FVC",
        "system": "respiratory",
        "outcome": "predicted forced vital capacity reference",
        "probability": False,
        "time": None,
        "inputs": {"sex": "M or F", "age": "years", "body_height": "cm"},
        "method_uri": "expert-source:Pulmonary FCV precicted male.xlsx",
        "version": "expert-worksheet-0.93-adjustment",
    },
    "prisq_prediabetes_screen": {
        "name_zh": "卡達糖尿病前期篩檢分數（PRISQ）",
        "name_en": "Prediabetes Risk Score in Qatar (PRISQ)",
        "system": "metabolic_endocrine",
        "outcome": "cross-sectional prediabetes screening classification",
        "probability": False,
        "time": "cross-sectional",
        "inputs": {"age": "years", "sex": "M or F", "bmi": "kg/m2", "waist_circumference": "cm", "systolic_bp": "mm[Hg]", "diastolic_bp": "mm[Hg]"},
        "method_uri": "https://doi.org/10.1111/jdi.13445",
        "version": "Abbas-2021-Table-2",
    },
    "torre_dementia_screen": {
        "name_zh": "Torre 失智症篩檢估計",
        "name_en": "Canadian Study of Health and Aging dementia risk calculator",
        "system": "neurocognitive",
        "outcome": "dementia screening index (heuristic; not an absolute event probability)",
        "probability": False,
        "time": "age-indexed screen; no prospective horizon supplied",
        "inputs": {"age": "years", "vascular_risk_factor_count": "integer", "family_history_dementia": "boolean"},
        "method_uri": "https://www.alzheimer-riese.it/images/stories/files/Docs/dementia_risk_calculator_csah_2014.pdf",
        "version": "CSAH-calculator-2014",
    },
}


def _number(data: Mapping[str, Any], key: str) -> float:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be a finite number")
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{key} must be a finite non-negative number")
    return value


def _bool(data: Mapping[str, Any], key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be boolean")
    return value


def _sex(data: Mapping[str, Any]) -> str:
    value = data.get("sex")
    if not isinstance(value, str) or value.strip().upper() not in {"M", "F"}:
        raise ValueError("sex must be 'M' or 'F'")
    return value.strip().upper()


def calculate_plala(data: Mapping[str, Any]) -> float:
    """Return the 0–3 PLALA score from the source workbook thresholds."""
    platelets = _number(data, "platelet_count")
    albumin = _number(data, "albumin")
    ast = _number(data, "ast_got")
    alt = _number(data, "alt_gpt")
    if alt == 0:
        raise ValueError("alt_gpt must be greater than zero")
    return float((platelets < 153) + (albumin < 4.0) + (ast / alt > 0.9))


def calculate_nafic(data: Mapping[str, Any], *, modified: bool = False) -> float:
    """Return original (0–4) or modified (0–5) NAFIC score."""
    sex = _sex(data)
    ferritin = _number(data, "ferritin")
    insulin = _number(data, "fasting_insulin")
    collagen = _number(data, "type_iv_collagen_7s")
    score = float(ferritin >= (300 if sex == "M" else 200)) + float(collagen >= 5.0) * 2
    if modified:
        score += 2.0 if insulin >= 15 else 1.0 if insulin >= 10 else 0.0
    else:
        score += float(insulin >= 10)
    return score


def calculate_modified_nafic(data: Mapping[str, Any]) -> float:
    return calculate_nafic(data, modified=True)


def calculate_fibroindex(data: Mapping[str, Any]) -> float:
    """Koda 2007 FibroIndex; platelet count is in 10^4/mm3, not 10^9/L."""
    platelets = _number(data, "platelet_count_10e4_per_mm3")
    ast = _number(data, "ast_got")
    gamma_globulin = _number(data, "gamma_globulin")
    return 1.738 - 0.064 * platelets + 0.005 * ast + 0.463 * gamma_globulin


def calculate_thin_dementia_60_79(data: Mapping[str, Any]) -> float:
    """Walters et al. 2016: return five-year risk percentage for age 60–79."""
    age = _number(data, "age")
    if not 60 <= age <= 79:
        raise ValueError("THIN 60–79 formula is applicable only to age 60 through 79")
    bmi = _number(data, "bmi")
    deprivation = _number(data, "deprivation_quintile")
    if deprivation not in {1, 2, 3, 4, 5}:
        raise ValueError("deprivation_quintile must be an integer from 1 through 5")
    calendar_year = _number(data, "calendar_year")
    sex = _sex(data)
    female = sex == "F"
    hyp = _bool(data, "anti_hypertensive_drugs")
    former = _bool(data, "former_smoker")
    current = _bool(data, "current_smoker")
    if former and current:
        raise ValueError("former_smoker and current_smoker cannot both be true")
    heavy_drinking = _bool(data, "heavy_drinking")
    depression = _bool(data, "depression_or_antidepressants")
    aspirin = _bool(data, "aspirin_use")
    stroke = _bool(data, "stroke_or_tia_history")
    af = _bool(data, "atrial_fibrillation_history")
    diabetes = _bool(data, "has_diabetes")
    a = age - 65.608
    b = bmi - 27.501
    deprivation_coefficients = {1: 0.0, 2: 0.013371, 3: 0.117904, 4: 0.201776, 5: 0.225529}
    p = (
        0.20921 * a - 0.00339 * a * a - 0.0616 * b + 0.002508 * b * b
        + 0.12854 * female - 0.13199 * hyp + 0.04477 * (calendar_year - 2003.719)
        + deprivation_coefficients[int(deprivation)] - 0.06792 * former - 0.08657 * current
        + 0.443535 * heavy_drinking + 0.833612 * depression + 0.252833 * aspirin
        + 0.577207 * stroke + 0.220728 * af + 0.286701 * diabetes
    )
    return 100.0 * (1.0 - math.pow(0.9969, math.exp(p)))


def calculate_load_probable_score(data: Mapping[str, Any]) -> dict[str, float | str]:
    """Reitz 2010 probable-LOAD point score and derivation-cohort category.

    The article's score is a risk-stratification score, not a calibrated
    individual absolute probability.  ``observed_case_percentage`` is retained
    solely as the percentage observed in the derivation cohort category.
    """
    age = _number(data, "age")
    if age < 65:
        raise ValueError("LOAD score was derived for people age 65 or older")
    sex = _sex(data)
    diabetes = _bool(data, "has_diabetes")
    hypertension = _bool(data, "has_hypertension")
    smoker = _bool(data, "current_smoker")
    low_hdl = _bool(data, "load_low_hdl_c")
    high_whr = _bool(data, "load_high_whr")
    education = _number(data, "education_years")
    ethnicity = data.get("ethnicity")
    if not isinstance(ethnicity, str) or ethnicity.strip().lower() not in {"white", "black", "hispanic"}:
        raise ValueError("ethnicity must be white, black, or hispanic for the source score")
    apoe_e4 = _number(data, "apoe_e4")
    age_score = 0 if age <= 70 else 6 if age <= 75 else 12 if age <= 80 else 14 if age <= 85 else 25
    education_score = 0 if education > 9 else 8 if education >= 7 else 10
    ethnicity_score = {"white": 0, "black": 5, "hispanic": 7}[ethnicity.strip().lower()]
    score = (
        age_score + int(sex == "F") + 2 * int(diabetes) + 0 * int(hypertension)
        + 7 * int(smoker) + 4 * int(low_hdl) + 9 * int(high_whr) + education_score
        + ethnicity_score + 5 * int(apoe_e4 >= 1)
    )
    if score <= 16:
        category, observed = "0-16", 0.4
    elif score <= 21:
        category, observed = "17-21", 3.7
    elif score <= 26:
        category, observed = "22-26", 3.2
    elif score <= 32:
        category, observed = "27-32", 8.2
    else:
        category, observed = ">32", 17.0
    return {"score": float(score), "category": category, "observed_case_percentage": observed}


def calculate_expert_epwv(data: Mapping[str, Any]) -> dict[str, float | str]:
    """Reproduce local ``PWV-WK`` formulas as a reference measurement.

    This returns both the three-component worksheet average and the patient vs
    optimal comparison actually used by the sheet.  It is not an event-risk
    probability or a diagnostic claim.
    """
    age = _number(data, "age")
    if not 0 < age < 90:
        raise ValueError("PWV-WK age bands cover greater than 0 and less than 90 years")
    sbp = _number(data, "systolic_bp")
    dbp = _number(data, "diastolic_bp")
    if sbp < dbp:
        raise ValueError("systolic_bp must be greater than or equal to diastolic_bp")
    map_value = (sbp + 2.0 * dbp) / 3.0
    if sbp < 110:
        bp_category, bp_value = "optimal", 0.00083 * age * age + 5.55
    elif sbp < 120:
        bp_category, bp_value = "normal", 0.00099 * age * age + 5.69
    elif sbp < 129:
        bp_category, bp_value = "high_normal", 0.00105 * age * age + 5.91
    elif sbp < 140:
        bp_category, bp_value = "grade_1_hypertension", 0.00118 * age * age + 6.17
    elif sbp < 200:
        bp_category, bp_value = "grade_2_3_hypertension", 0.00085 * age * age + 5.73 + 0.044 * age
    else:
        raise ValueError("PWV-WK has no systolic_bp formula for 200 mm[Hg] or higher")
    if age < 30:
        map_reference = 0.0472 * map_value + 2.2
    elif age < 40:
        map_reference = 0.0423 * map_value + 2.2
    elif age < 50:
        map_reference = 0.0646 * map_value + 1.41
    elif age < 60:
        map_reference = 0.0731 * map_value + 1.35
    elif age < 70:
        map_reference = 0.0715 * map_value + 3.16
    else:
        map_reference = 0.0676 * map_value + 5.46
    full = (
        9.58748315543126 - 0.402467539733184 * age + 0.00456020798207263 * age * age
        - 0.000026207705511664 * age * age * map_value + 0.0031762450559276 * age * map_value
        - 0.0183215068503821 * map_value
    )
    optimal_map = 83.0
    optimal = (
        9.58748315543126 - 0.402467539733184 * age + 0.00456020798207263 * age * age
        - 0.000026207705511664 * age * age * optimal_map + 0.0031762450559276 * age * optimal_map
        - 0.0183215068503821 * optimal_map
    )
    sheet_bp = bp_value * 0.95
    sheet_map = map_reference * 0.95
    sheet_patient = full * 0.95
    sheet_optimal = optimal * 0.9
    return {
        "mean_arterial_pressure": map_value,
        "bp_category": bp_category,
        "epwv_bp_component": sheet_bp,
        "epwv_map_component": sheet_map,
        "epwv_patient_component": sheet_patient,
        "epwv_worksheet_average": (sheet_bp + sheet_map + sheet_patient) / 3.0,
        "epwv_optimal_component": sheet_optimal,
        "patient_vs_optimal_percent": (sheet_patient - sheet_optimal) / sheet_optimal * 100.0,
    }


_CIMT_AGES = tuple(range(15, 90, 5))
_CIMT_PERCENTILES = (2.5, 10.0, 25.0, 50.0, 75.0, 90.0, 97.5)
_CIMT_TABLE = {
    "M": ((263,311,354,401,449,492,540),(280,331,377,427,478,524,575),(297,351,400,453,507,556,610),(314,372,423,479,536,587,645),(331,392,446,505,565,619,680),(349,412,468,531,594,651,714),(366,432,491,557,624,683,749),(383,452,514,583,653,715,784),(400,473,537,609,682,746,819),(417,493,560,635,711,778,854),(434,513,583,662,740,810,889),(451,533,606,688,769,842,924),(469,554,629,714,798,873,958),(486,574,652,740,827,905,993),(503,594,675,766,856,937,1028)),
    "F": ((265,311,351,396,441,482,527),(282,330,373,421,469,512,560),(299,350,395,446,497,542,593),(315,369,417,471,524,572,626),(332,389,439,496,552,602,659),(349,408,461,521,580,633,692),(366,428,483,545,607,663,725),(382,448,506,570,635,693,758),(399,467,528,595,663,723,791),(416,487,550,620,690,753,824),(433,506,572,645,718,783,857),(450,526,594,670,745,813,890),(466,545,616,694,773,843,923),(483,565,638,719,801,874,956),(500,585,660,744,828,904,989)),
}


def calculate_cimt_age_percentile(data: Mapping[str, Any]) -> float:
    """Linearly interpolate the supplied AgeCIMY reference table.

    Values outside the source table's 15–85 year or 2.5th–97.5th percentile
    range are deliberately rejected instead of extrapolated.
    """
    sex = _sex(data)
    age = _number(data, "age")
    cimt = _number(data, "cimt_um")
    if not 15 <= age <= 85:
        raise ValueError("AgeCIMY table applies only to ages 15 through 85")
    lower_index = int((age - 15) // 5)
    upper_index = min(lower_index + 1, len(_CIMT_AGES) - 1)
    lower_age, upper_age = _CIMT_AGES[lower_index], _CIMT_AGES[upper_index]
    fraction = 0.0 if upper_age == lower_age else (age - lower_age) / (upper_age - lower_age)
    cutoffs = tuple(
        _CIMT_TABLE[sex][lower_index][i] + fraction * (_CIMT_TABLE[sex][upper_index][i] - _CIMT_TABLE[sex][lower_index][i])
        for i in range(len(_CIMT_PERCENTILES))
    )
    if not cutoffs[0] <= cimt <= cutoffs[-1]:
        raise ValueError("cimt_um falls outside the source table's 2.5th–97.5th percentile span")
    for index, cutoff in enumerate(cutoffs):
        if cimt == cutoff:
            return _CIMT_PERCENTILES[index]
        if cimt < cutoff:
            previous_cutoff = cutoffs[index - 1]
            previous_percentile = _CIMT_PERCENTILES[index - 1]
            return previous_percentile + (cimt - previous_cutoff) * (_CIMT_PERCENTILES[index] - previous_percentile) / (cutoff - previous_cutoff)
    return _CIMT_PERCENTILES[-1]


def calculate_expert_fvc_reference(data: Mapping[str, Any]) -> dict[str, float]:
    """Return raw and worksheet-adjusted predicted FVC in litres.

    The 0.93 multiplier is kept solely because it appears in the expert
    worksheet; it is not labelled here as an ethnicity or population factor.
    """
    sex = _sex(data)
    age = _number(data, "age")
    height = _number(data, "body_height")
    raw = (0.0576 * height - 0.026 * age - 4.34) if sex == "M" else (0.0443 * height - 0.026 * age - 2.89)
    return {"predicted_fvc_l": raw, "expert_adjusted_predicted_fvc_l": raw * 0.93}


def calculate_prisq(data: Mapping[str, Any]) -> dict[str, float | str | bool]:
    """Abbas et al. PRISQ 0–45 prediabetes screening score.

    It identifies concurrent dysglycaemia in the Qatar derivation population;
    it is not a prospective probability of developing diabetes.
    """
    age = _number(data, "age")
    if age < 18:
        raise ValueError("PRISQ was derived for adults age 18 or older")
    sex = _sex(data)
    bmi = _number(data, "bmi")
    if bmi < 18.5:
        raise ValueError("PRISQ derivation excluded BMI below 18.5 kg/m2")
    waist = _number(data, "waist_circumference")
    sbp = _number(data, "systolic_bp")
    dbp = _number(data, "diastolic_bp")
    if sbp < dbp:
        raise ValueError("systolic_bp must be greater than or equal to diastolic_bp")
    age_score = 0 if age <= 35 else 12 if age <= 54 else 22
    bmi_score = 0 if bmi < 25 else 2 if bmi < 30 else 5
    hypertension_score = 0 if sbp < 130 and dbp < 80 else 6
    if sex == "M":
        waist_score = 0 if waist < 94 else 3 if waist <= 102 else 9
    else:
        waist_score = 0 if waist < 80 else 3 if waist <= 88 else 9
    score = age_score + bmi_score + hypertension_score + (3 if sex == "M" else 0) + waist_score
    if score <= 16:
        category = "low"
    elif score <= 27:
        category = "moderate"
    else:
        category = "high"
    return {"score": float(score), "category": category, "screen_positive": score > 16}


def calculate_torre_dementia_screen(data: Mapping[str, Any]) -> float:
    """Return the calculator's uncapped percentage-like heuristic index."""
    age = _number(data, "age")
    base_by_age = {65: 2.0, 70: 4.0, 75: 8.0, 80: 16.0, 85: 32.0}
    if age not in base_by_age:
        raise ValueError("Torre calculator provides only ages 65, 70, 75, 80, and 85")
    count = _number(data, "vascular_risk_factor_count")
    if not count.is_integer() or count < 0:
        raise ValueError("vascular_risk_factor_count must be a non-negative integer")
    family_history = _bool(data, "family_history_dementia")
    return base_by_age[int(age)] * (2.0 ** int(count)) * (2.0 if family_history else 1.0)


def calculate_china_nonobese_nafld(data: Mapping[str, Any]) -> dict[str, float]:
    """Return source-supplement 1- and 4-year incidence percentages.

    The point equations and polynomials are transcribed from the expert
    collection's ``additionalfile1 for CN NAFLD working.docx``.  They are not
    the unrelated Wang 2020 diagnostic nomogram's coefficients.
    """
    sex = _sex(data)
    age = _number(data, "age")
    if not 14 <= age <= 93:
        raise ValueError("source age bands cover 14 through 93 years")
    alt = _number(data, "alt_gpt")
    ua = _number(data, "uric_acid")
    glucose = _number(data, "fasting_glucose_mmol_l")
    total_cholesterol = _number(data, "total_cholesterol_mmol_l")
    triglycerides = _number(data, "triglycerides_mmol_l")
    hdl = _number(data, "hdl_cholesterol_mmol_l")
    bmi = _number(data, "bmi")
    sex_points = 28.106314 if sex == "M" else 10.0
    age_points = 30.0 if age <= 36 else 46.887634 if age <= 45 else 58.813573
    points = (
        sex_points + age_points + 0.178405561 * alt + 0.064792951 * ua
        + 2.447833368 * glucose - 7.343500103 + 4.682007728 * total_cholesterol
        - 7.023011592 + 4.776735085 * triglycerides - 18.257037181 * hdl
        + 73.028148724 + 9.090909091 * bmi - 127.272727273
    )
    one_year = -2.5e-07 * points ** 3 + 0.000108073 * points ** 2 - 0.015006616 * points + 1.644186245
    four_year = -7e-08 * points ** 3 - 2.5278e-05 * points ** 2 + 0.008832549 * points + 0.427150119
    return {"total_points": points, "one_year_incidence_percentage": one_year, "four_year_incidence_percentage": four_year}


__all__ = [
    "DEFINITIONS", "calculate_cimt_age_percentile", "calculate_expert_epwv",
    "calculate_expert_fvc_reference", "calculate_fibroindex", "calculate_load_probable_score",
    "calculate_prisq",
    "calculate_modified_nafic", "calculate_nafic", "calculate_plala",
    "calculate_thin_dementia_60_79", "calculate_torre_dementia_screen",
]
