"""Expert-source cancer and bone calculators with reconstructable equations.

This module deliberately does not register algorithms.  It is a narrow source
adapter: the registry, FHIR projection, unit normalization, authorization, and
clinical-governance policy are composed elsewhere.

Only equations whose full numerical specification was recoverable from the
expert-source bundle and the original/correcting publication belong here.
"""

from __future__ import annotations

import math
from typing import Any, Mapping


HUNT_LUNG_CANCER_6Y_URI = "https://doi.org/10.1016/j.ebiom.2022.104187"


DEFINITIONS = [
    {
        "id": "china_gastric_cancer_prescreen_score",
        "name": "Chinese Gastric Cancer Prescreening Score",
        "name_zh": "中國胃癌篩檢前風險積分",
        "inputs": ["age_years", "sex", "regular_pickled_food", "regular_fried_food", "h_pylori_igg_eiu", "pepsinogen_i_ii_ratio", "gastrin_17_pmol_l"],
        "system": "Cai et al. nationwide Chinese high-risk population, Gut 2019",
        "outcome": "gastric-cancer prescreening risk category",
        "probability": "ordinal score 0–25; derivation-cohort prevalence by band",
        "source": "Cai et al., Gut 2019, Table 2",
        "uri": "https://doi.org/10.1136/gutjnl-2018-317556",
        "horizon": "cross-sectional prescreening; no future-time probability",
        "calculator": "china_gastric_cancer_prescreen_score",
    },
    {
        "id": "bcra_chinese_american_absolute_risk",
        "name": "NCI Breast Cancer Risk Assessment Tool (Chinese-American)",
        "name_zh": "NCI Gail/BCRAT 華裔美國女性絕對風險",
        "inputs": [
            "initial_age_years", "projection_age_years", "age_at_menarche",
            "age_at_first_live_birth", "number_of_breast_biopsies",
            "atypical_hyperplasia", "first_degree_relatives_with_breast_cancer",
        ],
        "system": "NCI BCRA 2.0, race code 6 (Chinese-American SEER 1998-2002)",
        "outcome": "invasive breast cancer",
        "probability": "absolute probability, 0 to 1",
        "source": "NCI BCRA 2.0 / CRAN BCRA source",
        "uri": "https://raw.githubusercontent.com/cran/BCRA/master/R/absolute.risk.R",
        "horizon": "caller-selected interval, age 20 to 90",
        "calculator": "bcra_chinese_american_absolute_risk",
    },
    {
        "id": "hunt_lung_cancer_6y",
        "name": "HUNT Lung Cancer Model",
        "name_zh": "HUNT 肺癌六年風險模型",
        "inputs": [
            "age_years",
            "sex",
            "pack_years",
            "cigarettes_per_day",
            "quit_years",
            "bmi_kg_m2",
            "indoor_tobacco_smoke_hours_per_day",
            "daily_cough",
        ],
        "system": "HUNT2 ever-smoker model; corrected algorithm",
        "outcome": "lung cancer diagnosis",
        "probability": "six-year predicted probability, 0 to 1",
        "source": "Markaki et al., EBioMedicine 2018; corrigendum 2022",
        "uri": HUNT_LUNG_CANCER_6Y_URI,
        "horizon": "6 years",
        "calculator": "hunt_lung_cancer_6y",
    }
]


