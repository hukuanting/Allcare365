import math
from typing import Optional, Union, Tuple

def calculate_fhs_dm_score(
    sex: str,
    fasting_glucose: Optional[float] = None,
    bmi: Optional[float] = None,
    hdl_c_level: Optional[float] = None,
    parental_history: bool = False,
    triglyceride_level: Optional[float] = None,
    blood_pressure: Union[Tuple[Optional[float], Optional[float]], Optional[float]] = None,
    on_bp_treatment: bool = False
) -> Tuple[int, str]:
    """
    回傳 Framingham Heart Study 糖尿病風險分數與百分比文字 (例如 '7%', '>35%', '<3%')
    """
    score = 0

    # 空腹血糖 100-125 mg/dL
    if fasting_glucose is not None and 100 <= fasting_glucose < 126:
        score += 10

    # BMI
    if bmi is not None:
        if 25.0 <= bmi <= 29.9:
            score += 2
        elif bmi > 30.0:
            score += 5

    # HDL-C
    if hdl_c_level is not None:
        if sex == 'M' and hdl_c_level < 40:
            score += 5
        elif sex == 'F' and hdl_c_level < 50:
            score += 5

    # 家族糖尿病史
    if parental_history:
        score += 3

    # 三酸甘油脂 >150
    if triglyceride_level is not None and triglyceride_level > 150:
        score += 3

    # 血壓 >130/85 或正在服藥
    sbp_val, dbp_val = None, None
    if isinstance(blood_pressure, (tuple, list)):
        sbp_val, dbp_val = blood_pressure
    elif blood_pressure is not None:
        sbp_val = blood_pressure
    if (sbp_val is not None and sbp_val > 130) or (dbp_val is not None and dbp_val > 85) or on_bp_treatment:
        score += 2

    # 風險對照表
    risk_table = {
        10: '<3', 11: '4', 12: '4', 13: '5', 14: '6', 15: '7', 16: '9', 17: '11',
        18: '13', 19: '15', 20: '18', 21: '21', 22: '25', 23: '29', 24: '33'
    }
    if score >= 25:
        base = '>35'
    else:
        base = risk_table.get(score, '<3')

    # 加上百分比符號
    risk_percent = f"{base}%"

    return score, risk_percent

def calculate_egfr(creatinine: float, age: float, gender: str) -> float:
    """計算 eGFR (CKD-EPI 公式)"""
    # 確保 creatinine 和 age 是 float 類型
    creatinine = float(creatinine)
    age = float(age)
    
    if gender.upper() == 'F':  # 女性
        if creatinine <= 0.7:
            return 144 * (creatinine / 0.7) ** -0.329 * 0.993 ** age
        else:
            return 144 * (creatinine / 0.7) ** -1.209 * 0.993 ** age
    else:  # 男性
        if creatinine <= 0.9:
            return 141 * (creatinine / 0.9) ** -0.411 * 0.993 ** age
        else:
            return 141 * (creatinine / 0.9) ** -1.209 * 0.993 ** age

def women_cvd_10(age: float, TC: float, HDL: float, SBP: float, eGFR: float,
                 diabetes: int, current_smoker: int, anti_hyp_med: int, statin: int) -> float:
    # 確保所有參數都是正確的數據類型
    age = float(age)
    TC = float(TC)
    HDL = float(HDL)
    SBP = float(SBP)
    eGFR = float(eGFR)
    
    age_factor = (age - 55) / 10.0
    chol_term = ((TC - HDL) * 0.02586) - 3.5
    hdl_term = (float(HDL) * 0.02586 - 1.3) / 0.3
    SBP_term1 = (min(float(SBP), 110) - 110) / 20.0
    SBP_term2 = (max(float(SBP), 110) - 130) / 20.0
    eGFR_term1 = (min(float(eGFR), 60) - 60) / -15.0
    eGFR_term2 = (max(float(eGFR), 60) - 90) / -15.0

    log_odds = (
        -3.307728 +
        0.7939329 * age_factor +
        0.0305239 * chol_term +
        (-0.1606857 * hdl_term) +
        (-0.2394003 * SBP_term1) +
        0.360078  * SBP_term2 +
        0.8667604 * diabetes +
        0.5360739 * current_smoker +
        0.6045917 * eGFR_term1 +
        0.0433769 * eGFR_term2 +
        0.3151672 * anti_hyp_med +
        (-0.1477655 * statin) +
        (-0.0663612 * anti_hyp_med * SBP_term2) +
        0.1197879 * statin * chol_term +
        (-0.0819715 * age_factor * chol_term) +
        0.0306769 * age_factor * hdl_term +
        (-0.0946348 * age_factor * SBP_term2) +
        (-0.27057   * age_factor * diabetes) +
        (-0.078715  * age_factor * current_smoker) +
        (-0.1637806 * age_factor * eGFR_term1)
    )

    return math.exp(log_odds) / (1 + math.exp(log_odds))

