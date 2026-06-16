from dataclasses import dataclass
import math
from typing import Any, Dict, List, Optional


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
}

ALGORITHM_DISPLAY_LABELS = {
    "framingham_diabetes": "Framingham 糖尿病風險",
    "chinese_diabetes": "中國糖尿病風險",
    "metabolic_syndrome": "代謝症候群",
    "nafld_fibrosis": "脂肪肝與肝纖維化",
    "framingham_fatty_liver": "Framingham 脂肪肝風險",
    "ausdrisk_diabetes": "AusDRISK 糖尿病風險",
    "vascular_caide": "GVR CAIDE 血管與認知風險",
}

OUTCOME_DISPLAY_LABELS = {
    "diabetes_risk": "糖尿病風險",
    "ncep_mets": "代謝症候群判定",
    "fatty_liver_risk": "脂肪肝/纖維化指標",
    "incident_hepatic_steatosis": "脂肪肝發生風險",
    "dementia_vascular_risk": "血管與認知風險",
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

    def __post_init__(self) -> None:
        if self.missing_data:
            self.score = None
            self.risk_percentage = "資料不足"
            self.risk_level = "missing"
            self.risk_category = "資料缺失"

    def to_api_payload(self) -> Dict[str, Any]:
        return {
            "algorithm": self.algorithm_key,
            "outcome": self.outcome_key,
            "display_name": ALGORITHM_DISPLAY_LABELS.get(self.algorithm_key, self.algorithm_name),
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
        }


def calculate_fhs_diabetes(data: Dict[str, Any]) -> DiseaseRiskResult:
    """CORE.xlsx FHS DM compatible first-pass calculator."""
    missing = _missing(
        data,
        [
            "sex",
            "fasting_glucose",
            "bmi",
            "hdl_cholesterol",
            "triglycerides",
            "systolic_bp",
            "diastolic_bp",
        ],
    )
    score = 0
    sex = _sex(data.get("sex") or data.get("gender"))
    fasting_glucose = _float(data.get("fasting_glucose"))
    bmi = _float(data.get("bmi"))
    hdl = _float(data.get("hdl_cholesterol"))
    triglycerides = _float(data.get("triglycerides"))
    systolic_bp = _float(data.get("systolic_bp"))
    diastolic_bp = _float(data.get("diastolic_bp"))
    parental_history = _bool(data.get("family_history_diabetes"))
    on_bp_treatment = _bool(data.get("anti_hypertensive_drugs") or data.get("on_bp_treatment"))

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
    )


def calculate_chinese_diabetes(data: Dict[str, Any]) -> DiseaseRiskResult:
    """CORE.xlsx CH DM compatible first-pass calculator."""
    missing = _missing(
        data,
        [
            "age",
            "sex",
            "bmi",
            "family_history_diabetes",
            "systolic_bp",
            "anti_hypertensive_drugs",
            "resting_heart_rate",
            "fasting_glucose",
            "triglycerides",
            "using_lipid_lowering_drugs",
        ],
    )
    age = _float(data.get("age"))
    sex = _sex(data.get("sex") or data.get("gender"))
    bmi = _float(data.get("bmi"))
    family_history = _bool(data.get("family_history_diabetes"))
    systolic_bp = _float(data.get("systolic_bp"))
    anti_hypertensive_drugs = _bool(data.get("anti_hypertensive_drugs") or data.get("on_bp_treatment"))
    heart_rate = _float(data.get("resting_heart_rate") or data.get("heart_rate"))
    fasting_glucose = _float(data.get("fasting_glucose"))
    triglycerides = _float(data.get("triglycerides"))
    lipid_drugs = _bool(data.get("using_lipid_lowering_drugs") or data.get("statin"))

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
    if systolic_bp is not None:
        if 120 < systolic_bp <= 129:
            score += 1
        elif 130 <= systolic_bp < 140:
            score += 2
        elif 140 <= systolic_bp < 200:
            score += 4
    if anti_hypertensive_drugs:
        score += 4
    if heart_rate is not None:
        if 70 <= heart_rate < 90:
            score += 1
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
            "anti_hypertensive_drugs": anti_hypertensive_drugs,
            "resting_heart_rate": heart_rate,
            "fasting_glucose": fasting_glucose,
            "triglycerides": triglycerides,
            "using_lipid_lowering_drugs": lipid_drugs,
        },
        recommendation_text=_recommendation(risk_level, missing),
    )


