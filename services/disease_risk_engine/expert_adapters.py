"""Canonical input adapters for the source calculators (no database access)."""
from . import hepatic_neuro_calculators as hn
from . import expert_cardiovascular as cv
from .expert_cancer_bone import hunt_lung_cancer_6y, bcra_chinese_american_absolute_risk, china_gastric_cancer_prescreen_score


def plala(d):
    return hn.calculate_plala(d)


def nafic(d):
    return hn.calculate_nafic(d)


def modified_nafic(d):
    return hn.calculate_modified_nafic(d)


def fibroindex(d):
    return hn.calculate_fibroindex({**d, "platelet_count_10e4_per_mm3": d["platelet_count"]/10})


def torre(d):
    return hn.calculate_torre_dementia_screen(d)


def ukpds(d):
    if not d["has_diabetes"] or d["stroke_tia_history"]:
        raise ValueError("UKPDS first-stroke model requires T2DM and no previous stroke")
    age_dx = d["age"] - d["diabetes_duration_years"]
    if age_dx < 20 or age_dx > 65:
        raise ValueError("UKPDS cohort age at diagnosis was 25–65; risk engine excludes age <20")
    return cv.calculate_ukpds_stroke({**d, "sex": "male" if d["sex"] == "M" else "female"})


def hunt(d):
    if not d["ever_smoker"]:
        raise ValueError("HUNT is applicable to ever-smokers")
    if d["is_smoker"] and d["years_since_quitting"] != 0:
        raise ValueError("Current smokers must have years_since_quitting=0")
    if not 0 <= d["indoor_smoke_exposure_hours"] <= 24:
        raise ValueError("Daily indoor smoke exposure hours must be 0–24")
    return hunt_lung_cancer_6y({"age_years": d["age"], "sex": d["sex"],
        "pack_years": d["pack_years"], "cigarettes_per_day": d["cigarettes_per_day"],
        "quit_years": d["years_since_quitting"], "bmi_kg_m2": d["bmi"],
        "indoor_tobacco_smoke_hours_per_day": d["indoor_smoke_exposure_hours"],
        "daily_cough": d["periodical_daily_cough"]})


def nzdcs(d, endpoint):
    if not d["has_diabetes"] or d["cvd_history"]:
        raise ValueError("NZDCS first-event model requires diabetes and no baseline CVD")
    age_dx = d["age"]-d["diabetes_duration_years"]
    if age_dx < 0:
        raise ValueError("Diabetes duration cannot exceed age")
    acr = d["urine_albumin_creatinine_ratio"]/8.84
    threshold = 2.5 if d["sex"] == "M" else 3.5
    inputs = {**d, "age_at_diabetes_diagnosis": age_dx,
        "sex": "male" if d["sex"] == "M" else "female",
        "microalbuminuria": threshold <= acr < 30, "macroalbuminuria": acr>=30}
    return (cv.calculate_nzdcs_cvd_5y if endpoint=="cvd" else cv.calculate_nzdcs_mi_5y)(inputs)


def load(d):
    return hn.calculate_load_probable_score({**d, "current_smoker": d["is_smoker"], "ethnicity": d["load_ethnicity"]})["score"]


def pwv(d):
    components = hn.calculate_expert_epwv(d)
    return {"score": components["epwv_worksheet_average"], "components": components}


def cimt(d):
    return hn.calculate_cimt_age_percentile(d)


def fvc(d):
    components = hn.calculate_expert_fvc_reference(d)
    if components["predicted_fvc_l"] <= 0:
        raise ValueError("Predicted FVC must be positive")
    return {"score": components["expert_adjusted_predicted_fvc_l"], "components": components}


