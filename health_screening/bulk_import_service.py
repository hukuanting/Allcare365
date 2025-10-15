"""
Enhanced Bulk Data Import Service
支援多種格式的批量資料輸入，包括 CSV、JSON、XML 和 FHIR R4
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
from fhir_integration.services import FHIRService

logger = logging.getLogger(__name__)


class BulkImportService:
    """批量資料輸入服務"""
    
    def __init__(self):
        self.uscdi_mapper = USCDIv6Mapper()
        self.fhir_service = FHIRService()
        self.processed_count = 0
        self.error_count = 0
        self.errors = []
        
    def process_file_import(self, file_obj, file_format: str = 'auto') -> Dict[str, Any]:
        """
        處理檔案批量匯入
        支援格式：CSV, Excel, JSON, XML
        """
        try:
            # 自動偵測檔案格式
            if file_format == 'auto':
                file_format = self._detect_file_format(file_obj.name)
            
            # 根據格式解析檔案
            if file_format in ['csv']:
                data = self._parse_csv_file(file_obj)
            elif file_format in ['xlsx', 'xls']:
                data = self._parse_excel_file(file_obj)
            elif file_format == 'json':
                data = self._parse_json_file(file_obj)
            elif file_format == 'xml':
                data = self._parse_xml_file(file_obj)
            else:
                raise ValueError(f"不支援的檔案格式: {file_format}")
            
            # 處理資料匯入
            return self._process_bulk_data(data, source_format=file_format)
            
        except Exception as e:
            logger.error(f"File import error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'processed_count': 0,
                'error_count': 0
            }
    
    def process_text_import(self, text_data: str, data_format: str) -> Dict[str, Any]:
        """
        處理文字格式批量匯入
        支援格式：JSON, XML, CSV
        """
        try:
            if data_format == 'json':
                data = json.loads(text_data)
                if isinstance(data, dict):
                    data = [data]  # 轉換單一物件為陣列
            elif data_format == 'xml':
                data = self._parse_xml_text(text_data)
            elif data_format == 'csv':
                # 將CSV文字轉換為DataFrame
                import io
                data = pd.read_csv(io.StringIO(text_data)).to_dict('records')
            else:
                raise ValueError(f"不支援的文字格式: {data_format}")
            
            return self._process_bulk_data(data, source_format=data_format)
            
        except Exception as e:
            logger.error(f"Text import error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'processed_count': 0,
                'error_count': 0
            }
    
    def process_fhir_import(self, fhir_data: Any, data_format: str = 'json') -> Dict[str, Any]:
        """
        處理 FHIR R4 格式資料匯入 - 增強版
        支援 Bundle 和單一資源，符合 ONC 認證要求
        """
        try:
            # 解析 FHIR 資料
            if data_format == 'json':
                if isinstance(fhir_data, str):
                    fhir_json = json.loads(fhir_data)
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
    
    def _detect_file_format(self, filename: str) -> str:
        """自動偵測檔案格式"""
        extension = filename.lower().split('.')[-1]
        format_mapping = {
            'csv': 'csv',
            'xlsx': 'xlsx',
            'xls': 'xls',
            'json': 'json',
            'xml': 'xml'
        }
        return format_mapping.get(extension, 'unknown')
    
    def _parse_csv_file(self, file_obj) -> List[Dict[str, Any]]:
        """解析 CSV 檔案"""
        try:
            df = pd.read_csv(file_obj, low_memory=False)
            return df.to_dict('records')
        except Exception as e:
            raise ValueError(f"CSV 檔案解析失敗: {str(e)}")
    
    def _parse_excel_file(self, file_obj) -> List[Dict[str, Any]]:
        """解析 Excel 檔案"""
        try:
            df = pd.read_excel(file_obj)
            return df.to_dict('records')
        except Exception as e:
            raise ValueError(f"Excel 檔案解析失敗: {str(e)}")
    
    def _parse_json_file(self, file_obj) -> List[Dict[str, Any]]:
        """解析 JSON 檔案"""
        try:
            data = json.load(file_obj)
            if isinstance(data, dict):
                # 檢查是否為 FHIR Bundle
                if data.get('resourceType') == 'Bundle':
                    return self._extract_from_fhir_bundle(data)
                else:
                    return [data]
            elif isinstance(data, list):
                return data
            else:
                raise ValueError("JSON 格式不正確")
        except Exception as e:
            raise ValueError(f"JSON 檔案解析失敗: {str(e)}")
    
    def _parse_xml_file(self, file_obj) -> List[Dict[str, Any]]:
        """解析 XML 檔案"""
        try:
            tree = ET.parse(file_obj)
            root = tree.getroot()
            return self._xml_to_dict_list(root)
        except Exception as e:
            raise ValueError(f"XML 檔案解析失敗: {str(e)}")
    
    def _parse_xml_text(self, xml_text: str) -> List[Dict[str, Any]]:
        """解析 XML 文字"""
        try:
            root = ET.fromstring(xml_text)
            return self._xml_to_dict_list(root)
        except Exception as e:
            raise ValueError(f"XML 文字解析失敗: {str(e)}")
    
    def _xml_to_dict_list(self, root: ET.Element) -> List[Dict[str, Any]]:
        """將 XML 元素轉換為字典列表"""
        def element_to_dict(element):
            result = {}
            
            # 處理屬性
            if element.attrib:
                result.update(element.attrib)
            
            # 處理文字內容
            if element.text and element.text.strip():
                if len(element) == 0:  # 葉節點
                    return element.text.strip()
                else:
                    result['text'] = element.text.strip()
            
            # 處理子元素
            for child in element:
                child_data = element_to_dict(child)
                if child.tag in result:
                    # 如果已存在同名標籤，轉換為列表
                    if not isinstance(result[child.tag], list):
                        result[child.tag] = [result[child.tag]]
                    result[child.tag].append(child_data)
                else:
                    result[child.tag] = child_data
            
            return result
        
        # 如果根元素包含多個相同的子元素，返回列表
        if len(root) > 1 and len(set(child.tag for child in root)) == 1:
            return [element_to_dict(child) for child in root]
        else:
            return [element_to_dict(root)]
    
    def _extract_from_fhir_bundle(self, bundle: Dict[str, Any]) -> List[Dict[str, Any]]:
        """從 FHIR Bundle 提取資源"""
        resources = []
        if 'entry' in bundle:
            for entry in bundle['entry']:
                if 'resource' in entry:
                    resources.append(entry['resource'])
        return resources
    
    def _process_bulk_data(self, data: List[Dict[str, Any]], source_format: str) -> Dict[str, Any]:
        """處理批量資料"""
        self.processed_count = 0
        self.error_count = 0
        self.errors = []
        created_patients = 0
        created_screenings = 0
        
        # 逐個處理記錄，每個記錄使用獨立的事務
        for index, record in enumerate(data):
            try:
                with transaction.atomic():
                    # 使用 USCDI v6 映射器處理資料
                    uscdi_result = self.uscdi_mapper.map_csv_to_uscdi(record)
                    
                    if not uscdi_result['success']:
                        self.errors.append(f"第 {index + 1} 行: USCDI 映射失敗 - {uscdi_result['error']}")
                        self.error_count += 1
                        continue
                    
                    uscdi_data = uscdi_result['data']
                    
                    # 創建或更新患者
                    patient = self._create_or_update_patient(uscdi_data.get('demographics', {}))
                    if not patient:
                        self.errors.append(f"第 {index + 1} 行: 患者創建失敗")
                        self.error_count += 1
                        continue
                    
                    # 判斷是否為新患者
                    if hasattr(patient, '_created'):
                        created_patients += 1
                    
                    # 創建健檢記錄
                    screening = self._create_health_screening(patient, uscdi_data, record)
                    if screening:
                        created_screenings += 1
                        self.processed_count += 1
                    else:
                        self.error_count += 1
                        
            except Exception as e:
                self.errors.append(f"第 {index + 1} 行: {str(e)}")
                self.error_count += 1
                logger.error(f"Error processing record {index + 1}: {str(e)}")
        
        return {
            'success': True,
            'processed_count': self.processed_count,
            'error_count': self.error_count,
            'total_count': len(data),
            'errors': self.errors,
            'created_patients': created_patients,
            'created_screenings': created_screenings,
            'source_format': source_format
        }
    
    def _create_or_update_patient(self, demographics: Dict[str, Any]) -> Optional[Patient]:
        """創建或更新患者記錄"""
        if not demographics:
            return None
        
        try:
            # 尋找患者識別碼
            patient_id = demographics.get('patient_id')
            if not patient_id:
                return None
            
            # 嘗試根據病歷號查找現有患者
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
            
            # 處理姓名
            if demographics.get('full_name'):
                # 嘗試分割全名
                name_parts = demographics['full_name'].split()
                if len(name_parts) >= 2:
                    patient_data['first_name'] = ' '.join(name_parts[:-1])
                    patient_data['last_name'] = name_parts[-1]
                else:
                    patient_data['first_name'] = demographics['full_name']
                    patient_data['last_name'] = ''
            else:
                patient_data['first_name'] = demographics.get('first_name', f'Patient_{patient_id}')
                patient_data['last_name'] = demographics.get('last_name', '')
            
            # 處理出生日期
            birth_date = demographics.get('birth_date')
            if birth_date:
                patient_data['date_of_birth'] = self._parse_date(birth_date)
            
            # 處理性別
            gender = demographics.get('gender', '').upper()
            if gender in ['M', 'MALE', '男']:
                patient_data['gender'] = 'M'
            elif gender in ['F', 'FEMALE', '女']:
                patient_data['gender'] = 'F'
            else:
                patient_data['gender'] = 'U'
            
            # 處理聯絡資訊
            if demographics.get('phone'):
                patient_data['phone_mobile'] = demographics['phone']
            if demographics.get('email'):
                patient_data['email'] = demographics['email']
            
            # 處理地址資訊
            if demographics.get('address'):
                patient_data['address_line_1'] = demographics['address']
            if demographics.get('city'):
                patient_data['city'] = demographics['city']
            if demographics.get('state'):
                patient_data['state'] = demographics['state']
            if demographics.get('zip_code'):
                patient_data['postal_code'] = demographics['zip_code']
            
            # 使用 get_or_create 避免重複創建和事務衝突
            patient, created = Patient.objects.get_or_create(
                medical_record_number=str(patient_id),
                defaults=patient_data
            )
            
            if created:
                patient._created = True  # 標記為新創建
            
            return patient
            
        except Exception as e:
            logger.error(f"Patient creation error: {str(e)}")
            return None
    
    def _create_health_screening(self, patient: Patient, uscdi_data: Dict[str, Any], 
                               original_record: Dict[str, Any]) -> Optional[HealthScreening]:
        """創建健檢記錄"""
        try:
            # 確定檢查日期
            screening_date = self._get_screening_date(original_record)
            
            # 創建健檢主記錄
            screening = HealthScreening.objects.create(
                patient=patient,
                screening_date=screening_date,
                screening_type='comprehensive_health_check',
                # 移除 notes 參數，因為 HealthScreening 模型沒有此欄位
                # notes=f"批量匯入資料 - USCDI v6 合規性: {uscdi_data.get('compliance_score', {}).get('overall_score', 0)}%"
            )
            
            # 創建生命徵象記錄
            vital_signs_data = uscdi_data.get('vital_signs')
            if vital_signs_data:
                self._create_vital_signs(screening, vital_signs_data)
            
            # 創建實驗室檢查記錄
            laboratory_data = uscdi_data.get('laboratory')
            if laboratory_data:
                self._create_laboratory_results(screening, laboratory_data)
            
            # 創建病史記錄
            conditions_data = uscdi_data.get('conditions')
            medications_data = uscdi_data.get('medications')
            if conditions_data or medications_data:
                self._create_medical_history(screening, conditions_data, medications_data)
            
            # 創建生活習慣記錄
            self._create_lifestyle_questionnaire(screening, uscdi_data, original_record)
            
            return screening
            
        except Exception as e:
            logger.error(f"Health screening creation error: {str(e)}")
            return None
    
    def _create_vital_signs(self, screening: HealthScreening, vital_data: Dict[str, Any]):
        """創建生命徵象記錄"""
        try:
            vital_signs_data = {
                'health_screening': screening
            }
            
            # 映射生命徵象資料 - 使用實際模型欄位
            field_mappings = {
                'height_cm': 'height_cm',
                'weight_kg': 'weight_kg',
                'systolic_bp': 'systolic_bp_mmhg',
                'diastolic_bp': 'diastolic_bp_mmhg',
                'heart_rate': 'pulse_rate_bpm',
                'waist_circumference': 'waist_circumference_cm',
                'hip_circumference': 'hip_circumference_cm',
                'neck_circumference': 'neck_circumference_cm'
            }
            
            for uscdi_field, model_field in field_mappings.items():
                if uscdi_field in vital_data and vital_data[uscdi_field] is not None:
                    vital_value = vital_data[uscdi_field]
                    # 檢查數值範圍，避免溢出
                    if model_field in ['neck_circumference_cm', 'pulse_rate_bpm']:
                        # 精度 4,1，最大值 999.9
                        if vital_value > 999.9:
                            continue
                    elif model_field in ['height_cm', 'weight_kg', 'waist_circumference_cm', 'hip_circumference_cm']:
                        # 精度 5,1，最大值 9999.9
                        if vital_value > 9999.9:
                            continue
                    elif model_field in ['systolic_bp_mmhg', 'diastolic_bp_mmhg']:
                        # 血壓值合理範圍檢查
                        if vital_value > 300 or vital_value < 0:
                            continue
                    
                    vital_signs_data[model_field] = vital_value
            
            if len(vital_signs_data) > 1:  # 除了 health_screening 還有其他資料
                try:
                    VitalSigns.objects.create(**vital_signs_data)
                except Exception as e:
                    logger.error(f"Vital signs creation error: {str(e)}")
                    raise
                
        except Exception as e:
            logger.error(f"Vital signs creation error: {str(e)}")
    
    def _create_laboratory_results(self, screening: HealthScreening, lab_data: Dict[str, Any]):
        """創建實驗室檢查記錄"""
        try:
            lab_results_data = {
                'health_screening': screening
            }
            
            # 映射實驗室檢查資料 - 使用實際模型欄位
            field_mappings = {
                'fasting_glucose': 'fasting_glucose_mgdl',
                'hba1c': 'hba1c_percent',
                'total_cholesterol': 'total_cholesterol_mgdl',
                'hdl_cholesterol': 'hdl_cholesterol_mgdl',
                'ldl_cholesterol': 'ldl_cholesterol_mgdl',
                'triglycerides': 'triglycerides_mgdl',
                'creatinine': 'serum_creatinine_mgdl',
                'wbc_count': 'wbc_count'
            }
            
            for uscdi_field, model_field in field_mappings.items():
                if uscdi_field in lab_data and lab_data[uscdi_field] is not None:
                    lab_value = lab_data[uscdi_field]
                    # 檢查數值範圍，避免溢出
                    if model_field in ['hba1c_percent']:
                        # 精度 4,1，最大值 999.9
                        if lab_value > 999.9:
                            continue
                    elif model_field == 'serum_creatinine_mgdl':
                        # 精度 4,2，最大值 99.99
                        if lab_value > 99.99:
                            continue
                    elif model_field in ['fasting_glucose_mgdl', 'triglycerides_mgdl', 'total_cholesterol_mgdl', 'hdl_cholesterol_mgdl', 'ldl_cholesterol_mgdl']:
                        # 精度 5,1，最大值 9999.9
                        if lab_value > 9999.9:
                            continue
                    elif model_field == 'wbc_count':
                        # 白血球計數合理範圍
                        if lab_value > 999999 or lab_value < 0:
                            continue
                    
                    lab_results_data[model_field] = lab_value
            
            if len(lab_results_data) > 1:  # 除了 health_screening 還有其他資料
                try:
                    LaboratoryResults.objects.create(**lab_results_data)
                except Exception as e:
                    logger.error(f"Laboratory results creation error: {str(e)}")
                    raise
                
        except Exception as e:
            logger.error(f"Laboratory results creation error: {str(e)}")
    
    def _create_medical_history(self, screening: HealthScreening, 
                              conditions_data: Optional[List[Dict[str, Any]]], 
                              medications_data: Optional[List[Dict[str, Any]]]):
        """創建病史記錄"""
        try:
            history_data = {
                'health_screening': screening
            }
            
            # 處理疾病狀態
            if conditions_data:
                for condition in conditions_data:
                    condition_name = condition.get('condition', '')
                    if condition_name == 'diabetes':
                        history_data['diabetes_treated'] = True
                    elif condition_name == 'hypertension':
                        history_data['hypertension_treated'] = True
                    elif condition_name == 'hyperlipidemia':
                        history_data['hyperlipidemia_treated'] = True
            
            # 處理用藥狀態
            if medications_data:
                for medication in medications_data:
                    med_type = medication.get('medication_type', '')
                    if med_type == 'antihypertensive':
                        history_data['hypertension_treated'] = True
                    elif med_type == 'diabetes_medication':
                        history_data['diabetes_treated'] = True
                    elif med_type == 'lipid_lowering':
                        history_data['hyperlipidemia_treated'] = True
            
            if len(history_data) > 1:  # 除了 health_screening 還有其他資料
                try:
                    MedicalHistory.objects.create(**history_data)
                except Exception as e:
                    logger.error(f"Medical history creation error: {str(e)}")
                    raise
                
        except Exception as e:
            logger.error(f"Medical history creation error: {str(e)}")
    
    def _create_lifestyle_questionnaire(self, screening: HealthScreening, 
                                      uscdi_data: Dict[str, Any], 
                                      original_record: Dict[str, Any]):
        """創建生活習慣問卷記錄"""
        try:
            lifestyle_data = {
                'health_screening': screening
            }
            
            # 從原始記錄中提取生活習慣資料
            smoking_fields = ['HQ_SMOKE', 'is_current_smoker', 'smoking_status']
            for field in smoking_fields:
                if field in original_record:
                    value = str(original_record[field]).upper()
                    if value in ['TRUE', 'YES', 'CURRENT', 'Y', '1']:
                        lifestyle_data['is_current_smoker'] = True
                        break
                    elif value in ['FORMER', 'PREVIOUS']:
                        lifestyle_data['is_former_smoker'] = True
                        break
            
            # 運動習慣
            exercise_fields = ['HQ_Exercise', 'exercise_score', 'physical_activity']
            for field in exercise_fields:
                if field in original_record:
                    value = str(original_record[field]).upper()
                    if value in ['TRUE', 'YES', 'REGULAR', 'HIGH', '1']:
                        lifestyle_data['exercise_score'] = 'regularly'
                        break
                    elif value in ['FALSE', 'NO', 'SEDENTARY', 'LOW', '0']:
                        lifestyle_data['exercise_score'] = 'rarely'
                        break
            
            # 疾病狀態（從 conditions 資料中提取）
            conditions_data = uscdi_data.get('conditions', [])
            for condition in conditions_data:
                condition_name = condition.get('condition', '')
                if condition_name == 'diabetes':
                    lifestyle_data['has_diabetes'] = True
                elif condition_name == 'coronary_heart_disease':
                    lifestyle_data['has_coronary_heart_disease'] = True
                elif condition_name == 'arrhythmia':
                    # lifestyle_data['has_arrhythmia'] = True  # 此欄位在 LifestyleQuestionnaire 模型中不存在，已移除
                    pass
            
            if len(lifestyle_data) > 1:  # 除了 health_screening 還有其他資料
                try:
                    LifestyleQuestionnaire.objects.create(**lifestyle_data)
                except Exception as e:
                    logger.error(f"Lifestyle questionnaire creation error: {str(e)}")
                    raise
                
        except Exception as e:
            logger.error(f"Lifestyle questionnaire creation error: {str(e)}")
    
    def _get_screening_date(self, record: Dict[str, Any]) -> date:
        """獲取檢查日期"""
        date_fields = ['CheckDate', 'screening_date', 'exam_date', 'visit_date']
        
        for field in date_fields:
            if field in record and record[field]:
                parsed_date = self._parse_date(record[field])
                if parsed_date:
                    return parsed_date
        
        # 如果沒有找到日期，使用今天
        return timezone.now().date()
    
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
                # 嘗試多種日期格式
                date_formats = [
                    '%Y/%m/%d', '%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y',
                    '%m/%d/%Y', '%m-%d-%Y', '%Y%m%d'
                ]
                
                for fmt in date_formats:
                    try:
                        return datetime.strptime(date_value, fmt).date()
                    except ValueError:
                        continue
                
                # 使用 pandas 的日期解析
                import pandas as pd
                parsed_date = pd.to_datetime(date_value, errors='coerce')
                if not pd.isna(parsed_date):
                    return parsed_date.date()
            
        except Exception as e:
            logger.warning(f"Date parsing error: {str(e)}")
        
        return None
    
    def _parse_fhir_xml(self, xml_data: str) -> Dict[str, Any]:
        """解析 FHIR XML 格式資料"""
        try:
            root = ET.fromstring(xml_data)
            return self._xml_element_to_dict(root)
        except Exception as e:
            raise ValueError(f"FHIR XML 解析失敗: {str(e)}")
    
    def _xml_element_to_dict(self, element: ET.Element) -> Dict[str, Any]:
        """將 XML 元素轉換為字典"""
        result = {}
        if element.attrib:
            result.update(element.attrib)
        if element.text and element.text.strip():
            if len(element) == 0:
                return element.text.strip()
            else:
                result['value'] = element.text.strip()
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
        supported_types = [
            'Bundle', 'Patient', 'Observation', 'DiagnosticReport', 
            'Encounter', 'Condition', 'MedicationStatement', 
            'Immunization', 'Procedure', 'AllergyIntolerance'
        ]
        if resource_type == 'Bundle':
            return 'entry' in fhir_data and isinstance(fhir_data['entry'], list)
        else:
            return resource_type in supported_types
    
    def _process_fhir_resources(self, fhir_data: Dict[str, Any]) -> Dict[str, Any]:
        """處理 FHIR 資源並匯入資料庫"""
        # 簡化版 FHIR 處理 - 轉換為標準格式後使用現有邏輯
        resources = []
        patient_reference_mapping = {}  # fullUrl -> Patient ID 映射
        
        if fhir_data.get('resourceType') == 'Bundle':
            for entry in fhir_data.get('entry', []):
                if 'resource' in entry:
                    resource = entry['resource']
                    resources.append(resource)
                    
                    # 建立 Patient 引用映射
                    if resource.get('resourceType') == 'Patient':
                        full_url = entry.get('fullUrl')
                        patient_id = resource.get('id')
                        if full_url and patient_id:
                            patient_reference_mapping[full_url] = patient_id
                            # 也添加 UUID 部分的映射
                            if 'urn:uuid:' in full_url:
                                uuid_part = full_url.replace('urn:uuid:', '')
                                patient_reference_mapping[uuid_part] = patient_id
        else:
            resources.append(fhir_data)
        
        # 轉換 FHIR 資源為內部格式
        converted_data = []
        for resource in resources:
            if resource.get('resourceType') == 'Patient':
                patient_data = self._convert_fhir_patient(resource)
                if patient_data:
                    converted_data.append(patient_data)
        
        if not converted_data:
            return {
                'success': False,
                'error': '沒有找到可處理的 Patient 資源',
                'processed_count': 0,
                'error_count': 0
            }
        
        # 使用現有的批量處理邏輯
        return self._process_bulk_data(converted_data, source_format='fhir')
    
    def _convert_fhir_patient(self, patient_resource: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """將 FHIR Patient 資源轉換為內部格式"""
        try:
            data = {'ID': patient_resource.get('id', 'unknown')}
            
            # 處理姓名
            names = patient_resource.get('name', [])
            if names:
                name = names[0] if isinstance(names, list) else names
                given = name.get('given', [])
                family = name.get('family', '')
                if isinstance(given, list):
                    given_name = ' '.join(given)
                else:
                    given_name = given
                data['full_name'] = f"{given_name} {family}".strip()
            
            # 處理性別
            gender = patient_resource.get('gender', '').upper()
            if gender == 'MALE':
                data['SEX'] = 'M'
            elif gender == 'FEMALE':
                data['SEX'] = 'F'
            else:
                data['SEX'] = 'U'
            
            # 處理出生日期
            birth_date = patient_resource.get('birthDate')
            if birth_date:
                data['BirthDate'] = birth_date
            
            # 設置檢查日期為今天
            data['CheckDate'] = timezone.now().strftime('%Y/%m/%d')
            
            return data
            
        except Exception as e:
            logger.error(f"FHIR patient conversion error: {str(e)}")
            return None