def calculate_metabolic_syndrome(data: Dict[str, Any]) -> DiseaseRiskResult:
    """CORE.xlsx MetS first-pass NCEP metabolic syndrome calculator."""
    missing = _missing(data, ["sex", "waist_circumference", "fasting_glucose", "systolic_bp", "diastolic_bp", "hdl_cholesterol", "triglycerides"])
    sex = _sex(data.get("sex") or data.get("gender"))
    waist = _float(data.get("waist_circumference"))
    glucose = _float(data.get("fasting_glucose"))
    sbp = _float(data.get("systolic_bp"))
    dbp = _float(data.get("diastolic_bp"))
    hdl = _float(data.get("hdl_cholesterol"))
    tg = _float(data.get("triglycerides"))
    dm_or_predm = _bool(data.get("has_diabetes")) or _bool(data.get("prediabetes")) or _bool(data.get("dm_treated"))
    bp_treated = _bool(data.get("anti_hypertensive_drugs") or data.get("has_hypertension"))
    lipid_treated = _bool(data.get("using_lipid_lowering_drugs"))

    flags = {
        "central_obesity": (sex == "M" and waist is not None and waist >= 90) or (sex == "F" and waist is not None and waist >= 80),
        "hyperglycemia": dm_or_predm or (glucose is not None and glucose >= 100),
        "blood_pressure": bp_treated or (sbp is not None and sbp >= 130) or (dbp is not None and dbp >= 85),
        "low_hdl": lipid_treated or (sex == "M" and hdl is not None and hdl <= 40) or (sex == "F" and hdl is not None and hdl <= 50),
        "high_triglycerides": lipid_treated or (tg is not None and tg >= 150),
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
    )


def calculate_nafld(data: Dict[str, Any]) -> DiseaseRiskResult:
    """CORE.xlsx NAFLD first-pass liver steatosis/fibrosis calculator."""
    missing = _missing(data, ["age", "bmi", "fasting_glucose", "ast_got", "alt_gpt", "ast_uln", "platelet_count", "albumin", "triglycerides", "ggt", "waist_circumference", "insulin", "sex"])
    age = _float(data.get("age"))
    bmi = _float(data.get("bmi"))
    glucose = _float(data.get("fasting_glucose"))
    ast = _float(data.get("ast_got"))
    alt = _float(data.get("alt_gpt"))
    ast_uln = _float(data.get("ast_uln"))
    platelets = _float(data.get("platelet_count"))
    albumin = _float(data.get("albumin"))
    tg = _float(data.get("triglycerides"))
    ggt = _float(data.get("ggt"))
    waist = _float(data.get("waist_circumference"))
    insulin = _float(data.get("insulin"))
    sex = _sex(data.get("sex") or data.get("gender"))
    diabetes = _bool(data.get("has_diabetes")) or _bool(data.get("dm_treated"))
    mets = _bool(data.get("metabolic_syndrome"))

    apri = None
    if ast is not None and ast_uln not in (None, 0) and platelets not in (None, 0):
        apri = (ast / ast_uln) / (platelets / 100)
    fib4 = None
    if age is not None and ast is not None and platelets not in (None, 0) and alt not in (None, 0):
        fib4 = (age * ast) / (platelets * math.sqrt(alt))
    nfs = None
    if None not in (age, bmi, glucose, albumin, platelets):
        nfs = -1.675 + (0.037 * age) + (0.094 * bmi) + (1.13 * int(glucose >= 100 or diabetes)) + (0.99 * (ast / alt if alt else 0)) - (0.013 * platelets) - (0.66 * albumin)
    fli = None
    if None not in (tg, bmi, ggt, waist) and tg > 0 and ggt > 0:
        linear = 0.953 * math.log(tg) + 0.139 * bmi + 0.718 * math.log(ggt) + 0.053 * waist - 15.745
        fli = math.exp(linear) / (1 + math.exp(linear)) * 100
    hsi = None
    if ast not in (None, 0) and alt is not None and bmi is not None:
        hsi = 8 * (alt / ast) + bmi + (2 if sex == "F" else 0) + (2 if diabetes else 0)
    lfs = None
    if None not in (insulin, ast, albumin):
        lfs = (1.18 * int(mets)) + (0.45 * int(diabetes)) + (0.15 * insulin) + (0.04 * ast) - (0.94 * albumin) - 2.89

    available_scores = [value for value in (apri, fib4, nfs, fli, hsi, lfs) if value is not None]
    high_flags = 0
    if apri is not None and apri > 1.5:
        high_flags += 1
    if fib4 is not None and fib4 >= 2.67:
        high_flags += 1
    if nfs is not None and nfs >= 0.675:
        high_flags += 1
    if fli is not None and fli >= 60:
        high_flags += 1
    if hsi is not None and hsi >= 36:
        high_flags += 1
    if lfs is not None and lfs >= 0.16:
        high_flags += 1
    risk_level = "high" if high_flags >= 2 else ("moderate" if high_flags == 1 else "low")

    return DiseaseRiskResult(
        algorithm_key="nafld_fibrosis",
        outcome_key="fatty_liver_risk",
        algorithm_name="NAFLD / Fibrosis",
        score=round(sum(available_scores) / len(available_scores), 4) if available_scores else None,
        risk_percentage=f"{high_flags} high indicators",
        risk_level=risk_level,
        risk_category=risk_level,
        missing_data=missing,
        evidence={"apri": apri, "fib4": fib4, "nfs": nfs, "fli": fli, "hsi": hsi, "lfs": lfs},
        recommendation_text=_recommendation(risk_level, missing),
    )