def gail(d, lifetime=False):
    if d["sex"] != "F" or not 35 <= d["age"] <= 85:
        raise ValueError("BCRAT clinical calculator is for women age 35–85")
    if d["bcra_population"] != "chinese_american":
        raise ValueError("This implementation uses the Chinese-American BCRA incidence tables")
    if d["breast_cancer_or_dcis_history"] or d["lcis_history"] or d["brca_mutation"]:
        raise ValueError("BCRAT is not applicable with breast cancer/DCIS/LCIS or BRCA pathogenic variant")
    biopsy = d["number_of_breast_biopsies"]
    if biopsy == 0 and d["atypical_hyperplasia"]:
        raise ValueError("Atypical hyperplasia requires a biopsy history")
    return bcra_chinese_american_absolute_risk({
        "initial_age_years": d["age"], "projection_age_years": 90 if lifetime else d["age"]+5,
        "age_at_menarche": d["age_at_menarche"], "age_at_first_live_birth": d["age_at_first_live_birth"],
        "number_of_breast_biopsies": biopsy,
        "atypical_hyperplasia": None if biopsy==0 else d["atypical_hyperplasia"],
        "first_degree_relatives_with_breast_cancer": d["first_degree_relatives_with_breast_cancer"],
    })


def nelson_diabetes(d):
    if not d["has_diabetes"]:
        raise ValueError("Nelson diabetes branch requires diabetes")
    return cv.calculate_nelson_ckd_egfr45_5y_diabetes({**d,
        "sex": "male" if d["sex"] == "M" else "female",
        "black_race": d["race_black"], "history_cvd": d["cvd_history"],
        "hypertension": d["has_hypertension"]})


def china_gastric(d):
    result = china_gastric_cancer_prescreen_score({**d, "age_years":d["age"]})
    return {"score": result["score"], "components": result}


def prisq(d):
    result = hn.calculate_prisq(d)
    return {"score": result["score"], "components": result}


def spec(id, name, zh, inputs, fn, system, outcome, uri, source, probability=False, horizon=None, limitations=(), interpret=None):
    return dict(id=id, name=name, name_zh=zh, inputs=tuple(inputs), calculator=fn,
        system=system, outcome=outcome, uri=uri, source=source,
        probability=probability, horizon=horizon, limitations=limitations, interpret=interpret)


_NZDCS_INPUTS = ("age","sex","has_diabetes","cvd_history","diabetes_duration_years","former_smoker","is_smoker","hba1c","systolic_bp","total_cholesterol","hdl_cholesterol","east_asian","urine_albumin_creatinine_ratio")

_GAIL_INPUTS = ("sex","age","bcra_population","breast_cancer_or_dcis_history","lcis_history","brca_mutation","age_at_menarche","age_at_first_live_birth","number_of_breast_biopsies","atypical_hyperplasia","first_degree_relatives_with_breast_cancer")