def man_cvd_10(age: float, TC: float, HDL: float, SBP: float, eGFR: float,
                 diabetes: int, current_smoker: int, anti_hyp_med: int, statin: int) -> float:
        
        # Convert cholesterol from mg/dL to mmol/L (multiply by 0.02586)
        tc_mmol = TC * 0.02586
        hdl_mmol = HDL * 0.02586
        
        # Calculate base terms
        age_term = (age - 55) / 10
        lipid_term = (tc_mmol - hdl_mmol) - 3.5
        hdl_term = (hdl_mmol - 1.3) / 0.3
        # 確保所有參數都是正確的數據類型
        age = float(age)
        TC = float(TC)
        HDL = float(HDL)
        SBP = float(SBP)
        eGFR = float(eGFR)
        
        sbp_low = min(SBP, 110)
        sbp_high = max(SBP, 110)
        egfr_low = min(eGFR, 60)
        egfr_high = max(eGFR, 60)
        
        # Convert boolean values to numeric (1 for True, 0 for False)
        diabetes_num = 1 if diabetes else 0
        smoker_num = 1 if current_smoker else 0
        antihypertensive_num = 1 if anti_hyp_med else 0
        statin_num = 1 if statin else 0
        
        # Calculate log-odds based on the provided formula
        log_odds = (
            -3.031168 + 
            0.7688528 * age_term +
            0.0736174 * lipid_term -
            0.0954431 * hdl_term -
            0.4347345 * (sbp_low - 110) / 20 +
            0.3362658 * (sbp_high - 130) / 20 +
            0.7692857 * diabetes_num +
            0.4386871 * smoker_num +
            0.5378979 * (egfr_low - 60) / -15 +
            0.0164827 * (egfr_high - 90) / -15 +
            0.288879 * antihypertensive_num -
            0.1337349 * statin_num -
            0.0475924 * antihypertensive_num * (sbp_high - 130) / 20 +
            0.150273 * statin_num * lipid_term -
            0.0517874 * age_term * lipid_term +
            0.0191169 * age_term * hdl_term -
            0.1049477 * age_term * (sbp_high - 130) / 20 -
            0.2251948 * age_term * diabetes_num -
            0.0895067 * age_term * smoker_num -
            0.1543702 * age_term * (egfr_low - 60) / -15
        )      
        return math.exp(log_odds) / (1 + math.exp(log_odds))

def women_ascvd_10(age: float, TC: float, HDL: float, SBP: float, eGFR: float,
                 diabetes: int, current_smoker: int, anti_hyp_med: int, statin: int) -> float:
    age_factor = (age - 55) / 10.0
    chol_term = ((float(TC) - float(HDL)) * 0.02586) - 3.5
    hdl_term = (float(HDL) * 0.02586 - 1.3) / 0.3
    SBP_term1 = (min(float(SBP), 110) - 110) / 20.0
    SBP_term2 = (max(float(SBP), 110) - 130) / 20.0
    eGFR_term1 = (min(float(eGFR), 60) - 60) / -15.0
    eGFR_term2 = (max(float(eGFR), 60) - 90) / -15.0

    log_odds = (
        -3.819975 +
        0.719883 * age_factor +
        0.1176967 * chol_term +
        (-0.151185 * hdl_term) +
        (-0.0835358 * SBP_term1) +
        0.3592852 * SBP_term2 +
        0.8348585 * diabetes +
        0.4831078 * current_smoker +
        0.4864619 * eGFR_term1 +
        0.0397779 * eGFR_term2 +
        0.2265309 * anti_hyp_med +
        (-0.0592374 * statin) +
        (-0.0395762 * anti_hyp_med * SBP_term2) +
        0.0844423 * statin * chol_term +
        (-0.0567839 * age_factor * chol_term) +
        0.0325692 * age_factor * hdl_term +
        (-0.1035985 * age_factor * SBP_term2) +
        (-0.2417542 * age_factor * diabetes) +
        (-0.0791142 * age_factor * current_smoker) +
        (-0.1671492 * age_factor * eGFR_term1)
    )

    return math.exp(log_odds) / (1 + math.exp(log_odds))

