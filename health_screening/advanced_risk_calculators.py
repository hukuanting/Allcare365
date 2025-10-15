"""
Advanced Disease Risk Calculators for Allcare365
符合 ONC 認證標準的疾病風險評估算法
"""
import math
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

@dataclass
class RiskFactors:
    """風險因子數據結構"""
    age: float
    gender: str  # 'M' or 'F'
    height_cm: float
    weight_kg: float
    sbp: float  # 收縮壓
    dbp: float  # 舒張壓
    total_cholesterol: float
    hdl_cholesterol: float
    ldl_cholesterol: float
    triglycerides: float
    glucose: float
    hba1c: float
    creatinine: float
    bmi: Optional[float] = None
    smoking_status: str = 'never'  # 'never', 'current', 'former'
    diabetes: bool = False
    hypertension_medication: bool = False
    statin_use: bool = False
    family_history_cvd: bool = False
    physical_activity_level: str = 'moderate'  # 'low', 'moderate', 'high'
    alcohol_consumption: str = 'moderate'  # 'none', 'moderate', 'heavy'
    
    def __post_init__(self):
        if self.bmi is None:
            self.bmi = self.weight_kg / ((self.height_cm / 100) ** 2)

@dataclass
class RiskAssessmentResult:
    """風險評估結果"""
    risk_type: str
    risk_score: float
    risk_percentage: float
    risk_category: str
    recommendations: List[str]
    confidence_level: float
    time_horizon: str  # '1年', '5年', '10年'
    
