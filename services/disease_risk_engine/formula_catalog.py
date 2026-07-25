"""Canonical executable formula library for every approved disease-risk model.

Only deterministic formula code, result shaping, and the explicit formula-to-ID
execution map live here. Database access, clinical-data mapping, persistence,
FHIR projection, and API concerns remain outside this module.

Adding a formula that uses existing canonical inputs requires:
1. Declare governed metadata in algorithm_registry.py.
2. Implement the formula here and add exactly one calculation step below.
3. Add independent published or hospital-approved test vectors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Callable, Dict, Iterable, List, Optional

from .algorithm_registry import (
    CatalogInvariantError,
    algorithm_display_name_zh,
    runtime_registry,
)


_RUNTIME_ALGORITHM_REGISTRY = runtime_registry()


FIELD_DISPLAY_LABELS = {
    "age": "年齡",
    "sex": "性別",
    "gender": "性別",
    "fasting_glucose": "空腹血糖",
    "bmi": "BMI",
    "body_height": "身高",
    "body_weight": "體重",
    "hdl_cholesterol": "HDL 膽固醇",
    "total_cholesterol": "總膽固醇",
    "triglycerides": "三酸甘油脂",
    "systolic_bp": "收縮壓",
    "diastolic_bp": "舒張壓",
    "resting_heart_rate": "靜息心率",
    "heart_rate": "心率",
    "family_history_diabetes": "糖尿病家族史",
    "anti_hypertensive_drugs": "高血壓治療狀態",
    "using_lipid_lowering_drugs": "降血脂治療狀態",
    "statin_use": "Statin 使用狀態",
    "waist_circumference": "腰圍",
    "hip_circumference": "臀圍",
    "waist_hip_ratio": "腰臀比",
    "has_diabetes": "糖尿病狀態",
    "prediabetes": "糖尿病前期狀態",
    "has_hypertension": "高血壓狀態",
    "vegetables_daily": "每日蔬果攝取",
    "is_smoker": "吸菸狀態",
    "physical_activity_active": "規律活動狀態",
    "ast_got": "AST",
    "alt_gpt": "ALT",
    "ast_uln": "AST 正常上限",
    "platelet_count": "血小板",
    "albumin": "白蛋白",
    "ggt": "GGT",
    "insulin": "胰島素",
    "alcohol_drinks_per_week": "每週飲酒量",
    "apoe_e4": "APOE e4",
    "egfr": "估算腎絲球過濾率（eGFR）",
    "creatinine": "血清肌酸酐",
    "cvd_history": "既往心血管疾病狀態",
    "education_high_school_or_below": "高中或以下教育程度",
    "ever_high_blood_glucose": "曾被檢出高血糖",
    "ausdrisk_indigenous_or_pacific": "澳洲原住民／托雷斯海峽島民／太平洋島民／毛利族",
    "ausdrisk_high_risk_birth_region": "AUSDRISK 高風險出生地",
    "ausdrisk_lower_waist_threshold_group": "AUSDRISK 較低腰圍門檻族群",
}

OUTCOME_DISPLAY_LABELS = {
    "diabetes_risk": "糖尿病風險",
    "ncep_mets": "代謝症候群判定",
    "fatty_liver_risk": "脂肪肝/纖維化指標",
    "incident_hepatic_steatosis": "脂肪肝發生風險",
    "dementia_vascular_risk": "血管與認知風險",
    "total_cvd_10_year_risk": "10 年總心血管疾病風險",
    "ascvd_10_year_risk": "10 年動脈粥樣硬化性心血管疾病風險",
    "heart_failure_10_year_risk": "10 年心衰竭風險",
}


@dataclass
class DiseaseRiskResult:
    algorithm_key: str
    outcome_key: str
    algorithm_name: str
    score: Optional[float]
    risk_percentage: str
    risk_level: str
    risk_category: str
    missing_data: List[str]
    evidence: Dict[str, Any]
    recommendation_text: str
    model_version: Optional[str] = None
    method_uri: Optional[str] = None
    applicability: str = "applicable"
    limitations: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.missing_data:
            self.score = None
            self.risk_percentage = "資料不足"
            self.risk_level = "missing"
            self.risk_category = "資料缺失"
        elif self.applicability != "applicable":
            self.score = None
            self.risk_percentage = "不適用"
            self.risk_level = "not_applicable"
            self.risk_category = "不適用"

    def to_api_payload(self) -> Dict[str, Any]:
        metadata = _RUNTIME_ALGORITHM_REGISTRY.get_runtime(self.algorithm_key)
        if metadata is None:
            raise CatalogInvariantError(
                f"Runtime result references an unregistered algorithm: {self.algorithm_key!r}"
            )
        return {
            "algorithm": self.algorithm_key,
            "outcome": self.outcome_key,
            "display_name": algorithm_display_name_zh(self.algorithm_key, self.algorithm_name),
            "display_name_zh": algorithm_display_name_zh(self.algorithm_key, self.algorithm_name),
            "display_name_en": metadata.display_name,
            "outcome_label": OUTCOME_DISPLAY_LABELS.get(self.outcome_key, self.outcome_key),
            "algorithm_name": self.algorithm_name,
            "risk_score": self.score,
            "risk_percentage": self.risk_percentage,
            "risk_level": self.risk_level,
            "risk_category": self.risk_category,
            "missing_data": self.missing_data,
            "missing_data_labels": [FIELD_DISPLAY_LABELS.get(field, field) for field in self.missing_data],
            "evidence": self.evidence,
            "recommendation_text": self.recommendation_text,
            "model_version": self.model_version or metadata.model_version,
            "method_uri": self.method_uri or metadata.method_uri,
            "applicability": self.applicability,
            "limitations": self.limitations,
            "clinical_system": metadata.clinical_system.value,
            "fhir_output": metadata.output_resource.value,
            "governance_status": metadata.governance_status,
        }


def calculate_fhs_diabetes(data: Dict[str, Any]) -> DiseaseRiskResult:
    """CORE.xlsx FHS DM compatible first-pass calculator."""
    data, missing = _validated_data("framingham_diabetes", data)
    score = 0
    age = _float(data.get("age"))
    sex = _sex(data.get("sex"))
    fasting_glucose = _float(data.get("fasting_glucose"))
    bmi = _float(data.get("bmi"))
    hdl = _float(data.get("hdl_cholesterol"))
    triglycerides = _float(data.get("triglycerides"))
    systolic_bp = _float(data.get("systolic_bp"))
    diastolic_bp = _float(data.get("diastolic_bp"))
    parental_history = _bool(data.get("family_history_diabetes"))
    on_bp_treatment = _bool(data.get("anti_hypertensive_drugs"))

    if fasting_glucose is not None and 100 <= fasting_glucose < 126:
        score += 10
    if bmi is not None:
        if 25.0 <= bmi <= 29.9:
            score += 2
        elif bmi >= 30.0:
            score += 5
    if hdl is not None:
        if sex == "M" and hdl < 40:
            score += 5
        elif sex == "F" and hdl < 50:
            score += 5
    if parental_history:
        score += 3
    if triglycerides is not None and triglycerides > 150:
        score += 3
    if (
        (systolic_bp is not None and systolic_bp > 130)
        or (diastolic_bp is not None and diastolic_bp > 85)
        or on_bp_treatment
    ):
        score += 2

    risk_table = {
        0: "<3",
        1: "<3",
        2: "<3",
        3: "<3",
        4: "<3",
        5: "<3",
        6: "<3",
        7: "<3",
        8: "<3",
        9: "<3",
        10: "<3",
        11: "4",
        12: "4",
        13: "5",
        14: "6",
        15: "7",
        16: "9",
        17: "11",
        18: "13",
        19: "15",
        20: "18",
        21: "21",
        22: "25",
        23: "29",
        24: "33",
    }
    risk_percentage = ">35%" if score >= 25 else f"{risk_table.get(score, '<3')}%"
    risk_level, risk_category = _risk_level_from_percentage(risk_percentage)

    return DiseaseRiskResult(
        algorithm_key="framingham_diabetes",
        outcome_key="diabetes_risk",
        algorithm_name="Framingham Diabetes Risk",
        score=score,
        risk_percentage=risk_percentage,
        risk_level=risk_level,
        risk_category=risk_category,
        missing_data=missing,
        evidence={
            "age": age,
            "fasting_glucose": fasting_glucose,
            "bmi": bmi,
            "hdl_cholesterol": hdl,
            "triglycerides": triglycerides,
            "systolic_bp": systolic_bp,
            "diastolic_bp": diastolic_bp,
            "family_history_diabetes": parental_history,
            "anti_hypertensive_drugs": on_bp_treatment,
        },
        recommendation_text=_recommendation(risk_level, missing),
        applicability=(
            "applicable"
            if age is not None and 45 <= age <= 64 and (fasting_glucose is None or fasting_glucose < 126)
            else "not_applicable"
        ),
        model_version="Framingham-official-8y-simple-model",
        method_uri="https://www.framinghamheartstudy.org/fhs-risk-functions/diabetes/",
        limitations=["原模型為 45–64 歲、基線無糖尿病成人之 8 年風險。"],
    )


def calculate_chinese_diabetes(data: Dict[str, Any]) -> DiseaseRiskResult:
    """Kailuan accurate score for incident diabetes (mean follow-up 5.35 years)."""
    data, missing = _validated_data("chinese_diabetes", data)
    for field in ("diastolic_bp", "education_high_school_or_below"):
        if field not in data or data[field] is None:
            if field not in missing:
                missing.append(field)
    age = _float(data.get("age"))
    sex = _sex(data.get("sex"))
    bmi = _float(data.get("bmi"))
    family_history = _bool(data.get("family_history_diabetes"))
    systolic_bp = _float(data.get("systolic_bp"))
    diastolic_bp = _float(data.get("diastolic_bp"))
    anti_hypertensive_drugs = _bool(data.get("anti_hypertensive_drugs"))
    heart_rate = _float(data.get("resting_heart_rate"))
    fasting_glucose = _float(data.get("fasting_glucose"))
    triglycerides = _float(data.get("triglycerides"))
    lipid_drugs = _bool(data.get("using_lipid_lowering_drugs"))
    low_education = _bool(data.get("education_high_school_or_below"))

    score = 0
    if age is not None:
        if 30 <= age < 40:
            score += 6
        elif 40 <= age < 60:
            score += 10
        elif age >= 60:
            score += 11
    if sex == "M":
        score += 2
    if bmi is not None:
        if 24 <= bmi < 28:
            score += 4
        elif bmi >= 28:
            score += 9
    if family_history:
        score += 4
    if low_education:
        score += 3
    # The publication defines one mutually exclusive BP component.  Treatment
    # belongs to the highest category and must not be added a second time.
    if (
        anti_hypertensive_drugs
        or (systolic_bp is not None and systolic_bp >= 140)
        or (diastolic_bp is not None and diastolic_bp >= 90)
    ):
        score += 4
    elif (
        (systolic_bp is not None and systolic_bp >= 120)
        or (diastolic_bp is not None and diastolic_bp >= 80)
    ):
        score += 2
    if heart_rate is not None:
        if 70 <= heart_rate < 80:
            score += 1
        elif 80 <= heart_rate < 90:
            score += 2
        elif heart_rate >= 90:
            score += 4
    if fasting_glucose is not None:
        if 100 <= fasting_glucose <= 110:
            score += 11
        elif fasting_glucose > 110:
            score += 20
    if (triglycerides is not None and triglycerides >= 150) or lipid_drugs:
        score += 3

    if score <= 10:
        risk_percentage = "<3%"
    elif score <= 15:
        risk_percentage = "5%"
    elif score < 20:
        risk_percentage = "8%"
    elif score < 25:
        risk_percentage = "8-12%"
    elif score <= 27:
        risk_percentage = "12-18%"
    elif score < 32:
        risk_percentage = "18-25%"
    else:
        risk_percentage = ">25%"
    risk_level, risk_category = _risk_level_from_percentage(risk_percentage)

    return DiseaseRiskResult(
        algorithm_key="chinese_diabetes",
        outcome_key="diabetes_risk",
        algorithm_name="Chinese Diabetes Risk",
        score=score,
        risk_percentage=risk_percentage,
        risk_level=risk_level,
        risk_category=risk_category,
        missing_data=missing,
        evidence={
            "age": age,
            "sex": sex,
            "bmi": bmi,
            "family_history_diabetes": family_history,
            "systolic_bp": systolic_bp,
            "diastolic_bp": diastolic_bp,
            "anti_hypertensive_drugs": anti_hypertensive_drugs,
            "education_high_school_or_below": low_education,
            "resting_heart_rate": heart_rate,
            "fasting_glucose": fasting_glucose,
            "triglycerides": triglycerides,
            "using_lipid_lowering_drugs": lipid_drugs,
        },
        recommendation_text=_recommendation(risk_level, missing),
        model_version="Kailuan-accurate-score-2016",
        method_uri="https://doi.org/10.1186/s12933-016-0391-9",
        applicability="not_applicable" if fasting_glucose is not None and fasting_glucose >= 126 else "applicable",
        limitations=[
            "原模型在中國 Kailuan 成人、平均 5.35 年追蹤中建立；百分比區間沿用院內文件，並非個人化絕對風險方程。"
        ],
    )


def calculate_metabolic_syndrome(data: Dict[str, Any]) -> DiseaseRiskResult:
    """CORE.xlsx MetS first-pass NCEP metabolic syndrome calculator."""
    data, missing = _validated_data("metabolic_syndrome", data)
    sex = _sex(data.get("sex"))
    waist = _float(data.get("waist_circumference"))
    glucose = _float(data.get("fasting_glucose"))
    sbp = _float(data.get("systolic_bp"))
    dbp = _float(data.get("diastolic_bp"))
    hdl = _float(data.get("hdl_cholesterol"))
    tg = _float(data.get("triglycerides"))
    dm_or_predm = _bool(data.get("has_diabetes")) is True or _bool(data.get("prediabetes")) is True
    bp_treated = _bool(data.get("anti_hypertensive_drugs")) is True or _bool(data.get("has_hypertension")) is True
    flags = {
        "central_obesity": (sex == "M" and waist is not None and waist >= 90) or (sex == "F" and waist is not None and waist >= 80),
        "hyperglycemia": dm_or_predm or (glucose is not None and glucose >= 100),
        "blood_pressure": bp_treated or (sbp is not None and sbp >= 130) or (dbp is not None and dbp >= 85),
        # A generic lipid-lowering medication does not establish treatment for
        # either low HDL or hypertriglyceridemia.  Until indication-specific
        # medication data exists, these two components use measured thresholds.
        "low_hdl": (sex == "M" and hdl is not None and hdl <= 40) or (sex == "F" and hdl is not None and hdl <= 50),
        "high_triglycerides": tg is not None and tg >= 150,
    }
    score = sum(1 for value in flags.values() if value)
    risk_percentage = "yes" if score >= 3 else "no"
    risk_level = "high" if score >= 3 else ("moderate" if score == 2 else "low")
    risk_category = "metabolic_syndrome" if score >= 3 else "not_metabolic_syndrome"

    return DiseaseRiskResult(
        algorithm_key="metabolic_syndrome",
        outcome_key="ncep_mets",
        algorithm_name="Metabolic Syndrome",
        score=score,
        risk_percentage=risk_percentage,
        risk_level=risk_level,
        risk_category=risk_category,
        missing_data=missing,
        evidence=flags,
        recommendation_text=_recommendation(risk_level, missing),
        limitations=[
            "HDL and triglyceride treatment components require indication-specific medication data; generic lipid-lowering therapy is not counted."
        ],
    )



def calculate_ausdrisk_diabetes(data: Dict[str, Any]) -> DiseaseRiskResult:
    """Official AUSDRISK five-year type 2 diabetes point score."""
    data, missing = _validated_data("ausdrisk_diabetes", data)
    extra_required = (
        "ever_high_blood_glucose",
        "ausdrisk_indigenous_or_pacific",
        "ausdrisk_high_risk_birth_region",
        "ausdrisk_lower_waist_threshold_group",
    )
    for field in extra_required:
        if not isinstance(data.get(field), bool) and field not in missing:
            missing.append(field)
    age = _float(data.get("age"))
    sex = _sex(data.get("sex"))
    waist = _float(data.get("waist_circumference"))
    score = 0
    if age is not None:
        if 35 <= age <= 44:
            score += 2
        elif 45 <= age <= 54:
            score += 4
        elif 55 <= age <= 64:
            score += 6
        elif age >= 65:
            score += 8
    if sex == "M":
        score += 3
    if _bool(data.get("ausdrisk_indigenous_or_pacific")) is True:
        score += 2
    if _bool(data.get("ausdrisk_high_risk_birth_region")) is True:
        score += 2
    if _bool(data.get("family_history_diabetes")) is True:
        score += 3
    if _bool(data.get("ever_high_blood_glucose")) is True:
        score += 6
    # Official question asks specifically about current blood-pressure tablets.
    if _bool(data.get("anti_hypertensive_drugs")) is True:
        score += 2
    if _bool(data.get("vegetables_daily")) is False:
        score += 1
    if _bool(data.get("is_smoker")) is True:
        score += 2
    if _bool(data.get("physical_activity_active")) is False:
        score += 2
    if waist is not None:
        lower_thresholds = _bool(data.get("ausdrisk_lower_waist_threshold_group")) is True
        if sex == "M":
            medium, high = (90, 100) if lower_thresholds else (102, 110)
            score += 7 if waist > high else (4 if waist >= medium else 0)
        elif sex == "F":
            medium, high = (80, 90) if lower_thresholds else (88, 100)
            score += 7 if waist > high else (4 if waist >= medium else 0)
    if score <= 5:
        risk_percentage = "1%"
    elif score <= 8:
        risk_percentage = "2%"
    elif score <= 11:
        risk_percentage = "3.3%"
    elif score < 16:
        risk_percentage = "7.1%"
    elif score < 20:
        risk_percentage = "14.3%"
    else:
        risk_percentage = "33.3%"
    risk_level, risk_category = _risk_level_from_percentage(risk_percentage)

    return DiseaseRiskResult(
        algorithm_key="ausdrisk_diabetes",
        outcome_key="diabetes_risk",
        algorithm_name="Australian Type 2 Diabetes Risk",
        score=score,
        risk_percentage=risk_percentage,
        risk_level=risk_level,
        risk_category=risk_category,
        missing_data=missing,
        evidence={
            "age": age,
            "sex": sex,
            "waist_circumference": waist,
            **{field: data.get(field) for field in extra_required},
        },
        recommendation_text=_recommendation(risk_level, missing),
        model_version="AUSDRISK-official-5y",
        method_uri="https://www.health.gov.au/resources/apps-and-tools/the-australian-type-2-diabetes-risk-assessment-tool-ausdrisk",
        applicability="not_applicable" if _bool(data.get("has_diabetes")) is True else "applicable",
        limitations=["預測澳洲成人未來 5 年第二型糖尿病風險；臺灣族群外推需另行驗證。"],
    )


def _validated_data(algorithm_id: str, data: Dict[str, Any]) -> tuple[Dict[str, Any], List[str]]:
    validation = _RUNTIME_ALGORITHM_REGISTRY.validate_required_inputs(algorithm_id, data)
    canonical = dict(data)
    canonical.update(validation.values)
    return canonical, list(validation.missing_fields)


def _float(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return numeric if math.isfinite(numeric) and numeric >= 0 else None


def _bool(value: Any) -> Optional[bool]:
    return value if isinstance(value, bool) else None


def _sex(value: Any) -> str:
    return value if value in {"M", "F"} else "U"


def _risk_level_from_percentage(value: str) -> tuple[str, str]:
    numeric = _risk_numeric(value)
    if numeric < 5:
        return "low", "低風險"
    if numeric < 10:
        return "moderate_low", "中低風險"
    if numeric < 20:
        return "moderate", "中度風險"
    if numeric < 30:
        return "moderate_high", "中高風險"
    return "high", "高風險"


def _risk_numeric(value: str) -> float:
    normalized = (
        str(value)
        .replace("%", "")
        .replace(">", "")
        .replace("<", "")
        .replace("~", "-")
        .strip()
    )
    if "-" in normalized:
        parts = [part for part in normalized.split("-") if part]
        numbers = [float(part) for part in parts]
        return sum(numbers) / len(numbers)
    try:
        return float(normalized)
    except ValueError:
        return 0.0


def _recommendation(risk_level: str, missing: List[str]) -> str:
    if missing:
        return "資料不足，建議先補齊缺漏欄位後重新判讀。"
    if risk_level in {"high", "moderate_high"}:
        return "建議醫師覆核，安排追蹤檢驗與生活型態介入。"
    if risk_level == "moderate":
        return "建議追蹤血糖、血脂、血壓，並於下次回診重新評估。"
    return "維持例行追蹤，持續保存後續健檢與問卷資料。"


# --- Governed closed-form and regression formulas ---

def _logistic(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def _result(
    algorithm_id: str,
    data: Dict[str, Any],
    calculate: Callable[[Dict[str, Any]], float],
    *,
    category: Callable[[float], str] | None = None,
    probability: bool = False,
    positive: tuple[str, ...] = (),
    evidence: Dict[str, Any] | None = None,
    limitations: list[str] | None = None,
    valid_ranges: Dict[str, tuple[float, float]] | None = None,
    applicable: Callable[[Dict[str, Any]], bool] | None = None,
) -> DiseaseRiskResult:
    registry = _RUNTIME_ALGORITHM_REGISTRY
    metadata = registry.get_runtime(algorithm_id)
    validation = registry.validate_required_inputs(algorithm_id, data)
    missing = list(validation.missing_fields)
    values = dict(data)
    values.update(validation.values)
    for field in positive:
        if field not in missing and values.get(field, 0) <= 0:
            missing.append(field)
    for field, (minimum, maximum) in (valid_ranges or {}).items():
        value = values.get(field)
        if field not in missing and not minimum <= value <= maximum:
            missing.append(field)

    is_applicable = not missing and (applicable(values) if applicable else True)
    score = None if missing or not is_applicable else float(calculate(values))
    risk_category = "資料不足" if score is None else (category(score) if category else "已計算")
    if score is None:
        display = "資料不足"
        risk_level = "missing"
    elif probability:
        display = f"{score * 100:.1f}%"
        risk_level = "high" if score >= .20 else "moderate" if score >= .10 else "low"
    else:
        display = f"{score:.3f}".rstrip("0").rstrip(".")
        if risk_category in {"high", "likely", "rule_in", "severe", "high_>30%"}:
            risk_level = "high"
        elif risk_category in {"elevated", "moderate", "elevated_15-30%", "indeterminate"}:
            risk_level = "moderate"
        else:
            risk_level = "low"

    return DiseaseRiskResult(
        algorithm_key=algorithm_id,
        outcome_key=metadata.outcome_key,
        algorithm_name=metadata.display_name,
        score=score,
        risk_percentage=display,
        risk_level=risk_level,
        risk_category=risk_category,
        missing_data=missing,
        evidence=evidence or {key: values.get(key) for key in metadata.required_inputs},
        recommendation_text=(
            "缺少必要且具來源可追溯性的輸入，未執行公式。"
            if missing
            else "此結果為篩檢或風險分層工具，應結合臨床評估，不可單獨作為診斷。"
        ),
        limitations=limitations or [],
        applicability="applicable" if missing or is_applicable else "not_applicable",
    )


def calculate_bmi(data: Dict[str, Any]) -> DiseaseRiskResult:
    return _result("bmi", data, lambda d: d["body_weight"] / (d["body_height"] / 100) ** 2,
                   positive=("body_weight", "body_height"))


def calculate_tyg(data: Dict[str, Any]) -> DiseaseRiskResult:
    return _result("tyg_index", data, lambda d: math.log(d["triglycerides"] * d["fasting_glucose"] / 2),
                   positive=("triglycerides", "fasting_glucose"),
                   limitations=["TyG 使用自然對數；解讀門檻依族群而異。"])


def calculate_homa_ir(data: Dict[str, Any]) -> DiseaseRiskResult:
    return _result("homa_ir", data, lambda d: d["insulin"] * d["fasting_glucose"] / 405,
                   positive=("fasting_glucose",))


def calculate_quicki(data: Dict[str, Any]) -> DiseaseRiskResult:
    return _result("quicki", data, lambda d: 1 / (math.log10(d["insulin"]) + math.log10(d["fasting_glucose"])),
                   positive=("insulin", "fasting_glucose"), limitations=["QUICKI 使用以 10 為底的對數。"])


def calculate_hsi(data: Dict[str, Any]) -> DiseaseRiskResult:
    return _result("hepatic_steatosis_index", data,
                   lambda d: 8 * d["alt_gpt"] / d["ast_got"] + d["bmi"] + (2 if d["has_diabetes"] else 0) + (2 if d["sex"] == "F" else 0),
                   category=lambda s: "rule_out" if s < 30 else "likely" if s >= 36 else "indeterminate",
                   positive=("alt_gpt", "ast_got", "bmi"))


def calculate_lfs(data: Dict[str, Any]) -> DiseaseRiskResult:
    return _result("nafld_liver_fat_score", data,
                   lambda d: -2.89 + 1.18 * d["metabolic_syndrome"] + .45 * (2 if d["has_diabetes"] else 0) + .15 * d["insulin"] + .04 * d["ast_got"] - .94 * d["ast_got"] / d["alt_gpt"],
                   category=lambda s: "rule_in" if s > -.64 else "rule_out",
                   positive=("alt_gpt",), limitations=["糖尿病依原模型編碼為有=2、無=0。"])


def calculate_fli(data: Dict[str, Any]) -> DiseaseRiskResult:
    def formula(d):
        lp = .953 * math.log(d["triglycerides"]) + .139 * d["bmi"] + .718 * math.log(d["ggt"]) + .053 * d["waist_circumference"] - 15.745
        return 100 * _logistic(lp)
    return _result("fatty_liver_index", data, formula,
                   category=lambda s: "rule_out" if s < 30 else "rule_in" if s >= 60 else "indeterminate",
                   positive=("triglycerides", "bmi", "ggt", "waist_circumference"))


def calculate_fib4(data: Dict[str, Any]) -> DiseaseRiskResult:
    return _result("fib4", data, lambda d: d["age"] * d["ast_got"] / (d["platelet_count"] * math.sqrt(d["alt_gpt"])),
                   positive=("age", "alt_gpt", "platelet_count"), limitations=["門檻須依疾病與年齡政策解讀。"])


def calculate_apri(data: Dict[str, Any]) -> DiseaseRiskResult:
    return _result("apri", data, lambda d: ((d["ast_got"] / d["ast_uln"]) * 100) / d["platelet_count"],
                   positive=("ast_uln", "platelet_count"))


def calculate_rpr(data: Dict[str, Any]) -> DiseaseRiskResult:
    return _result("rpr", data, lambda d: d["rdw"] / d["platelet_count"], positive=("platelet_count",))


def calculate_nfs(data: Dict[str, Any]) -> DiseaseRiskResult:
    return _result("nafld_fibrosis_score", data,
                   lambda d: -1.675 + .037*d["age"] + .094*d["bmi"] + 1.13*(d["prediabetes"] or d["has_diabetes"]) + .99*d["ast_got"]/d["alt_gpt"] - .013*d["platelet_count"] - .66*d["albumin"],
                   category=lambda s: "low" if s < -1.455 else "high" if s > .676 else "indeterminate",
                   positive=("alt_gpt", "platelet_count", "albumin"))


def calculate_incident_steatosis(data: Dict[str, Any]) -> DiseaseRiskResult:
    return _result("incident_hepatic_steatosis_model_2", data,
                   lambda d: _logistic(-7.7109 - 1.103*(d["sex"] == "F") + .0374*d["age"] + .1643*d["bmi"] - .1108*d["alcohol_drinks_per_week"] + .00519*d["triglycerides"]),
                   probability=True, positive=("age", "bmi", "triglycerides"),
                   applicable=lambda d: 30 <= d["age"] <= 70 and 16 <= d["bmi"] <= 47 and 25 <= d["triglycerides"] <= 500,
                   limitations=["僅適用於原核定模型定義的族群與預測期間。"])


def calculate_nafld_cv(data: Dict[str, Any]) -> DiseaseRiskResult:
    return _result("nafld_cv_risk_score", data,
                   lambda d: .06*d["age"] + .963*d["mean_platelet_volume"] + .26*(1 if d["has_diabetes"] else 2) - 16.44,
                   category=lambda s: "elevated" if s >= -3.98 else "lower",
                   positive=("age", "mean_platelet_volume"), limitations=["原論文糖尿病編碼為有=1、無=2。"])


def calculate_cambridge(data: Dict[str, Any]) -> DiseaseRiskResult:
    def formula(d):
        bmi_term = 0 if d["bmi"] < 25 else .699 if d["bmi"] < 27.5 else 1.97 if d["bmi"] < 30 else 2.518
        family_term = .753 if d["family_history_diabetes_both"] else .728 if d["family_history_diabetes"] else 0
        smoking_term = .855 if d["is_smoker"] else -.218 if d["former_smoker"] else 0
        return _logistic(-6.322 - .879*(d["sex"] == "F") + 1.222*d["anti_hypertensive_drugs"] + 2.191*d["prescribed_steroids"] + .063*d["age"] + bmi_term + family_term + smoking_term)
    return _result("cambridge_diabetes_risk", data, formula, probability=True, positive=("age", "bmi"))


def _framingham(data: Dict[str, Any], lipids: bool) -> float:
    male = data["sex"] == "M"
    treated = data["anti_hypertensive_drugs"]
    if lipids:
        if male:
            s = 3.06117*math.log(data["age"]) + (1.99881 if treated else 1.93303)*math.log(data["systolic_bp"]) + 1.12370*math.log(data["total_cholesterol"]) - .93263*math.log(data["hdl_cholesterol"]) + .65451*data["is_smoker"] + .57367*data["has_diabetes"]
            return 1 - .88936 ** math.exp(s - 23.9802)
        s = 2.32888*math.log(data["age"]) + (2.82263 if treated else 2.76157)*math.log(data["systolic_bp"]) + 1.20904*math.log(data["total_cholesterol"]) - .70833*math.log(data["hdl_cholesterol"]) + .52873*data["is_smoker"] + .69154*data["has_diabetes"]
        return 1 - .95012 ** math.exp(s - 26.1931)
    if male:
        s = 3.11296*math.log(data["age"]) + (1.92672 if treated else 1.85508)*math.log(data["systolic_bp"]) + .70953*data["is_smoker"] + .79277*math.log(data["bmi"]) + .53160*data["has_diabetes"]
        return 1 - .88431 ** math.exp(s - 23.9388)
    s = 2.72107*math.log(data["age"]) + (2.88267 if treated else 2.81291)*math.log(data["systolic_bp"]) + .61868*data["is_smoker"] + .51125*math.log(data["bmi"]) + .77763*data["has_diabetes"]
    return 1 - .94833 ** math.exp(s - 26.0145)


def calculate_framingham_lipids(data):
    return _result("framingham_cvd_10_lipids", data, lambda d: _framingham(d, True), probability=True,
                   positive=("age", "systolic_bp", "total_cholesterol", "hdl_cholesterol"),
                   applicable=lambda d: 30 <= d["age"] <= 74)


def calculate_framingham_bmi(data):
    return _result("framingham_cvd_10_bmi", data, lambda d: _framingham(d, False), probability=True,
                   positive=("age", "systolic_bp", "bmi"), applicable=lambda d: 30 <= d["age"] <= 74)


def calculate_framingham_hypertension(data):
    def formula(d):
        bx = 22.949536 - .156412*d["age"] - .202933*(d["sex"] == "F") - .033881*d["bmi"] - .05933*d["systolic_bp"] - .128468*d["diastolic_bp"] - .190731*d["is_smoker"] - .166121*d["parental_hypertension_count"] + .001624*d["age"]*d["diastolic_bp"]
        return 1 - math.exp(-math.exp((math.log(4) - bx) / .876925))
    return _result("framingham_hypertension", data, formula, probability=True,
                   positive=("age", "bmi", "systolic_bp", "diastolic_bp"),
                   valid_ranges={"parental_hypertension_count": (0, 2)},
                   applicable=lambda d: 20 <= d["age"] <= 80 and d["systolic_bp"] < 140 and d["diastolic_bp"] < 90)


def calculate_dementia(data):
    def formula(d):
        age, bmi, q = d["age"], d["bmi"], d["deprivation_quintile"]
        p = .20921*(age-65.608) - .00339*(age-65.608)**2 - .0616*(bmi-27.501) + .002508*(bmi-27.501)**2 + .12854*(d["sex"] == "F") + .13199*d["has_hypertension"] + .04477*(d["evaluation_year"]-2003.719)
        p += {1:0, 2:.013371, 3:.117904, 4:.201776, 5:.225529}[q]
        p += -.06792*d["former_smoker"] - .08657*d["is_smoker"] + .443535*d["heavy_alcohol"] + .833612*d["depression_or_antidepressant"] + .252833*d["aspirin_use"] + .577207*d["stroke_tia_history"] + .220728*d["atrial_fibrillation"] + .286701*d["has_diabetes"]
        return 1 - .9969 ** math.exp(p)
    return _result("dementia_risk_score_thin_60_79", data, formula, probability=True,
                   positive=("age", "bmi"), valid_ranges={"deprivation_quintile": (1, 5)},
                   applicable=lambda d: 60 <= d["age"] <= 79,
                   limitations=["模型僅適用 60–79 歲；日曆年依評估日期。"])


def calculate_nomas(data):
    def formula(d):
        male = d["sex"] == "M"
        g = .08338*d["age"] + .37949*male + .02770*d["race_black"] - .22214*d["ethnicity_hispanic"] + .02156*(d["waist_circumference"]/2.54) - .18039*d["moderate_alcohol"] + .16383*d["former_smoker"] + .69142*d["is_smoker"] - .16333*d["moderate_heavy_activity"] - 1.01324*(d["moderate_heavy_activity"]*male) + .00158*d["systolic_bp"] + .01195*d["diastolic_bp"] + .00247*(d["diastolic_bp"]*d["anti_hypertensive_drugs"]) + .26737*d["pvd_history"] + .00432*d["fasting_glucose"] + .05678*(d["total_cholesterol"]/d["hdl_cholesterol"])
        return 1 - math.exp(-.0000306931 * math.exp(g))
    return _result("nomas_global_vascular_risk", data, formula, probability=True,
                   positive=("age", "waist_circumference", "hdl_cholesterol"),
                   limitations=["NOMAS 種族/族裔係數在臺灣族群的可轉移性有限，結果需標示來源族群。"])


def calculate_mayo(data):
    return _result("mayo_pulmonary_nodule", data,
                   lambda d: _logistic(-6.8272 + .0391*d["age"] + .7917*d["ever_smoker"] + 1.3388*d["extrathoracic_cancer_over_5y"] + .1274*d["pulmonary_nodule_diameter"] + 1.0407*d["nodule_spiculation"] + .7838*d["nodule_upper_lobe"]),
                   probability=True, positive=("age", "pulmonary_nodule_diameter"),
                   applicable=lambda d: 4 <= d["pulmonary_nodule_diameter"] <= 30,
                   limitations=["原模型結節直徑範圍 4–30 mm；胸外癌係指距評估至少 5 年。"])


def calculate_christianson(data):
    def formula(d):
        age = d["age"]
        points = (6 if age < 60 else 20 if age < 75 else 41) if d["sex"] == "M" else (0 if age < 60 else 9 if age < 75 else 22)
        points += 0 if d["diabetes_duration_years"] < 5 else 2 if d["diabetes_duration_years"] < 10 else 5
        points += 2 if d["is_smoker"] else 0
        points += 0 if d["hba1c"] < 7 else 2 if d["hba1c"] < 8 else 6
        points += 0 if d["systolic_bp"] < 120 else 1 if d["systolic_bp"] < 140 else 4
        ratio = d["total_cholesterol"] / d["hdl_cholesterol"]
        points += 0 if ratio < 4 else 6 if ratio < 6 else 10
        points += 1 if d["microalbumin_excretion_rate"] >= 30 else 0
        return points
    return _result("christianson_t2dm_chd_score", data, formula,
                   category=lambda s: "average_<15%" if s <= 17 else "elevated_15-30%" if s <= 31 else "high_>30%",
                   positive=("age", "hdl_cholesterol"), applicable=lambda d: d["has_diabetes"],
                   limitations=["僅適用已診斷第二型糖尿病者；依醫院核定的最終點數表實作，未採用前段草稿 IF。"])


def calculate_gad7(data):
    return _result("gad7", data, lambda d: sum(d[f"gad7_q{i}"] for i in range(1, 8)),
                   category=lambda s: "minimal" if s < 5 else "mild" if s < 10 else "moderate" if s < 15 else "severe",
                   valid_ranges={f"gad7_q{i}": (0, 3) for i in range(1, 8)},
                   limitations=["GAD-7 是症狀嚴重度篩檢，不是診斷；需另記功能影響。"])


# --- AHA PREVENT published base equations ---

PREVENT_MODEL_VERSION = "AHA-PREVENT-base-2023-10y"
PREVENT_METHOD_URI = "https://doi.org/10.1161/CIRCULATIONAHA.123.067626"

# Coefficient order follows _prepare_prevent_terms(). Each outcome is modeled
# separately and has sex-specific coefficients, including the intercept.
_PREVENT_COEFFICIENTS = {
    "total_cvd": {
        "F": [0.7939329, 0.0305239, -0.1606857, -0.2394003, 0.3600781, 0.8667604, 0.5360739, 0.0, 0.0, 0.6045917, 0.0433769, 0.3151672, -0.1477655, -0.0663612, 0.1197879, -0.0819715, 0.0306769, -0.0946348, -0.27057, -0.078715, 0.0, -0.1637806, -3.307728],
        "M": [0.7688528, 0.0736174, -0.0954431, -0.4347345, 0.3362658, 0.7692857, 0.4386871, 0.0, 0.0, 0.5378979, 0.0164827, 0.288879, -0.1337349, -0.0475924, 0.150273, -0.0517874, 0.0191169, -0.1049477, -0.2251948, -0.0895067, 0.0, -0.1543702, -3.031168],
    },
    "ascvd": {
        "F": [0.719883, 0.1176967, -0.151185, -0.0835358, 0.3592852, 0.8348585, 0.4831078, 0.0, 0.0, 0.4864619, 0.0397779, 0.2265309, -0.0592374, -0.0395762, 0.0844423, -0.0567839, 0.0325692, -0.1035985, -0.2417542, -0.0791142, 0.0, -0.1671492, -3.819975],
        "M": [0.7099847, 0.1658663, -0.1144285, -0.2837212, 0.3239977, 0.7189597, 0.3956973, 0.0, 0.0, 0.3690075, 0.0203619, 0.2036522, -0.0865581, -0.0322916, 0.114563, -0.0300005, 0.0232747, -0.0927024, -0.2018525, -0.0970527, 0.0, -0.1217081, -3.500655],
    },
    "heart_failure": {
        "F": [0.8998235, 0.0, 0.0, -0.4559771, 0.3576505, 1.038346, 0.583916, -0.0072294, 0.2997706, 0.7451638, 0.0557087, 0.3534442, 0.0, -0.0981511, 0.0, 0.0, 0.0, -0.0946663, -0.3581041, -0.1159453, -0.003878, -0.1884289, -4.310409],
        "M": [0.8972642, 0.0, 0.0, -0.6811466, 0.3634461, 0.923776, 0.5023736, -0.0485841, 0.3726929, 0.6926917, 0.0251827, 0.2980922, 0.0, -0.0497731, 0.0, 0.0, 0.0, -0.1289201, -0.3040924, -0.1401688, 0.0068126, -0.1797778, -3.946391],
    },
}

_PREVENT_OUTCOMES = {
    "total_cvd": {
        "algorithm_key": "aha_prevent_cvd_10y",
        "outcome_key": "total_cvd_10_year_risk",
        "algorithm_name": "AHA PREVENT-CVD Base Equation (10-year)",
    },
    "ascvd": {
        "algorithm_key": "aha_prevent_ascvd_10y",
        "outcome_key": "ascvd_10_year_risk",
        "algorithm_name": "AHA PREVENT-ASCVD Base Equation (10-year)",
    },
    "heart_failure": {
        "algorithm_key": "aha_prevent_hf_10y",
        "outcome_key": "heart_failure_10_year_risk",
        "algorithm_name": "AHA PREVENT-HF Base Equation (10-year)",
    },
}

_PREVENT_VALID_RANGES = {
    "age": (30.0, 79.0),
    "systolic_bp": (90.0, 200.0),
    "total_cholesterol": (130.0, 320.0),
    "hdl_cholesterol": (20.0, 100.0),
    "bmi": (18.5, 39.9),
    "egfr": (15.0, 140.0),
}


def calculate_prevent_risks(data: Dict[str, Any]) -> List[DiseaseRiskResult]:
    """Calculate PREVENT-CVD, PREVENT-ASCVD and PREVENT-HF 10-year risks."""
    prepared: Dict[str, Dict[str, Any]] = {}
    for outcome, metadata in _PREVENT_OUTCOMES.items():
        validation = _RUNTIME_ALGORITHM_REGISTRY.validate_required_inputs(metadata["algorithm_key"], data)
        inputs = dict(validation.values)
        missing = list(validation.missing_fields)
        # PREVENT specifically uses statin exposure, not generic lipid-lowering
        # treatment.  Require the semantically precise field even if an older
        # registry still exposes using_lipid_lowering_drugs.
        if isinstance(data.get("statin_use"), bool):
            inputs["statin_use"] = data["statin_use"]
        elif "statin_use" not in missing:
            missing.append("statin_use")
        for history_field in (
            "cvd_history", "ascvd_history", "chd_history", "pvd_history",
            "stroke_tia_history", "heart_failure_history",
        ):
            if isinstance(data.get(history_field), bool):
                inputs[history_field] = data[history_field]
        limitations = _prevent_input_limitations(inputs)
        if not missing and _known_prevent_cvd(inputs):
            limitations.insert(0, "已有 ASCVD、心衰竭或其他既往心血管疾病紀錄；PREVENT 僅適用於初級預防族群。")
        probability = None
        if not missing and not limitations:
            sex = inputs["sex"]
            terms = _prepare_prevent_terms(inputs)
            coefficients = _PREVENT_COEFFICIENTS[outcome][sex]
            log_odds = sum(coefficient * term for coefficient, term in zip(coefficients, terms))
            probability = 1.0 / (1.0 + math.exp(-log_odds))
        prepared[outcome] = {
            "inputs": inputs,
            "missing": missing,
            "limitations": limitations,
            "probability": probability,
        }

    results = []
    for outcome, metadata in _PREVENT_OUTCOMES.items():
        calculation = prepared[outcome]
        inputs = calculation["inputs"]
        missing = calculation["missing"]
        limitations = calculation["limitations"]
        probability = calculation["probability"]
        if missing:
            recommendation = "PREVENT 必填臨床資料不足，請補齊畫面所列欄位後重新計算。"
            applicability = "insufficient_data"
        elif limitations:
            recommendation = "此患者或輸入值不在 PREVENT 已驗證範圍內，因此未產生風險百分比，請由醫師判讀。"
            applicability = "not_applicable"
        else:
            if probability is None:
                raise RuntimeError("PREVENT probability was not calculated for a valid input contract")
            recommendation = _prevent_recommendation(outcome, probability)
            applicability = "applicable"

        risk_level, risk_category = _prevent_risk_band(outcome, probability)
        evidence = {
            "inputs": inputs,
            "equation": "AHA PREVENT base equation",
            "outcome": outcome,
            "time_horizon_years": 10,
            "cholesterol_unit": "mg/dL",
            "egfr_unit": "mL/min/1.73m2",
            "development_population": "United States adults without known cardiovascular disease",
            "model_version": PREVENT_MODEL_VERSION,
            "reference": PREVENT_METHOD_URI,
        }
        results.append(
            DiseaseRiskResult(
                algorithm_key=metadata["algorithm_key"],
                outcome_key=metadata["outcome_key"],
                algorithm_name=metadata["algorithm_name"],
                score=round(probability, 6) if probability is not None else None,
                risk_percentage=f"{probability * 100:.1f}%" if probability is not None else "N/A",
                risk_level=risk_level,
                risk_category=risk_category,
                missing_data=list(missing),
                evidence=evidence,
                recommendation_text=recommendation,
                model_version=PREVENT_MODEL_VERSION,
                method_uri=PREVENT_METHOD_URI,
                applicability=applicability,
                limitations=list(limitations),
            )
        )
    return results


def _prepare_prevent_terms(inputs: Dict[str, Any]) -> List[float]:
    age = (inputs["age"] - 55.0) / 10.0
    non_hdl = ((inputs["total_cholesterol"] - inputs["hdl_cholesterol"]) * 0.02586) - 3.5
    hdl = ((inputs["hdl_cholesterol"] * 0.02586) - 1.3) / 0.3
    sbp_lt_110 = (min(inputs["systolic_bp"], 110.0) - 110.0) / 20.0
    sbp_gte_110 = (max(inputs["systolic_bp"], 110.0) - 130.0) / 20.0
    diabetes = float(inputs["has_diabetes"])
    smoking = float(inputs["is_smoker"])
    bmi_lt_30 = (min(inputs["bmi"], 30.0) - 25.0) / 5.0
    bmi_gte_30 = (max(inputs["bmi"], 30.0) - 30.0) / 5.0
    egfr_lt_60 = (min(inputs["egfr"], 60.0) - 60.0) / -15.0
    egfr_gte_60 = (max(inputs["egfr"], 60.0) - 90.0) / -15.0
    bp_treatment = float(inputs["anti_hypertensive_drugs"])
    statin = float(inputs["statin_use"])
    return [
        age,
        non_hdl,
        hdl,
        sbp_lt_110,
        sbp_gte_110,
        diabetes,
        smoking,
        bmi_lt_30,
        bmi_gte_30,
        egfr_lt_60,
        egfr_gte_60,
        bp_treatment,
        statin,
        bp_treatment * sbp_gte_110,
        statin * non_hdl,
        age * non_hdl,
        age * hdl,
        age * sbp_gte_110,
        age * diabetes,
        age * smoking,
        age * bmi_gte_30,
        age * egfr_lt_60,
        1.0,
    ]


def _prevent_input_limitations(inputs: Dict[str, Any]) -> List[str]:
    limitations = []
    for field, (lower, upper) in _PREVENT_VALID_RANGES.items():
        value = inputs.get(field)
        if value is not None and not lower <= value <= upper:
            limitations.append(f"{field}={value:g} 超出 PREVENT 驗證範圍 {lower:g}–{upper:g}。")
    total_cholesterol = inputs.get("total_cholesterol")
    hdl = inputs.get("hdl_cholesterol")
    if total_cholesterol is not None and hdl is not None and total_cholesterol <= hdl:
        limitations.append("總膽固醇必須高於 HDL 膽固醇。")
    return limitations


def _known_prevent_cvd(data: Dict[str, Any]) -> bool:
    return any(
        data.get(field) is True
        for field in (
            "cvd_history", "ascvd_history", "chd_history", "pvd_history",
            "stroke_tia_history", "heart_failure_history",
        )
    )


def _prevent_risk_band(outcome: str, probability: Optional[float]) -> tuple[str, str]:
    if probability is None:
        return "missing", "資料不足"
    percentage = probability * 100
    if outcome == "ascvd":
        if percentage < 3:
            return "low", "低風險（<3%）"
        if percentage < 5:
            return "moderate_low", "邊緣風險（3%–<5%）"
        if percentage < 10:
            return "moderate", "中度風險（5%–<10%）"
        return "high", "高風險（≥10%）"
    if percentage < 5:
        return "low", "低風險"
    if percentage < 10:
        return "moderate_low", "中低風險"
    if percentage < 20:
        return "moderate", "中度風險"
    return "high", "高風險"


def _prevent_recommendation(outcome: str, probability: float) -> str:
    population_note = "PREVENT 源自美國成人資料，套用於台灣族群時需由醫師審慎外推。"
    if outcome == "heart_failure":
        return f"PREVENT-HF 目前沒有通用治療切點；請由醫師結合血壓、腎功能、糖尿病與症狀共同判讀。{population_note}"
    if outcome == "ascvd":
        return f"請由醫師依完整病史與現行血脂指引共同決策；此風險值不會自動產生處方。{population_note}"
    if probability >= 0.075:
        return f"10 年 PREVENT-CVD 已達 7.5%；可供第一期高血壓之臨床共同決策參考，仍須由醫師確認適用條件。{population_note}"
    return f"供心血管初級預防與生活型態共同決策參考，建議隨最新臨床資料定期重算。{population_note}"


# --- Hospital-approved expanded formulas verified against primary sources ---

ScalarFormula = Callable[[Dict[str, Any]], float]


@dataclass(frozen=True, slots=True)
class ExpandedFormulaDefinition:
    """Auditable source definition for an approved scalar formula."""

    algorithm_id: str
    display_name: str
    outcome: str
    time_horizon: str
    required_inputs: tuple[str, ...]
    formula: str
    source_file: str
    reference: str
    calculator: ScalarFormula
    limitations: tuple[str, ...] = ()


def _candidate_values(data: Dict[str, Any], fields: tuple[str, ...]) -> Dict[str, Any]:
    missing = [field for field in fields if field not in data or data[field] is None]
    if missing:
        raise ValueError(f"Missing candidate inputs: {', '.join(missing)}")
    return data


def _candidate_bool(data: Dict[str, Any], field: str) -> bool:
    value = data[field]
    if not isinstance(value, bool):
        raise ValueError(f"Candidate input {field} must be a boolean")
    return value


def _candidate_sex(data: Dict[str, Any]) -> str:
    value = str(data["sex"]).upper()
    if value not in {"F", "M"}:
        raise ValueError("Candidate input sex must be 'F' or 'M'")
    return value


def _reynolds_women_10y_formula(data: Dict[str, Any]) -> float:
    """Reynolds Risk Score 10-year cardiovascular risk equation for women."""
    fields = (
        "age", "sex", "systolic_bp", "hs_crp", "total_cholesterol",
        "hdl_cholesterol", "hba1c", "has_diabetes", "is_smoker",
        "parental_mi_before_60",
    )
    d = _candidate_values(data, fields)
    if _candidate_sex(d) != "F":
        raise ValueError("The Reynolds women equation applies only to women")
    age = float(d["age"])
    sbp = float(d["systolic_bp"])
    hs_crp = float(d["hs_crp"])
    total_cholesterol = float(d["total_cholesterol"])
    hdl_cholesterol = float(d["hdl_cholesterol"])
    hba1c = float(d["hba1c"])
    if age < 45:
        raise ValueError("The Reynolds women equation was developed for ages 45 years and older")
    if min(sbp, hs_crp, total_cholesterol, hdl_cholesterol) <= 0:
        raise ValueError("Reynolds logarithmic inputs must be positive")
    has_diabetes = _candidate_bool(d, "has_diabetes")
    is_smoker = _candidate_bool(d, "is_smoker")
    parental_mi = _candidate_bool(d, "parental_mi_before_60")
    if has_diabetes and hba1c <= 0:
        raise ValueError("HbA1c must be positive for a woman with diabetes")
    linear_predictor = (
        0.0799 * age
        + 3.137 * math.log(sbp)
        + 0.180 * math.log(hs_crp)
        + 1.382 * math.log(total_cholesterol)
        - 1.172 * math.log(hdl_cholesterol)
        + 0.134 * hba1c * has_diabetes
        + 0.818 * is_smoker
        + 0.438 * parental_mi
    )
    return 1.0 - 0.98634 ** math.exp(linear_predictor - 22.325)


def _reynolds_men_10y_formula(data: Dict[str, Any]) -> float:
    """Reynolds Risk Score 10-year cardiovascular risk equation for men."""
    fields = (
        "age", "sex", "systolic_bp", "hs_crp", "total_cholesterol",
        "hdl_cholesterol", "is_smoker", "parental_mi_before_60",
    )
    d = _candidate_values(data, fields)
    if _candidate_sex(d) != "M":
        raise ValueError("The Reynolds men equation applies only to men")
    age = float(d["age"])
    sbp = float(d["systolic_bp"])
    hs_crp = float(d["hs_crp"])
    total_cholesterol = float(d["total_cholesterol"])
    hdl_cholesterol = float(d["hdl_cholesterol"])
    if age < 50:
        raise ValueError("The Reynolds men equation was developed for ages 50 years and older")
    if min(age, sbp, hs_crp, total_cholesterol, hdl_cholesterol) <= 0:
        raise ValueError("Reynolds logarithmic inputs must be positive")
    is_smoker = _candidate_bool(d, "is_smoker")
    parental_mi = _candidate_bool(d, "parental_mi_before_60")
    linear_predictor = (
        4.385 * math.log(age)
        + 2.607 * math.log(sbp)
        + 0.102 * math.log(hs_crp)
        + 0.963 * math.log(total_cholesterol)
        - 0.772 * math.log(hdl_cholesterol)
        + 0.405 * is_smoker
        + 0.541 * parental_mi
    )
    return 1.0 - 0.8990 ** math.exp(linear_predictor - 33.097)


def _pooled_cohort_ascvd_10y_formula(data: Dict[str, Any]) -> float:
    """2013 ACC/AHA Pooled Cohort Equation for first hard ASCVD event."""
    fields = (
        "age", "sex", "pce_race", "total_cholesterol", "hdl_cholesterol",
        "systolic_bp", "anti_hypertensive_drugs", "is_smoker", "has_diabetes",
    )
    d = _candidate_values(data, fields)
    age = float(d["age"])
    total_cholesterol = float(d["total_cholesterol"])
    hdl_cholesterol = float(d["hdl_cholesterol"])
    sbp = float(d["systolic_bp"])
    sex = _candidate_sex(d)
    race = str(d["pce_race"]).lower()
    if not 40 <= age <= 79:
        raise ValueError("The Pooled Cohort Equations are intended for ages 40-79 years")
    if race not in {"black", "white"}:
        raise ValueError("PCE race must be 'black' or 'white'; do not silently map another population")
    if min(total_cholesterol, hdl_cholesterol, sbp) <= 0:
        raise ValueError("PCE cholesterol and blood-pressure inputs must be positive")
    treated = _candidate_bool(d, "anti_hypertensive_drugs")
    smoker = _candidate_bool(d, "is_smoker")
    diabetes = _candidate_bool(d, "has_diabetes")
    ln_age = math.log(age)
    ln_tc = math.log(total_cholesterol)
    ln_hdl = math.log(hdl_cholesterol)
    ln_sbp = math.log(sbp)

    if sex == "F" and race == "white":
        individual_sum = (
            -29.799 * ln_age + 4.884 * ln_age ** 2
            + 13.540 * ln_tc - 3.114 * ln_age * ln_tc
            - 13.578 * ln_hdl + 3.149 * ln_age * ln_hdl
            + (2.019 if treated else 1.957) * ln_sbp
            + 7.574 * smoker - 1.665 * ln_age * smoker
            + 0.661 * diabetes
        )
        baseline_survival, mean_sum = 0.9665, -29.18
    elif sex == "F" and race == "black":
        individual_sum = (
            17.114 * ln_age + 0.940 * ln_tc
            - 18.920 * ln_hdl + 4.475 * ln_age * ln_hdl
            + (29.291 * ln_sbp - 6.432 * ln_age * ln_sbp if treated
               else 27.820 * ln_sbp - 6.087 * ln_age * ln_sbp)
            + 0.691 * smoker + 0.874 * diabetes
        )
        baseline_survival, mean_sum = 0.9533, 86.61
    elif sex == "M" and race == "white":
        individual_sum = (
            12.344 * ln_age + 11.853 * ln_tc - 2.664 * ln_age * ln_tc
            - 7.990 * ln_hdl + 1.769 * ln_age * ln_hdl
            + (1.797 if treated else 1.764) * ln_sbp
            + 7.837 * smoker - 1.795 * ln_age * smoker
            + 0.658 * diabetes
        )
        baseline_survival, mean_sum = 0.9144, 61.18
    else:
        individual_sum = (
            2.469 * ln_age + 0.302 * ln_tc - 0.307 * ln_hdl
            + (1.916 if treated else 1.809) * ln_sbp
            + 0.549 * smoker + 0.645 * diabetes
        )
        baseline_survival, mean_sum = 0.8954, 19.54
    return 1.0 - baseline_survival ** math.exp(individual_sum - mean_sum)


def _cardiometabolic_index_formula(data: Dict[str, Any]) -> float:
    """Cardiometabolic Index: TG/HDL-C multiplied by waist/height."""
    fields = (
        "triglycerides", "hdl_cholesterol",
        "waist_circumference", "body_height",
    )
    d = _candidate_values(data, fields)
    triglycerides = float(d["triglycerides"])
    hdl = float(d["hdl_cholesterol"])
    waist = float(d["waist_circumference"])
    height = float(d["body_height"])
    if min(triglycerides, hdl, waist, height) <= 0:
        raise ValueError("CMI inputs must be positive")
    return (triglycerides / hdl) * (waist / height)


def _lipid_accumulation_product_formula(data: Dict[str, Any]) -> float:
    """Original sex-specific Lipid Accumulation Product."""
    fields = ("sex", "waist_circumference", "triglycerides")
    d = _candidate_values(data, fields)
    sex = _candidate_sex(d)
    waist = float(d["waist_circumference"])
    triglycerides = float(d["triglycerides"]) * 0.01129
    waist_constant = 65.0 if sex == "M" else 58.0
    if triglycerides <= 0 or waist <= waist_constant:
        raise ValueError("LAP requires positive TG and waist above its sex-specific constant")
    return (waist - waist_constant) * triglycerides


def _ggt_platelet_ratio_formula(data: Dict[str, Any]) -> float:
    """GGT-to-platelet ratio (GPR), normalized to the laboratory GGT ULN."""
    fields = ("ggt", "ggt_uln", "platelet_count")
    d = _candidate_values(data, fields)
    ggt = float(d["ggt"])
    ggt_uln = float(d["ggt_uln"])
    platelets = float(d["platelet_count"])
    if ggt < 0 or ggt_uln <= 0 or platelets <= 0:
        raise ValueError("GPR requires GGT >= 0, GGT ULN > 0 and platelet count > 0")
    return ((ggt / ggt_uln) / platelets) * 100.0


def _ipag_copd_questionnaire_formula(data: Dict[str, Any]) -> float:
    """International Primary Care Airways Group COPD screening score."""
    fields = (
        "age", "pack_years", "bmi", "weather_affected_cough",
        "sputum_without_cold", "morning_sputum",
        "wheeze_sometimes_or_often", "allergy_history",
    )
    d = _candidate_values(data, fields)
    age = float(d["age"])
    pack_years = float(d["pack_years"])
    bmi = float(d["bmi"])
    if age < 40:
        raise ValueError("The IPAG COPD questionnaire is intended for adults aged 40 years or older")
    if pack_years < 0 or bmi <= 0:
        raise ValueError("IPAG pack-years must be non-negative and BMI must be positive")
    score = 0
    score += 0 if age < 50 else 4 if age < 60 else 8 if age < 70 else 10
    score += 0 if pack_years < 15 else 2 if pack_years < 25 else 3 if pack_years < 50 else 7
    score += 5 if bmi < 25.4 else 1 if bmi <= 29.7 else 0
    score += 3 if _candidate_bool(d, "weather_affected_cough") else 0
    score += 3 if _candidate_bool(d, "sputum_without_cold") else 0
    score += 0 if _candidate_bool(d, "morning_sputum") else 3
    score += 4 if _candidate_bool(d, "wheeze_sometimes_or_often") else 0
    score += 0 if _candidate_bool(d, "allergy_history") else 3
    return float(score)


def _mci_to_ad_3y_formula(data: Dict[str, Any]) -> float:
    """Point score for 3-year progression from amnestic MCI to probable AD."""
    fields = (
        "has_amnestic_mci", "sex", "stubborn_or_resistive",
        "upset_when_separated_from_caregiver", "difficulty_shopping_alone",
        "forgets_appointments", "mean_words_recalled", "orientation_correct",
        "clock_drawing_score",
    )
    d = _candidate_values(data, fields)
    if not _candidate_bool(d, "has_amnestic_mci"):
        raise ValueError("This conversion score applies only to patients with amnestic MCI")
    sex = _candidate_sex(d)
    words = float(d["mean_words_recalled"])
    orientation = int(d["orientation_correct"])
    clock = int(d["clock_drawing_score"])
    if not 0 <= words <= 10 or not 0 <= orientation <= 8 or not 0 <= clock <= 5:
        raise ValueError("MCI score ranges are words 0-10, orientation 0-8 and clock 0-5")
    score = 1 if sex == "F" else 0
    score += 2 if _candidate_bool(d, "stubborn_or_resistive") else 0
    score += 1 if _candidate_bool(d, "upset_when_separated_from_caregiver") else 0
    score += 2 if _candidate_bool(d, "difficulty_shopping_alone") else 0
    score += 2 if _candidate_bool(d, "forgets_appointments") else 0
    score += 0 if words > 6 else 1 if words > 5 else 3 if words > 4 else 4
    score += 0 if orientation == 8 else 1 if orientation == 7 else 2
    score += 0 if clock >= 4 else 2
    return float(score)


def _anu_adri_formula(data: Dict[str, Any]) -> float:
    """Full 15-factor Australian National University AD Risk Index."""
    fields = (
        "age", "sex", "education_years", "bmi", "has_diabetes",
        "depressive_symptoms", "high_cholesterol", "traumatic_brain_injury",
        "smoking_status", "alcohol_category", "social_engagement_level",
        "physical_activity_level", "cognitive_activity_level",
        "fish_servings_per_week", "pesticide_exposure",
    )
    d = _candidate_values(data, fields)
    age = float(d["age"])
    education = float(d["education_years"])
    bmi = float(d["bmi"])
    fish = float(d["fish_servings_per_week"])
    sex = _candidate_sex(d)
    if age <= 0 or education < 0 or bmi <= 0 or fish < 0:
        raise ValueError("ANU-ADRI age/BMI must be positive; education/fish cannot be negative")

    smoking = str(d["smoking_status"]).lower()
    alcohol = str(d["alcohol_category"]).lower()
    social = str(d["social_engagement_level"]).lower()
    physical = str(d["physical_activity_level"]).lower()
    cognitive = str(d["cognitive_activity_level"]).lower()
    category_contracts = {
        "smoking_status": (smoking, {"never", "former", "current"}),
        "alcohol_category": (alcohol, {"none", "light_moderate", "heavy"}),
        "social_engagement_level": (social, {"high", "medium_high", "medium_low", "low"}),
        "physical_activity_level": (physical, {"low", "medium", "high"}),
        "cognitive_activity_level": (cognitive, {"low", "medium", "high"}),
    }
    for field, (value, allowed) in category_contracts.items():
        if value not in allowed:
            raise ValueError(f"ANU-ADRI {field} must be one of {sorted(allowed)}")

    if age < 65:
        age_points = 0
    elif age < 70:
        age_points = 1 if sex == "M" else 5
    elif age < 75:
        age_points = 12 if sex == "M" else 14
    elif age < 80:
        age_points = 18 if sex == "M" else 21
    elif age < 85:
        age_points = 26 if sex == "M" else 29
    elif age < 90:
        age_points = 33 if sex == "M" else 35
    else:
        age_points = 38 if sex == "M" else 41

    score = age_points
    score += 6 if education < 8 else 3 if education <= 11 else 0
    # BMI and high cholesterol are midlife-only components in the original
    # algorithm and are scored zero from age 60 onward.
    if age < 60:
        score += 0 if bmi < 25 else 2 if bmi < 30 else 5
        score += 3 if _candidate_bool(d, "high_cholesterol") else 0
    else:
        _candidate_bool(d, "high_cholesterol")
    score += 3 if _candidate_bool(d, "has_diabetes") else 0
    score += 2 if _candidate_bool(d, "depressive_symptoms") else 0
    score += 4 if _candidate_bool(d, "traumatic_brain_injury") else 0
    score += {"never": 0, "former": 1, "current": 4}[smoking]
    score += {"none": 0, "light_moderate": -3, "heavy": 0}[alcohol]
    score += {"high": 0, "medium_high": 1, "medium_low": 4, "low": 6}[social]
    score += {"low": 0, "medium": -2, "high": -3}[physical]
    score += {"low": 0, "medium": -6, "high": -7}[cognitive]
    score += 0 if fish <= 0.25 else -3 if fish <= 2.0 else -4 if fish <= 4.0 else -5
    score += 2 if _candidate_bool(d, "pesticide_exposure") else 0
    return float(score)


def _brock_pancan_nodule_formula(data: Dict[str, Any]) -> float:
    """Full Brock/PanCan pulmonary-nodule malignancy probability model."""
    fields = (
        "age", "sex", "family_history_lung_cancer", "has_emphysema",
        "pulmonary_nodule_diameter", "nodule_type", "nodule_upper_lobe",
        "nodule_count", "nodule_spiculation",
    )
    d = _candidate_values(data, fields)
    age = float(d["age"])
    diameter = float(d["pulmonary_nodule_diameter"])
    nodule_count = int(d["nodule_count"])
    sex = _candidate_sex(d)
    nodule_type = str(d["nodule_type"]).lower()
    nodule_type_terms = {"solid": 0.0, "part_solid": 0.377, "nonsolid": -0.1276}
    if age <= 0 or diameter <= 0 or nodule_count < 1:
        raise ValueError("Brock age, diameter and nodule count must be positive")
    if nodule_type not in nodule_type_terms:
        raise ValueError("Brock nodule_type must be solid, part_solid or nonsolid")
    linear_predictor = (
        -6.7892
        + 0.0287 * (age - 62.0)
        + 0.6011 * (sex == "F")
        + 0.2961 * _candidate_bool(d, "family_history_lung_cancer")
        + 0.2953 * _candidate_bool(d, "has_emphysema")
        - 5.3854 * ((diameter / 10.0) ** -0.5 - 1.58113883)
        + nodule_type_terms[nodule_type]
        + 0.6581 * _candidate_bool(d, "nodule_upper_lobe")
        - 0.0824 * (nodule_count - 4)
        + 0.7729 * _candidate_bool(d, "nodule_spiculation")
    )
    return _logistic(linear_predictor)


def _va_pulmonary_nodule_formula(data: Dict[str, Any]) -> float:
    """Veterans Affairs solitary pulmonary-nodule malignancy model."""
    fields = ("age", "ever_smoker", "pulmonary_nodule_diameter", "years_since_quitting")
    d = _candidate_values(data, fields)
    age = float(d["age"])
    diameter = float(d["pulmonary_nodule_diameter"])
    years_since_quitting = float(d["years_since_quitting"])
    ever_smoker = _candidate_bool(d, "ever_smoker")
    if age <= 0 or not 7 <= diameter <= 30 or years_since_quitting < 0:
        raise ValueError("VA model requires age > 0, nodule diameter 7-30 mm and years quit >= 0")
    if not ever_smoker and years_since_quitting != 0:
        raise ValueError("years_since_quitting must be 0 for a never-smoker")
    linear_predictor = (
        -8.404
        + 2.061 * ever_smoker
        + 0.779 * (age / 10.0)
        + 0.112 * diameter
        - 0.567 * (years_since_quitting / 10.0)
    )
    return _logistic(linear_predictor)


def _caide_dementia_20y_formula(data: Dict[str, Any]) -> float:
    """Original clinical CAIDE score without the optional APOE extension."""
    fields = (
        "age", "sex", "education_years", "systolic_bp", "bmi",
        "total_cholesterol", "physical_activity_active",
    )
    d = _candidate_values(data, fields)
    age = float(d["age"])
    education = float(d["education_years"])
    score = 0
    score += 0 if age < 47 else 3 if age <= 53 else 4
    score += 0 if education >= 10 else 2 if education >= 7 else 3
    score += 1 if _candidate_sex(d) == "M" else 0
    score += 2 if float(d["systolic_bp"]) > 140 else 0
    score += 2 if float(d["bmi"]) > 30 else 0
    score += 2 if float(d["total_cholesterol"]) * 0.02586 > 6.5 else 0
    score += 0 if _candidate_bool(d, "physical_activity_active") else 1
    return float(score)


def _bdsi_dementia_6y_formula(data: Dict[str, Any]) -> float:
    """Brief Dementia Screening Indicator for adults aged 65–79 years."""
    fields = (
        "age", "education_years", "bmi", "has_diabetes", "stroke_tia_history",
        "needs_help_money_or_medications", "depressive_symptoms",
    )
    d = _candidate_values(data, fields)
    age = float(d["age"])
    if not 65 <= age <= 79:
        raise ValueError("BDSI was developed for ages 65–79 years")
    score = int(age) - 65
    score += 9 if float(d["education_years"]) < 12 else 0
    score += 8 if float(d["bmi"]) < 18.5 else 0
    score += 3 if _candidate_bool(d, "has_diabetes") else 0
    score += 6 if _candidate_bool(d, "stroke_tia_history") else 0
    score += 10 if _candidate_bool(d, "needs_help_money_or_medications") else 0
    score += 6 if _candidate_bool(d, "depressive_symptoms") else 0
    return float(score)


EXPANDED_FORMULAS = {
    "caide_dementia_20y": ExpandedFormulaDefinition(
        algorithm_id="caide_dementia_20y",
        display_name="CAIDE Dementia Risk Score (clinical)",
        outcome="20-year dementia risk score",
        time_horizon="20 years",
        required_inputs=("age", "sex", "education_years", "systolic_bp", "bmi", "total_cholesterol", "physical_activity_active"),
        formula="age points + education points + male(1) + SBP>140(2) + BMI>30(2) + TC>6.5 mmol/L(2) + inactive(1)",
        source_file="dementia risk prediction tools.docx",
        reference="https://doi.org/10.1016/S1474-4422(06)70537-3",
        calculator=_caide_dementia_20y_formula,
        limitations=("Clinical score only; optional APOE extension is not included.", "Developed from midlife Finnish cohorts."),
    ),
    "bdsi_dementia_6y": ExpandedFormulaDefinition(
        algorithm_id="bdsi_dementia_6y",
        display_name="Brief Dementia Screening Indicator",
        outcome="6-year incident dementia screening score",
        time_horizon="6 years",
        required_inputs=("age", "education_years", "bmi", "has_diabetes", "stroke_tia_history", "needs_help_money_or_medications", "depressive_symptoms"),
        formula="(age-65) + education<12(9) + BMI<18.5(8) + diabetes(3) + stroke(6) + help with money/medications(10) + depressive symptoms(6)",
        source_file="dementia risk prediction tools.docx",
        reference="https://doi.org/10.1016/j.jalz.2013.11.006",
        calculator=_bdsi_dementia_6y_formula,
        limitations=("Only for ages 65–79; a score >=22 identifies a higher-risk screening group.",),
    ),
    "reynolds_risk_score_women_10y": ExpandedFormulaDefinition(
        algorithm_id="reynolds_risk_score_women_10y",
        display_name="Reynolds Risk Score for Women",
        outcome="10-year major cardiovascular event probability",
        time_horizon="10 years",
        required_inputs=("age", "sex", "systolic_bp", "hs_crp", "total_cholesterol", "hdl_cholesterol", "hba1c", "has_diabetes", "is_smoker", "parental_mi_before_60"),
        formula="1 - 0.98634^exp(B-22.325), where B=0.0799*age+3.137*ln(SBP)+0.180*ln(hsCRP)+1.382*ln(TC)-1.172*ln(HDL)+0.134*HbA1c*diabetes+0.818*smoker+0.438*parental premature MI",
        source_file="CVD Reynolds.xlsx; Reynolds.docx",
        reference="https://jamanetwork.com/journals/jama/fullarticle/205528",
        calculator=_reynolds_women_10y_formula,
        limitations=("Primary prevention only; developed in initially healthy US women aged 45 years or older.", "Lipids are mg/dL, SBP is mmHg, hs-CRP is mg/L and HbA1c is percent."),
    ),
    "reynolds_risk_score_men_10y": ExpandedFormulaDefinition(
        algorithm_id="reynolds_risk_score_men_10y",
        display_name="Reynolds Risk Score for Men",
        outcome="10-year major cardiovascular event probability",
        time_horizon="10 years",
        required_inputs=("age", "sex", "systolic_bp", "hs_crp", "total_cholesterol", "hdl_cholesterol", "is_smoker", "parental_mi_before_60"),
        formula="1 - 0.8990^exp(B-33.097), where B=4.385*ln(age)+2.607*ln(SBP)+0.102*ln(hsCRP)+0.963*ln(TC)-0.772*ln(HDL)+0.405*smoker+0.541*parental premature MI",
        source_file="CVD Reynolds.xlsx; Reynolds.docx",
        reference="https://pmc.ncbi.nlm.nih.gov/articles/PMC2752381/",
        calculator=_reynolds_men_10y_formula,
        limitations=("Primary prevention only; developed in initially healthy US men aged 50 years or older.", "Lipids are mg/dL, SBP is mmHg and hs-CRP is mg/L."),
    ),
    "pooled_cohort_ascvd_10y": ExpandedFormulaDefinition(
        algorithm_id="pooled_cohort_ascvd_10y",
        display_name="2013 ACC/AHA Pooled Cohort Equation",
        outcome="10-year first hard ASCVD event probability",
        time_horizon="10 years",
        required_inputs=("age", "sex", "pce_race", "total_cholesterol", "hdl_cholesterol", "systolic_bp", "anti_hypertensive_drugs", "is_smoker", "has_diabetes"),
        formula="1 - S0^exp(individual coefficient sum - race/sex-specific mean sum); all four published Black/White women/men equations are encoded",
        source_file="ASCVDtesting.xlsx; ASCVD-Optimal.xlsx",
        reference="https://www.jacc.org/doi/10.1016/j.jacc.2013.11.005",
        calculator=_pooled_cohort_ascvd_10y_formula,
        limitations=("For ages 40-79 without prior ASCVD; predicts first hard ASCVD, not total CVD.", "The source workbook's final survival expression and female baseline were incorrect and were not copied.", "No Asian-specific coefficient set exists; never silently map Taiwanese patients to White."),
    ),
    "cardiometabolic_index": ExpandedFormulaDefinition(
        algorithm_id="cardiometabolic_index",
        display_name="Cardiometabolic Index (CMI)",
        outcome="continuous cardiometabolic risk marker",
        time_horizon="cross-sectional index",
        required_inputs=("triglycerides", "hdl_cholesterol", "waist_circumference", "body_height"),
        formula="(TG / HDL-C) * (waist circumference / height)",
        source_file="CMI working.xlsx; CMI working.docx",
        reference="https://doi.org/10.1016/j.cca.2014.08.034",
        calculator=_cardiometabolic_index_formula,
        limitations=("This is a continuous index, not a calibrated absolute disease probability.", "TG and HDL-C must use the same units; this binding explicitly uses mmol/L. Waist and height use cm."),
    ),
    "lipid_accumulation_product": ExpandedFormulaDefinition(
        algorithm_id="lipid_accumulation_product",
        display_name="Lipid Accumulation Product (LAP)",
        outcome="continuous lipid overaccumulation marker",
        time_horizon="cross-sectional index",
        required_inputs=("sex", "waist_circumference", "triglycerides"),
        formula="men: (waist_cm-65)*TG_mmol/L; women: (waist_cm-58)*TG_mmol/L",
        source_file="CMI working.xlsx; CMI working.docx",
        reference="https://pmc.ncbi.nlm.nih.gov/articles/PMC1236917/",
        calculator=_lipid_accumulation_product_formula,
        limitations=("This is an index, not a diagnosis or calibrated absolute risk.", "The original US population constants are used; the unverified Chinese-LAP constants in the workbook were not substituted."),
    ),
    "ggt_platelet_ratio": ExpandedFormulaDefinition(
        algorithm_id="ggt_platelet_ratio",
        display_name="GGT-to-Platelet Ratio (GPR/GPRI)",
        outcome="non-invasive liver-fibrosis marker",
        time_horizon="cross-sectional index",
        required_inputs=("ggt", "ggt_uln", "platelet_count"),
        formula="((GGT / laboratory GGT ULN) / platelet_count_10^9_per_L) * 100",
        source_file="Liver fibrosis.xlsx; HRA演算法導入自動化(肝纖維化-更新).xlsx; UKPDS DM STROKE Version 2.xlsx",
        reference="https://pmc.ncbi.nlm.nih.gov/articles/PMC5536766/",
        calculator=_ggt_platelet_ratio_formula,
        limitations=("Platelet count must be expressed in 10^9/L and GGT must use the same unit as its laboratory ULN.", "Cutoffs vary by liver-disease population; no generic diagnostic cutoff is assigned.", "A workbook version omitted ULN normalization and multiplied inside the denominator; that version was rejected."),
    ),
    "ipag_copd_questionnaire": ExpandedFormulaDefinition(
        algorithm_id="ipag_copd_questionnaire",
        display_name="IPAG COPD Diagnostic Questionnaire",
        outcome="COPD screening score",
        time_horizon="screening at assessment",
        required_inputs=("age", "pack_years", "bmi", "weather_affected_cough", "sputum_without_cold", "morning_sputum", "wheeze_sometimes_or_often", "allergy_history"),
        formula="published eight-item point score: age + pack-years + BMI + cough/sputum/wheeze/allergy responses",
        source_file="HRA 慢性阻塞性肺病COPD ( 澳洲 ).xlsx",
        reference="https://pmc.ncbi.nlm.nih.gov/articles/PMC1513460/",
        calculator=_ipag_copd_questionnaire_formula,
        limitations=("For adults aged 40 or older; score >=17 is screening-positive and requires spirometry.", "It is not a COPD diagnosis and the local 17-19/20+ severity labels are not part of the validated questionnaire."),
    ),
    "mci_to_ad_3y": ExpandedFormulaDefinition(
        algorithm_id="mci_to_ad_3y",
        display_name="Amnestic MCI to Probable Alzheimer Disease Score",
        outcome="3-year progression from amnestic MCI to probable Alzheimer disease",
        time_horizon="3 years",
        required_inputs=("has_amnestic_mci", "sex", "stubborn_or_resistive", "upset_when_separated_from_caregiver", "difficulty_shopping_alone", "forgets_appointments", "mean_words_recalled", "orientation_correct", "clock_drawing_score"),
        formula="0-16 point score using sex, four informant items, mean word recall, orientation and clock drawing",
        source_file="MCI assess.docx",
        reference="https://pmc.ncbi.nlm.nih.gov/articles/PMC4259326/",
        calculator=_mci_to_ad_3y_formula,
        limitations=("Applies only after amnestic MCI is established using the study's clinical context.", "Published score groups 0-2, 3-8 and 9-16 corresponded to approximately 14%, 51% and 91% 3-year conversion in the development cohort; they are not recalibrated for Taiwan."),
    ),
    "anu_adri": ExpandedFormulaDefinition(
        algorithm_id="anu_adri",
        display_name="Australian National University Alzheimer Disease Risk Index (ANU-ADRI)",
        outcome="future Alzheimer disease risk index",
        time_horizon="not a fixed calibrated probability horizon",
        required_inputs=("age", "sex", "education_years", "bmi", "has_diabetes", "depressive_symptoms", "high_cholesterol", "traumatic_brain_injury", "smoking_status", "alcohol_category", "social_engagement_level", "physical_activity_level", "cognitive_activity_level", "fish_servings_per_week", "pesticide_exposure"),
        formula="sum of the published age-sex, education, midlife BMI/cholesterol, diabetes, depression, TBI, smoking, alcohol, social, physical, cognitive, fish and pesticide point components",
        source_file="journal.pone.0086141.t002.png",
        reference="https://pmc.ncbi.nlm.nih.gov/articles/PMC3696462/",
        calculator=_anu_adri_formula,
        limitations=("This is a relative risk index, not an absolute probability; published quartiles varied by validation cohort.", "BMI and high cholesterol are scored only before age 60 in the original algorithm.", "The local validation-table PNG contains an implausibly reversed education-points column and only the factors available in those cohorts; the full original 15-factor development table was used instead."),
    ),
    "brock_pancan_pulmonary_nodule": ExpandedFormulaDefinition(
        algorithm_id="brock_pancan_pulmonary_nodule",
        display_name="Brock/PanCan Pulmonary Nodule Model (full)",
        outcome="pulmonary nodule malignancy probability",
        time_horizon="diagnostic work-up",
        required_inputs=("age", "sex", "family_history_lung_cancer", "has_emphysema", "pulmonary_nodule_diameter", "nodule_type", "nodule_upper_lobe", "nodule_count", "nodule_spiculation"),
        formula="logistic(-6.7892 + age + female + family-history + emphysema + transformed diameter + nodule type + upper-lobe + nodule-count + spiculation terms)",
        source_file="https-m.medsci.cnscale  .docx; Solitary Pulmonary Nodule.docx",
        reference="https://pmc.ncbi.nlm.nih.gov/articles/PMC6835111/",
        calculator=_brock_pancan_nodule_formula,
        limitations=("Use for CT-detected pulmonary nodules in a population reasonably similar to the screening cohorts.", "This is the full model including spiculation; it must not be confused with reduced model variants."),
    ),
    "va_pulmonary_nodule": ExpandedFormulaDefinition(
        algorithm_id="va_pulmonary_nodule",
        display_name="Veterans Affairs Pulmonary Nodule Model",
        outcome="solitary pulmonary nodule malignancy probability",
        time_horizon="diagnostic work-up",
        required_inputs=("age", "ever_smoker", "pulmonary_nodule_diameter", "years_since_quitting"),
        formula="logistic(-8.404 + 2.061*ever_smoker + 0.779*(age/10) + 0.112*diameter_mm - 0.567*(years_quit/10))",
        source_file="Solitary Pulmonary Nodule.docx",
        reference="https://pmc.ncbi.nlm.nih.gov/articles/PMC3008547/",
        calculator=_va_pulmonary_nodule_formula,
        limitations=("Validated nodule diameter range is 7-30 mm.", "Developed in a predominantly male US Veterans Affairs cohort; transportability requires local validation."),
    ),
}


_EXPANDED_PROBABILITY_ALGORITHMS = {
    "reynolds_risk_score_women_10y",
    "reynolds_risk_score_men_10y",
    "pooled_cohort_ascvd_10y",
    "brock_pancan_pulmonary_nodule",
    "va_pulmonary_nodule",
}


def _expanded_formula_result(algorithm_id: str, data: Dict[str, Any]) -> DiseaseRiskResult:
    definition = EXPANDED_FORMULAS[algorithm_id]
    metadata = _RUNTIME_ALGORITHM_REGISTRY.get_runtime(algorithm_id)
    if metadata is None:
        raise CatalogInvariantError(f"Expanded formula {algorithm_id!r} has no runtime metadata")
    validation = _RUNTIME_ALGORITHM_REGISTRY.validate_required_inputs(algorithm_id, data)
    inputs = dict(validation.values)
    missing = list(validation.missing_fields)
    applicability = "insufficient_data" if missing else "applicable"
    limitations = list(definition.limitations)
    score: Optional[float] = None
    if not missing:
        try:
            score = float(definition.calculator(inputs))
        except ValueError as exc:
            applicability = "not_applicable"
            limitations.append(str(exc))

    risk_level = "informational"
    risk_category = "已計算"
    risk_display = "資料不足" if missing else "不適用" if score is None else f"{score:.3f}"
    if score is not None and algorithm_id in _EXPANDED_PROBABILITY_ALGORITHMS:
        score = min(max(score, 0.0), 1.0)
        risk_display = f"{score * 100:.1f}%"
        risk_level, risk_category = _risk_level_from_percentage(risk_display)
    elif score is not None and algorithm_id == "ipag_copd_questionnaire":
        risk_level = "high" if score >= 17 else "low"
        risk_category = "screen_positive" if score >= 17 else "screen_negative"
    elif score is not None and algorithm_id == "mci_to_ad_3y":
        if score <= 2:
            risk_level, risk_category, risk_display = "low", "low_0_2", "約14%"
        elif score <= 8:
            risk_level, risk_category, risk_display = "moderate", "moderate_3_8", "約51%"
        else:
            risk_level, risk_category, risk_display = "high", "high_9_16", "約91%"
    elif score is not None and algorithm_id == "bdsi_dementia_6y":
        risk_level = "high" if score >= 22 else "low"
        risk_category = "screen_positive" if score >= 22 else "screen_negative"
    elif score is not None and algorithm_id == "caide_dementia_20y":
        caide_bands = (
            (5, "1.0%", "low"),
            (7, "1.9%", "low"),
            (9, "4.2%", "low"),
            (11, "7.4%", "moderate"),
            (15, "16.4%", "moderate"),
        )
        risk_display, risk_level = "16.4%", "high"
        for upper, display, level in caide_bands:
            if score <= upper:
                risk_display, risk_level = display, level
                break
        risk_category = f"score_{int(score)}"

    if missing:
        recommendation = "補齊必要資料後重新計算。"
    elif score is None:
        recommendation = "目前不符合此模型的已驗證適用條件。"
    else:
        recommendation = "結果僅供風險分層，請結合臨床資料判讀。"

    return DiseaseRiskResult(
        algorithm_key=algorithm_id,
        outcome_key=metadata.outcome_key,
        algorithm_name=definition.display_name,
        score=score,
        risk_percentage=risk_display,
        risk_level=risk_level,
        risk_category=risk_category,
        missing_data=missing,
        evidence={
            "inputs": inputs,
            "time_horizon": definition.time_horizon,
            "reference": definition.reference,
        },
        recommendation_text=recommendation,
        model_version=metadata.model_version,
        method_uri=metadata.method_uri,
        applicability=applicability,
        limitations=limitations,
    )


def calculate_reynolds_women_10y(data):
    return _expanded_formula_result("reynolds_risk_score_women_10y", data)


def calculate_reynolds_men_10y(data):
    return _expanded_formula_result("reynolds_risk_score_men_10y", data)


def calculate_pooled_cohort_ascvd_10y(data):
    return _expanded_formula_result("pooled_cohort_ascvd_10y", data)


def calculate_cardiometabolic_index(data):
    return _expanded_formula_result("cardiometabolic_index", data)


def calculate_lipid_accumulation_product(data):
    return _expanded_formula_result("lipid_accumulation_product", data)


def calculate_ggt_platelet_ratio(data):
    return _expanded_formula_result("ggt_platelet_ratio", data)


def calculate_ipag_copd_questionnaire(data):
    return _expanded_formula_result("ipag_copd_questionnaire", data)


def calculate_mci_to_ad_3y(data):
    return _expanded_formula_result("mci_to_ad_3y", data)


def calculate_anu_adri(data):
    return _expanded_formula_result("anu_adri", data)


def calculate_brock_pancan_nodule(data):
    return _expanded_formula_result("brock_pancan_pulmonary_nodule", data)


def calculate_va_pulmonary_nodule(data):
    return _expanded_formula_result("va_pulmonary_nodule", data)


def calculate_caide_dementia_20y(data):
    return _expanded_formula_result("caide_dementia_20y", data)


def calculate_bdsi_dementia_6y(data):
    return _expanded_formula_result("bdsi_dementia_6y", data)


FormulaCalculator = Callable[
    [Dict[str, Any]],
    DiseaseRiskResult | Iterable[DiseaseRiskResult],
]


@dataclass(frozen=True, slots=True)
class FormulaCalculationStep:
    """One explicit, auditable binding between governed IDs and formula code."""

    algorithm_ids: tuple[str, ...]
    calculator: FormulaCalculator


FORMULA_CALCULATION_STEPS = (
    FormulaCalculationStep(("framingham_diabetes",), calculate_fhs_diabetes),
    FormulaCalculationStep(("chinese_diabetes",), calculate_chinese_diabetes),
    FormulaCalculationStep(("metabolic_syndrome",), calculate_metabolic_syndrome),
    FormulaCalculationStep(("bmi",), calculate_bmi),
    FormulaCalculationStep(("tyg_index",), calculate_tyg),
    FormulaCalculationStep(("homa_ir",), calculate_homa_ir),
    FormulaCalculationStep(("quicki",), calculate_quicki),
    FormulaCalculationStep(("hepatic_steatosis_index",), calculate_hsi),
    FormulaCalculationStep(("nafld_liver_fat_score",), calculate_lfs),
    FormulaCalculationStep(("fatty_liver_index",), calculate_fli),
    FormulaCalculationStep(("fib4",), calculate_fib4),
    FormulaCalculationStep(("apri",), calculate_apri),
    FormulaCalculationStep(("rpr",), calculate_rpr),
    FormulaCalculationStep(("nafld_fibrosis_score",), calculate_nfs),
    FormulaCalculationStep(
        ("incident_hepatic_steatosis_model_2",),
        calculate_incident_steatosis,
    ),
    FormulaCalculationStep(("nafld_cv_risk_score",), calculate_nafld_cv),
    FormulaCalculationStep(("cambridge_diabetes_risk",), calculate_cambridge),
    FormulaCalculationStep(("framingham_cvd_10_lipids",), calculate_framingham_lipids),
    FormulaCalculationStep(("framingham_cvd_10_bmi",), calculate_framingham_bmi),
    FormulaCalculationStep(("framingham_hypertension",), calculate_framingham_hypertension),
    FormulaCalculationStep(("dementia_risk_score_thin_60_79",), calculate_dementia),
    FormulaCalculationStep(("nomas_global_vascular_risk",), calculate_nomas),
    FormulaCalculationStep(("mayo_pulmonary_nodule",), calculate_mayo),
    FormulaCalculationStep(("christianson_t2dm_chd_score",), calculate_christianson),
    FormulaCalculationStep(("gad7",), calculate_gad7),
    FormulaCalculationStep(("ausdrisk_diabetes",), calculate_ausdrisk_diabetes),
    FormulaCalculationStep(
        ("aha_prevent_cvd_10y", "aha_prevent_ascvd_10y", "aha_prevent_hf_10y"),
        calculate_prevent_risks,
    ),
    FormulaCalculationStep(("reynolds_risk_score_women_10y",), calculate_reynolds_women_10y),
    FormulaCalculationStep(("reynolds_risk_score_men_10y",), calculate_reynolds_men_10y),
    FormulaCalculationStep(("pooled_cohort_ascvd_10y",), calculate_pooled_cohort_ascvd_10y),
    FormulaCalculationStep(("cardiometabolic_index",), calculate_cardiometabolic_index),
    FormulaCalculationStep(("lipid_accumulation_product",), calculate_lipid_accumulation_product),
    FormulaCalculationStep(("ggt_platelet_ratio",), calculate_ggt_platelet_ratio),
    FormulaCalculationStep(("ipag_copd_questionnaire",), calculate_ipag_copd_questionnaire),
    FormulaCalculationStep(("mci_to_ad_3y",), calculate_mci_to_ad_3y),
    FormulaCalculationStep(("anu_adri",), calculate_anu_adri),
    FormulaCalculationStep(("brock_pancan_pulmonary_nodule",), calculate_brock_pancan_nodule),
    FormulaCalculationStep(("va_pulmonary_nodule",), calculate_va_pulmonary_nodule),
    FormulaCalculationStep(("caide_dementia_20y",), calculate_caide_dementia_20y),
    FormulaCalculationStep(("bdsi_dementia_6y",), calculate_bdsi_dementia_6y),
)


__all__ = [
    "DiseaseRiskResult",
    "ExpandedFormulaDefinition",
    "EXPANDED_FORMULAS",
    "FORMULA_CALCULATION_STEPS",
    "FormulaCalculationStep",
    "PREVENT_METHOD_URI",
    "PREVENT_MODEL_VERSION",
    "calculate_prevent_risks",
    "calculate_anu_adri",
    "calculate_bdsi_dementia_6y",
    "calculate_brock_pancan_nodule",
    "calculate_caide_dementia_20y",
    "calculate_cardiometabolic_index",
    "calculate_ggt_platelet_ratio",
    "calculate_ipag_copd_questionnaire",
    "calculate_lipid_accumulation_product",
    "calculate_mci_to_ad_3y",
    "calculate_pooled_cohort_ascvd_10y",
    "calculate_reynolds_men_10y",
    "calculate_reynolds_women_10y",
    "calculate_va_pulmonary_nodule",
]