def man_ascvd_10(age: float, TC: float, HDL: float, SBP: float, eGFR: float,
                 diabetes: int, current_smoker: int, anti_hyp_med: int, statin: int) -> float:
    # 確保所有參數都是正確的數據類型
    age = float(age)
    TC = float(TC)
    HDL = float(HDL)
    SBP = float(SBP)
    eGFR = float(eGFR)
    
    age_factor = (age - 55) / 10.0
    chol_term = ((TC - HDL) * 0.02586) - 3.5

    hdl_term = (float(HDL) * 0.02586 - 1.3) / 0.3

    SBP_term1 = (min(float(SBP), 110) - 110) / 20.0
    SBP_term2 = (max(float(SBP), 110) - 130) / 20.0

    eGFR_term1 = (min(float(eGFR), 60) - 60) / -15.0
    eGFR_term2 = (max(float(eGFR), 60) - 90) / -15.0

    log_odds = (
        -3.500655 +
        0.7099847 * age_factor +
        0.1658663 * chol_term +
        (-0.1144285) * hdl_term +
        (-0.2837212) * SBP_term1 +
        0.3239977 * SBP_term2 +
        0.7189597 * diabetes +
        0.3956973 * current_smoker +
        0.3690075 * eGFR_term1 +
        0.0203619 * eGFR_term2 +
        0.2036522 * anti_hyp_med +
        (-0.0865581) * statin +
        (-0.0322916) * anti_hyp_med * SBP_term2 +
        0.114563 * statin * chol_term +
        (-0.0300005) * age_factor * chol_term +
        0.0232747 * age_factor * hdl_term +
        (-0.0927024) * age_factor * SBP_term2 +
        (-0.2018525) * age_factor * diabetes +
        (-0.0970527) * age_factor * current_smoker +
        (-0.1217081) * age_factor * eGFR_term1
    )

    return math.exp(log_odds) / (1 + math.exp(log_odds))

def women_hf_10(age: float, SBP: float, BMI: float, eGFR: float,
                 diabetes: int, current_smoker: int, anti_hyp_med: int) -> float:
    
    age_factor = (age - 55) / 10.0

    # 收縮壓 (SBP) 部分：
    # 使用 min() 與 max() 限制 SBP 的不同區段
    SBP_min = min(float(SBP), 110)         # 低於 110 的部分
    SBP_max = max(float(SBP), 110)         # 高於 110 的部分
    SBP_term_min = (SBP_min - 110) / 20.0   # (min(SBP, 110) - 110) /20
    SBP_term_max = (SBP_max - 130) / 20.0   # (max(SBP, 110) - 130) /20

    # BMI 部分：
    # 將 BMI 分為兩段，低於 30 與高於 30 分別處理
    BMI_min = min(float(BMI), 30)              # 當 BMI <= 30，取 BMI；若超過 30，則取 30
    BMI_max = max(float(BMI), 30)              # 當 BMI > 30，則取 BMI；否則為 30
    BMI_term_min = (BMI_min - 25) / 5.0  # (min(BMI, 30) - 25) /5
    BMI_term_max = (BMI_max - 30) / 5.0  # (max(BMI, 30) - 30) /5

    # eGFR 部分：
    # 亦使用 min() 與 max() 來分別處理低於或高於特定值的部分
    eGFR_min = min(float(eGFR), 60)                # min(eGFR, 60)
    eGFR_max = max(float(eGFR), 60)                # max(eGFR, 60)
    eGFR_term_min = (eGFR_min - 60) / -15.0   # (min(eGFR, 60) - 60) / -15
    eGFR_term_max = (eGFR_max - 90) / -15.0   # (max(eGFR, 60) - 90) / -15

    # 根據公式逐項累加，注意各項的係數與變數乘法
    log_odds = (
        -4.310409 +
        0.8998235 * age_factor +
        (-0.4559771) * SBP_term_min +
        0.3576505 * SBP_term_max +
        1.038346  * diabetes +
        0.583916  * current_smoker +
        (-0.0072294) * BMI_term_min +
        0.2997706 * BMI_term_max +
        0.7451638 * eGFR_term_min +
        0.0557087 * eGFR_term_max +
        0.3534442 * anti_hyp_med +
        (-0.0981511) * anti_hyp_med * SBP_term_max +
        (-0.0946663) * age_factor * SBP_term_max +
        (-0.3581041) * age_factor * diabetes +
        (-0.1159453) * age_factor * current_smoker +
        (-0.003878)  * age_factor * BMI_term_max +
        (-0.1884289) * age_factor * eGFR_term_min
    )

    return math.exp(log_odds) / (1 + math.exp(log_odds))