DEFINITIONS = (
    spec("nelson_ckd_egfr45_5y_diabetes", "Nelson five-year incident eGFR below 45 (diabetes)", "Nelson 糖尿病患者五年新發 eGFR 低於45風險",
        ("sex","age","has_diabetes","egfr","hba1c","bmi","urine_albumin_creatinine_ratio","race_black","cvd_history","ever_smoker","has_hypertension","diabetes_medication"),
        nelson_diabetes, "renal", "incident_egfr_below_45_5_year_risk", "https://doi.org/10.1001/jama.2019.17379",
        "GFR.docx; Nelson et al. 2019 eTable 11", True, "5 years", limitations=("適用基線 eGFR>60；採糖尿病分支與所有新發eGFR<45終點。",)),
    spec("china_gastric_cancer_prescreen_score", "Chinese gastric cancer prescreen score", "中國胃癌篩檢前風險積分",
        ("age","sex","regular_pickled_food","regular_fried_food","h_pylori_igg_eiu","pepsinogen_i_ii_ratio","gastrin_17_pmol_l"),
        china_gastric, "other", "gastric_cancer_prescreen_score", "https://doi.org/10.1136/gutjnl-2018-317556",
        "CORE20220414.xlsx!GI-WK; Cai et al. Gut 2019 Table 2", limitations=("40歲以上中國高風險篩檢世代；點數與世代盛行率不是未來個人罹癌機率。",),
        interpret=lambda s: ("low","低風險積分") if s<=11 else (("moderate","中風險積分") if s<=16 else ("high","高風險積分"))),
    spec("prisq_prediabetes_screen", "PRISQ prediabetes screening", "PRISQ 糖尿病前期篩檢分數",
        ("age","sex","bmi","waist_circumference","systolic_bp","diastolic_bp"), prisq, "metabolic_endocrine", "prediabetes_screening_score",
        "https://doi.org/10.1111/jdi.13445", "CORE20220414.xlsx; Abbas 2021 Table 2",
        limitations=("卡達橫斷面糖尿病前期篩檢；不是未來糖尿病發生機率。",),
        interpret=lambda s: ("low","低風險積分") if s<=16 else (("moderate","中風險積分") if s<=27 else ("high","高風險積分"))),
    spec("gail_chinese_american_5y", "NCI BCRA Chinese-American five-year risk", "NCI Gail 華裔美國女性五年乳癌風險",
        _GAIL_INPUTS, gail, "other", "invasive_breast_cancer_5_year_risk",
        "https://bcrisktool.cancer.gov/about.html", "乳癌 (Gail Model).xlsx; NCI BCRA 2.0 race 6", True, "5 years",
        limitations=("使用華裔美國女性 SEER 發生率及競爭死亡率；不是台灣校準率。",)),
    spec("gail_chinese_american_lifetime", "NCI BCRA Chinese-American risk to age 90", "NCI Gail 華裔美國女性至九十歲乳癌風險",
        _GAIL_INPUTS, lambda d: gail(d,True), "other", "invasive_breast_cancer_lifetime_risk",
        "https://bcrisktool.cancer.gov/about.html", "乳癌 (Gail Model).xlsx; NCI BCRA 2.0 race 6", True, "to age 90",
        limitations=("使用華裔美國女性 SEER 發生率及競爭死亡率；不是台灣校準率。",)),
    {**spec("estimated_pwv_expert", "Expert worksheet estimated PWV", "專家工作表推估脈波速度",
        ("age","systolic_bp","diastolic_bp"), pwv, "cardiovascular", "arterial_stiffness_reference", None,
        "CORE 20220414.xlsx!PWV-WK; CORE 20220415.xlsx!PWV-WK", limitations=("保留工作表三成分平均與調整係數；非事件機率。",)), "unit":"m/s"},
    {**spec("cimt_age_sex_percentile", "CIMT age/sex reference percentile", "頸動脈內膜中層厚度年齡性別百分位",
        ("age","sex","cimt_um"), cimt, "cardiovascular", "cimt_reference_percentile", None,
        "AgeCIMY table.docx", limitations=("依專家表於年齡與量測值內線性插值；只涵蓋15–85歲及2.5–97.5百分位。",)), "unit":"%"},
    {**spec("predicted_fvc_expert", "Expert worksheet predicted FVC", "專家工作表肺活量參考值",
        ("age","sex","body_height"), fvc, "respiratory", "predicted_fvc_reference", None,
        "FCV precicted male.xlsx; Pulmonary FCV precicted male.xlsx", limitations=("0.93只表示來源工作表調整，不推論族群，也不是COPD機率。",)), "unit":"L"},
    spec("nzdcs_cvd_5y", "NZDCS five-year CVD", "紐西蘭糖尿病世代五年心血管疾病風險",
        _NZDCS_INPUTS, lambda d: nzdcs(d,"cvd"), "cardiovascular", "cvd_5_year_risk", cv.NZDCS_URI,
        "NZ DM Heart.docx; Elley 2010", True, "5 years", limitations=("採專家整理 East Asian 分支；非其他族群校準版。",)),
    spec("nzdcs_mi_5y", "NZDCS five-year MI", "紐西蘭糖尿病世代五年心肌梗塞風險",
        _NZDCS_INPUTS, lambda d: nzdcs(d,"mi"), "cardiovascular", "mi_5_year_risk", cv.NZDCS_URI,
        "NZ DM Heart.docx; Elley 2010", True, "5 years"),
    spec("load_probable_score", "Probable late-onset Alzheimer disease score", "晚發型阿茲海默症 LOAD 評分",
        ("age","sex","has_diabetes","has_hypertension","is_smoker","load_low_hdl_c","load_high_whr","education_years","load_ethnicity","apoe_e4"),
        load, "neurocognitive", "late_onset_alzheimer_score", "https://doi.org/10.1001/archneurol.2010.136",
        "HRA 晚發型阿茲海默症(LOAD).xlsx; Reitz 2010 Table 4/5",
        limitations=("原研究白人／黑人／Hispanic 65 歲以上；回傳點數，不將組別觀察率當個體機率。",)),
    spec("plala_cirrhosis", "PLALA score", "PLALA 肝硬化篩檢分數",
        ("platelet_count","albumin","ast_got","alt_gpt"), plala, "hepatic", "cirrhosis_screening",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC4123339/", "Liver fibrosis.xlsx!Sheet1!I16:I19",
        limitations=("用於 NAFLD 肝硬化辨識；不是未來發生機率。",),
        interpret=lambda s: ("high", "PLALA 篩檢陽性") if s>=2 else ("low", "PLALA 篩檢陰性")),
    spec("nafic_nash", "NAFIC score", "NAFIC NASH 分數",
        ("sex","ferritin","fasting_insulin","type_iv_collagen_7s"), nafic, "hepatic", "nash_screening",
        "https://pubmed.ncbi.nlm.nih.gov/20842510/", "Liver fibrosis.xlsx; Sumida 2011 corrected definition",
        limitations=("日本活檢 NAFLD 族群之 NASH 辨識評分。",)),
    spec("modified_nafic_nash", "Modified NAFIC score", "修正版 NAFIC NASH 分數",
        ("sex","ferritin","fasting_insulin","type_iv_collagen_7s"), modified_nafic, "hepatic", "nash_screening",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC4020262/", "Liver fibrosis.xlsx; Sumida 2014 corrected definition"),
    spec("fibroindex_hcv", "FibroIndex", "FibroIndex 肝纖維化指數",
        ("platelet_count","ast_got","gamma_globulin"), fibroindex, "hepatic", "liver_fibrosis_screening",
        "https://doi.org/10.1002/hep.21520", "Liver fibrosis.xlsx!Sheet1!F12; Koda 2007 corrected coefficients",
        limitations=("原模型為慢性 C 型肝炎之顯著肝纖維化，不能當 NAFLD 未來機率。",)),
    spec("torre_dementia_screen", "CSHA 2014 dementia heuristic", "Torre 失智症啟發式篩檢估計",
        ("age","vascular_risk_factor_count","family_history_dementia"), torre, "neurocognitive", "dementia_screening",
        "https://www.alzheimer-riese.it/images/stories/files/Docs/dementia_risk_calculator_csah_2014.pdf",
        "HRA Dementia (Torre J.C. Canada)暫未納入.xlsx; CSHA calculator 2014",
        limitations=("來源為年齡及危險因子倍增的啟發式估計（單位百分比）；沒有指定縱向預測期，不作校準後事件機率。",)),
    spec("ukpds_stroke_10y", "UKPDS Risk Engine 2.0 stroke", "UKPDS 第二型糖尿病十年中風風險",
        ("age","sex","has_diabetes","stroke_tia_history","diabetes_duration_years","is_smoker","atrial_fibrillation","systolic_bp","total_cholesterol","hdl_cholesterol"),
        ukpds, "cardiovascular", "stroke_10_year_risk", cv.UKPDS_STROKE_URI,
        "UKPDS DM STROKE Version 1.xlsx; UKPDS DM STROKE Version 2.xlsx; Oxford corrected 2.0 equation", True, "10 years"),
    spec("hunt_lung_cancer_6y", "HUNT Lung Cancer Model", "HUNT 肺癌六年風險",
        ("age","sex","ever_smoker","is_smoker","pack_years","cigarettes_per_day","years_since_quitting","bmi","indoor_smoke_exposure_hours","periodical_daily_cough"),
        hunt, "respiratory", "lung_cancer_6_year_risk", "https://doi.org/10.1016/j.ebiom.2022.104187",
        "How does lung cancer risk calculator work.docx; Markaki 2022 corrigendum", True, "6 years"),
)
