"""
Healthcare 365 實時風險分析引擎
每秒更新患者風險評估
"""

import numpy as np
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q, Avg
from .models import RealTimeVitalSigns, RealTimeRiskAnalysis, RealTimeAlert
from health_screening.advanced_risk_calculators import AdvancedRiskCalculator
import logging

logger = logging.getLogger(__name__)


class RealTimeRiskEngine:
    """實時風險分析引擎"""
    
    def __init__(self):
        self.risk_calculator = AdvancedRiskCalculator()
        self.risk_thresholds = {
            'heart_rate': {'low': 50, 'high': 120, 'critical': 140},
            'systolic_bp': {'low': 90, 'high': 140, 'critical': 180},
            'diastolic_bp': {'low': 60, 'high': 90, 'critical': 110},
            'oxygen_saturation': {'critical_low': 90, 'low': 95, 'normal': 98},
            'respiration_rate': {'low': 12, 'high': 20, 'critical': 30},
        }
    
    def analyze_patient_risk(self, patient_id, device_id):
        """分析單一患者的實時風險"""
        try:
            # 獲取最新的生命體徵數據
            latest_vitals = self._get_latest_vitals(patient_id, device_id)
            if not latest_vitals:
                return None
            
            # 獲取歷史趨勢數據 (過去5分鐘)
            trend_data = self._get_trend_data(patient_id, device_id, minutes=5)
            
            # 執行各種風險分析
            risk_results = []
            
            # 1. 心血管風險分析
            cv_risk = self._analyze_cardiovascular_risk(latest_vitals, trend_data)
            if cv_risk:
                risk_results.append(cv_risk)
            
            # 2. 呼吸系統風險分析
            resp_risk = self._analyze_respiratory_risk(latest_vitals, trend_data)
            if resp_risk:
                risk_results.append(resp_risk)
            
            # 3. 心律不整風險分析
            arrhythmia_risk = self._analyze_arrhythmia_risk(latest_vitals, trend_data)
            if arrhythmia_risk:
                risk_results.append(arrhythmia_risk)
            
            # 4. 血壓異常風險分析
            bp_risk = self._analyze_blood_pressure_risk(latest_vitals, trend_data)
            if bp_risk:
                risk_results.append(bp_risk)
            
            # 保存風險分析結果
            saved_results = []
            for risk_data in risk_results:
                risk_analysis = self._save_risk_analysis(latest_vitals, risk_data)
                saved_results.append(risk_analysis)
                
                # 檢查是否需要觸發警報
                if risk_analysis.alert_triggered:
                    self._create_alert(risk_analysis)
            
            return saved_results
            
        except Exception as e:
            logger.error(f"風險分析失敗 - 患者 {patient_id}: {str(e)}")
            return None
    
    def _get_latest_vitals(self, patient_id, device_id):
        """獲取最新的生命體徵數據"""
        return RealTimeVitalSigns.objects.filter(
            patient_id=patient_id,
            device_id=device_id
        ).order_by('-timestamp').first()
    
    def _get_trend_data(self, patient_id, device_id, minutes=5):
        """獲取趨勢數據"""
        cutoff_time = timezone.now() - timedelta(minutes=minutes)
        return RealTimeVitalSigns.objects.filter(
            patient_id=patient_id,
            device_id=device_id,
            timestamp__gte=cutoff_time
        ).order_by('timestamp')
    
    def _analyze_cardiovascular_risk(self, vitals, trend_data):
        """分析心血管風險"""
        if not vitals.heart_rate or not vitals.systolic_bp:
            return None
        
        risk_score = 0
        contributing_factors = []
        
        # 心率異常檢測
        if vitals.heart_rate > self.risk_thresholds['heart_rate']['critical']:
            risk_score += 3
            contributing_factors.append(f"心率過高: {vitals.heart_rate} bpm")
        elif vitals.heart_rate > self.risk_thresholds['heart_rate']['high']:
            risk_score += 2
            contributing_factors.append(f"心率偏高: {vitals.heart_rate} bpm")
        elif vitals.heart_rate < self.risk_thresholds['heart_rate']['low']:
            risk_score += 2
            contributing_factors.append(f"心率過低: {vitals.heart_rate} bpm")
        
        # 血壓異常檢測
        if vitals.systolic_bp > self.risk_thresholds['systolic_bp']['critical']:
            risk_score += 3
            contributing_factors.append(f"收縮壓危急: {vitals.systolic_bp} mmHg")
        elif vitals.systolic_bp > self.risk_thresholds['systolic_bp']['high']:
            risk_score += 2
            contributing_factors.append(f"收縮壓偏高: {vitals.systolic_bp} mmHg")
        
        # 趨勢分析
        if len(trend_data) >= 3:
            hr_trend = self._calculate_trend(trend_data, 'heart_rate')
            bp_trend = self._calculate_trend(trend_data, 'systolic_bp')
            
            if hr_trend > 10:  # 心率快速上升
                risk_score += 1
                contributing_factors.append("心率快速上升趨勢")
            if bp_trend > 20:  # 血壓快速上升
                risk_score += 1
                contributing_factors.append("血壓快速上升趨勢")
        
        # 計算風險等級
        risk_level = self._calculate_risk_level(risk_score)
        risk_percentage = min(risk_score * 15, 100)
        
        return {
            'risk_type': 'cardiovascular',
            'risk_level': risk_level,
            'risk_score': risk_score,
            'risk_percentage': risk_percentage,
            'contributing_factors': contributing_factors,
            'recommendations': self._get_cardiovascular_recommendations(risk_level),
            'alert_triggered': risk_score >= 3
        }
    
    def _analyze_respiratory_risk(self, vitals, trend_data):
        """分析呼吸系統風險"""
        if not vitals.oxygen_saturation or not vitals.respiration_rate:
            return None
        
        risk_score = 0
        contributing_factors = []
        
        # 血氧飽和度檢測
        if vitals.oxygen_saturation < self.risk_thresholds['oxygen_saturation']['critical_low']:
            risk_score += 3
            contributing_factors.append(f"血氧危急低下: {vitals.oxygen_saturation}%")
        elif vitals.oxygen_saturation < self.risk_thresholds['oxygen_saturation']['low']:
            risk_score += 2
            contributing_factors.append(f"血氧偏低: {vitals.oxygen_saturation}%")
        
        # 呼吸頻率檢測
        if vitals.respiration_rate > self.risk_thresholds['respiration_rate']['critical']:
            risk_score += 3
            contributing_factors.append(f"呼吸過快: {vitals.respiration_rate} breaths/min")
        elif vitals.respiration_rate > self.risk_thresholds['respiration_rate']['high']:
            risk_score += 2
            contributing_factors.append(f"呼吸偏快: {vitals.respiration_rate} breaths/min")
        elif vitals.respiration_rate < self.risk_thresholds['respiration_rate']['low']:
            risk_score += 2
            contributing_factors.append(f"呼吸過慢: {vitals.respiration_rate} breaths/min")
        
        risk_level = self._calculate_risk_level(risk_score)
        risk_percentage = min(risk_score * 20, 100)
        
        return {
            'risk_type': 'respiratory',
            'risk_level': risk_level,
            'risk_score': risk_score,
            'risk_percentage': risk_percentage,
            'contributing_factors': contributing_factors,
            'recommendations': self._get_respiratory_recommendations(risk_level),
            'alert_triggered': risk_score >= 3
        }