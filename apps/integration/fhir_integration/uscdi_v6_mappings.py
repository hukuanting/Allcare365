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
        'allergies': {
            'name': 'Allergies and Intolerances',
            'required_elements': [
                'Medication Allergy Intolerance',
                'Drug Class Allergy Intolerance',
                'Non-Medication Allergy Intolerance',
                'Reaction'
            ]
        },
        'care_plan': {
            'name': 'Care Plan',
            'required_elements': [
                'Assessment and Plan of Treatment',
                'Care Plan'
            ]
        },
        'care_team': {
            'name': 'Care Team Members',
            'required_elements': [
                'Care Team Member Name',
                'Care Team Member Identifier',
                'Care Team Member Role',
                'Care Team Member Location',
                'Care Team Member Telecom'
            ]
        },
        'clinical_notes': {
            'name': 'Clinical Notes',
            'required_elements': [
                'Consultation Note',
                'Discharge Summary Note',
                'Emergency Department Note',
                'History & Physical',
                'Operative Note',
                'Procedure Note',
                'Progress Note'
            ]
        },
        'clinical_tests': {
            'name': 'Clinical Tests',
            'required_elements': [
                'Clinical Test',
                'Clinical Test Result/Report'
            ]
        },
        'diagnostic_imaging': {
            'name': 'Diagnostic Imaging',
            'required_elements': [
                'Diagnostic Imaging Test',
                'Diagnostic Imaging Report'
            ]
        },
        'encounter_information': {
            'name': 'Encounter Information',
            'required_elements': [
                'Encounter Type',
                'Encounter Identifier',
                'Encounter Diagnosis',
                'Encounter Time',
                'Encounter Location',
                'Encounter Disposition'
            ]
        },
        'facility_information': {
            'name': 'Facility Information',
            'required_elements': [
                'Facility Identifier',
                'Facility Type',
                'Facility Name',
                'Facility Address'
            ]
        },
        'family_health_history': {
            'name': 'Family Health History',
            'required_elements': [
                'Family Health History'
            ]
        },
        'goals_and_preferences': {
            'name': 'Goals and Preferences',
            'required_elements': [
                'Patient Goals',
                'SDOH Goals',
                'Advance Directive Observation',
                'Care Experience Preference',
                'Treatment Intervention Preference'
            ]
        },
        'health_insurance_information': {
            'name': 'Health Insurance Information',
            'required_elements': [
                'Coverage Status',
                'Coverage Type',
                'Relationship to Subscriber',
                'Member Identifier',
                'Subscriber Identifier',
                'Group Identifier',
                'Payer Identifier'
            ]
        },
        'health_status_assessments': {
            'name': 'Health Status Assessments',
            'required_elements': [
                'Health Concerns',
                'Functional Status',
                'Disability Status',
                'Mental/Cognitive Status',
                'Pregnancy Status',
                'Alcohol Use',
                'Substance Use',
                'Physical Activity',
                'SDOH Assessment',
                'Smoking Status'
            ]
        },
        'immunizations': {
            'name': 'Immunizations',
            'required_elements': [
                'Immunizations',
                'Lot Number'
            ]
        },
        'laboratory': {
            'name': 'Laboratory',
            'required_elements': [
                'Tests',
                'Values/Results',
                'Specimen Type',
                'Result Status',
                'Result Unit of Measure',
                'Result Reference Range',
                'Result Interpretation',
                'Specimen Source Site',
                'Specimen Identifier',
                'Specimen Condition Acceptability'
            ]
        },
        'medical_devices': {
            'name': 'Medical Devices',
            'required_elements': [
                'Unique Device Identifier (UDI)'
            ]
        },
        'medications': {
            'name': 'Medications',
            'required_elements': [
                'Medications',
                'Dose',
                'Dose Unit of Measure',
                'Route of Administration',
                'Indication',
                'Dispense Status',
                'Medication Instructions',
                'Medication Adherence'
            ]
        },
        'orders': {
            'name': 'Orders',
            'required_elements': [
                'Medication Order',
                'Laboratory Order',
                'Diagnostic Imaging Order',
                'Clinical Test Order',
                'Procedure Order',
                'Portable Medical Order'
            ]
        },
        'patient_demographics': {
            'name': 'Patient Demographics/Information',
            'required_elements': [
                'First Name',
                'Last Name',
                'Middle Name (Including middle initial)',
                'Name Suffix',
                'Previous Name',
                'Date of Birth',
                'Date of Death',
                'Race',
                'Ethnicity',
                'Tribal Affiliation',
                'Sex',
                'Preferred Language',
                'Interpreter Needed',
                'Current Address',
                'Previous Address',
                'Phone Number',
                'Phone Number Type',
                'Email Address',
                'Related Person\'s Name',
                'Relationship Type',
                'Occupation',
                'Occupation Industry'
            ]
        },
        'problems': {
            'name': 'Problems',
            'required_elements': [
                'Problems',
                'SDOH Problems/Health Concerns',
                'Date of Onset',
                'Date of Diagnosis',
                'Date of Resolution'
            ]
        },
        'procedures': {
            'name': 'Procedures',
            'required_elements': [
                'Procedures',
                'Performance Time',
                'SDOH Interventions',
                'Reason for Referral'
            ]
        },
        'provenance': {
            'name': 'Provenance',
            'required_elements': [
                'Author',
                'Author Role',
                'Author Time Stamp',
                'Author Organization'
            ]
        },
        'vital_signs': {
            'name': 'Vital Signs',
            'required_elements': [
                'Systolic Blood Pressure',
                'Diastolic Blood Pressure',
                'Average Blood Pressure',
                'Heart Rate',
                'Respiratory Rate',
                'Body Temperature',
                'Body Height',
                'Body Weight',
                'Pulse Oximetry',
                'Inhaled Oxygen Concentration',
                'BMI Percentile (2 - 20 years)',
                'Weight-for-length Percentile (Birth - 24 Months)',
                'Head Occipital-frontal Circumference Percentile (Birth - 36 Months)'
            ]
        }
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
                'allergies': self._extract_allergies(csv_data),
                'care_plan': self._extract_care_plan(csv_data),
                'care_team': self._extract_care_team(csv_data),
                'clinical_notes': self._extract_clinical_notes(csv_data),
                'clinical_tests': self._extract_clinical_tests(csv_data),
                'diagnostic_imaging': self._extract_diagnostic_imaging(csv_data),
                'encounter_information': self._extract_encounter_information(csv_data),
                'facility_information': self._extract_facility_information(csv_data),
                'family_health_history': self._extract_family_health_history(csv_data),
                'goals_and_preferences': self._extract_goals_and_preferences(csv_data),
                'health_insurance_information': self._extract_health_insurance_information(csv_data),
                'health_status_assessments': self._extract_health_status_assessments(csv_data),
                'immunizations': self._extract_immunizations(csv_data),
                'laboratory': self._extract_laboratory(csv_data),
                'medical_devices': self._extract_medical_devices(csv_data),
                'medications': self._extract_medications(csv_data),
                'orders': self._extract_orders(csv_data),
                'patient_demographics': self._extract_patient_demographics(csv_data),
                'problems': self._extract_problems(csv_data),
                'procedures': self._extract_procedures(csv_data),
                'provenance': self._extract_provenance(csv_data),
                'vital_signs': self._extract_vital_signs(csv_data)
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
    
    # --- Extraction Methods ---

    def _extract_patient_demographics(self, csv_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取人口統計學資料"""
        demographics = {}
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
        vital_mappings = {
            'height_cm': ['Height', 'height', 'height_cm', 'BodyHeight'],
            'weight_kg': ['Weight', 'weight', 'weight_kg', 'BodyWeight'],
            'systolic_bp': ['SBP', 'systolic_bp', 'SystolicBP', 'Systolic'],
            'diastolic_bp': ['DBP', 'diastolic_bp', 'DiastolicBP', 'Diastolic'],
            'heart_rate': ['PulseRate', 'heart_rate', 'HeartRate', 'Pulse'],
            'respiratory_rate': ['RespRate', 'respiratory_rate', 'RespiratoryRate'],
            'temperature': ['Temperature', 'temp', 'body_temperature'],
            'oxygen_saturation': ['SpO2', 'oxygen_saturation', 'OxygenSat']
        }
        for uscdi_field, csv_fields in vital_mappings.items():
            value = self._find_numeric_value_in_csv(csv_data, csv_fields)
            if value is not None:
                vital_signs[uscdi_field] = value
        
        if 'height_cm' in vital_signs and 'weight_kg' in vital_signs:
            height_m = vital_signs['height_cm'] / 100
            vital_signs['bmi'] = round(vital_signs['weight_kg'] / (height_m ** 2), 1)
        
        return vital_signs if vital_signs else None
    
    def _extract_laboratory(self, csv_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取實驗室檢查資料"""
        laboratory = {}
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
    
    def _extract_problems(self, csv_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取疾病/問題資料 (Problems)"""
        conditions = []
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
        allergy_fields = ['Allergies', 'allergies', 'AllergyList', 'KnownAllergies']
        for field in allergy_fields:
            if field in csv_data and csv_data[field]:
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

    def _extract_provenance(self, csv_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取資料來源(Provenance)"""
        provenance = {}
        author_fields = ['Author', 'Provider', 'EnteredBy', 'Source']
        time_fields = ['EntryDate', 'RecordedDate', 'Timestamp']
        
        author = self._find_value_in_csv(csv_data, author_fields)
        if author:
            provenance['author'] = author
            
        timestamp = self._find_value_in_csv(csv_data, time_fields)
        if timestamp:
            provenance['author_time_stamp'] = timestamp
        else:
            provenance['author_time_stamp'] = csv_data.get('CheckDate', datetime.now().isoformat())
            
        return provenance if provenance else None

    def _extract_health_status_assessments(self, csv_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取健康狀態評估 (Health Status Assessments)"""
        assessments = {}
        
        # Smoking Status
        status_fields = ['Smoking', 'SmokingStatus', 'TobaccoUse']
        status = self._find_value_in_csv(csv_data, status_fields)
        if status:
            assessments['smoking_status'] = status

        # Health Concerns
        concern_fields = ['HealthConcerns', 'Concerns', 'PatientConcerns']
        for field in concern_fields:
            if field in csv_data and csv_data[field]:
                assessments['health_concerns'] = str(csv_data[field])

        # Functional Status
        func_fields = ['FunctionalStatus', 'ADL', 'Function']
        func_val = self._find_value_in_csv(csv_data, func_fields)
        if func_val:
            assessments['functional_status'] = func_val
            
        # Disability Status
        disability_fields = ['Disability', 'DisabilityStatus']
        dis_val = self._find_value_in_csv(csv_data, disability_fields)
        if dis_val:
            assessments['disability_status'] = dis_val
            
        # Mental Status
        mental_fields = ['MentalStatus', 'CognitiveStatus']
        mental_val = self._find_value_in_csv(csv_data, mental_fields)
        if mental_val:
            assessments['mental_status'] = mental_val
            
        return assessments if assessments else None

    def _extract_goals_and_preferences(self, csv_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取目標與偏好 (Goals and Preferences)"""
        goals = []
        goal_fields = ['Goals', 'PatientGoals', 'TreatmentGoals']
        sdoh_goal_fields = ['SDOHGoals', 'SocialGoals']
        
        for field in goal_fields:
            if field in csv_data and csv_data[field]:
                text = str(csv_data[field])
                if text.lower() not in ['none', '無', '']:
                    items = [item.strip() for item in text.split(',')]
                    for item in items:
                        if item:
                            goals.append({'description': item, 'type': 'patient_goal', 'status': 'active'})
                            
        for field in sdoh_goal_fields:
            if field in csv_data and csv_data[field]:
                text = str(csv_data[field])
                if text.lower() not in ['none', '無', '']:
                    items = [item.strip() for item in text.split(',')]
                    for item in items:
                        if item:
                            goals.append({'description': item, 'type': 'sdoh_goal', 'status': 'active'})
                            
        return goals if goals else None

    # --- New Placeholder Methods for USCDI v6 Completeness ---

    def _extract_care_plan(self, csv_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """提取照護計畫 (Care Plan)"""
        # Placeholder implementation
        return None

    def _extract_care_team(self, csv_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """提取照護團隊 (Care Team Members)"""
        # Placeholder implementation
        return None

    def _extract_clinical_notes(self, csv_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """提取臨床筆記 (Clinical Notes)"""
        # Placeholder implementation
        return None

    def _extract_clinical_tests(self, csv_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """提取臨床測試 (Clinical Tests)"""
        # Placeholder implementation
        return None

    def _extract_diagnostic_imaging(self, csv_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """提取診斷影像 (Diagnostic Imaging)"""
        # Placeholder implementation
        return None

    def _extract_encounter_information(self, csv_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """提取就醫資訊 (Encounter Information)"""
        # Placeholder implementation
        return None

    def _extract_facility_information(self, csv_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """提取機構資訊 (Facility Information)"""
        # Placeholder implementation
        return None

    def _extract_family_health_history(self, csv_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """提取家族病史 (Family Health History)"""
        # Placeholder implementation
        return None

    def _extract_health_insurance_information(self, csv_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """提取保險資訊 (Health Insurance Information)"""
        # Placeholder implementation
        return None

    def _extract_medical_devices(self, csv_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """提取醫療器材 (Medical Devices)"""
        # Placeholder implementation
        return None

    def _extract_orders(self, csv_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """提取醫囑 (Orders)"""
        # Placeholder implementation
        return None

    # --- Helper Methods ---

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
            required_fields = ['patient_id', 'birth_date', 'gender']
            present_required = sum(1 for field in required_fields if field in data and data[field])
            return round((present_required / len(required_fields)) * 100, 1)
        
        elif class_name == 'vital_signs':
            core_vitals = ['height_cm', 'weight_kg', 'systolic_bp', 'diastolic_bp']
            present_vitals = sum(1 for vital in core_vitals if vital in data and data[vital])
            return round((present_vitals / len(core_vitals)) * 100, 1)
        
        elif class_name == 'laboratory':
            core_labs = ['fasting_glucose', 'total_cholesterol', 'hdl_cholesterol']
            present_labs = sum(1 for lab in core_labs if lab in data and data[lab])
            return round((present_labs / len(core_labs)) * 100, 1)
        
        else:
            return 100.0 if data else 0.0