def calculate_framingham_fatty_liver(data: Dict[str, Any]) -> DiseaseRiskResult:
    """CORE.xlsx FHSFLD incident hepatic steatosis calculator."""
    missing = _missing(data, ["sex", "age", "bmi", "alcohol_drinks_per_week", "triglycerides"])
    sex = _sex(data.get("sex") or data.get("gender"))
    age = _float(data.get("age"))
    bmi = _float(data.get("bmi"))
    drinks = _float(data.get("alcohol_drinks_per_week")) or 0
    tg = _float(data.get("triglycerides"))
    probability = None
    if None not in (age, bmi, tg):
        female = 1 if sex == "F" else 0
        linear = -7.7109 + (-1.103 * female) + (0.0374 * age) + (0.1643 * bmi) + (-0.1108 * drinks) + (0.00519 * tg)
        probability = 1 / (1 + math.exp(-linear))
    risk_percentage = f"{round(probability * 100, 1)}%" if probability is not None else "N/A"
    risk_level, risk_category = _risk_level_from_percentage(risk_percentage)

    return DiseaseRiskResult(
        algorithm_key="framingham_fatty_liver",
        outcome_key="incident_hepatic_steatosis",
        algorithm_name="Framingham Fatty Liver",
        score=round(probability, 4) if probability is not None else None,
        risk_percentage=risk_percentage,
        risk_level=risk_level,
        risk_category=risk_category,
        missing_data=missing,
        evidence={"age": age, "sex": sex, "bmi": bmi, "alcohol_drinks_per_week": drinks, "triglycerides": tg},
        recommendation_text=_recommendation(risk_level, missing),
    )