def man_hf_10(age: float, SBP: float, BMI: float, eGFR: float,
                 diabetes: int, current_smoker: int, anti_hyp_med: int) -> float:
    
    age_factor = (age - 55) / 10.0

    # 收縮壓 (SBP) 處理
    SBP_min = min(float(SBP), 110)
    SBP_max = max(float(SBP), 110)
    SBP_term_min = (SBP_min - 110) / 20.0
    SBP_term_max = (SBP_max - 130) / 20.0

    # BMI 處理
    BMI_min = min(float(BMI), 30)
    BMI_max = max(float(BMI), 30)
    BMI_term_min = (BMI_min - 25) / 5.0
    BMI_term_max = (BMI_max - 30) / 5.0

    # eGFR 處理
    eGFR_min = min(float(eGFR), 60)
    eGFR_max = max(float(eGFR), 60)
    eGFR_term_min = (eGFR_min - 60) / -15.0
    eGFR_term_max = (eGFR_max - 90) / -15.0

    # 計算 log-Odds
    log_odds = (
        -3.946391 +
        0.8972642 * age_factor +
        (-0.6811466) * SBP_term_min +
        0.3634461 * SBP_term_max +
        0.923776  * diabetes +
        0.5023736 * current_smoker +
        (-0.0485841) * BMI_term_min +
        0.3726929 * BMI_term_max +
        0.6926917 * eGFR_term_min +
        0.0251827 * eGFR_term_max +
        0.2980922 * anti_hyp_med +
        (-0.0497731) * anti_hyp_med * SBP_term_max +
        (-0.1289201) * age_factor * SBP_term_max +
        (-0.3040924) * age_factor * diabetes +
        (-0.1401688) * age_factor * current_smoker +
        0.0068126  * age_factor * BMI_term_max +
        (-0.1797778) * age_factor * eGFR_term_min
    )

    return math.exp(log_odds) / (1 + math.exp(log_odds))


