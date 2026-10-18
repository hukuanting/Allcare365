"""Expert-source anthropometry/metabolic calculations; canonical mg/dL inputs.

Source locations and published references travel with each definition. The
source workbook conversion factors are retained where its formula uses them;
CVAI transcription errors are corrected against Xia 2016 (4.32, log10 mmol/L).
No index is interpreted as an absolute event probability.
"""
import math


def positive(d, *keys):
    for key in keys:
        if d[key] <= 0:
            raise ValueError(f"{key} must be greater than zero")


def vai(d):
    positive(d, "bmi", "waist_circumference", "triglycerides", "hdl_cholesterol")
    tg = d["triglycerides"] / 88.57
    hdl = d["hdl_cholesterol"] / 38.66976
    if d["sex"] == "M":
        return d["waist_circumference"] / (39.68 + 1.88*d["bmi"]) * tg/1.03 * 1.31/hdl
    return d["waist_circumference"] / (36.58 + 1.89*d["bmi"]) * tg/0.81 * 1.52/hdl


def cvai(d):
    positive(d, "bmi", "waist_circumference", "triglycerides", "hdl_cholesterol")
    tg = d["triglycerides"] / 88.57
    hdl = d["hdl_cholesterol"] / 38.66976
    if d["sex"] == "M":
        return -267.93 + .68*d["age"] + .03*d["bmi"] + 4*d["waist_circumference"] + 22*math.log10(tg) - 16.32*hdl
    return -187.32 + 1.71*d["age"] + 4.32*d["bmi"] + 1.12*d["waist_circumference"] + 39.76*math.log10(tg) - 11.66*hdl


def tyg_bmi(d):
    positive(d, "triglycerides", "fasting_glucose", "bmi")
    return math.log(d["triglycerides"]*d["fasting_glucose"]/2)*d["bmi"]


def lap_cn(d):
    positive(d, "triglycerides", "waist_circumference")
    return (d["waist_circumference"] - (61.3 if d["sex"] == "M" else 55.6))*d["triglycerides"]/88.57


def eag(d):
    if not 4 <= d["hba1c"] <= 12:
        raise ValueError("ADAG measured HbA1c supported range is 4–12%")
    return 28.7*d["hba1c"] - 46.7


def egdr(d):
    positive(d, "waist_circumference", "hba1c")
    return 21.158 - .09*d["waist_circumference"] - 3.407*int(d["has_hypertension"]) - .551*d["hba1c"]


def ratio(d, numerator, denominator):
    positive(d, denominator)
    return d[numerator] / d[denominator]


def ideal(d, method):
    positive(d, "body_height")
    if d["body_height"] < 152.4:
        raise ValueError("Height must be at least 5 feet for this source equation")
    inches = d["body_height"] / 2.54 - 60
    male = d["sex"] == "M"
    constants = {
        "robinson": (52 if male else 49, 1.9 if male else 1.7),
        "miller": (56.2 if male else 53.1, 1.41 if male else 1.36),
        "hamwi": (48.08 if male else 45.36, 2.72 if male else 2.27),
        "devine": (50 if male else 45.5, 2.3),
    }
    base, slope = constants[method]
    return base+slope*inches


def spec(id, name, zh, inputs, fn, *, unit="1", uri=None, source="Cardiometa.xlsx; Cardiometa LIN CK.xlsx", system="metabolic_endocrine", outcome="metabolic_indicator"):
    return dict(id=id, name=name, name_zh=zh, inputs=tuple(inputs), calculator=fn,
                unit=unit, uri=uri, source=source, system=system, outcome=outcome,
                probability=False, horizon=None, version="expert-source-2026-10-10")