class AdvancedRiskCalculator:
    """先進疾病風險計算器"""
    
    def __init__(self):
        self.risk_thresholds = {
            'cardiovascular': {
                'low': 5.0,
                'moderate': 10.0,
                'high': 20.0,
                'very_high': 30.0
            },
            'diabetes': {
                'low': 5.0,
                'moderate': 15.0,
                'high': 25.0,
                'very_high': 40.0
            },
            'stroke': {
                'low': 3.0,
                'moderate': 8.0,
                'high': 15.0,
                'very_high': 25.0
            },
            'metabolic_syndrome': {
                'low': 10.0,
                'moderate': 25.0,
                'high': 50.0,
                'very_high': 75.0
            }
        }
    
    def calculate_cardiovascular_risk_10_year(self, factors: RiskFactors) -> RiskAssessmentResult:
        """
        10年心血管疾病風險計算 (基於Framingham Risk Score改良版)
        """
        try:
            if factors.gender.upper() == 'M':
                risk_score = self._male_cvd_risk(factors)
            else:
                risk_score = self._female_cvd_risk(factors)
            
            # 轉換為百分比
            risk_percentage = risk_score * 100
            
            # 風險分級
            risk_category = self._categorize_risk(risk_percentage, 'cardiovascular')
            
            # 建議
            recommendations = self._generate_cvd_recommendations(factors, risk_category)
            
            return RiskAssessmentResult(
                risk_type='cardiovascular',
                risk_score=risk_score,
                risk_percentage=risk_percentage,
                risk_category=risk_category,
                recommendations=recommendations,
                confidence_level=0.85,
                time_horizon='10年'
            )
        except Exception as e:
            logger.error(f"心血管風險計算錯誤: {e}")
            raise
    
    def _male_cvd_risk(self, factors: RiskFactors) -> float:
        """男性心血管風險計算"""
        # 年齡因子
        if factors.age < 35:
            age_points = -1
        elif factors.age < 40:
            age_points = 0
        elif factors.age < 45:
            age_points = 1
        elif factors.age < 50:
            age_points = 2
        elif factors.age < 55:
            age_points = 3
        elif factors.age < 60:
            age_points = 4
        elif factors.age < 65:
            age_points = 5
        elif factors.age < 70:
            age_points = 6
        else:
            age_points = 7
        
        # 總膽固醇因子
        if factors.total_cholesterol < 160:
            chol_points = -3
        elif factors.total_cholesterol < 200:
            chol_points = 0
        elif factors.total_cholesterol < 240:
            chol_points = 1
        elif factors.total_cholesterol < 280:
            chol_points = 2
        else:
            chol_points = 3
        
        # HDL膽固醇因子
        if factors.hdl_cholesterol >= 60:
            hdl_points = -2
        elif factors.hdl_cholesterol >= 50:
            hdl_points = -1
        elif factors.hdl_cholesterol >= 40:
            hdl_points = 0
        elif factors.hdl_cholesterol >= 35:
            hdl_points = 1
        else:
            hdl_points = 2
        
        # 血壓因子
        if factors.sbp < 120:
            bp_points = -2
        elif factors.sbp < 130:
            bp_points = 0
        elif factors.sbp < 140:
            bp_points = 1
        elif factors.sbp < 160:
            bp_points = 2
        else:
            bp_points = 3
        
        # 其他風險因子
        diabetes_points = 2 if factors.diabetes else 0
        smoking_points = 2 if factors.smoking_status == 'current' else 0
        
        # 計算總分
        total_points = (age_points + chol_points + hdl_points + 
                       bp_points + diabetes_points + smoking_points)
        
        # 轉換為風險概率
        risk_lookup = {
            -3: 0.01, -2: 0.01, -1: 0.01, 0: 0.01,
            1: 0.01, 2: 0.02, 3: 0.02, 4: 0.03,
            5: 0.04, 6: 0.05, 7: 0.06, 8: 0.08,
            9: 0.10, 10: 0.13, 11: 0.16, 12: 0.20,
            13: 0.25, 14: 0.31, 15: 0.37, 16: 0.45
        }
        
        return risk_lookup.get(total_points, 0.50)
    
    def _female_cvd_risk(self, factors: RiskFactors) -> float:
        """女性心血管風險計算"""
        # 類似男性計算，但係數不同
        age_factor = max(0, (factors.age - 40) / 10)
        chol_factor = max(0, (factors.total_cholesterol - 200) / 40)
        hdl_factor = max(0, (40 - factors.hdl_cholesterol) / 10)
        bp_factor = max(0, (factors.sbp - 120) / 20)
        
        diabetes_factor = 3.0 if factors.diabetes else 0
        smoking_factor = 2.5 if factors.smoking_status == 'current' else 0
        
        # 女性風險通常較男性低
        base_risk = 0.02
        total_risk = (base_risk + 
                     age_factor * 0.03 +
                     chol_factor * 0.02 +
                     hdl_factor * 0.015 +
                     bp_factor * 0.025 +
                     diabetes_factor * 0.02 +
                     smoking_factor * 0.02)
        
        return min(total_risk, 0.60)  # 最大60%風險
    
    def calculate_diabetes_risk(self, factors: RiskFactors) -> RiskAssessmentResult:
        """
        糖尿病風險評估 (基於FINDRISC量表改良)
        """
        points = 0
        
        # 年齡
        if factors.age < 45:
            points += 0
        elif factors.age < 55:
            points += 2
        elif factors.age < 65:
            points += 3
        else:
            points += 4
        
        # BMI
        if factors.bmi < 25:
            points += 0
        elif factors.bmi < 30:
            points += 1
        else:
            points += 3
        
        # 腰圍 (估算)
        waist_estimate = factors.bmi * 2.5  # 簡化估算
        if factors.gender.upper() == 'M':
            if waist_estimate < 94:
                points += 0
            elif waist_estimate < 102:
                points += 3
            else:
                points += 4
        else:
            if waist_estimate < 80:
                points += 0
            elif waist_estimate < 88:
                points += 3
            else:
                points += 4
        
        # 血糖
        if factors.glucose >= 126:
            points += 5
        elif factors.glucose >= 100:
            points += 3
        
        # HbA1c
        if factors.hba1c >= 6.5:
            points += 5
        elif factors.hba1c >= 5.7:
            points += 3
        
        # 高血壓
        if factors.sbp >= 140 or factors.dbp >= 90:
            points += 2
        
        # 家族史
        if factors.family_history_cvd:
            points += 5
        
        # 計算風險百分比
        if points < 7:
            risk_percentage = 1.0
        elif points < 12:
            risk_percentage = 4.0
        elif points < 15:
            risk_percentage = 17.0
        elif points < 20:
            risk_percentage = 33.0
        else:
            risk_percentage = 50.0
        
        risk_category = self._categorize_risk(risk_percentage, 'diabetes')
        recommendations = self._generate_diabetes_recommendations(factors, risk_category)
        
        return RiskAssessmentResult(
            risk_type='diabetes',
            risk_score=risk_percentage / 100,
            risk_percentage=risk_percentage,
            risk_category=risk_category,
            recommendations=recommendations,
            confidence_level=0.80,
            time_horizon='10年'
        )
    
    def calculate_stroke_risk(self, factors: RiskFactors) -> RiskAssessmentResult:
        """中風風險評估"""
        # CHA2DS2-VASc score 改良版
        points = 0
        
        # 年齡
        if factors.age >= 75:
            points += 2
        elif factors.age >= 65:
            points += 1
        
        # 性別
        if factors.gender.upper() == 'F':
            points += 1
        
        # 糖尿病
        if factors.diabetes:
            points += 1
        
        # 高血壓
        if factors.sbp >= 140 or factors.dbp >= 90:
            points += 1
        
        # 計算風險
        risk_lookup = {
            0: 0.2, 1: 0.6, 2: 2.2, 3: 3.2,
            4: 4.0, 5: 6.7, 6: 9.8, 7: 9.6,
            8: 12.5, 9: 15.2
        }
        
        risk_percentage = risk_lookup.get(min(points, 9), 15.2)
        risk_category = self._categorize_risk(risk_percentage, 'stroke')
        recommendations = self._generate_stroke_recommendations(factors, risk_category)
        
        return RiskAssessmentResult(
            risk_type='stroke',
            risk_score=risk_percentage / 100,
            risk_percentage=risk_percentage,
            risk_category=risk_category,
            recommendations=recommendations,
            confidence_level=0.75,
            time_horizon='1年'
        )
    
    def calculate_metabolic_syndrome_risk(self, factors: RiskFactors) -> RiskAssessmentResult:
        """代謝症候群風險評估"""
        criteria_met = 0
        
        # 腰圍 (BMI估算)
        waist_estimate = factors.bmi * 2.5
        if factors.gender.upper() == 'M':
            if waist_estimate >= 90:  # 亞洲男性標準
                criteria_met += 1
        else:
            if waist_estimate >= 80:  # 亞洲女性標準
                criteria_met += 1
        
        # 三酸甘油酯
        if factors.triglycerides >= 150:
            criteria_met += 1
        
        # HDL膽固醇
        if factors.gender.upper() == 'M':
            if factors.hdl_cholesterol < 40:
                criteria_met += 1
        else:
            if factors.hdl_cholesterol < 50:
                criteria_met += 1
        
        # 血壓
        if factors.sbp >= 130 or factors.dbp >= 85:
            criteria_met += 1
        
        # 血糖
        if factors.glucose >= 100:
            criteria_met += 1
        
        # 計算風險
        if criteria_met >= 3:
            risk_percentage = 90.0  # 已經是代謝症候群
        elif criteria_met == 2:
            risk_percentage = 60.0
        elif criteria_met == 1:
            risk_percentage = 30.0
        else:
            risk_percentage = 10.0
        
        risk_category = self._categorize_risk(risk_percentage, 'metabolic_syndrome')
        recommendations = self._generate_metabolic_recommendations(factors, risk_category)
        
        return RiskAssessmentResult(
            risk_type='metabolic_syndrome',
            risk_score=risk_percentage / 100,
            risk_percentage=risk_percentage,
            risk_category=risk_category,
            recommendations=recommendations,
            confidence_level=0.90,
            time_horizon='當前'
        )
    
    def _categorize_risk(self, risk_percentage: float, risk_type: str) -> str:
        """風險分級"""
        thresholds = self.risk_thresholds[risk_type]
        
        if risk_percentage < thresholds['low']:
            return '低風險'
        elif risk_percentage < thresholds['moderate']:
            return '中等風險'
        elif risk_percentage < thresholds['high']:
            return '高風險'
        else:
            return '極高風險'
    
    def _generate_cvd_recommendations(self, factors: RiskFactors, risk_category: str) -> List[str]:
        """心血管疾病建議"""
        recommendations = []
        
        if risk_category in ['高風險', '極高風險']:
            recommendations.extend([
                "建議立即就醫，進行詳細心血管檢查",
                "考慮使用降血脂藥物治療",
                "嚴格控制血壓至目標值"
            ])
        
        if factors.smoking_status == 'current':
            recommendations.append("強烈建議戒菸")
        
        if factors.bmi >= 25:
            recommendations.append("建議減重至理想BMI範圍")
        
        if factors.total_cholesterol >= 200:
            recommendations.append("控制膽固醇攝取，增加纖維食物")
        
        recommendations.extend([
            "每週至少150分鐘中等強度運動",
            "採用地中海飲食模式",
            "定期監測血壓和血脂"
        ])
        
        return recommendations
    
    def _generate_diabetes_recommendations(self, factors: RiskFactors, risk_category: str) -> List[str]:
        """糖尿病建議"""
        recommendations = []
        
        if risk_category in ['高風險', '極高風險']:
            recommendations.extend([
                "建議進行口服葡萄糖耐量測試",
                "每3-6個月檢查HbA1c",
                "考慮預防性藥物治療"
            ])
        
        if factors.bmi >= 25:
            recommendations.append("目標減重5-10%")
        
        recommendations.extend([
            "限制精製糖和碳水化合物攝取",
            "增加全穀物和蔬菜攝取",
            "每週至少150分鐘體能活動",
            "定期監測血糖"
        ])
        
        return recommendations
    
    def _generate_stroke_recommendations(self, factors: RiskFactors, risk_category: str) -> List[str]:
        """中風建議"""
        recommendations = []
        
        if risk_category in ['高風險', '極高風險']:
            recommendations.extend([
                "建議神經科專科評估",
                "考慮抗凝血治療",
                "嚴格血壓控制"
            ])
        
        recommendations.extend([
            "控制血壓至130/80 mmHg以下",
            "戒菸限酒",
            "規律運動",
            "健康飲食",
            "定期追蹤"
        ])
        
        return recommendations
    
    def _generate_metabolic_recommendations(self, factors: RiskFactors, risk_category: str) -> List[str]:
        """代謝症候群建議"""
        recommendations = []
        
        if risk_category in ['高風險', '極高風險']:
            recommendations.append("建議內分泌科專科治療")
        
        recommendations.extend([
            "減重至理想體重",
            "限制飽和脂肪攝取",
            "增加Omega-3脂肪酸攝取",
            "控制鈉攝取量",
            "規律有氧運動",
            "充足睡眠",
            "壓力管理"
        ])
        
        return recommendations
    
    def calculate_comprehensive_risk_profile(self, factors: RiskFactors) -> Dict[str, RiskAssessmentResult]:
        """綜合風險評估"""
        profile = {}
        
        try:
            profile['cardiovascular'] = self.calculate_cardiovascular_risk_10_year(factors)
            profile['diabetes'] = self.calculate_diabetes_risk(factors)
            profile['stroke'] = self.calculate_stroke_risk(factors)
            profile['metabolic_syndrome'] = self.calculate_metabolic_syndrome_risk(factors)
        except Exception as e:
            logger.error(f"綜合風險評估錯誤: {e}")
            raise
        
        return profile

# 實用工具函數
def bmi_calculator(height_cm: float, weight_kg: float) -> float:
    """BMI計算"""
    return weight_kg / ((height_cm / 100) ** 2)

def egfr_calculator(creatinine: float, age: float, gender: str, race: str = 'other') -> float:
    """eGFR計算 (CKD-EPI公式)"""
    if gender.upper() == 'F':
        if creatinine <= 0.7:
            egfr = 144 * ((creatinine / 0.7) ** -0.329) * (0.993 ** age)
        else:
            egfr = 144 * ((creatinine / 0.7) ** -1.209) * (0.993 ** age)
    else:
        if creatinine <= 0.9:
            egfr = 141 * ((creatinine / 0.9) ** -0.411) * (0.993 ** age)
        else:
            egfr = 141 * ((creatinine / 0.9) ** -1.209) * (0.993 ** age)
    
    # 種族調整
    if race.lower() == 'african_american':
        egfr *= 1.159
    
    return egfr

def framingham_risk_score(factors: RiskFactors) -> float:
    """Framingham風險評分"""
    calculator = AdvancedRiskCalculator()
    result = calculator.calculate_cardiovascular_risk_10_year(factors)
    return result.risk_percentage