def calculate_fhs_dm_score(
    sex: str,
    fasting_glucose: Optional[float] = None,
    bmi: Optional[float] = None,
    hdl_c_level: Optional[float] = None,
    parental_history: bool = False,
    triglyceride_level: Optional[float] = None,
    blood_pressure: Union[Tuple[Optional[float], Optional[float]], Optional[float]] = None,
    on_bp_treatment: bool = False
) -> Tuple[int, str]:
    """
    計算 Framingham Heart Study 糖尿病風險分數
    
    參數:
        sex: 性別 ('M' 或 'F')
        fasting_glucose: 空腹血糖 (mg/dL)
        bmi: 身體質量指數
        hdl_c_level: 高密度膽固醇 (mg/dL)
        parental_history: 父母糖尿病史
        triglyceride_level: 三酸甘油脂 (mg/dL)
        blood_pressure: 血壓 (收縮壓, 舒張壓) 或只有收縮壓
        on_bp_treatment: 是否正在服用降血壓藥物
    
    回傳:
        Tuple[int, str]: (風險分數, 風險百分比文字)
    """
    score = 0

    # 空腹血糖 100-125 mg/dL (前糖尿病)
    if fasting_glucose is not None and 100 <= fasting_glucose < 126:
        score += 10

    # BMI 分級
    if bmi is not None:
        if 25.0 <= bmi <= 29.9:  # 過重
            score += 2
        elif bmi >= 30.0:  # 肥胖
            score += 5

    # HDL-C 低值
    if hdl_c_level is not None:
        if sex == 'M' and hdl_c_level < 40:  # 男性 HDL-C < 40
            score += 5
        elif sex == 'F' and hdl_c_level < 50:  # 女性 HDL-C < 50
            score += 5

    # 家族糖尿病史 (父母)
    if parental_history:
        score += 3

    # 三酸甘油脂 >150 mg/dL
    if triglyceride_level is not None and triglyceride_level > 150:
        score += 3

    # 血壓 >130/85 mmHg 或正在服用降血壓藥物
    sbp_val, dbp_val = None, None
    if isinstance(blood_pressure, (tuple, list)) and len(blood_pressure) >= 2:
        sbp_val, dbp_val = blood_pressure[0], blood_pressure[1]
    elif blood_pressure is not None:
        sbp_val = blood_pressure
    
    if (sbp_val is not None and sbp_val > 130) or \
       (dbp_val is not None and dbp_val > 85) or \
       on_bp_treatment:
        score += 2

    # Framingham 糖尿病風險對照表
    risk_table = {
        0: '<3', 1: '<3', 2: '<3', 3: '<3', 4: '<3', 5: '<3', 6: '<3', 7: '<3', 8: '<3', 9: '<3',
        10: '<3', 11: '4', 12: '4', 13: '5', 14: '6', 15: '7', 16: '9', 17: '11',
        18: '13', 19: '15', 20: '18', 21: '21', 22: '25', 23: '29', 24: '33'
    }
    
    if score >= 25:
        base_risk = '>35'
    else:
        base_risk = risk_table.get(score, '<3')

    # 加上百分比符號
    risk_percent = f"{base_risk}%"

    return score, risk_percent


def calculate_fhs_dm_risk_assessment(
    sex: str,
    age: Optional[int] = None,
    fasting_glucose: Optional[float] = None,
    bmi: Optional[float] = None,
    hdl_c_level: Optional[float] = None,
    parental_history: bool = False,
    triglyceride_level: Optional[float] = None,
    systolic_bp: Optional[float] = None,
    diastolic_bp: Optional[float] = None,
    on_bp_treatment: bool = False,
    **kwargs
) -> dict:
    """
    完整的 Framingham Heart Study 糖尿病風險評估
    
    回傳詳細的風險評估結果，包含分數、百分比、風險分級和建議
    """
    
    # 計算基本風險分數
    blood_pressure = (systolic_bp, diastolic_bp) if systolic_bp and diastolic_bp else systolic_bp
    score, risk_percentage = calculate_fhs_dm_score(
        sex=sex,
        fasting_glucose=fasting_glucose,
        bmi=bmi,
        hdl_c_level=hdl_c_level,
        parental_history=parental_history,
        triglyceride_level=triglyceride_level,
        blood_pressure=blood_pressure,
        on_bp_treatment=on_bp_treatment
    )
    
    # 提取數值風險百分比用於分級
    risk_value = risk_percentage.replace('%', '').replace('>', '').replace('<', '')
    try:
        risk_numeric = float(risk_value)
    except ValueError:
        risk_numeric = 0
    
    # 風險分級
    if risk_numeric < 3:
        risk_category = "低風險"
        risk_level = "low"
    elif risk_numeric < 10:
        risk_category = "中低風險"
        risk_level = "moderate-low"
    elif risk_numeric < 20:
        risk_category = "中等風險"
        risk_level = "moderate"
    elif risk_numeric < 30:
        risk_category = "中高風險"
        risk_level = "moderate-high"
    else:
        risk_category = "高風險"
        risk_level = "high"
    
    # 生成建議
    recommendations = generate_fhs_dm_recommendations(
        risk_level=risk_level,
        score=score,
        fasting_glucose=fasting_glucose,
        bmi=bmi,
        hdl_c_level=hdl_c_level,
        triglyceride_level=triglyceride_level,
        systolic_bp=systolic_bp,
        diastolic_bp=diastolic_bp,
        sex=sex
    )
    
    return {
        'algorithm': 'Framingham Heart Study Diabetes Mellitus',
        'risk_score': score,
        'risk_percentage': risk_percentage,
        'risk_category': risk_category,
        'risk_level': risk_level,
        'recommendations': recommendations,
        'interpretation': {
            'score_range': '0-30+',
            'risk_factors_evaluated': [
                '空腹血糖 (100-125 mg/dL)',
                'BMI (過重/肥胖)',
                'HDL膽固醇 (低值)',
                '家族糖尿病史',
                '三酸甘油脂 (>150 mg/dL)',
                '血壓 (>130/85 mmHg 或服藥)'
            ]
        }
    }


