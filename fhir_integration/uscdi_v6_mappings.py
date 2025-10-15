"""
USCDI v6 Data Element Mappings and Processing
支援完整的 USCDI v6 資料類別和元素
"""

from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime, date
import json

logger = logging.getLogger(__name__)


class USCDIv6Mapper:
    """USCDI v6 資料映射器"""
    
    # USCDI v6 完整資料類別定義
    USCDI_V6_DATA_CLASSES = {
        'demographics': {
            'name': 'Patient Demographics',
            'required_elements': [
                'Patient Name',
                'Sex (assigned at birth)',
                'Date of Birth',
                'Race',
                'Ethnicity',
                'Preferred Language',
                'Sexual Orientation',
                'Gender Identity',
                'Date of Death',
                'Address',
                'Phone Number',
                'Email'
            ]
        },
        'vital_signs': {
            'name': 'Vital Signs',
            'required_elements': [
                'Diastolic blood pressure',
                'Systolic blood pressure',
                'Body height',
                'Body weight',
                'Heart rate',
                'Respiratory rate',
                'Body temperature',
                'Pulse oximetry',
                'Inhaled oxygen concentration',
                'BMI percentile per age and sex for youth 2-20',
                'Weight-for-length percentile per age and sex',
                'Head occipital-frontal circumference per age and sex',
                'Blood pressure percentile per age and sex'
            ]
        },
        'laboratory': {
            'name': 'Laboratory',
            'required_elements': [
                'Tests',
                'Values/Results'
            ]
        },
        'medications': {
            'name': 'Medications',
            'required_elements': [
                'Medication',
                'Dosage',
                'Frequency',
                'Route',
                'Medication lot number',
                'Medication expiration date'
            ]
        },
        'allergies': {
            'name': 'Allergies and Intolerances',
            'required_elements': [
                'Substance (Medication)',
                'Substance (Drug class)',
                'Substance (Ingredient)',
                'Substance (Food)',
                'Substance (Environmental)',
                'Reaction'
            ]
        },
        'conditions': {
            'name': 'Problems',
            'required_elements': [
                'Problem',
                'Date of diagnosis',
                'Date of resolution'
            ]
        },
        'procedures': {
            'name': 'Procedures',
            'required_elements': [
                'Procedure',
                'Date',
                'Report'
            ]
        },
        'immunizations': {
            'name': 'Immunizations',
            'required_elements': [
                'Immunization',
                'Date',
                'Lot number',
                'Expiration date',
                'Route',
                'Site'
            ]
        },
        'care_team': {
            'name': 'Care Team Members',
            'required_elements': [
                'Care team member name',
                'Role',
                'Telecom',
                'Address',
                'Location',
                'Organization',
                'Period'
            ]
        },
        'clinical_notes': {
            'name': 'Clinical Notes',
            'required_elements': [
                'Consultation note',
                'Discharge summary note',
                'History and physical note',
                'Imaging narrative',
                'Laboratory report narrative',
                'Pathology report narrative',
                'Procedure note',
                'Progress note'
            ]
        }
    }
    
    # LOINC 碼映射表 - 常用檢驗項目
    LOINC_MAPPINGS = {
        # 生命徵象
        '8480-6': {'name': 'Systolic blood pressure', 'unit': 'mmHg', 'category': 'vital_signs'},
        '8462-4': {'name': 'Diastolic blood pressure', 'unit': 'mmHg', 'category': 'vital_signs'},
        '8302-2': {'name': 'Body height', 'unit': 'cm', 'category': 'vital_signs'},
        '29463-7': {'name': 'Body weight', 'unit': 'kg', 'category': 'vital_signs'},
        '8867-4': {'name': 'Heart rate', 'unit': 'beats/min', 'category': 'vital_signs'},
        '9279-1': {'name': 'Respiratory rate', 'unit': 'breaths/min', 'category': 'vital_signs'},
        '8310-5': {'name': 'Body temperature', 'unit': 'Cel', 'category': 'vital_signs'},
        '2708-6': {'name': 'Oxygen saturation', 'unit': '%', 'category': 'vital_signs'},
        '39156-5': {'name': 'Body mass index', 'unit': 'kg/m2', 'category': 'vital_signs'},
        
        # 實驗室檢查 - 血糖代謝
        '1558-6': {'name': 'Fasting glucose', 'unit': 'mg/dL', 'category': 'laboratory'},
        '4548-4': {'name': 'Hemoglobin A1c', 'unit': '%', 'category': 'laboratory'},
        '33747-0': {'name': 'Random glucose', 'unit': 'mg/dL', 'category': 'laboratory'},
        
        # 實驗室檢查 - 血脂
        '2093-3': {'name': 'Total cholesterol', 'unit': 'mg/dL', 'category': 'laboratory'},
        '2085-9': {'name': 'HDL cholesterol', 'unit': 'mg/dL', 'category': 'laboratory'},
        '18261-8': {'name': 'LDL cholesterol', 'unit': 'mg/dL', 'category': 'laboratory'},
        '2571-8': {'name': 'Triglycerides', 'unit': 'mg/dL', 'category': 'laboratory'},
        
        # 實驗室檢查 - 腎功能
        '2160-0': {'name': 'Serum creatinine', 'unit': 'mg/dL', 'category': 'laboratory'},
        '6299-2': {'name': 'Urea nitrogen', 'unit': 'mg/dL', 'category': 'laboratory'},
        '33914-3': {'name': 'eGFR', 'unit': 'mL/min/1.73m2', 'category': 'laboratory'},
        
        # 實驗室檢查 - 血液檢查
        '718-7': {'name': 'Hemoglobin', 'unit': 'g/dL', 'category': 'laboratory'},
        '4544-3': {'name': 'Hematocrit', 'unit': '%', 'category': 'laboratory'},
        '6690-2': {'name': 'White blood cell count', 'unit': '10*3/uL', 'category': 'laboratory'},
        '777-3': {'name': 'Platelet count', 'unit': '10*3/uL', 'category': 'laboratory'},
        
        # 實驗室檢查 - 肝功能
        '1742-6': {'name': 'ALT', 'unit': 'U/L', 'category': 'laboratory'},
        '1920-8': {'name': 'AST', 'unit': 'U/L', 'category': 'laboratory'},
        '1975-2': {'name': 'Total bilirubin', 'unit': 'mg/dL', 'category': 'laboratory'},
        
        # 實驗室檢查 - 電解質
        '2947-0': {'name': 'Sodium', 'unit': 'mmol/L', 'category': 'laboratory'},
        '2823-3': {'name': 'Potassium', 'unit': 'mmol/L', 'category': 'laboratory'},
        '2075-0': {'name': 'Chloride', 'unit': 'mmol/L', 'category': 'laboratory'},
    }
    
    def __init__(self):
        self.processed_count = 0
        self.error_count = 0
        self.errors = []
    
    def map_csv_to_uscdi(self, csv_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        將 CSV 資料映射到 USCDI v6 標準格式
        """
        try:
            uscdi_data = {
                'demographics': self._extract_demographics(csv_data),
                'vital_signs': self._extract_vital_signs(csv_data),
                'laboratory': self._extract_laboratory(csv_data),
                'conditions': self._extract_conditions(csv_data),
                'medications': self._extract_medications(csv_data),
                'allergies': self._extract_allergies(csv_data),
                'immunizations': self._extract_immunizations(csv_data),
                'procedures': self._extract_procedures(csv_data)
            }
            
            # 移除空的資料類別
            uscdi_data = {k: v for k, v in uscdi_data.items() if v}
            
            return {
                'success': True,
                'data': uscdi_data,
                'compliance_score': self._calculate_compliance_score(uscdi_data)
            }
            
        except Exception as e:
            logger.error(f"USCDI mapping error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'data': None
            }
    
    def _extract_demographics(self, csv_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取人口統計學資料"""
        demographics = {}
        
        # 基本資料映射
        field_mappings = {
            'patient_id': ['ID', 'patient_id', 'PatientID', 'Patient_ID'],
            'first_name': ['FirstName', 'first_name', 'Given', 'GivenName'],
            'last_name': ['LastName', 'last_name', 'Family', 'FamilyName'],
            'full_name': ['Name', 'PatientName', 'patient_name'],
            'birth_date': ['BirthDate', 'birth_date', 'DOB', 'DateOfBirth'],
            'gender': ['SEX', 'Gender', 'gender', 'Sex'],
            'race': ['Race', 'race'],
            'ethnicity': ['Ethnicity', 'ethnicity'],
            'language': ['Language', 'PreferredLanguage', 'language'],
            'phone': ['Phone', 'PhoneNumber', 'phone_number'],
            'email': ['Email', 'email', 'EmailAddress'],
            'address': ['Address', 'address', 'StreetAddress'],
            'city': ['City', 'city'],
            'state': ['State', 'state'],
            'zip_code': ['ZipCode', 'zip_code', 'PostalCode', 'postal_code']
        }
        
        for uscdi_field, csv_fields in field_mappings.items():
            value = self._find_value_in_csv(csv_data, csv_fields)
            if value:
                demographics[uscdi_field] = value
        
        return demographics if demographics else None
    
    def _extract_vital_signs(self, csv_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取生命徵象"""
        vital_signs = {}
        
        # 生命徵象映射
        vital_mappings = {
            'height_cm': ['Height', 'height', 'height_cm', 'BodyHeight'],
            'weight_kg': ['Weight', 'weight', 'weight_kg', 'BodyWeight'],
            'systolic_bp': ['SBP', 'systolic_bp', 'SystolicBP', 'Systolic'],
            'diastolic_bp': ['DBP', 'diastolic_bp', 'DiastolicBP', 'Diastolic'],
            'heart_rate': ['PulseRate', 'heart_rate', 'HeartRate', 'Pulse'],
            'respiratory_rate': ['RespRate', 'respiratory_rate', 'RespiratoryRate'],
            'temperature': ['Temperature', 'temp', 'body_temperature'],
            'oxygen_saturation': ['SpO2', 'oxygen_saturation', 'OxygenSat'],
            'waist_circumference': ['Waist', 'waist_circumference', 'WaistCirc'],
            'hip_circumference': ['Hip', 'hip_circumference', 'HipCirc'],
            'neck_circumference': ['Neck', 'neck_circumference', 'NeckCirc']
        }
        
        for uscdi_field, csv_fields in vital_mappings.items():
            value = self._find_numeric_value_in_csv(csv_data, csv_fields)
            if value is not None:
                vital_signs[uscdi_field] = value
        
        # 計算 BMI 如果有身高體重
        if 'height_cm' in vital_signs and 'weight_kg' in vital_signs:
            height_m = vital_signs['height_cm'] / 100
            vital_signs['bmi'] = round(vital_signs['weight_kg'] / (height_m ** 2), 1)
        
        return vital_signs if vital_signs else None
    
    def _extract_laboratory(self, csv_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取實驗室檢查資料"""
        laboratory = {}
        
        # 實驗室檢查映射
        lab_mappings = {
            'fasting_glucose': ['FPG', 'fasting_glucose', 'FastingGlucose', 'Glucose'],
            'hba1c': ['HbA1C', 'hba1c', 'HemoglobinA1c', 'A1C'],
            'total_cholesterol': ['TC', 'total_cholesterol', 'TotalCholesterol', 'Cholesterol'],
            'hdl_cholesterol': ['HDL', 'hdl_cholesterol', 'HDLCholesterol'],
            'ldl_cholesterol': ['LDL', 'ldl_cholesterol', 'LDLCholesterol'],
            'triglycerides': ['TG', 'triglycerides', 'Triglycerides'],
            'creatinine': ['Creatinine', 'creatinine', 'SerumCreatinine'],
            'bun': ['BUN', 'bun', 'UreaNitrogen'],
            'hemoglobin': ['Hb', 'hemoglobin', 'Hemoglobin'],
            'hematocrit': ['Hct', 'hematocrit', 'Hematocrit'],
            'wbc_count': ['WBC', 'wbc_count', 'WhiteBloodCell'],
            'platelet_count': ['PLT', 'platelet_count', 'Platelet'],
            'alt': ['ALT', 'alt', 'SGPT'],
            'ast': ['AST', 'ast', 'SGOT'],
            'sodium': ['Na', 'sodium', 'Sodium'],
            'potassium': ['K', 'potassium', 'Potassium'],
            'chloride': ['Cl', 'chloride', 'Chloride']
        }
        
        for uscdi_field, csv_fields in lab_mappings.items():
            value = self._find_numeric_value_in_csv(csv_data, csv_fields)
            if value is not None:
                laboratory[uscdi_field] = value
        
        return laboratory if laboratory else None
    
    def _extract_conditions(self, csv_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取疾病/問題資料"""
        conditions = []
        
        # 布林型疾病狀態映射
        condition_mappings = {
            'diabetes': ['HQ_Diabetes', 'has_diabetes', 'Diabetes'],
            'hypertension': ['HQ_Hypertension', 'has_hypertension', 'Hypertension'],
            'coronary_heart_disease': ['HQ_CHD', 'has_coronary_heart_disease', 'CHD'],
            'arrhythmia': ['HQ_arrhythmia', 'has_arrhythmia', 'Arrhythmia'],
            'hyperlipidemia': ['HQ_Hyperlipidemia', 'has_hyperlipidemia', 'Hyperlipidemia']
        }
        
        for condition_name, csv_fields in condition_mappings.items():
            value = self._find_boolean_value_in_csv(csv_data, csv_fields)
            if value:
                conditions.append({
                    'condition': condition_name,
                    'status': 'active',
                    'date_identified': csv_data.get('CheckDate', csv_data.get('screening_date'))
                })
        
        return conditions if conditions else None
    
    def _extract_medications(self, csv_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取用藥資料"""
        medications = []
        
        # 治療狀態映射
        treatment_mappings = {
            'antihypertensive': ['HQ_BP_Treat', 'hypertension_treated', 'BP_Treatment'],
            'diabetes_medication': ['HQ_Diabetes_Treat', 'diabetes_treated', 'DM_Treatment'],
            'lipid_lowering': ['HQ_low_fat_Treat', 'hyperlipidemia_treated', 'Lipid_Treatment']
        }
        
        for med_type, csv_fields in treatment_mappings.items():
            value = self._find_boolean_value_in_csv(csv_data, csv_fields)
            if value:
                medications.append({
                    'medication_type': med_type,
                    'status': 'active',
                    'start_date': csv_data.get('CheckDate', csv_data.get('screening_date'))
                })
        
        return medications if medications else None
    
    def _extract_allergies(self, csv_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取過敏資料"""
        allergies = []
        
        # 過敏相關欄位映射
        allergy_fields = ['Allergies', 'allergies', 'AllergyList', 'KnownAllergies']
        
        for field in allergy_fields:
            if field in csv_data and csv_data[field]:
                # 如果是字串，嘗試分割多個過敏原
                allergy_text = str(csv_data[field])
                if allergy_text.lower() not in ['none', 'nka', 'nkda', '無', '']:
                    allergy_items = [item.strip() for item in allergy_text.split(',')]
                    for allergen in allergy_items:
                        if allergen:
                            allergies.append({
                                'allergen': allergen,
                                'type': 'allergy',
                                'status': 'active'
                            })
        
        return allergies if allergies else None
    
    def _extract_immunizations(self, csv_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取疫苗接種資料"""
        immunizations = []
        
        # 疫苗相關欄位映射
        vaccine_fields = ['Vaccines', 'immunizations', 'VaccineHistory']
        
        for field in vaccine_fields:
            if field in csv_data and csv_data[field]:
                vaccine_text = str(csv_data[field])
                if vaccine_text.lower() not in ['none', '無', '']:
                    vaccine_items = [item.strip() for item in vaccine_text.split(',')]
                    for vaccine in vaccine_items:
                        if vaccine:
                            immunizations.append({
                                'vaccine': vaccine,
                                'status': 'completed',
                                'date': csv_data.get('CheckDate', csv_data.get('screening_date'))
                            })
        
        return immunizations if immunizations else None
    
    def _extract_procedures(self, csv_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取醫療程序資料"""
        procedures = []
        
        # 程序相關欄位映射
        procedure_fields = ['Procedures', 'procedures', 'MedicalProcedures']
        
        for field in procedure_fields:
            if field in csv_data and csv_data[field]:
                procedure_text = str(csv_data[field])
                if procedure_text.lower() not in ['none', '無', '']:
                    procedure_items = [item.strip() for item in procedure_text.split(',')]
                    for procedure in procedure_items:
                        if procedure:
                            procedures.append({
                                'procedure': procedure,
                                'status': 'completed',
                                'date': csv_data.get('CheckDate', csv_data.get('screening_date'))
                            })
        
        return procedures if procedures else None
    
    def _find_value_in_csv(self, csv_data: Dict[str, Any], field_names: List[str]) -> Optional[str]:
        """在 CSV 資料中尋找欄位值"""
        for field_name in field_names:
            if field_name in csv_data and csv_data[field_name] is not None:
                value = str(csv_data[field_name]).strip()
                if value and value.lower() not in ['', 'nan', 'null', 'none']:
                    return value
        return None
    
    def _find_numeric_value_in_csv(self, csv_data: Dict[str, Any], field_names: List[str]) -> Optional[float]:
        """在 CSV 資料中尋找數值型欄位值"""
        for field_name in field_names:
            if field_name in csv_data and csv_data[field_name] is not None:
                try:
                    value = float(csv_data[field_name])
                    if not (value != value):  # 檢查 NaN
                        return value
                except (ValueError, TypeError):
                    continue
        return None
    
    def _find_boolean_value_in_csv(self, csv_data: Dict[str, Any], field_names: List[str]) -> bool:
        """在 CSV 資料中尋找布林型欄位值"""
        for field_name in field_names:
            if field_name in csv_data and csv_data[field_name] is not None:
                value = str(csv_data[field_name]).strip().upper()
                if value in ['TRUE', 'YES', 'Y', '1', 'T']:
                    return True
                elif value in ['FALSE', 'NO', 'N', '0', 'F']:
                    return False
        return False
    
    def _calculate_compliance_score(self, uscdi_data: Dict[str, Any]) -> Dict[str, Any]:
        """計算 USCDI v6 合規性評分"""
        total_classes = len(self.USCDI_V6_DATA_CLASSES)
        present_classes = len([k for k in uscdi_data.keys() if uscdi_data[k]])
        
        compliance_score = {
            'overall_score': round((present_classes / total_classes) * 100, 1),
            'present_classes': present_classes,
            'total_classes': total_classes,
            'missing_classes': [
                class_name for class_name in self.USCDI_V6_DATA_CLASSES.keys()
                if class_name not in uscdi_data or not uscdi_data[class_name]
            ],
            'detailed_scores': {}
        }
        
        # 計算各類別詳細評分
        for class_name, class_info in self.USCDI_V6_DATA_CLASSES.items():
            if class_name in uscdi_data and uscdi_data[class_name]:
                compliance_score['detailed_scores'][class_name] = {
                    'present': True,
                    'completeness': self._calculate_class_completeness(
                        class_name, uscdi_data[class_name], class_info
                    )
                }
            else:
                compliance_score['detailed_scores'][class_name] = {
                    'present': False,
                    'completeness': 0
                }
        
        return compliance_score
    
    def _calculate_class_completeness(self, class_name: str, data: Any, class_info: Dict[str, Any]) -> float:
        """計算特定資料類別的完整性"""
        if not data:
            return 0.0
        
        if class_name == 'demographics':
            # 人口統計學資料完整性
            required_fields = ['patient_id', 'birth_date', 'gender']
            present_required = sum(1 for field in required_fields if field in data and data[field])
            return round((present_required / len(required_fields)) * 100, 1)
        
        elif class_name == 'vital_signs':
            # 生命徵象完整性
            core_vitals = ['height_cm', 'weight_kg', 'systolic_bp', 'diastolic_bp']
            present_vitals = sum(1 for vital in core_vitals if vital in data and data[vital])
            return round((present_vitals / len(core_vitals)) * 100, 1)
        
        elif class_name == 'laboratory':
            # 實驗室檢查完整性
            core_labs = ['fasting_glucose', 'total_cholesterol', 'hdl_cholesterol']
            present_labs = sum(1 for lab in core_labs if lab in data and data[lab])
            return round((present_labs / len(core_labs)) * 100, 1)
        
        else:
            # 其他類別，如果有資料就算100%
            return 100.0 if data else 0.0