def calculate_ausdrisk_diabetes(data: Dict[str, Any]) -> DiseaseRiskResult:
    """CORE.xlsx AusDM first-pass diabetes risk calculator."""
    missing = _missing(data, ["age", "sex", "waist_circumference", "family_history_diabetes", "prediabetes", "has_hypertension", "vegetables_daily", "is_smoker", "physical_activity_active"])
    age = _float(data.get("age"))
    sex = _sex(data.get("sex") or data.get("gender"))
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
    if _bool(data.get("family_history_diabetes")):
        score += 3
    if _bool(data.get("prediabetes")):
        score += 6
    if _bool(data.get("has_hypertension") or data.get("anti_hypertensive_drugs")):
        score += 2
    if not _bool(data.get("vegetables_daily")):
        score += 1
    if _bool(data.get("is_smoker")):
        score += 2
    if not _bool(data.get("physical_activity_active")):
        score += 2
    if waist is not None:
        if sex == "M":
            score += 7 if waist >= 100 else (4 if waist >= 90 else 0)
        elif sex == "F":
            score += 7 if waist >= 90 else (4 if waist >= 80 else 0)
    if score < 12:
        risk_percentage = "<5%"
    elif score < 16:
        risk_percentage = "5-15%"
    elif score < 20:
        risk_percentage = "15%"
    else:
        risk_percentage = "33%"
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
        evidence={"age": age, "sex": sex, "waist_circumference": waist},
        recommendation_text=_recommendation(risk_level, missing),
    )


def calculate_vascular_caide(data: Dict[str, Any]) -> DiseaseRiskResult:
    """CORE.xlsx GVR CAIDE first-pass dementia/vascular risk calculator."""
    missing = _missing(data, ["age", "sex", "systolic_bp", "bmi", "total_cholesterol", "hdl_cholesterol", "waist_hip_ratio", "has_diabetes", "is_smoker", "apoe_e4"])
    age = _float(data.get("age"))
    sex = _sex(data.get("sex") or data.get("gender"))
    sbp = _float(data.get("systolic_bp"))
    bmi = _float(data.get("bmi"))
    tc = _float(data.get("total_cholesterol"))
    hdl = _float(data.get("hdl_cholesterol"))
    whr = _float(data.get("waist_hip_ratio"))
    apoe = _float(data.get("apoe_e4")) or 0
    score = 0
    if sex == "F":
        score += 1
    if age is not None:
        if 71 <= age <= 75:
            score += 6
        elif 76 <= age <= 80:
            score += 12
        elif 81 <= age <= 85:
            score += 14
        elif age >= 86:
            score += 25
    if _bool(data.get("has_diabetes")):
        score += 2
    if _bool(data.get("is_smoker")):
        score += 7
    if hdl is not None and ((sex == "M" and hdl <= 35) or (sex == "F" and hdl <= 50)):
        score += 4
    if whr is not None and ((sex == "M" and whr > 0.9) or (sex == "F" and whr > 0.85)):
        score += 9
    if sbp is not None and sbp > 140:
        score += 2
    if bmi is not None and bmi > 30:
        score += 2
    if tc is not None and tc > 250:
        score += 2
    if apoe >= 1:
        score += 5
    if score <= 14:
        risk_percentage = "1%"
    elif score <= 22:
        risk_percentage = "3.6x"
    elif score <= 28:
        risk_percentage = "12.6x"
    else:
        risk_percentage = "20.5x"
    risk_level = "high" if score >= 23 else ("moderate" if score >= 15 else "low")

    return DiseaseRiskResult(
        algorithm_key="vascular_caide",
        outcome_key="dementia_vascular_risk",
        algorithm_name="GVR CAIDE",
        score=score,
        risk_percentage=risk_percentage,
        risk_level=risk_level,
        risk_category=risk_level,
        missing_data=missing,
        evidence={"age": age, "sex": sex, "systolic_bp": sbp, "bmi": bmi, "total_cholesterol": tc, "hdl_cholesterol": hdl, "waist_hip_ratio": whr, "apoe_e4": apoe},
        recommendation_text=_recommendation(risk_level, missing),
    )


def _missing(data: Dict[str, Any], fields: List[str]) -> List[str]:
    return [field for field in fields if data.get(field) in (None, "")]


def _float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "treated", "current", "positive"}


def _sex(value: Any) -> str:
    normalized = str(value or "").strip().upper()
    if normalized in {"M", "MALE"}:
        return "M"
    if normalized in {"F", "FEMALE"}:
        return "F"
    return normalized or "U"


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