def generate_fhs_dm_recommendations(
    risk_level: str,
    score: int,
    fasting_glucose: Optional[float] = None,
    bmi: Optional[float] = None,
    hdl_c_level: Optional[float] = None,
    triglyceride_level: Optional[float] = None,
    systolic_bp: Optional[float] = None,
    diastolic_bp: Optional[float] = None,
    sex: str = None,
    **kwargs
) -> list:
    """
    根據 Framingham 糖尿病風險評估結果生成個人化建議
    """
    recommendations = []
    
    # 基於整體風險等級的建議
    if risk_level == "high":
        recommendations.extend([
            "🚨 高糖尿病風險：建議立即諮詢內分泌科醫師",
            "📅 建議每3-6個月檢查血糖和糖化血色素",
            "💊 可能需要考慮預防性藥物治療 (如 Metformin)"
        ])
    elif risk_level in ["moderate-high", "moderate"]:
        recommendations.extend([
            "⚠️ 中等糖尿病風險：建議加強生活方式干預",
            "📅 建議每6-12個月檢查血糖",
            "🏃‍♂️ 積極進行體重管理和運動計畫"
        ])
    else:
        recommendations.extend([
            "✅ 糖尿病風險相對較低",
            "📅 建議每年定期檢查血糖",
            "🥗 維持健康的生活方式"
        ])
    
    # 基於具體風險因子的建議
    if fasting_glucose is not None and 100 <= fasting_glucose < 126:
        recommendations.append("🍯 空腹血糖偏高：建議減少精製糖攝取，增加纖維攝取")
    
    if bmi is not None:
        if bmi >= 30:
            recommendations.append("⚖️ BMI過高：建議減重至少5-10%，諮詢營養師制定減重計畫")
        elif bmi >= 25:
            recommendations.append("⚖️ 體重過重：建議控制體重，目標BMI < 25")
    
    if hdl_c_level is not None:
        if (sex == 'M' and hdl_c_level < 40) or (sex == 'F' and hdl_c_level < 50):
            recommendations.append("💪 HDL膽固醇偏低：建議增加有氧運動，減少反式脂肪攝取")
    
    if triglyceride_level is not None and triglyceride_level > 150:
        recommendations.append("🐟 三酸甘油脂偏高：建議減少精製碳水化合物，增加Omega-3攝取")
    
    if (systolic_bp is not None and systolic_bp > 130) or (diastolic_bp is not None and diastolic_bp > 85):
        recommendations.append("🩺 血壓偏高：建議減鹽飲食，規律運動，必要時諮詢心臟科")
    
    # 一般預防建議
    recommendations.extend([
        "🥗 飲食建議：地中海飲食模式，多蔬果、全穀類、瘦肉",
        "🏃‍♂️ 運動建議：每週至少150分鐘中等強度有氧運動",
        "😴 生活建議：充足睡眠、壓力管理、戒菸限酒"
    ])
    
    return recommendations