DEFINITIONS = [
    spec("visceral_adiposity_index", "Visceral Adiposity Index", "內臟脂肪指數 VAI", ("sex","bmi","waist_circumference","triglycerides","hdl_cholesterol"), vai, uri="https://doi.org/10.2337/dc09-1825"),
    spec("chinese_visceral_adiposity_index", "Chinese Visceral Adiposity Index", "中國內臟脂肪指數 CVAI", ("sex","age","bmi","waist_circumference","triglycerides","hdl_cholesterol"), cvai, uri="https://doi.org/10.1038/srep38214"),
    spec("tyg_bmi", "Triglyceride glucose BMI index", "TyG–BMI 胰島素阻抗指標", ("triglycerides","fasting_glucose","bmi"), tyg_bmi, uri="https://doi.org/10.1371/journal.pone.0149731"),
    spec("chinese_lipid_accumulation_product", "Beijing Lipid Accumulation Product", "北京族群脂質蓄積指數", ("sex","waist_circumference","triglycerides"), lap_cn, source="CMI working.xlsx!Sheet1!M8", uri="https://pubmed.ncbi.nlm.nih.gov/28464592/"),
    spec("estimated_average_glucose", "ADAG estimated average glucose", "HbA1c 推估平均血糖", ("hba1c",), eag, unit="mg/dL", uri="https://doi.org/10.2337/dc08-0545"),
    spec("estimated_glucose_disposal_rate", "Estimated Glucose Disposal Rate (waist)", "腰圍版推估葡萄糖處置速率", ("waist_circumference","has_hypertension","hba1c"), egdr, unit="mg/kg/min", source="Cardiometa.xlsx!Sheet1!C14"),
    spec("waist_height_ratio", "Waist to height ratio", "腰高比", ("waist_circumference","body_height"), lambda d: ratio(d,"waist_circumference","body_height")),
    spec("waist_hip_ratio_indicator", "Waist to hip ratio", "腰臀比", ("waist_circumference","hip_circumference"), lambda d: ratio(d,"waist_circumference","hip_circumference")),
    spec("total_hdl_ratio", "Total cholesterol HDL ratio", "總膽固醇／HDL 比值", ("total_cholesterol","hdl_cholesterol"), lambda d: ratio(d,"total_cholesterol","hdl_cholesterol")),
    spec("ldl_hdl_ratio", "LDL HDL ratio", "LDL／HDL 比值", ("ldl_cholesterol","hdl_cholesterol"), lambda d: ratio(d,"ldl_cholesterol","hdl_cholesterol")),
    spec("tg_hdl_mass_ratio", "TG HDL ratio (mg/dL)", "TG／HDL 質量濃度比", ("triglycerides","hdl_cholesterol"), lambda d: ratio(d,"triglycerides","hdl_cholesterol")),
    spec("atherogenic_index_plasma", "Atherogenic Index of Plasma", "血漿動脈粥樣硬化指數", ("triglycerides","hdl_cholesterol"), lambda d: math.log10(ratio(d,"triglycerides","hdl_cholesterol")*38.66976/88.57)),
    spec("non_hdl_cholesterol", "Non HDL cholesterol", "非 HDL 膽固醇", ("total_cholesterol","hdl_cholesterol"), lambda d: d["total_cholesterol"]-d["hdl_cholesterol"], unit="mg/dL"),
    spec("remnant_cholesterol", "Calculated remnant cholesterol", "計算殘餘膽固醇", ("total_cholesterol","hdl_cholesterol","ldl_cholesterol"), lambda d: d["total_cholesterol"]-d["hdl_cholesterol"]-d["ldl_cholesterol"], unit="mg/dL"),
    spec("non_hdl_hdl_ratio", "Non HDL HDL ratio", "非 HDL／HDL 比值", ("total_cholesterol","hdl_cholesterol"), lambda d: ratio(d,"total_cholesterol","hdl_cholesterol")-1),
    spec("pulse_pressure", "Pulse pressure", "脈壓", ("systolic_bp","diastolic_bp"), lambda d: d["systolic_bp"]-d["diastolic_bp"], unit="mm[Hg]", system="cardiovascular", outcome="hemodynamic_indicator"),
    spec("mean_arterial_pressure", "Mean arterial pressure", "平均動脈壓", ("systolic_bp","diastolic_bp"), lambda d: (d["systolic_bp"]+2*d["diastolic_bp"])/3, unit="mm[Hg]", system="cardiovascular", outcome="hemodynamic_indicator"),
    spec("body_weight_bmi22", "Body weight at BMI 22", "BMI 22 參考體重", ("body_height",), lambda d: 22*(d["body_height"]/100)**2, unit="kg", source="Ideal body weight.xlsx!Sheet1!J21"),
]
for method in ("robinson", "miller", "hamwi", "devine"):
    DEFINITIONS.append(spec(f"ideal_body_weight_{method}", f"{method.title()} ideal body weight", f"{method.title()} 理想體重", ("sex","body_height"), lambda d,m=method: ideal(d,m), unit="kg", source="Ideal body weight.xlsx!Sheet1!F21:I21"))
