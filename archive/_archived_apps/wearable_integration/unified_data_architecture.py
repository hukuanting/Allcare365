"""
Healthcare 365 統一數據架構
基於最新數據來源的智能風險分析
"""

from django.db import models, transaction
from django.utils import timezone
from datetime import datetime, timedelta
from patients.models import Patient, PatientVitals
from health_screening.models import HealthScreening, CardiovascularRiskIndex
from .models import RealTimeVitalSigns, WearableDevice
import logging

logger = logging.getLogger(__name__)


class UnifiedDataManager:
    """統一數據管理器 - 智能選擇最新數據進行風險分析"""
    
    def __init__(self):
        self.data_priority_map = {
            # 數據類型: (表名, 時效性權重, 欄位映射)
            'height': ('health_screening', 30, 'height'),  # 30天內有效
            'weight': ('health_screening', 7, 'weight'),   # 7天內有效
            'hba1c': ('health_screening', 90, 'hba1c'),    # 90天內有效
            'egfr': ('health_screening', 30, 'egfr'),      # 30天內有效
            'blood_pressure': ('multiple', 1, ['systolic_bp', 'diastolic_bp']),  # 1天內有效
            'heart_rate': ('realtime', 0.017, 'heart_rate'),  # 1分鐘內有效（實時）
        }
    
    def get_patient_latest_data(self, patient_id, required_fields):
        """
        獲取患者最新的完整數據集
        
        Args:
            patient_id: 患者ID
            required_fields: 風險分析需要的欄位列表
            
        Returns:
            dict: 最新數據集和數據來源信息
        """
        try:
            patient = Patient.objects.get(id=patient_id)
            
            latest_data = {}
            data_sources = {}
            
            for field in required_fields:
                field_data = self._get_latest_field_data(patient, field)
                if field_data:
                    latest_data[field] = field_data['value']
                    data_sources[field] = {
                        'source': field_data['source'],
                        'timestamp': field_data['timestamp'],
                        'age_hours': field_data['age_hours']
                    }
                else:
                    latest_data[field] = None
                    data_sources[field] = {'source': 'none', 'timestamp': None}
            
            return {
                'patient_id': patient_id,
                'patient_name': patient.full_name,
                'data': latest_data,
                'sources': data_sources,
                'completeness': self._calculate_data_completeness(latest_data),
                'last_updated': timezone.now()
            }
            
        except Patient.DoesNotExist:
            raise ValueError(f"患者 {patient_id} 不存在")
        except Exception as e:
            logger.error(f"獲取患者最新數據失敗: {str(e)}")
            raise
    
    def _get_latest_field_data(self, patient, field):
        """獲取特定欄位的最新數據"""
        now = timezone.now()
        
        if field == 'height':
            return self._get_from_health_screening(patient, 'height', now, days=365)
        
        elif field == 'weight':
            return self._get_from_health_screening(patient, 'weight', now, days=30)
        
        elif field == 'hba1c':
            return self._get_from_health_screening(patient, 'hba1c', now, days=180)
        
        elif field == 'egfr':
            return self._get_from_health_screening(patient, 'egfr', now, days=90)
        
        elif field == 'blood_pressure':
            # 優先順序: 實時數據 > 最近健檢 > 患者生命體徵
            return self._get_blood_pressure_latest(patient, now)
        
        elif field == 'heart_rate':
            # 優先實時數據
            return self._get_heart_rate_latest(patient, now)
        
        else:
            return None
    
    def _get_from_health_screening(self, patient, field, now, days):
        """從健檢記錄中獲取數據"""
        cutoff_date = now - timedelta(days=days)
        
        screenings = HealthScreening.objects.filter(
            patient=patient,
            screening_date__gte=cutoff_date
        ).order_by('-screening_date')
        
        for screening in screenings:
            value = getattr(screening, field, None)
            if value is not None:
                age_hours = (now - screening.screening_date).total_seconds() / 3600
                return {
                    'value': value,
                    'source': f'健檢記錄 ({screening.screening_date.strftime("%Y-%m-%d")})',
                    'timestamp': screening.screening_date,
                    'age_hours': age_hours
                }
        
        return None
    
    def _get_blood_pressure_latest(self, patient, now):
        """獲取最新血壓數據"""
        # 1. 先檢查實時數據 (最近1小時)
        realtime_bp = RealTimeVitalSigns.objects.filter(
            patient=patient,
            timestamp__gte=now - timedelta(hours=1),
            systolic_bp__isnull=False,
            diastolic_bp__isnull=False
        ).order_by('-timestamp').first()
        
        if realtime_bp:
            age_minutes = (now - realtime_bp.timestamp).total_seconds() / 60
            return {
                'value': {
                    'systolic': realtime_bp.systolic_bp,
                    'diastolic': realtime_bp.diastolic_bp
                },
                'source': f'穿戴式裝置 ({age_minutes:.1f}分鐘前)',
                'timestamp': realtime_bp.timestamp,
                'age_hours': age_minutes / 60
            }
        
        # 2. 檢查患者生命體徵記錄 (最近7天)
        patient_vitals = PatientVitals.objects.filter(
            patient=patient,
            measurement_date__gte=now - timedelta(days=7),
            blood_pressure_systolic__isnull=False,
            blood_pressure_diastolic__isnull=False
        ).order_by('-measurement_date').first()
        
        if patient_vitals:
            age_hours = (now - patient_vitals.measurement_date).total_seconds() / 3600
            return {
                'value': {
                    'systolic': patient_vitals.blood_pressure_systolic,
                    'diastolic': patient_vitals.blood_pressure_diastolic
                },
                'source': f'生命體徵記錄 ({age_hours:.1f}小時前)',
                'timestamp': patient_vitals.measurement_date,
                'age_hours': age_hours
            }
        
        # 3. 檢查健檢記錄 (最近30天)
        return self._get_from_health_screening(patient, 'blood_pressure', now, days=30)
    
    def _get_heart_rate_latest(self, patient, now):
        """獲取最新心率數據"""
        # 1. 優先實時數據 (最近5分鐘)
        realtime_hr = RealTimeVitalSigns.objects.filter(
            patient=patient,
            timestamp__gte=now - timedelta(minutes=5),
            heart_rate__isnull=False
        ).order_by('-timestamp').first()
        
        if realtime_hr:
            age_seconds = (now - realtime_hr.timestamp).total_seconds()
            return {
                'value': realtime_hr.heart_rate,
                'source': f'穿戴式裝置 ({age_seconds:.0f}秒前)',
                'timestamp': realtime_hr.timestamp,
                'age_hours': age_seconds / 3600
            }
        
        # 2. 檢查患者生命體徵記錄
        patient_vitals = PatientVitals.objects.filter(
            patient=patient,
            measurement_date__gte=now - timedelta(days=1),
            heart_rate__isnull=False
        ).order_by('-measurement_date').first()
        
        if patient_vitals:
            age_hours = (now - patient_vitals.measurement_date).total_seconds() / 3600
            return {
                'value': patient_vitals.heart_rate,
                'source': f'生命體徵記錄 ({age_hours:.1f}小時前)',
                'timestamp': patient_vitals.measurement_date,
                'age_hours': age_hours
            }
        
        return None
    
    def _calculate_data_completeness(self, data):
        """計算數據完整性百分比"""
        total_fields = len(data)
        available_fields = sum(1 for value in data.values() if value is not None)
        return round((available_fields / total_fields) * 100, 1) if total_fields > 0 else 0
    
    def save_wearable_data_to_vitals(self, patient_mrn, device_id, wearable_data):
        """
        將穿戴式裝置數據保存到統一的生命體徵表
        不創建重複的數據結構
        """
        try:
            with transaction.atomic():
                # 獲取或創建患者
                patient = self._get_or_create_patient(patient_mrn)
                
                # 獲取或創建設備記錄
                device = self._get_or_create_device(device_id)
                
                # 保存到實時生命體徵表（這是我們的主要數據來源）
                vital_record = RealTimeVitalSigns.objects.create(
                    patient=patient,
                    device=device,
                    timestamp=timezone.now(),
                    heart_rate=wearable_data.get('heart_rate'),
                    systolic_bp=wearable_data.get('systolic_bp'),
                    diastolic_bp=wearable_data.get('diastolic_bp'),
                    mean_arterial_pressure=wearable_data.get('mean_arterial_pressure'),
                    oxygen_saturation=wearable_data.get('oxygen_saturation'),
                    respiration_rate=wearable_data.get('respiration_rate'),
                    skin_temperature=wearable_data.get('skin_temperature'),
                    posture=wearable_data.get('posture'),
                    activity_level=wearable_data.get('activity_level'),
                    signal_quality=wearable_data.get('signal_quality', {}),
                    data_complete=wearable_data.get('data_complete', True)
                )
                
                logger.info(f"保存穿戴式裝置數據: 患者 {patient.full_name}, 心率 {vital_record.heart_rate}")
                
                return {
                    'success': True,
                    'patient_id': patient.id,
                    'patient_name': patient.full_name,
                    'vital_record_id': vital_record.id,
                    'device_id': device.device_id
                }
                
        except Exception as e:
            logger.error(f"保存穿戴式裝置數據失敗: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_or_create_patient(self, patient_mrn):
        """獲取或創建患者"""
        try:
            return Patient.objects.get(medical_record_number=patient_mrn, is_active=True)
        except Patient.DoesNotExist:
            return Patient.objects.create(
                medical_record_number=patient_mrn,
                first_name="患者",
                last_name=patient_mrn,
                date_of_birth="1990-01-01",
                gender="U",
                status="active"
            )
    
    def _get_or_create_device(self, device_id):
        """獲取或創建設備"""
        device, created = WearableDevice.objects.get_or_create(
            device_id=device_id,
            defaults={
                'device_type': 'continuous_monitor',
                'manufacturer': 'Sotera Wireless',
                'model': 'ViSi Mobile',
                'serial_number': device_id,
                'status': 'active'
            }
        )
        return device


class RealTimeRiskAnalyzer:
    """實時風險分析器 - 基於最新數據進行風險計算"""
    
    def __init__(self):
        self.data_manager = UnifiedDataManager()
    
    def analyze_patient_risk(self, patient_id, risk_algorithm='cardiovascular'):
        """
        分析患者風險 - 使用最新可用數據
        
        Args:
            patient_id: 患者ID
            risk_algorithm: 風險演算法類型
            
        Returns:
            dict: 風險分析結果
        """
        try:
            # 定義不同演算法所需的欄位
            algorithm_requirements = {
                'cardiovascular': ['height', 'weight', 'hba1c', 'egfr', 'blood_pressure', 'heart_rate'],
                'diabetes': ['weight', 'hba1c', 'blood_pressure'],
                'kidney': ['egfr', 'blood_pressure', 'weight'],
                'basic_vitals': ['blood_pressure', 'heart_rate']
            }
            
            required_fields = algorithm_requirements.get(risk_algorithm, ['heart_rate', 'blood_pressure'])
            
            # 獲取最新數據
            patient_data = self.data_manager.get_patient_latest_data(patient_id, required_fields)
            
            # 執行風險計算
            risk_result = self._calculate_risk(patient_data['data'], risk_algorithm)
            
            # 組合結果
            analysis_result = {
                'patient_id': patient_id,
                'patient_name': patient_data['patient_name'],
                'risk_algorithm': risk_algorithm,
                'risk_score': risk_result['score'],
                'risk_level': risk_result['level'],
                'risk_percentage': risk_result['percentage'],
                'data_used': patient_data['data'],
                'data_sources': patient_data['sources'],
                'data_completeness': patient_data['completeness'],
                'analysis_timestamp': timezone.now(),
                'recommendations': risk_result.get('recommendations', [])
            }
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"風險分析失敗: {str(e)}")
            return {
                'error': str(e),
                'patient_id': patient_id
            }
    
    def _calculate_risk(self, data, algorithm):
        """計算風險分數"""
        if algorithm == 'cardiovascular':
            return self._calculate_cardiovascular_risk(data)
        elif algorithm == 'basic_vitals':
            return self._calculate_basic_vital_risk(data)
        else:
            return {'score': 0, 'level': 'unknown', 'percentage': 0}
    
    def _calculate_cardiovascular_risk(self, data):
        """心血管風險計算"""
        risk_score = 0
        
        # 心率風險
        heart_rate = data.get('heart_rate')
        if heart_rate:
            if heart_rate > 120 or heart_rate < 50:
                risk_score += 3
            elif heart_rate > 100 or heart_rate < 60:
                risk_score += 1
        
        # 血壓風險
        blood_pressure = data.get('blood_pressure')
        if blood_pressure:
            systolic = blood_pressure.get('systolic')
            diastolic = blood_pressure.get('diastolic')
            if systolic and systolic > 180:
                risk_score += 3
            elif systolic and systolic > 140:
                risk_score += 2
            if diastolic and diastolic > 110:
                risk_score += 3
            elif diastolic and diastolic > 90:
                risk_score += 2
        
        # HbA1c風險
        hba1c = data.get('hba1c')
        if hba1c:
            if hba1c > 10:
                risk_score += 3
            elif hba1c > 7:
                risk_score += 2
        
        # eGFR風險
        egfr = data.get('egfr')
        if egfr:
            if egfr < 30:
                risk_score += 3
            elif egfr < 60:
                risk_score += 2
        
        # 計算風險等級
        if risk_score >= 6:
            level = 'critical'
            percentage = min(90 + risk_score, 100)
        elif risk_score >= 4:
            level = 'high'
            percentage = 70 + risk_score * 5
        elif risk_score >= 2:
            level = 'medium'
            percentage = 40 + risk_score * 10
        else:
            level = 'low'
            percentage = max(risk_score * 15, 5)
        
        return {
            'score': risk_score,
            'level': level,
            'percentage': percentage,
            'recommendations': self._get_recommendations(level)
        }
    
    def _calculate_basic_vital_risk(self, data):
        """基本生命體徵風險計算"""
        risk_score = 0
        
        heart_rate = data.get('heart_rate')
        if heart_rate:
            if heart_rate > 120 or heart_rate < 50:
                risk_score += 2
        
        blood_pressure = data.get('blood_pressure')
        if blood_pressure:
            systolic = blood_pressure.get('systolic')
            if systolic and (systolic > 180 or systolic < 90):
                risk_score += 2
        
        level = 'high' if risk_score >= 3 else 'medium' if risk_score >= 1 else 'low'
        percentage = min(risk_score * 25, 90)
        
        return {
            'score': risk_score,
            'level': level,
            'percentage': percentage
        }
    
    def _get_recommendations(self, risk_level):
        """獲取建議"""
        recommendations = {
            'critical': ['立即就醫', '持續監控', '避免劇烈運動'],
            'high': ['儘快諮詢醫師', '增加監控頻率', '注意休息'],
            'medium': ['定期追蹤', '保持健康生活', '適度運動'],
            'low': ['維持現狀', '定期健檢']
        }
        return recommendations.get(risk_level, [])


# 使用範例
def example_usage():
    """使用範例"""
    analyzer = RealTimeRiskAnalyzer()
    
    # 分析患者風險
    result = analyzer.analyze_patient_risk(
        patient_id=1,
        risk_algorithm='cardiovascular'
    )
    
    print("風險分析結果:")
    print(f"患者: {result.get('patient_name')}")
    print(f"風險等級: {result.get('risk_level')}")
    print(f"風險百分比: {result.get('risk_percentage')}%")
    print(f"數據完整性: {result.get('data_completeness')}%")
    print("\n數據來源:")
    for field, source in result.get('data_sources', {}).items():
        print(f"  {field}: {source['source']}")
    
    return result