def calculate_ch_dm_score(
    age: int,
    sex: str,
    bmi: float,
    family_history_diabetes: bool,
    sbp: float,
    anti_hypertensive_drugs: bool,
    resting_heart_rate: float,
    fpg: float,
    tg: float,
    using_lipid_lowering_drugs: bool,
    auc: float = 0.0
) -> Tuple[int, str]:
    """
    基於論文 "Changes in ideal cardiovascular health status and risk of new-onset type 2 diabetes" 
    計算中國健檢糖尿病風險分數
    
    參數:
        age: 年齡
        sex: 性別 ('M' 或 'F')
        bmi: 身體質量指數
        family_history_diabetes: 家族糖尿病史
        sbp: 收縮壓 (mmHg)
        anti_hypertensive_drugs: 是否使用降血壓藥物
        resting_heart_rate: 靜息心率 (bpm)
        fpg: 空腹血糖 (mg/dL)
        tg: 三酸甘油脂 (mg/dL)
        using_lipid_lowering_drugs: 是否使用降血脂藥物
        auc: AUC值 (預設為0)
    
    回傳:
        Tuple[int, str]: (風險分數, 風險百分比文字)
    """
    risk_score = 0
    
    # 年齡評分
    if 18 <= age < 30:
        risk_score += 0
    elif 30 <= age < 40:
        risk_score += 6
    elif 40 <= age < 60:
        risk_score += 10
    elif age >= 60:
        risk_score += 11
    
    # 性別評分 (男性)
    if sex.upper() == 'M':
        risk_score += 2
    
    # BMI評分
    if bmi < 24:
        risk_score += 0
    elif 24 <= bmi < 28:
        risk_score += 4
    else:  # bmi >= 28
        risk_score += 9
    
    # 家族糖尿病史
    if family_history_diabetes:
        risk_score += 4
    
    # 收縮壓評分
    if 90 <= sbp <= 120:
        risk_score += 0
    elif 120 < sbp <= 129:
        risk_score += 1
    elif 130 <= sbp < 140:
        risk_score += 2
    elif 140 <= sbp < 200 or anti_hypertensive_drugs:
        risk_score += 4
    
    # 靜息心率評分
    if resting_heart_rate < 70:
        risk_score += 0
    elif 70 <= resting_heart_rate < 80:
        risk_score += 1
    elif 80 <= resting_heart_rate < 90:
        risk_score += 1
    else:  # resting_heart_rate >= 90
        risk_score += 4
    
    # 空腹血糖評分
    if 20 <= fpg < 100:
        risk_score += 0
    elif 100 <= fpg <= 110:
        risk_score += 11
    elif 110 < fpg <= 126:
        risk_score += 20
    else:  # fpg > 126
        risk_score += 20
    
    # 三酸甘油脂評分
    if tg >= 150 or using_lipid_lowering_drugs:
        risk_score += 3
    
    # 加入AUC值
    risk_score += auc
    
    # 風險百分比對照
    if risk_score <= 10:
        prob = "<3%"
    elif 10 < risk_score <= 15:
        prob = "5%"
    elif 15 < risk_score < 20:
        prob = "8%"
    elif 20 <= risk_score < 25:
        prob = "8~12%"
    elif 25 <= risk_score <= 27:
        prob = "12~18%"
    elif 27 < risk_score < 32:
        prob = "18~25%"
    else:  # risk_score >= 32
        prob = ">25%"
    
    return risk_score, prob


def calculate_ch_dm_risk_assessment(
    age: int,
    sex: str,
    bmi: float,
    family_history_diabetes: bool = False,
    sbp: float = 120.0,
    anti_hypertensive_drugs: bool = False,
    resting_heart_rate: float = 70.0,
    fpg: float = 90.0,
    tg: float = 150.0,
    using_lipid_lowering_drugs: bool = False,
    auc: float = 0.0,
    **kwargs
) -> dict:
    """
    完整的中國健檢糖尿病風險評估
    
    回傳詳細的風險評估結果，包含分數、百分比、風險分級和建議
    """
    
    # 計算基本風險分數
    score, risk_percentage = calculate_ch_dm_score(
        age=age,
        sex=sex,
        bmi=bmi,
        family_history_diabetes=family_history_diabetes,
        sbp=sbp,
        anti_hypertensive_drugs=anti_hypertensive_drugs,
        resting_heart_rate=resting_heart_rate,
        fpg=fpg,
        tg=tg,
        using_lipid_lowering_drugs=using_lipid_lowering_drugs,
        auc=auc
    )
    
    # 風險分級
    def get_ch_dm_risk_category(risk_percent_str):
        if risk_percent_str in ["<3%", "5%"]:
            return '低風險'
        elif risk_percent_str == "8%":
            return '中低風險'
        elif risk_percent_str in ["8~12%", "12~18%"]:
            return '中等風險'
        elif risk_percent_str in ["18~25%", ">25%"]:
            return '高風險'
        else:
            return '未知風險'
    
    risk_category = get_ch_dm_risk_category(risk_percentage)
    risk_level = risk_category.replace('風險', '').lower()
    
    # 生成建議
    recommendations = generate_ch_dm_recommendations(
        risk_level=risk_level,
        score=score,
        age=age,
        sex=sex,
        bmi=bmi,
        sbp=sbp,
        fpg=fpg,
        tg=tg,
        resting_heart_rate=resting_heart_rate
    )
    
    return {
        'algorithm': 'Changes in Ideal Cardiovascular Health - Diabetes Mellitus',
        'risk_score': score,
        'risk_percentage': risk_percentage,
        'risk_category': risk_category,
        'risk_level': risk_level,
        'recommendations': recommendations,
        'interpretation': {
            'score_range': '0-50+',
            'risk_factors_evaluated': [
                '年齡 (18-60+)',
                '性別 (男性風險較高)',
                'BMI (24-28+)',
                '家族糖尿病史',
                '收縮壓 (90-200 mmHg)',
                '降血壓藥物使用',
                '靜息心率 (70-90+ bpm)',
                '空腹血糖 (100-126+ mg/dL)',
                '三酸甘油脂 (150+ mg/dL)',
                '降血脂藥物使用'
            ]
        }
    }


