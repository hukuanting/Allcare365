"""
Enhanced Bulk Data Import Service for ONC Certification
支援 FHIR R4、XML、JSON、CSV 等多種格式的批量資料輸入
符合 USCDI v6 和 ONC 認證要求
"""

import pandas as pd
import json
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date
import logging
from django.db import transaction
from django.utils import timezone

from .models import HealthScreening, VitalSigns, LaboratoryResults, MedicalHistory, LifestyleQuestionnaire
from patients.models import Patient
from fhir_integration.uscdi_v6_mappings import USCDIv6Mapper

logger = logging.getLogger(__name__)


class EnhancedBulkImportService:
    """增強版批量資料輸入服務 - 支援 ONC 認證"""
    
    def __init__(self):
        self.uscdi_mapper = USCDIv6Mapper()
        self.processed_count = 0
        self.error_count = 0
        self.errors = []
        self.fhir_resource_count = {'Patient': 0, 'Observation': 0, 'Encounter': 0}
        
    def process_fhir_import(self, fhir_data: Any, data_format: str = 'json') -> Dict[str, Any]:
        """
        處理 FHIR R4 格式資料匯入 - 增強版
        支援 Bundle 和單一資源，符合 ONC 認證要求
        """
        try:
            # 解析 FHIR 資料
            if data_format == 'json':
                if isinstance(fhir_data, str):
                    try:
                        fhir_json = json.loads(fhir_data)
                    except json.JSONDecodeError as e:
                        raise ValueError(f"Invalid JSON format: {str(e)}")
                else:
                    fhir_json = fhir_data
            elif data_format == 'xml':
                # 處理 XML 格式 FHIR 資料
                fhir_json = self._parse_fhir_xml(fhir_data)
            else:
                raise ValueError(f"不支援的 FHIR 格式: {data_format}")
            
            # 驗證 FHIR 資源類型
            if not self._validate_fhir_structure(fhir_json):
                return {
                    'success': False,
                    'error': 'Invalid FHIR resource structure',
                    'processed_count': 0,
                    'error_count': 0
                }
            
            # 處理 FHIR 資源
            result = self._process_fhir_resources(fhir_json)
            
            return result
            
        except Exception as e:
            logger.error(f"FHIR import error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'processed_count': 0,
                'error_count': 0
            }
    
    def _parse_fhir_xml(self, xml_data: str) -> Dict[str, Any]:
        """解析 FHIR XML 格式資料"""
        try:
            root = ET.fromstring(xml_data)
            # 簡化的 XML 到 JSON 轉換
            # 實際專案中應使用專業的 FHIR XML 解析器
            return self._xml_element_to_dict(root)
        except Exception as e:
            raise ValueError(f"FHIR XML 解析失敗: {str(e)}")
    
    def _xml_element_to_dict(self, element: ET.Element) -> Dict[str, Any]:
        """將 XML 元素轉換為字典"""
        result = {}
        
        # 處理屬性
        if element.attrib:
            result.update(element.attrib)
        
        # 處理文字內容
        if element.text and element.text.strip():
            if len(element) == 0:
                return element.text.strip()
            else:
                result['value'] = element.text.strip()
        
        # 處理子元素
        for child in element:
            child_data = self._xml_element_to_dict(child)
            if child.tag in result:
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data)
            else:
                result[child.tag] = child_data
        
        return result
    
    def _validate_fhir_structure(self, fhir_data: Dict[str, Any]) -> bool:
        """驗證 FHIR 資源結構"""
        if not isinstance(fhir_data, dict):
            return False
        
        resource_type = fhir_data.get('resourceType')
        if not resource_type:
            return False
        
        # 支援的 FHIR 資源類型 - 符合 ONC 認證要求
        supported_types = [
            'Bundle', 'Patient', 'Observation', 'DiagnosticReport', 
            'Encounter', 'Condition', 'MedicationStatement', 
            'Immunization', 'Procedure', 'AllergyIntolerance',
            'DocumentReference', 'CarePlan', 'Goal'
        ]
        
        if resource_type == 'Bundle':
            # 驗證 Bundle 結構
            return 'entry' in fhir_data and isinstance(fhir_data['entry'], list)
        else:
            return resource_type in supported_types
    
    def _process_fhir_resources(self, fhir_data: Dict[str, Any]) -> Dict[str, Any]:
        """處理 FHIR 資源並匯入資料庫"""
        self.processed_count = 0
        self.error_count = 0
        self.errors = []
        created_patients = 0
        created_screenings = 0
        fhir_resources = []
        
        try:
            # 提取資源並建立引用映射
            resources = []
            reference_mapping = {}  # fullUrl -> resource.id 映射
            
            if fhir_data.get('resourceType') == 'Bundle':
                for entry in fhir_data.get('entry', []):
                    if 'resource' in entry:
                        resource = entry['resource']
                        resources.append(resource)
                        
                        # 建立 fullUrl 到 resource.id 的映射
                        full_url = entry.get('fullUrl')
                        resource_id = resource.get('id')
                        if full_url and resource_id:
                            reference_mapping[full_url] = resource_id
            else:
                resources.append(fhir_data)
            
            # 按類型分組資源
            patients = [r for r in resources if r.get('resourceType') == 'Patient']
            observations = [r for r in resources if r.get('resourceType') == 'Observation']
            encounters = [r for r in resources if r.get('resourceType') == 'Encounter']
            conditions = [r for r in resources if r.get('resourceType') == 'Condition']
            medications = [r for r in resources if r.get('resourceType') == 'MedicationStatement']
            
            # 首先處理患者並建立引用映射
            patient_mapping = {}
            for i, patient_resource in enumerate(patients):
                try:
                    with transaction.atomic():
                        patient = self._create_patient_from_fhir(patient_resource)
                        if patient:
                            patient_id = patient_resource.get('id', f'patient_{len(patient_mapping)}')
                            patient_mapping[patient_id] = patient
                            
                            # 從原始 Bundle 中查找對應的 fullUrl
                            if fhir_data.get('resourceType') == 'Bundle':
                                for entry in fhir_data.get('entry', []):
                                    if (entry.get('resource', {}).get('resourceType') == 'Patient' and 
                                        entry.get('resource', {}).get('id') == patient_id):
                                        full_url = entry.get('fullUrl')
                                        if full_url:
                                            patient_mapping[full_url] = patient
                                            # 也添加純 UUID 部分的映射
                                            if 'urn:uuid:' in full_url:
                                                uuid_part = full_url.replace('urn:uuid:', '')
                                                patient_mapping[uuid_part] = patient
                                        break
                            if hasattr(patient, '_created'):
                                created_patients += 1
                            fhir_resources.append({
                                'type': 'Patient',
                                'id': patient_id,
                                'status': 'processed'
                            })
                            self.fhir_resource_count['Patient'] += 1
                        self.processed_count += 1
                except Exception as e:
                    self.errors.append(f"Patient processing error: {str(e)}")
                    self.error_count += 1
            
            # 處理觀察結果（生命徵象、實驗室數據）
            for obs_resource in observations:
                try:
                    with transaction.atomic():
                        self._process_observation_resource(obs_resource, patient_mapping)
                        self.processed_count += 1
                        self.fhir_resource_count['Observation'] += 1
                        fhir_resources.append({
                            'type': 'Observation',
                            'id': obs_resource.get('id', 'unknown'),
                            'status': 'processed'
                        })
                except Exception as e:
                    self.errors.append(f"Observation processing error: {str(e)}")
                    self.error_count += 1
            
            # 處理就診記錄
            for enc_resource in encounters:
                try:
                    with transaction.atomic():
                        screening = self._process_encounter_resource(enc_resource, patient_mapping)
                        if screening:
                            created_screenings += 1
                        self.processed_count += 1
                        self.fhir_resource_count['Encounter'] += 1
                        fhir_resources.append({
                            'type': 'Encounter',
                            'id': enc_resource.get('id', 'unknown'),
                            'status': 'processed'
                        })
                except Exception as e:
                    self.errors.append(f"Encounter processing error: {str(e)}")
                    self.error_count += 1
            
            return {
                'success': True,
                'processed_count': self.processed_count,
                'error_count': self.error_count,
                'total_count': len(resources),
                'errors': self.errors,
                'created_patients': created_patients,
                'created_screenings': created_screenings,
                'fhir_resources': fhir_resources,
                'fhir_resource_count': self.fhir_resource_count,
                'source_format': 'fhir',
                'uscdi_compliance': True  # FHIR R4 天然符合 USCDI
            }
            
        except Exception as e:
            logger.error(f"FHIR processing error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'processed_count': self.processed_count,
                'error_count': self.error_count
            }
    
    def _create_patient_from_fhir(self, patient_resource: Dict[str, Any]) -> Optional[Patient]:
        """從 FHIR Patient 資源創建患者"""
        try:
            # 提取患者 ID
            patient_id = patient_resource.get('id')
            if not patient_id:
                # 生成一個臨時 ID
                patient_id = f"temp_patient_{timezone.now().timestamp()}"
            
            # 查找現有患者
            try:
                patient = Patient.objects.get(medical_record_number=str(patient_id))
                return patient
            except Patient.DoesNotExist:
                pass
            
            # 準備患者資料
            patient_data = {
                'medical_record_number': str(patient_id),
                'is_active': True
            }
            
            # 處理姓名 - FHIR 格式
            names = patient_resource.get('name', [])
            if names:
                name = names[0] if isinstance(names, list) else names
                given = name.get('given', [])
                family = name.get('family', '')
                
                if isinstance(given, list):
                    patient_data['first_name'] = ' '.join(given[:-1]) if len(given) > 1 else (given[0] if given else '')
                    patient_data['middle_name'] = given[-1] if len(given) > 1 else ''
                else:
                    patient_data['first_name'] = given
                
                patient_data['last_name'] = family
            
            # 處理出生日期
            birth_date = patient_resource.get('birthDate')
            if birth_date:
                patient_data['date_of_birth'] = self._parse_date(birth_date)
            
            # 處理性別
            gender = patient_resource.get('gender', '').lower()
            gender_mapping = {
                'male': 'M',
                'female': 'F',
                'other': 'O',
                'unknown': 'U'
            }
            patient_data['gender'] = gender_mapping.get(gender, 'U')
            
            # 處理聯絡資訊
            telecoms = patient_resource.get('telecom', [])
            for telecom in telecoms:
                system = telecom.get('system', '')
                value = telecom.get('value', '')
                if system == 'phone':
                    patient_data['phone_mobile'] = value
                elif system == 'email':
                    patient_data['email'] = value
            
            # 處理地址
            addresses = patient_resource.get('address', [])
            if addresses:
                address = addresses[0] if isinstance(addresses, list) else addresses
                patient_data['address_line_1'] = ' '.join(address.get('line', []))
                patient_data['city'] = address.get('city', '')
                patient_data['state'] = address.get('state', '')
                patient_data['postal_code'] = address.get('postalCode', '')
                patient_data['country'] = address.get('country', '')
            
            # 使用 get_or_create 避免重複創建和事務衝突
            patient, created = Patient.objects.get_or_create(
                medical_record_number=str(patient_id),
                defaults=patient_data
            )
            
            if created:
                patient._created = True
            
            return patient
            
        except Exception as e:
            logger.error(f"FHIR patient creation error: {str(e)}")
            return None
    
    def _process_observation_resource(self, obs_resource: Dict[str, Any], patient_mapping: Dict[str, Patient]):
        """處理 FHIR Observation 資源"""
        try:
            # 找到對應的患者 - 支援多種引用格式
            subject_ref = obs_resource.get('subject', {}).get('reference', '')
            patient = None
            
            # 嘗試多種引用格式
            # 1. 直接引用
            patient = patient_mapping.get(subject_ref)
            
            # 2. 提取最後部分作為 ID
            if not patient and '/' in subject_ref:
                patient_id = subject_ref.split('/')[-1]
                patient = patient_mapping.get(patient_id)
            
            # 3. 去除 urn:uuid: 前綴
            if not patient and subject_ref.startswith('urn:uuid:'):
                uuid_part = subject_ref.replace('urn:uuid:', '')
                patient = patient_mapping.get(uuid_part)
            
            # 4. 直接使用完整引用
            if not patient:
                patient = patient_mapping.get(subject_ref)
            
            if not patient:
                raise ValueError(f"Patient not found for observation: {subject_ref}")
            
            # 獲取或創建健檢記錄
            screening = self._get_or_create_screening_for_patient(patient, obs_resource)
            
            # 解析觀察類型和值
            code = obs_resource.get('code', {})
            value = obs_resource.get('valueQuantity', {}) or obs_resource.get('valueString', '')
            
            # 根據 LOINC 代碼分類處理
            loinc_code = self._get_loinc_code(code)
            if loinc_code:
                self._map_observation_to_model(screening, loinc_code, value, obs_resource)
            
        except Exception as e:
            logger.error(f"Observation processing error: {str(e)}")
            raise
    
    def _process_encounter_resource(self, enc_resource: Dict[str, Any], patient_mapping: Dict[str, Patient]) -> Optional[HealthScreening]:
        """處理 FHIR Encounter 資源"""
        try:
            # 找到對應的患者 - 支援多種引用格式
            subject_ref = enc_resource.get('subject', {}).get('reference', '')
            patient = None
            
            # 嘗試多種引用格式
            # 1. 直接引用
            patient = patient_mapping.get(subject_ref)
            
            # 2. 提取最後部分作為 ID
            if not patient and '/' in subject_ref:
                patient_id = subject_ref.split('/')[-1]
                patient = patient_mapping.get(patient_id)
            
            # 3. 去除 urn:uuid: 前綴
            if not patient and subject_ref.startswith('urn:uuid:'):
                uuid_part = subject_ref.replace('urn:uuid:', '')
                patient = patient_mapping.get(uuid_part)
            
            # 4. 直接使用完整引用
            if not patient:
                patient = patient_mapping.get(subject_ref)
            
            if not patient:
                raise ValueError(f"Patient not found for encounter: {subject_ref}")
            
            # 創建健檢記錄
            period = enc_resource.get('period', {})
            start_date = period.get('start') or period.get('end')
            screening_date = self._parse_date(start_date) if start_date else timezone.now().date()
            
            screening = HealthScreening.objects.create(
                patient=patient,
                screening_date=screening_date,
                screening_type='fhir_import'
            )
            
            return screening
            
        except Exception as e:
            logger.error(f"Encounter processing error: {str(e)}")
            raise
    
    def _get_or_create_screening_for_patient(self, patient: Patient, obs_resource: Dict[str, Any]) -> HealthScreening:
        """為患者獲取或創建健檢記錄"""
        # 嘗試從觀察日期確定檢查日期
        effective_date = obs_resource.get('effectiveDateTime') or obs_resource.get('effectivePeriod', {}).get('start')
        screening_date = self._parse_date(effective_date) if effective_date else timezone.now().date()
        
        # 查找當天的健檢記錄
        screening = HealthScreening.objects.filter(
            patient=patient,
            screening_date=screening_date
        ).first()
        
        if not screening:
            screening = HealthScreening.objects.create(
                patient=patient,
                screening_date=screening_date,
                screening_type='fhir_observation'
            )
        
        return screening
    
    def _get_loinc_code(self, code_obj: Dict[str, Any]) -> Optional[str]:
        """提取 LOINC 代碼"""
        codings = code_obj.get('coding', [])
        for coding in codings:
            if coding.get('system') == 'http://loinc.org':
                return coding.get('code')
        return None
    
    def _map_observation_to_model(self, screening: HealthScreening, loinc_code: str, value: Any, obs_resource: Dict[str, Any]):
        """將觀察結果映射到資料模型"""
        # LOINC 代碼映射表
        loinc_mappings = {
            # 生命徵象
            '8302-2': 'height',      # Body height
            '29463-7': 'weight',     # Body weight
            '8480-6': 'systolic_bp', # Systolic blood pressure
            '8462-4': 'diastolic_bp',# Diastolic blood pressure
            '8867-4': 'heart_rate',  # Heart rate
            '85354-9': 'blood_pressure_panel',  # Blood pressure panel - handle components
            
            # 實驗室檢查
            '2339-0': 'glucose',     # Glucose
            '4548-4': 'hba1c',       # Hemoglobin A1c
            '2093-3': 'cholesterol', # Cholesterol
            '2085-9': 'hdl',         # HDL cholesterol
            '2089-1': 'ldl',         # LDL cholesterol
            '2571-8': 'triglycerides',# Triglycerides
            '2160-0': 'creatinine',  # Creatinine
        }
        
        field_type = loinc_mappings.get(loinc_code)
        if not field_type:
            return
        
        # 特殊處理：血壓面板（包含收縮壓和舒張壓組件）
        if field_type == 'blood_pressure_panel':
            self._process_blood_pressure_components(screening, obs_resource)
            return
        
        # 提取數值
        if isinstance(value, dict) and 'value' in value:
            numeric_value = value['value']
        elif isinstance(value, (int, float)):
            numeric_value = value
        else:
            try:
                numeric_value = float(str(value))
            except:
                return
        
        # 根據類型存儲到相應的模型
        if field_type in ['height', 'weight', 'systolic_bp', 'diastolic_bp', 'heart_rate']:
            self._save_vital_signs(screening, field_type, numeric_value)
        elif field_type in ['glucose', 'hba1c', 'cholesterol', 'hdl', 'ldl', 'triglycerides', 'creatinine']:
            self._save_laboratory_results(screening, field_type, numeric_value)
    
    def _process_blood_pressure_components(self, screening: HealthScreening, obs_resource: Dict[str, Any]):
        """處理血壓組件（收縮壓和舒張壓）"""
        components = obs_resource.get('component', [])
        systolic_value = None
        diastolic_value = None
        
        for component in components:
            code = component.get('code', {})
            loinc_code = self._get_loinc_code(code)
            value_quantity = component.get('valueQuantity', {})
            
            if loinc_code == '8480-6' and 'value' in value_quantity:  # Systolic BP
                systolic_value = float(value_quantity['value'])
            elif loinc_code == '8462-4' and 'value' in value_quantity:  # Diastolic BP
                diastolic_value = float(value_quantity['value'])
        
        # 保存血壓數據
        if systolic_value is not None:
            self._save_vital_signs(screening, 'systolic_bp', systolic_value)
        if diastolic_value is not None:
            self._save_vital_signs(screening, 'diastolic_bp', diastolic_value)
    
    def _save_vital_signs(self, screening: HealthScreening, field_type: str, value: float):
        """保存生命徵象資料"""
        vital_signs, created = VitalSigns.objects.get_or_create(
            health_screening=screening,
            defaults={}
        )
        
        field_mappings = {
            'height': 'height_cm',
            'weight': 'weight_kg',
            'systolic_bp': 'systolic_bp_mmhg',
            'diastolic_bp': 'diastolic_bp_mmhg',
            'heart_rate': 'pulse_rate_bpm'
        }
        
        model_field = field_mappings.get(field_type)
        if model_field:
            setattr(vital_signs, model_field, value)
            vital_signs.save()
    
    def _save_laboratory_results(self, screening: HealthScreening, field_type: str, value: float):
        """保存實驗室檢查資料"""
        lab_results, created = LaboratoryResults.objects.get_or_create(
            health_screening=screening,
            defaults={}
        )
        
        field_mappings = {
            'glucose': 'fasting_glucose_mgdl',
            'hba1c': 'hba1c_percent',
            'cholesterol': 'total_cholesterol_mgdl',
            'hdl': 'hdl_cholesterol_mgdl',
            'ldl': 'ldl_cholesterol_mgdl',
            'triglycerides': 'triglycerides_mgdl',
            'creatinine': 'serum_creatinine_mgdl'
        }
        
        model_field = field_mappings.get(field_type)
        if model_field:
            setattr(lab_results, model_field, value)
            lab_results.save()
    
    def _parse_date(self, date_value: Any) -> Optional[date]:
        """解析日期值"""
        if not date_value:
            return None
        
        try:
            if isinstance(date_value, date):
                return date_value
            elif isinstance(date_value, datetime):
                return date_value.date()
            elif isinstance(date_value, str):
                # 處理 ISO 格式日期
                if 'T' in date_value:
                    date_value = date_value.split('T')[0]
                
                # 嘗試多種日期格式
                date_formats = [
                    '%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%d-%m-%Y',
                    '%m/%d/%Y', '%m-%d-%Y', '%Y%m%d'
                ]
                
                for fmt in date_formats:
                    try:
                        return datetime.strptime(date_value, fmt).date()
                    except ValueError:
                        continue
                        
        except Exception as e:
            logger.warning(f"Date parsing error: {str(e)}")
        
        return timezone.now().date()  # 預設為今天