def _number(data: Mapping[str, Any], key: str, *, minimum: float = 0.0) -> float:
    try:
        value = float(data[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{key} is required and must be numeric") from exc
    if not math.isfinite(value) or value < minimum:
        raise ValueError(f"{key} must be finite and >= {minimum}")
    return value


def _binary(data: Mapping[str, Any], key: str) -> int:
    value = data.get(key)
    if value in (True, 1, "1", "yes", "Yes", "YES"):
        return 1
    if value in (False, 0, "0", "no", "No", "NO"):
        return 0
    raise ValueError(f"{key} is required and must be a boolean")


def _male(data: Mapping[str, Any]) -> int:
    value = data.get("sex")
    if value in ("male", "Male", "MALE", "M", "m", 1):
        return 1
    if value in ("female", "Female", "FEMALE", "F", "f", 0):
        return 0
    raise ValueError("sex is required and must be male or female for this model")


def hunt_lung_cancer_6y(data: Mapping[str, Any]) -> float:
    """Return corrected HUNT six-year lung-cancer probability for an ever-smoker.

    The 2022 corrigendum corrected the published supplementary equations by
    adding one inside all logarithm arguments.  `quit_years` is zero for a
    current smoker.  The function intentionally does not infer ever-smoker
    status; the caller must enforce the population applicability criterion.
    """

    age = _number(data, "age_years", minimum=0.000001)
    pack_years = _number(data, "pack_years")
    cigarettes_per_day = _number(data, "cigarettes_per_day")
    quit_years = _number(data, "quit_years")
    bmi = _number(data, "bmi_kg_m2", minimum=0.000001)
    indoor_hours = _number(data, "indoor_tobacco_smoke_hours_per_day")

    xb = (
        1.18203062
        + 0.31573217 * _male(data)
        - 1.98496138 * (age / 100.0) ** -1
        + 1.11994217 * math.log(pack_years + 1.0)
        - 0.04002877 * cigarettes_per_day
        - 0.24019955 * math.log(quit_years + 1.0)
        - 1.70238304 * math.log(bmi + 1.0)
        + 0.08072420 * math.log(indoor_hours + 1.0)
        + 0.49212668 * _binary(data, "daily_cough")
    )
    # A numerically stable logistic transformation preserves the exact model.
    if xb >= 0:
        return 1.0 / (1.0 + math.exp(-xb))
    exp_xb = math.exp(xb)
    return exp_xb / (1.0 + exp_xb)


def china_gastric_cancer_prescreen_score(data: Mapping[str, Any]) -> dict[str, Any]:
    """Return the exact 0–25 Gut 2019 Chinese gastric-cancer prescreen score.

    This is a score-based triage rule for the source study population, not a
    time-to-event probability.  Regular pickled/fried food means >=3 times per
    week as defined in the study questionnaire.
    """
    age = _number(data, "age_years", minimum=0)
    sex = _male(data)
    hp_igg = _number(data, "h_pylori_igg_eiu")
    pgr = _number(data, "pepsinogen_i_ii_ratio")
    g17 = _number(data, "gastrin_17_pmol_l")
    pickled = _binary(data, "regular_pickled_food")
    fried = _binary(data, "regular_fried_food")
    if age < 40:
        raise ValueError("The source rule applies to people aged 40 years or older")
    age_points = 0 if age < 50 else 4 if age < 60 else 6 if age <= 69 else 9
    score = age_points + 4 * sex + 2 * pickled + 2 * fried
    score += 1 if hp_igg >= 34 else 0
    score += 3 if pgr < 3.89 else 0
    score += 0 if g17 <= 1.49 else 3 if g17 <= 5.70 else 4
    if score <= 11:
        band, prevalence = "low", 0.012
    elif score <= 16:
        band, prevalence = "medium", 0.044
    else:
        band, prevalence = "high", 0.123
    return {"score": score, "risk_band": band, "derivation_cohort_prevalence": prevalence}


# NCI BCRA 2.0 source constants for race code 6 (Chinese-American).  Rates are
# annual hazards in 5-year age bands 20–24 through 85–89, expanded below to
# annual ages exactly as the NCI package does.
_BCRA_CHINESE_INCIDENCE = (
    0.000004059636, 0.000045944465, 0.000188279352, 0.000492930493,
    0.000913603501, 0.001471537353, 0.001421275482, 0.001970946494,
    0.001674745804, 0.001821581075, 0.001834477198, 0.001919911972,
    0.002233371071, 0.002247315779,
)
_BCRA_CHINESE_COMPETING_MORTALITY = (
    0.000210649076, 0.000192644865, 0.000244435215, 0.000317895949,
    0.000473261994, 0.000800271380, 0.001217480226, 0.002099836508,
    0.003436889186, 0.006097405623, 0.010664526765, 0.020148678452,
    0.037990796590, 0.098333900733,
)
_BCRA_ASIAN_BETA = (0.55263612260619, 0.07499257592975, 0.27638268294593, 0.79185633720481, 0.0, 0.0)
_BCRA_ASIAN_ONE_MINUS_AR = (0.47519806426735, 0.50316401683903)


def _bcra_category(value: Any, kind: str, initial_age: float) -> int:
    if kind == "biopsies":
        value = int(value)
        return 0 if value in (0, 99) else 1 if value == 1 else 2
    if kind == "menarche":
        value = int(value)
        if value == 99 or 14 <= value <= initial_age:
            return 0
        if 12 <= value <= 13:
            return 1
        if 0 < value <= 11:
            return 2
    if kind == "first_birth":
        value = int(value)
        if value == 99 or value < 20:
            return 0
        if value < 25:
            return 1
        if value == 98 or value < 30:
            return 2
        if value < 98:
            return 3
    if kind == "relatives":
        value = int(value)
        return 0 if value in (0, 99) else 1 if value == 1 else 2
    raise ValueError(f"Unsupported BCRA category {kind}")


def bcra_chinese_american_absolute_risk(data: Mapping[str, Any]) -> float:
    """Implement the public NCI BCRA 2.0 absolute-risk integral for race code 6.

    This is deliberately named for the published source population.  It must
    not be relabelled as a Taiwan incidence model without a Taiwan recalibration.
    ``atypical_hyperplasia`` is True/False when biopsies are positive, and None
    when no biopsy is recorded.  Use age 98 for nulliparity and 99 for unknown,
    matching the NCI source convention.
    """
    t1 = _number(data, "initial_age_years", minimum=20)
    t2 = _number(data, "projection_age_years", minimum=20)
    if t1 >= 90 or t2 > 90 or t1 >= t2:
        raise ValueError("BCRA requires 20 <= initial_age < projection_age <= 90")
    nb_raw = int(data.get("number_of_breast_biopsies", 99))
    hyper = data.get("atypical_hyperplasia")
    if nb_raw in (0, 99):
        if hyper not in (None, 99):
            raise ValueError("atypical_hyperplasia must be None when no biopsy is recorded")
        r_hyp = 1.0
    else:
        if hyper is True:
            r_hyp = 1.82
        elif hyper is False:
            r_hyp = 0.93
        elif hyper in (None, 99):
            r_hyp = 1.0
        else:
            raise ValueError("atypical_hyperplasia must be boolean or None")

    nb = _bcra_category(nb_raw, "biopsies", t1)
    am = _bcra_category(data.get("age_at_menarche", 99), "menarche", t1)
    af = _bcra_category(data.get("age_at_first_live_birth", 99), "first_birth", t1)
    nr = _bcra_category(data.get("first_degree_relatives_with_breast_cancer", 99), "relatives", t1)
    beta = _BCRA_ASIAN_BETA
    lp1 = nb * beta[0] + am * beta[1] + af * beta[2] + nr * beta[3] + af * nr * beta[5] + math.log(r_hyp)
    rr1 = math.exp(lp1)
    rr2 = math.exp(lp1 + nb * beta[4])
    incidence = tuple(rate for rate in _BCRA_CHINESE_INCIDENCE for _ in range(5))
    mortality = tuple(rate for rate in _BCRA_CHINESE_COMPETING_MORTALITY for _ in range(5))
    start = math.floor(t1) - 20
    count = math.ceil(t2) - math.floor(t1)
    cumulative_hazard = 0.0
    risk = 0.0
    for offset in range(count):
        age_index = start + offset
        # Fractional first and final years follow the NCI source loop.
        if count == 1:
            interval = t2 - t1
        elif offset == 0:
            interval = 1.0 - (t1 - math.floor(t1))
        elif offset == count - 1:
            interval = (t2 - math.floor(t2)) if t2 > math.floor(t2) else 1.0
        else:
            interval = 1.0
        one_minus_ar_rr = (_BCRA_ASIAN_ONE_MINUS_AR[0] if age_index < 30 else _BCRA_ASIAN_ONE_MINUS_AR[1]) * (rr1 if age_index < 30 else rr2)
        hazard = incidence[age_index] * one_minus_ar_rr + mortality[age_index]
        risk += (one_minus_ar_rr * incidence[age_index] / hazard) * math.exp(-cumulative_hazard) * (1.0 - math.exp(-hazard * interval))
        cumulative_hazard += hazard * interval
    return risk


__all__ = ["DEFINITIONS", "HUNT_LUNG_CANCER_6Y_URI", "bcra_chinese_american_absolute_risk", "china_gastric_cancer_prescreen_score", "hunt_lung_cancer_6y"]