def generate_ch_dm_recommendations(
    risk_level: str,
    score: int,
    age: int = None,
    sex: str = None,
    bmi: float = None,
    sbp: float = None,
    fpg: float = None,
    tg: float = None,
    resting_heart_rate: float = None,
    **kwargs
) -> list:
    """
    根據中國健檢糖尿病風險評估結果生成個人化建議
    """
    recommendations = []
    
    # 基於整體風險等級的建議
    if risk_level in ["高", "high"]:
        recommendations.extend([
            "🚨 高糖尿病風險：建議立即諮詢內分泌科醫師進行詳細評估",
            "📅 建議每3個月檢查血糖、糖化血色素和相關代謝指標",
            "💊 可能需要考慮預防性藥物治療，請諮詢專科醫師",
            "🏥 建議進行口服葡萄糖耐量試驗 (OGTT) 進一步確認"
        ])
    elif risk_level in ["中等", "moderate", "中"]:
        recommendations.extend([
            "⚠️ 中等糖尿病風險：建議積極進行生活方式干預",
            "📅 建議每6個月檢查血糖和相關代謝指標",
            "🏃‍♂️ 建議制定結構化的運動和飲食計畫",
            "📚 建議參加糖尿病預防教育課程"
        ])
    elif risk_level in ["中低", "moderate-low", "低中"]:
        recommendations.extend([
            "📊 中低糖尿病風險：建議注意生活方式調整",
            "📅 建議每年檢查血糖",
            "🥗 建議維持健康飲食習慣"
        ])
    else:
        recommendations.extend([
            "✅ 糖尿病風險相對較低",
            "📅 建議每年定期健康檢查",
            "🥗 持續維持健康的生活方式"
        ])
    
    # 基於具體風險因子的個人化建議
    if age is not None and age >= 40:
        recommendations.append("👥 40歲以上：建議更密切關注代謝健康，定期檢查")
    
    if sex == 'M':
        recommendations.append("👨 男性：糖尿病風險較高，建議特別注意體重和運動")
    
    if bmi is not None:
        if bmi >= 28:
            recommendations.append("⚖️ BMI過高：建議減重至少7-10%，諮詢營養師制定減重計畫")
        elif bmi >= 24:
            recommendations.append("⚖️ 體重過重：建議控制體重，目標BMI < 24 (亞洲標準)")
    
    if sbp is not None and sbp >= 130:
        recommendations.append("🩺 血壓偏高：建議減鹽飲食、規律運動，必要時諮詢心臟科")
    
    if fpg is not None and fpg >= 100:
        recommendations.append("🍯 空腹血糖偏高：建議減少精製糖攝取，增加膳食纖維")
    
    if tg is not None and tg >= 150:
        recommendations.append("🐟 三酸甘油脂偏高：建議減少精製碳水化合物，增加Omega-3攝取")
    
    if resting_heart_rate is not None and resting_heart_rate >= 80:
        recommendations.append("💓 靜息心率偏高：建議增加有氧運動，改善心血管健康")
    
    # 一般預防建議
    recommendations.extend([
        "🥗 飲食建議：採用低升糖指數飲食，多攝取蔬菜、全穀類、優質蛋白質",
        "🏃‍♂️ 運動建議：每週至少150分鐘中等強度有氧運動 + 阻力訓練",
        "😴 生活建議：充足睡眠(7-9小時)、壓力管理、戒菸限酒",
        "📊 監測建議：定期自我監測體重、血壓，記錄飲食和運動日誌"
    ])
    
    return recommendations

