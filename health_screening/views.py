from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta
import pandas as pd
import json
import io
import openpyxl
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FileUploadParser
from django_filters.rest_framework import DjangoFilterBackend
from .models import (
    HealthScreening, VitalSigns, LaboratoryResults, 
    CardiovascularRiskIndex, MedicalHistory, LifestyleQuestionnaire
)
from .serializers import (
    HealthScreeningSerializer, HealthScreeningListSerializer,
    BulkHealthScreeningSerializer
)
from .advanced_risk_calculators import AdvancedRiskCalculator, RiskFactors
from patients.models import Patient
from django.contrib.auth.models import User


class HealthScreeningViewSet(viewsets.ModelViewSet):
    """健康檢查數據管理 API"""
    queryset = HealthScreening.objects.all()
    permission_classes = [AllowAny]  # 暫時允許所有用戶訪問，用於測試
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['patient', 'provider', 'screening_type', 'screening_date']
    search_fields = ['patient__first_name', 'patient__last_name']
    ordering_fields = ['screening_date', 'created_at']
    ordering = ['-screening_date']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return HealthScreeningListSerializer
        elif self.action == 'bulk_import':
            return BulkHealthScreeningSerializer
        elif self.action == 'fhir_import':
            return HealthScreeningSerializer  # FHIR 匯入使用標準序列化器
        return HealthScreeningSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        patient_id = self.request.query_params.get('patient_id')
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        return queryset.select_related('patient', 'provider').prefetch_related(
            'vital_signs', 'laboratory_results', 'cardiovascular_risk',
            'medical_history', 'lifestyle'
        )
    
    @action(detail=False, methods=['post'])
    def fhir_import(self, request):
        """FHIR R4 格式數據匯入 - 增強版"""
        try:
            from .enhanced_bulk_import_service import EnhancedBulkImportService
            
            fhir_data = request.data.get('fhir_data')
            data_format = request.data.get('format', 'json')
            
            if not fhir_data:
                return Response({
                    'success': False,
                    'error': '沒有提供 FHIR 數據'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 使用增強的批量匯入服務
            bulk_service = EnhancedBulkImportService()
            result = bulk_service.process_fhir_import(fhir_data, data_format)
            
            return Response(result)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': f'FHIR 處理失敗: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser])
    def bulk_import(self, request):
        """批量匯入健檢數據 - 增強版支援多種格式"""
        try:
            from .enhanced_bulk_import_service import EnhancedBulkImportService
            
            # 檢查是否有上傳檔案
            if 'file' in request.FILES:
                file = request.FILES['file']
                
                # 回退到原始的批量匯入服務以保持兼容性
                from .bulk_import_service import BulkImportService
                bulk_service = BulkImportService()
                result = bulk_service.process_file_import(file)
                return Response(result)
            
            elif 'text_data' in request.data:
                # 處理文字格式數據（JSON, XML, CSV）
                text_data = request.data['text_data']
                data_format = request.data.get('format', 'json')
                
                # 回退到原始的批量匯入服務以保持兼容性
                from .bulk_import_service import BulkImportService
                bulk_service = BulkImportService()
                result = bulk_service.process_text_import(text_data, data_format)
                return Response(result)
            
            elif 'data' in request.data:
                # 向後兼容：來自前端預覽的JSON數據
                data = json.loads(request.data['data'])
                df = pd.DataFrame(data)
                result = self._process_bulk_data(df)
                return Response(result)
            
            else:
                return Response({
                    'success': False,
                    'error': '沒有提供檔案或數據'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': f'處理失敗: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _process_bulk_data(self, df):
        """處理批量數據"""
        success_count = 0
        error_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # 使用獨立事務處理每一行數據
                from django.db import transaction
                with transaction.atomic():
                    # 處理H2U CSV格式的數據映射
                    patient_id = row.get('ID') or row.get('patient_id')
                    if pd.isna(patient_id):
                        errors.append(f'第 {index + 1} 行: 缺少患者編號')
                        error_count += 1
                        continue
                    
                    # 準備患者資料
                    birth_date = row.get('BirthDate')
                    gender = row.get('SEX', 'U')
                    if gender == 'F':
                        gender = 'F'
                    elif gender == 'M':
                        gender = 'M'
                    else:
                        gender = 'U'
                    
                    # 解析出生日期
                    if birth_date and not pd.isna(birth_date):
                        try:
                            if isinstance(birth_date, str):
                                birth_date = pd.to_datetime(birth_date, format='%Y/%m/%d').date()
                            else:
                                birth_date = pd.to_datetime(birth_date).date()
                        except:
                            birth_date = None
                    else:
                        birth_date = None
                    
                    # 使用 get_or_create 避免重複創建和事務衝突
                    patient, created = Patient.objects.get_or_create(
                        medical_record_number=str(patient_id),
                        defaults={
                            'first_name': f'Patient_{patient_id}',
                            'last_name': '',
                            'date_of_birth': birth_date,
                            'gender': gender,
                            'is_active': True
                        }
                    )
                    
                    # 準備健檢數據
                    check_date = row.get('CheckDate')
                    if check_date and not pd.isna(check_date):
                        try:
                            if isinstance(check_date, str):
                                screening_date = pd.to_datetime(check_date, format='%Y/%m/%d').date()
                            else:
                                screening_date = pd.to_datetime(check_date).date()
                        except:
                            screening_date = timezone.now().date()
                    else:
                        screening_date = timezone.now().date()
                    
                    screening_data = {
                        'patient': patient,
                        'screening_date': screening_date,
                        'screening_type': 'annual_physical',
                        # 移除notes欄位，因為HealthScreening模型中沒有此欄位
                    }
                    
                    # 查找執行醫師
                    provider_id = row.get('provider')
                    if provider_id and not pd.isna(provider_id):
                        try:
                            screening_data['provider'] = User.objects.get(id=int(provider_id))
                        except (User.DoesNotExist, ValueError):
                            pass
                    
                    # 創建健檢記錄
                    screening = HealthScreening.objects.create(**screening_data)
                    
                    # 處理生命體徵 - H2U CSV格式映射
                    vital_data = {}
                    
                    # 映射H2U CSV欄位到我們的模型欄位
                    h2u_vital_mapping = {
                        'Height': 'height_cm',
                        'Weight': 'weight_kg',
                        'Waist': 'waist_circumference_cm',
                        'PulseRate': 'pulse_rate_bpm',
                        'SBP': 'systolic_bp_mmhg',
                        'DBP': 'diastolic_bp_mmhg',
                        'Neck': 'neck_circumference_cm',
                        'Hip': 'hip_circumference_cm'
                    }
                    
                    for h2u_field, model_field in h2u_vital_mapping.items():
                        value = row.get(h2u_field)
                        if value and not pd.isna(value):
                            try:
                                float_value = float(value)
                                # 檢查數值範圍，避免溢出
                                if model_field in ['neck_circumference_cm', 'pulse_rate_bpm']:
                                    # 這些欄位精度是 4,1，最大值是 999.9
                                    if float_value > 999.9:
                                        continue
                                elif model_field in ['height_cm', 'weight_kg', 'waist_circumference_cm', 'hip_circumference_cm', 'chest_circumference_cm']:
                                    # 這些欄位精度是 5,1，最大值是 9999.9
                                    if float_value > 9999.9:
                                        continue
                                vital_data[model_field] = float_value
                            except (ValueError, TypeError):
                                pass
                    
                    if vital_data:
                        try:
                            VitalSigns.objects.create(health_screening=screening, **vital_data)
                        except Exception as vital_error:
                            errors.append(f'第 {index + 1} 行: 生命體徵創建失敗 - {str(vital_error)}')
                    
                    # 處理檢驗結果 - H2U CSV格式映射
                    lab_data = {}
                    
                    # 映射H2U CSV欄位到我們的模型欄位 - 注意Creatinine欄位名稱
                    h2u_lab_mapping = {
                        'FPG': 'fasting_glucose_mgdl',
                        'HbA1C': 'hba1c_percent',
                        'WBC': 'wbc_count',
                        'TG': 'triglycerides_mgdl',
                        'TC': 'total_cholesterol_mgdl',
                        'HDL': 'hdl_cholesterol_mgdl',
                        'LDL': 'ldl_cholesterol_mgdl',
                        'Creatinine': 'serum_creatinine_mgdl'  # 修正為正確的欄位名稱
                    }
                    
                    for h2u_field, model_field in h2u_lab_mapping.items():
                        value = row.get(h2u_field)
                        if value and not pd.isna(value):
                            try:
                                float_value = float(value)
                                # 檢查數值範圍，避免溢出
                                if model_field in ['hba1c_percent', 'serum_creatinine_mgdl']:
                                    # 這些欄位精度是 4,1 或 4,2，需要限制範圍
                                    if model_field == 'serum_creatinine_mgdl' and float_value > 99.99:
                                        continue
                                    elif model_field == 'hba1c_percent' and float_value > 999.9:
                                        continue
                                elif model_field in ['fasting_glucose_mgdl', 'triglycerides_mgdl', 'total_cholesterol_mgdl', 'hdl_cholesterol_mgdl', 'ldl_cholesterol_mgdl']:
                                    # 這些欄位精度是 5,1，最大值是 9999.9
                                    if float_value > 9999.9:
                                        continue
                                lab_data[model_field] = float_value
                            except (ValueError, TypeError):
                                pass
                    
                    if lab_data:
                        try:
                            LaboratoryResults.objects.create(health_screening=screening, **lab_data)
                        except Exception as lab_error:
                            errors.append(f'第 {index + 1} 行: 檢驗結果創建失敗 - {str(lab_error)}')
                    
                    # 處理病史 - H2U CSV格式映射
                    history_data = {}
                    
                    # 映射H2U CSV布林欄位到我們的模型欄位
                    h2u_history_mapping = {
                        'HQ_BP_Treat': 'hypertension_treated',
                        'HQ_Diabetes_Treat': 'diabetes_treated',
                        'HQ_low_fat_Treat': 'hyperlipidemia_treated'
                    }
                    
                    for h2u_field, model_field in h2u_history_mapping.items():
                        value = row.get(h2u_field)
                        if value and not pd.isna(value):
                            # 處理布林值 - H2U使用TRUE/FALSE字符串
                            if isinstance(value, str):
                                history_data[model_field] = value.upper() == 'TRUE'
                            else:
                                history_data[model_field] = bool(value)
                    
                    if history_data:
                        try:
                            MedicalHistory.objects.create(health_screening=screening, **history_data)
                        except Exception as history_error:
                            errors.append(f'第 {index + 1} 行: 病史創建失敗 - {str(history_error)}')
                    
                    # 處理生活習慣問卷 - H2U CSV格式映射
                    lifestyle_data = {}
                    
                    # 映射H2U CSV布林欄位到我們的模型欄位 - 移除不存在的欄位
                    h2u_lifestyle_mapping = {
                        'HQ_SMOKE': 'is_current_smoker',
                        'HQ_Diabetes': 'has_diabetes',
                        'HQ_CHD': 'has_coronary_heart_disease',
                        # 'HQ_arrhythmia': 'has_arrhythmia',  # 這個欄位在模型中不存在
                        'HQ_Exercise': 'exercise_score'
                    }
                    
                    for h2u_field, model_field in h2u_lifestyle_mapping.items():
                        value = row.get(h2u_field)
                        if value and not pd.isna(value):
                            # 處理布林值 - H2U使用TRUE/FALSE字符串
                            if h2u_field in ['HQ_SMOKE', 'HQ_Diabetes', 'HQ_CHD']:
                                if isinstance(value, str):
                                    lifestyle_data[model_field] = value.upper() == 'TRUE'
                                else:
                                    lifestyle_data[model_field] = bool(value)
                            elif h2u_field == 'HQ_Exercise':
                                # 運動習慣轉換為評分
                                if isinstance(value, str):
                                    lifestyle_data[model_field] = 'regularly' if value.upper() == 'TRUE' else 'rarely'
                                else:
                                    lifestyle_data[model_field] = 'regularly' if bool(value) else 'rarely'
                    
                    if lifestyle_data:
                        try:
                            LifestyleQuestionnaire.objects.create(health_screening=screening, **lifestyle_data)
                        except Exception as lifestyle_error:
                            errors.append(f'第 {index + 1} 行: 生活習慣問卷創建失敗 - {str(lifestyle_error)}')
                    
                    success_count += 1
                
            except Exception as e:
                errors.append(f'第 {index + 1} 行: {str(e)}')
                error_count += 1
        
        return {
            'success': True,
            'success_count': success_count,
            'error_count': error_count,
            'total_count': success_count + error_count,
            'errors': errors
        }
    
    @action(detail=False, methods=['post'])
    def validate_uscdi_compliance(self, request):
        """驗證 USCDI v6 合規性"""
        try:
            from .bulk_import_service import BulkImportService
            from fhir_integration.uscdi_v6_mappings import USCDIv6Mapper
            
            data = request.data.get('data')
            if not data:
                return Response({
                    'success': False,
                    'error': '沒有提供數據'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 使用 USCDI v6 映射器檢查合規性
            mapper = USCDIv6Mapper()
            
            if isinstance(data, list):
                # 批量檢查
                results = []
                for index, record in enumerate(data):
                    result = mapper.map_csv_to_uscdi(record)
                    results.append({
                        'record_index': index + 1,
                        'success': result['success'],
                        'compliance_score': result.get('compliance_score'),
                        'uscdi_data': result.get('data'),
                        'error': result.get('error')
                    })
                
                return Response({
                    'success': True,
                    'total_records': len(data),
                    'results': results
                })
            else:
                # 單筆檢查
                result = mapper.map_csv_to_uscdi(data)
                return Response(result)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': f'USCDI 合規性檢查失敗: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def calculate_comprehensive_risk(self, request, pk=None):
        """計算綜合疾病風險"""
        try:
            screening = self.get_object()
            
            # 獲取相關數據
            vital_signs = getattr(screening, 'vital_signs', None)
            lab_results = getattr(screening, 'laboratory_results', None)
            medical_history = getattr(screening, 'medical_history', None)
            lifestyle = getattr(screening, 'lifestyle', None)
            
            # 簡化的風險計算 - 暫時不依賴複雜的風險計算器
            result = self._calculate_simple_risk(screening, vital_signs, lab_results, medical_history, lifestyle)
            
            return Response(result)
            
        except Exception as e:
            return Response({
                'error': f'風險計算失敗: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _calculate_simple_risk(self, screening, vital_signs, lab_results, medical_history, lifestyle):
        """使用 AHA PREVENT 演算法計算心血管疾病風險，並加入 Framingham Heart Study 糖尿病風險和中國健檢糖尿病風險(CH_DM)"""
        from .risk_calculators import women_cvd_10, man_cvd_10, women_ascvd_10, man_ascvd_10, women_hf_10, man_hf_10, calculate_egfr, calculate_fhs_dm_score, calculate_ch_dm_score
        
        patient = screening.patient
        
        # 檢查必要數據完整性 - 避免使用假數據進行風險計算
        missing_data = []
        
        # 檢查基本資料
        if not hasattr(patient, 'age') or patient.age is None:
            missing_data.append('患者年齡')
        if not hasattr(patient, 'gender') or patient.gender is None:
            missing_data.append('患者性別')
            
        # 檢查生命徵象
        if not vital_signs:
            missing_data.append('生命徵象數據')
        else:
            if vital_signs.height_cm is None:
                missing_data.append('身高')
            if vital_signs.weight_kg is None:
                missing_data.append('體重')
            if vital_signs.systolic_bp_mmhg is None:
                missing_data.append('收縮壓')
                
        # 檢查實驗室數據
        if not lab_results:
            missing_data.append('實驗室檢查數據')
        else:
            if lab_results.total_cholesterol_mgdl is None:
                missing_data.append('總膽固醇')
            if lab_results.hdl_cholesterol_mgdl is None:
                missing_data.append('HDL膽固醇')
            if lab_results.fasting_glucose_mgdl is None:
                missing_data.append('空腹血糖')
        
        # 如果有關鍵數據缺失，返回錯誤而不是使用假數據
        if missing_data:
            return {
                'error': '數據不完整，無法進行風險分析',
                'missing_data': missing_data,
                'message': f'缺少以下必要數據：{", ".join(missing_data)}',
                'suggestion': '請確保已正確匯入完整的健檢數據後再進行風險分析',
                'data_integrity_check': False
            }
        
        # 使用真實數據進行計算
        age = float(patient.age)
        gender = patient.gender
        height = float(vital_signs.height_cm)
        weight = float(vital_signs.weight_kg)
        sbp = float(vital_signs.systolic_bp_mmhg)
        
        # 計算BMI
        bmi = weight / ((height / 100) ** 2)
        
        # 實驗室數據
        total_chol = float(lab_results.total_cholesterol_mgdl)
        hdl_chol = float(lab_results.hdl_cholesterol_mgdl)
        creatinine = float(lab_results.serum_creatinine_mgdl if lab_results.serum_creatinine_mgdl is not None else 1.0)
        
        # 計算 eGFR
        egfr = calculate_egfr(creatinine, age, gender)
        
        # 疾病史和用藥史 - has_diabetes 在 lifestyle 中，不在 medical_history 中，安全處理 None 值
        has_diabetes = int(lifestyle.has_diabetes if lifestyle and hasattr(lifestyle, 'has_diabetes') and lifestyle.has_diabetes is not None else False)
        is_smoker = int(lifestyle.is_current_smoker if lifestyle and hasattr(lifestyle, 'is_current_smoker') and lifestyle.is_current_smoker is not None else False)
        anti_hyp_med = int(medical_history.hypertension_treated if medical_history and hasattr(medical_history, 'hypertension_treated') and medical_history.hypertension_treated is not None else False)
        statin = int(medical_history.hyperlipidemia_treated if medical_history and hasattr(medical_history, 'hyperlipidemia_treated') and medical_history.hyperlipidemia_treated is not None else False)
        
        # 使用 AHA PREVENT 演算法計算風險
        if gender.upper() == 'F':  # 女性
            cvd_risk = women_cvd_10(age, total_chol, hdl_chol, sbp, egfr, has_diabetes, is_smoker, anti_hyp_med, statin)
            ascvd_risk = women_ascvd_10(age, total_chol, hdl_chol, sbp, egfr, has_diabetes, is_smoker, anti_hyp_med, statin)
            hf_risk = women_hf_10(age, sbp, bmi, egfr, has_diabetes, is_smoker, anti_hyp_med)
        else:  # 男性
            cvd_risk = man_cvd_10(age, total_chol, hdl_chol, sbp, egfr, has_diabetes, is_smoker, anti_hyp_med, statin)
            ascvd_risk = man_ascvd_10(age, total_chol, hdl_chol, sbp, egfr, has_diabetes, is_smoker, anti_hyp_med, statin)
            hf_risk = man_hf_10(age, sbp, bmi, egfr, has_diabetes, is_smoker, anti_hyp_med)
        
        # 計算 Framingham Heart Study 糖尿病風險
        # 獲取額外的數據，安全處理 None 值 - 使用H2U CSV中的實際數據
        fasting_glucose = float(lab_results.fasting_glucose_mgdl if lab_results and lab_results.fasting_glucose_mgdl is not None else 100.0)
        triglycerides = float(lab_results.triglycerides_mgdl if lab_results and lab_results.triglycerides_mgdl is not None else 150.0)
        dbp = float(vital_signs.diastolic_bp_mmhg if vital_signs and vital_signs.diastolic_bp_mmhg is not None else 80)
        
        # 家族糖尿病史 - 從生活習慣問卷或病史中獲取，安全處理 None 值
        # 如果沒有明確的家族史數據，預設為False以確保FHS DM計算能執行
        parental_diabetes_history = bool(lifestyle.family_diabetes if lifestyle and hasattr(lifestyle, 'family_diabetes') and lifestyle.family_diabetes is not None else False)
        
        # 計算 FHS 糖尿病風險 - 檢查必要數據是否完整
        # FHS DM 需要的關鍵數據：家族糖尿病史、完整的血壓和血脂數據
        fhs_dm_required_data = {
            'parental_diabetes_history': parental_diabetes_history,
            'triglycerides': triglycerides,
            'fasting_glucose': fasting_glucose,
            'hdl_cholesterol': hdl_chol,
            'bmi': bmi
        }
        
        # 檢查是否有明確的家族史數據（H2U CSV中通常沒有）
        has_family_history_data = (
            lifestyle and 
            hasattr(lifestyle, 'family_diabetes') and 
            lifestyle.family_diabetes is not None
        )
        
        # 如果缺少關鍵數據（特別是家族史），顯示數據缺失
        if not has_family_history_data:
            fhs_dm_score = None
            fhs_dm_risk_percent = "數據缺失"
            print("FHS DM: 缺少家族糖尿病史數據，無法計算風險")
        else:
            try:
                fhs_dm_score, fhs_dm_risk_percent = calculate_fhs_dm_score(
                    sex=gender.upper(),
                    fasting_glucose=fasting_glucose,
                    bmi=bmi,
                    hdl_c_level=hdl_chol,
                    parental_history=parental_diabetes_history,
                    triglyceride_level=triglycerides,
                    blood_pressure=(sbp, dbp),
                    on_bp_treatment=bool(anti_hyp_med)
                )
            except Exception as e:
                print(f"FHS DM計算錯誤: {e}")
                fhs_dm_score = None
                fhs_dm_risk_percent = "數據缺失"
        
        # 轉換為百分比
        cvd_percentage = round(cvd_risk * 100, 1)
        ascvd_percentage = round(ascvd_risk * 100, 1)
        hf_percentage = round(hf_risk * 100, 1)
        
        # 風險分級
        def get_risk_category(percentage):
            if percentage < 5:
                return '低風險'
            elif percentage < 7.5:
                return '中低風險'
            elif percentage < 20:
                return '中等風險'
            else:
                return '高風險'
        
        # 生成建議
        def get_recommendations(category, risk_type):
            base_recommendations = [
                '定期監測血壓、血糖、血脂',
                '維持健康體重',
                '規律運動',
                '健康飲食',
                '戒菸限酒'
            ]
            
            if category == '高風險':
                return base_recommendations + [
                    f'建議立即就醫評估{risk_type}風險',
                    '考慮藥物治療',
                    '每3個月追蹤檢查'
                ]
            elif category == '中等風險':
                return base_recommendations + [
                    f'建議6個月內就醫評估{risk_type}風險',
                    '加強生活方式調整',
                    '每6個月追蹤檢查'
                ]
            else:
                return base_recommendations + [
                    '維持健康生活方式',
                    '年度健康檢查'
                ]
        
        # 計算 CH_DM (中國健檢糖尿病風險) - 使用更多的本地化數據
        # 獲取靜息心率數據，如果沒有則使用脈搏
        resting_heart_rate = float(vital_signs.pulse_rate_bpm if vital_signs and vital_signs.pulse_rate_bpm is not None else 70.0)
        
        # 檢查是否有足夠的數據進行 CH_DM 計算
        ch_dm_required_data_available = all([
            age is not None,
            gender is not None,
            bmi is not None,
            sbp is not None,
            fasting_glucose is not None,
            triglycerides is not None,
            resting_heart_rate is not None
        ])
        
        if ch_dm_required_data_available:
            try:
                ch_dm_score, ch_dm_risk_percent = calculate_ch_dm_score(
                    age=int(age),
                    sex=gender.upper(),
                    bmi=bmi,
                    family_history_diabetes=parental_diabetes_history,
                    sbp=sbp,
                    anti_hypertensive_drugs=bool(anti_hyp_med),
                    resting_heart_rate=resting_heart_rate,
                    fpg=fasting_glucose,
                    tg=triglycerides,
                    using_lipid_lowering_drugs=bool(statin),
                    auc=0.0  # 預設AUC為0，可以之後擴展
                )
            except Exception as e:
                print(f"CH_DM計算錯誤: {e}")
                ch_dm_score = None
                ch_dm_risk_percent = "數據缺失"
        else:
            ch_dm_score = None
            ch_dm_risk_percent = "數據缺失"
            print("CH_DM: 缺少必要數據，無法計算風險")

        # 為 FHS 糖尿病風險生成風險分級和建議
        def get_diabetes_risk_category(risk_percent_str):
            # 處理數據缺失情況
            if risk_percent_str == "數據缺失":
                return '數據缺失'
            # 提取數字部分
            elif risk_percent_str.startswith('<'):
                return '低風險'
            elif risk_percent_str.startswith('>'):
                return '極高風險'
            else:
                try:
                    risk_num = float(risk_percent_str.replace('%', ''))
                    if risk_num < 5:
                        return '低風險'
                    elif risk_num < 10:
                        return '中低風險'
                    elif risk_num < 20:
                        return '中等風險'
                    else:
                        return '高風險'
                except:
                    return '數據缺失'
        
        # 為 CH_DM 風險生成風險分級和建議
        def get_ch_dm_risk_category(risk_percent_str):
            if risk_percent_str == "數據缺失":
                return '數據缺失'
            elif risk_percent_str in ["<3%", "5%"]:
                return '低風險'
            elif risk_percent_str == "8%":
                return '中低風險'
            elif risk_percent_str in ["8~12%", "12~18%"]:
                return '中等風險'
            elif risk_percent_str in ["18~25%", ">25%"]:
                return '高風險'
            else:
                return '未知風險'
        
        def get_diabetes_recommendations(category):
            base_recommendations = [
                '維持健康體重',
                '規律運動',
                '健康飲食，控制糖分攝取',
                '定期監測血糖',
                '戒菸限酒'
            ]
            
            if category == '數據缺失':
                return [
                    '需要補充家族糖尿病史資料',
                    '建議進行完整的糖尿病風險評估',
                    '諮詢醫師進行個人化風險評估',
                    '維持健康生活方式'
                ]
            elif category == '極高風險':
                return base_recommendations + [
                    '建議立即就醫評估糖尿病風險',
                    '考慮進行口服葡萄糖耐量試驗',
                    '每3個月追蹤檢查'
                ]
            elif category == '高風險':
                return base_recommendations + [
                    '建議6個月內就醫評估',
                    '加強生活方式調整',
                    '每6個月追蹤血糖'
                ]
            elif category in ['中等風險', '中低風險']:
                return base_recommendations + [
                    '年度健康檢查',
                    '注意飲食控制',
                    '保持規律運動'
                ]
            else:
                return base_recommendations + [
                    '維持健康生活方式',
                    '年度健康檢查'
                ]
        
        def get_ch_dm_recommendations(category):
            base_recommendations = [
                '維持健康體重',
                '規律運動',
                '健康飲食，控制糖分攝取',
                '定期監測血糖',
                '戒菸限酒'
            ]
            
            if category == '數據缺失':
                return [
                    '需要補充必要的健康檢查數據',
                    '建議進行完整的糖尿病風險評估',
                    '諮詢醫師進行個人化風險評估',
                    '維持健康生活方式'
                ]
            elif category == '高風險':
                return base_recommendations + [
                    '建議立即諮詢內分泌科醫師進行詳細評估',
                    '建議每3個月檢查血糖、糖化血色素',
                    '可能需要考慮預防性藥物治療',
                    '建議進行口服葡萄糖耐量試驗'
                ]
            elif category == '中等風險':
                return base_recommendations + [
                    '建議積極進行生活方式干預',
                    '建議每6個月檢查血糖和相關代謝指標',
                    '建議制定結構化的運動和飲食計畫'
                ]
            elif category == '中低風險':
                return base_recommendations + [
                    '建議注意生活方式調整',
                    '建議每年檢查血糖',
                    '建議維持健康飲食習慣'
                ]
            else:  # 低風險或其他
                return base_recommendations + [
                    '維持健康生活方式',
                    '年度健康檢查'
                ]

        return {
            'aha_prevent': {
                'cvd_10_year': {
                    'risk_type': 'AHA PREVENT - 心血管疾病 (10年)',
                    'risk_percentage': cvd_percentage,
                    'risk_category': get_risk_category(cvd_percentage),
                    'recommendations': get_recommendations(get_risk_category(cvd_percentage), '心血管疾病'),
                    'confidence_level': 0.92,
                    'time_horizon': '10年',
                    'algorithm': 'AHA PREVENT CVD'
                },
                'ascvd_10_year': {
                    'risk_type': 'AHA PREVENT - 動脈硬化性心血管疾病 (10年)',
                    'risk_percentage': ascvd_percentage,
                    'risk_category': get_risk_category(ascvd_percentage),
                    'recommendations': get_recommendations(get_risk_category(ascvd_percentage), '動脈硬化性心血管疾病'),
                    'confidence_level': 0.90,
                    'time_horizon': '10年',
                    'algorithm': 'AHA PREVENT ASCVD'
                },
                'heart_failure_10_year': {
                    'risk_type': 'AHA PREVENT - 心臟衰竭 (10年)',
                    'risk_percentage': hf_percentage,
                    'risk_category': get_risk_category(hf_percentage),
                    'recommendations': get_recommendations(get_risk_category(hf_percentage), '心臟衰竭'),
                    'confidence_level': 0.88,
                    'time_horizon': '10年',
                    'algorithm': 'AHA PREVENT HF'
                }
            },
            'framingham_diabetes': {
                'diabetes_risk': {
                    'risk_type': 'Framingham Heart Study - 糖尿病風險',
                    'risk_score': fhs_dm_score,
                    'risk_percentage': fhs_dm_risk_percent,
                    'risk_category': get_diabetes_risk_category(fhs_dm_risk_percent),
                    'recommendations': get_diabetes_recommendations(get_diabetes_risk_category(fhs_dm_risk_percent)),
                    'confidence_level': 0.85,
                    'time_horizon': '8年',
                    'algorithm': 'Framingham Heart Study DM'
                }
            },
            'chinese_health_diabetes': {
                'diabetes_risk': {
                    'risk_type': 'Changes in Ideal Cardiovascular Health - 糖尿病風險 (中國健檢)',
                    'risk_score': ch_dm_score,
                    'risk_percentage': ch_dm_risk_percent,
                    'risk_category': get_ch_dm_risk_category(ch_dm_risk_percent),
                    'recommendations': get_ch_dm_recommendations(get_ch_dm_risk_category(ch_dm_risk_percent)),
                    'confidence_level': 0.88,
                    'time_horizon': '糖尿病新發病風險',
                    'algorithm': 'CH_DM (Changes in Ideal CVH)'
                }
            },
            'patient_info': {
                'age': age,
                'gender': '女性' if gender.upper() == 'F' else '男性',
                'bmi': round(bmi, 1),
                'egfr': round(egfr, 1),
                'total_cholesterol': total_chol,
                'hdl_cholesterol': hdl_chol,
                'systolic_bp': sbp,
                'diastolic_bp': dbp,
                'fasting_glucose': fasting_glucose,
                'triglycerides': triglycerides,
                'has_diabetes': bool(has_diabetes),
                'is_smoker': bool(is_smoker),
                'on_hypertension_med': bool(anti_hyp_med),
                'on_statin': bool(statin),
                'parental_diabetes_history': parental_diabetes_history
            }
        }
    
    def _assess_cardiovascular_risk(self, age, gender, sbp, total_chol, hdl_chol, diabetes, smoking):
        """評估心血管疾病風險"""
        risk_score = 0
        
        # 年齡風險
        if age >= 65:
            risk_score += 3
        elif age >= 55:
            risk_score += 2
        elif age >= 45:
            risk_score += 1
        
        # 血壓風險
        if sbp >= 160:
            risk_score += 3
        elif sbp >= 140:
            risk_score += 2
        elif sbp >= 130:
            risk_score += 1
        
        # 膽固醇風險
        if total_chol >= 240:
            risk_score += 2
        elif total_chol >= 200:
            risk_score += 1
        
        if hdl_chol < 40:
            risk_score += 2
        elif hdl_chol < 50:
            risk_score += 1
        
        # 疾病史
        if diabetes:
            risk_score += 3
        if smoking:
            risk_score += 2
        
        # 性別調整
        if gender == 'M':
            risk_score += 1
        
        # 計算風險百分比和分類
        risk_percentage = min(risk_score * 2.5, 30.0)  # 最高30%
        
        if risk_percentage < 5:
            category = '低風險'
        elif risk_percentage < 10:
            category = '中等風險'
        elif risk_percentage < 20:
            category = '高風險'
        else:
            category = '極高風險'
        
        recommendations = self._get_cardiovascular_recommendations(category)
        
        return {
            'risk_type': '心血管疾病',
            'risk_score': risk_score,
            'risk_percentage': risk_percentage,
            'risk_category': category,
            'recommendations': recommendations,
            'confidence_level': 0.85,
            'time_horizon': '10年'
        }
    
    def _assess_diabetes_risk(self, age, bmi, glucose, has_diabetes):
        """評估糖尿病風險"""
        if has_diabetes:
            return {
                'risk_type': '糖尿病',
                'risk_score': 10,
                'risk_percentage': 100.0,
                'risk_category': '已確診',
                'recommendations': ['定期監測血糖', '遵循醫師用藥指示', '控制飲食', '規律運動'],
                'confidence_level': 1.0,
                'time_horizon': '當前'
            }
        
        risk_score = 0
        
        # 年齡風險
        if age >= 65:
            risk_score += 3
        elif age >= 45:
            risk_score += 2
        elif age >= 35:
            risk_score += 1
        
        # BMI風險
        if bmi >= 30:
            risk_score += 3
        elif bmi >= 25:
            risk_score += 2
        elif bmi >= 23:
            risk_score += 1
        
        # 血糖風險
        if glucose >= 126:
            risk_score += 4
        elif glucose >= 110:
            risk_score += 3
        elif glucose >= 100:
            risk_score += 1
        
        risk_percentage = min(risk_score * 3.0, 25.0)
        
        if risk_percentage < 5:
            category = '低風險'
        elif risk_percentage < 10:
            category = '中等風險'
        elif risk_percentage < 15:
            category = '高風險'
        else:
            category = '極高風險'
        
        recommendations = self._get_diabetes_recommendations(category)
        
        return {
            'risk_type': '糖尿病',
            'risk_score': risk_score,
            'risk_percentage': risk_percentage,
            'risk_category': category,
            'recommendations': recommendations,
            'confidence_level': 0.80,
            'time_horizon': '5年'
        }
    
    def _assess_metabolic_risk(self, bmi, sbp, glucose, total_chol, hdl_chol):
        """評估代謝症候群風險"""
        risk_factors = 0
        
        # 肥胖
        if bmi >= 25:
            risk_factors += 1
        
        # 高血壓
        if sbp >= 130:
            risk_factors += 1
        
        # 高血糖
        if glucose >= 100:
            risk_factors += 1
        
        # 血脂異常
        if total_chol >= 200 or hdl_chol < 50:
            risk_factors += 1
        
        risk_percentage = risk_factors * 20.0
        
        if risk_factors <= 1:
            category = '低風險'
        elif risk_factors == 2:
            category = '中等風險'
        elif risk_factors == 3:
            category = '高風險'
        else:
            category = '極高風險'
        
        recommendations = self._get_metabolic_recommendations(category)
        
        return {
            'risk_type': '代謝症候群',
            'risk_score': risk_factors,
            'risk_percentage': risk_percentage,
            'risk_category': category,
            'recommendations': recommendations,
            'confidence_level': 0.75,
            'time_horizon': '當前'
        }
    
    def _get_cardiovascular_recommendations(self, category):
        """獲取心血管疾病建議"""
        base_recommendations = ['定期監測血壓', '控制膽固醇', '戒菸限酒', '規律運動']
        
        if category == '極高風險':
            return base_recommendations + ['立即就醫評估', '考慮藥物治療', '每月追蹤']
        elif category == '高風險':
            return base_recommendations + ['3個月內就醫', '考慮預防性用藥']
        elif category == '中等風險':
            return base_recommendations + ['6個月內健檢', '生活方式調整']
        else:
            return base_recommendations + ['年度健檢', '維持健康生活']
    
    def _get_diabetes_recommendations(self, category):
        """獲取糖尿病建議"""
        base_recommendations = ['控制體重', '健康飲食', '規律運動', '定期檢查']
        
        if category == '極高風險':
            return base_recommendations + ['立即就醫', '血糖監測', '營養諮詢']
        elif category == '高風險':
            return base_recommendations + ['3個月內就醫', '糖化血色素檢查']
        elif category == '中等風險':
            return base_recommendations + ['6個月內檢查', '飲食調整']
        else:
            return base_recommendations + ['年度檢查', '維持健康體重']
    
    def _get_metabolic_recommendations(self, category):
        """獲取代謝症候群建議"""
        base_recommendations = ['體重管理', '血壓控制', '血糖監測', '血脂管理']
        
        if category == '極高風險':
            return base_recommendations + ['綜合治療', '專科會診', '密切追蹤']
        elif category == '高風險':
            return base_recommendations + ['積極治療', '3個月追蹤']
        elif category == '中等風險':
            return base_recommendations + ['生活調整', '6個月追蹤']
        else:
            return base_recommendations + ['預防保健', '年度檢查']
    
    def _build_risk_factors(self, screening, vital_signs, lab_results, medical_history, lifestyle):
        """構建風險因子數據結構"""
        # 獲取患者基本資訊
        patient = screening.patient
        
        # 計算年齡
        if patient.date_of_birth:
            from datetime import date
            today = date.today()
            age = today.year - patient.date_of_birth.year - ((today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day))
        else:
            age = screening.age_at_screening or 50  # 預設值
        
        # 性別
        gender = patient.gender if hasattr(patient, 'gender') else 'M'
        
        # 生命徵象數據 - 確保轉換為 float 類型
        height_cm = float(vital_signs.height_cm if vital_signs and vital_signs.height_cm else 170.0)
        weight_kg = float(vital_signs.weight_kg if vital_signs and vital_signs.weight_kg else 70.0)
        sbp = float(vital_signs.systolic_bp_mmhg if vital_signs and vital_signs.systolic_bp_mmhg else 120.0)
        dbp = float(vital_signs.diastolic_bp_mmhg if vital_signs and vital_signs.diastolic_bp_mmhg else 80.0)
        
        # 實驗室數據 - 確保轉換為 float 類型
        total_cholesterol = float(lab_results.total_cholesterol_mgdl if lab_results and lab_results.total_cholesterol_mgdl else 200.0)
        hdl_cholesterol = float(lab_results.hdl_cholesterol_mgdl if lab_results and lab_results.hdl_cholesterol_mgdl else 50.0)
        ldl_cholesterol = float(lab_results.ldl_cholesterol_mgdl if lab_results and lab_results.ldl_cholesterol_mgdl else 130.0)
        triglycerides = float(lab_results.triglycerides_mgdl if lab_results and lab_results.triglycerides_mgdl else 150.0)
        glucose = float(lab_results.fasting_glucose_mgdl if lab_results and lab_results.fasting_glucose_mgdl else 100.0)
        hba1c = float(lab_results.hba1c_percent if lab_results and lab_results.hba1c_percent else 5.5)
        creatinine = float(lab_results.urine_creatinine_mgdl if lab_results and lab_results.urine_creatinine_mgdl else 1.0)
        
        # 病史數據 - 檢查lifestyle中的疾病史
        diabetes = lifestyle.has_diabetes if lifestyle and hasattr(lifestyle, 'has_diabetes') else False
        hypertension = lifestyle.has_hypertension if lifestyle and hasattr(lifestyle, 'has_hypertension') else False
        family_history_cvd = lifestyle.family_cvd if lifestyle and hasattr(lifestyle, 'family_cvd') else False
        
        # 生活方式數據 - 根據實際模型字段
        # 吸菸狀態處理
        if lifestyle:
            if hasattr(lifestyle, 'is_current_smoker') and lifestyle.is_current_smoker:
                smoking_status = 'current'
            elif hasattr(lifestyle, 'is_former_smoker') and lifestyle.is_former_smoker:
                smoking_status = 'former'
            else:
                smoking_status = 'never'
        else:
            smoking_status = 'never'
            
        alcohol_consumption = lifestyle.drinking_status if lifestyle and hasattr(lifestyle, 'drinking_status') else 'moderate'
        physical_activity_level = lifestyle.exercise_score if lifestyle and hasattr(lifestyle, 'exercise_score') else 'moderate'
        
        # 用藥史 - 使用預設值，因為模型中可能沒有這些字段
        hypertension_medication = False
        statin_use = False
        
        return RiskFactors(
            age=float(age),
            gender=gender,
            height_cm=float(height_cm),
            weight_kg=float(weight_kg),
            sbp=float(sbp),
            dbp=float(dbp),
            total_cholesterol=float(total_cholesterol),
            hdl_cholesterol=float(hdl_cholesterol),
            ldl_cholesterol=float(ldl_cholesterol),
            triglycerides=float(triglycerides),
            glucose=float(glucose),
            hba1c=float(hba1c),
            creatinine=float(creatinine),
            bun=15.0,  # 預設值，如果沒有數據
            diabetes=diabetes,
            smoking_status=smoking_status,
            hypertension_medication=hypertension_medication,
            statin_use=statin_use,
            family_history_cvd=family_history_cvd,
            physical_activity_level=physical_activity_level,
            alcohol_consumption=alcohol_consumption
        )
    
    def _process_fhir_data(self, fhir_data, data_format):
        """處理 FHIR R4 格式數據"""
        import xml.etree.ElementTree as ET
        from datetime import datetime
        
        success_count = 0
        error_count = 0
        errors = []
        created_patients = 0
        created_screenings = 0
        
        try:
            # 解析 FHIR 數據
            if data_format == 'json':
                if isinstance(fhir_data, str):
                    fhir_json = json.loads(fhir_data)
                else:
                    fhir_json = fhir_data
            else:  # XML 格式
                # 簡化的 XML 處理
                root = ET.fromstring(fhir_data)
                # 這裡可以添加更複雜的 XML 解析邏輯
                errors.append('XML 格式暫不完全支援，建議使用 JSON 格式')
                return {
                    'success': False,
                    'error': 'XML 格式暫不完全支援',
                    'created_patients': 0,
                    'created_screenings': 0
                }
            
            # 處理 Bundle 或單一資源
            resources = []
            if fhir_json.get('resourceType') == 'Bundle':
                if 'entry' in fhir_json:
                    for entry in fhir_json['entry']:
                        if 'resource' in entry:
                            resources.append(entry['resource'])
            elif fhir_json.get('resourceType'):
                resources.append(fhir_json)
            
            # 按類型分組資源
            patients = [r for r in resources if r.get('resourceType') == 'Patient']
            observations = [r for r in resources if r.get('resourceType') == 'Observation']
            diagnostic_reports = [r for r in resources if r.get('resourceType') == 'DiagnosticReport']
            encounters = [r for r in resources if r.get('resourceType') == 'Encounter']
            
            # 處理患者資源
            patient_mapping = {}
            for patient_resource in patients:
                try:
                    patient = self._create_patient_from_fhir(patient_resource)
                    patient_mapping[patient_resource.get('id')] = patient
                    created_patients += 1
                    success_count += 1
                except Exception as e:
                    errors.append(f'患者創建失敗: {str(e)}')
                    error_count += 1
            
            # 處理檢驗數據 - 創建健檢記錄
            encounter_mapping = {}
            for obs_resource in observations:
                try:
                    # 嘗試從 Observation 創建或更新健檢記錄
                    screening = self._create_screening_from_observation(obs_resource, patient_mapping)
                    if screening:
                        encounter_id = obs_resource.get('encounter', {}).get('reference', '').replace('Encounter/', '')
                        if encounter_id:
                            encounter_mapping[encounter_id] = screening
                        created_screenings += 1
                        success_count += 1
                except Exception as e:
                    errors.append(f'檢驗數據處理失敗: {str(e)}')
                    error_count += 1
            
            # 處理診斷報告
            for report_resource in diagnostic_reports:
                try:
                    self._process_diagnostic_report(report_resource, patient_mapping, encounter_mapping)
                    success_count += 1
                except Exception as e:
                    errors.append(f'診斷報告處理失敗: {str(e)}')
                    error_count += 1
            
            return {
                'success': True,
                'success_count': success_count,
                'error_count': error_count,
                'total_count': success_count + error_count,
                'created_patients': created_patients,
                'created_screenings': created_screenings,
                'errors': errors
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'FHIR 數據解析失敗: {str(e)}',
                'created_patients': 0,
                'created_screenings': 0
            }
    
    def _create_patient_from_fhir(self, patient_resource):
        """從 FHIR Patient 資源創建患者"""
        # 提取患者基本信息
        patient_id = patient_resource.get('id', '')
        identifiers = patient_resource.get('identifier', [])
        names = patient_resource.get('name', [])
        gender = patient_resource.get('gender', 'unknown')
        birth_date = patient_resource.get('birthDate')
        
        # 提取病歷號
        medical_record_number = None
        for identifier in identifiers:
            if identifier.get('type', {}).get('coding', [{}])[0].get('code') == 'MR':
                medical_record_number = identifier.get('value')
                break
        
        if not medical_record_number:
            medical_record_number = f'FHIR_{patient_id}'
        
        # 提取姓名
        first_name = ''
        last_name = ''
        if names:
            name = names[0]
            if 'given' in name:
                first_name = ' '.join(name['given'])
            if 'family' in name:
                last_name = name['family']
        
        # 轉換性別
        gender_mapping = {
            'male': 'M',
            'female': 'F',
            'other': 'O',
            'unknown': 'U'
        }
        django_gender = gender_mapping.get(gender, 'U')
        
        # 轉換出生日期
        date_of_birth = None
        if birth_date:
            try:
                date_of_birth = datetime.strptime(birth_date, '%Y-%m-%d').date()
            except:
                pass
        
        # 檢查患者是否已存在
        try:
            patient = Patient.objects.get(medical_record_number=medical_record_number)
            # 更新現有患者信息
            if first_name:
                patient.first_name = first_name
            if last_name:
                patient.last_name = last_name
            if date_of_birth:
                patient.date_of_birth = date_of_birth
            patient.gender = django_gender
            patient.save()
        except Patient.DoesNotExist:
            # 創建新患者
            patient = Patient.objects.create(
                medical_record_number=medical_record_number,
                first_name=first_name or 'Unknown',
                last_name=last_name or 'Patient',
                date_of_birth=date_of_birth,
                gender=django_gender,
                is_active=True
            )
        
        return patient
    
    def _create_screening_from_observation(self, obs_resource, patient_mapping):
        """從 FHIR Observation 創建健檢記錄"""
        # 提取患者引用
        subject_ref = obs_resource.get('subject', {}).get('reference', '')
        patient_id = subject_ref.replace('Patient/', '') if subject_ref.startswith('Patient/') else subject_ref
        
        if patient_id not in patient_mapping:
            raise ValueError(f'無法找到患者 ID: {patient_id}')
        
        patient = patient_mapping[patient_id]
        
        # 提取檢查日期
        effective_date = obs_resource.get('effectiveDateTime') or obs_resource.get('effectiveDate')
        if effective_date:
            try:
                screening_date = datetime.strptime(effective_date.split('T')[0], '%Y-%m-%d').date()
            except:
                screening_date = timezone.now().date()
        else:
            screening_date = timezone.now().date()
        
        # 查找或創建健檢記錄
        screening, created = HealthScreening.objects.get_or_create(
            patient=patient,
            screening_date=screening_date,
            defaults={
                'screening_type': 'fhir_import',
            }
        )
        
        # 處理檢驗數據
        self._process_observation_data(obs_resource, screening)
        
        return screening
    
    def _process_observation_data(self, obs_resource, screening):
        """處理 Observation 中的檢驗數據"""
        code = obs_resource.get('code', {})
        value = obs_resource.get('valueQuantity', {}).get('value') or obs_resource.get('valueString')
        
        # LOINC 編碼映射到我們的字段
        loinc_mapping = {
            '8302-2': ('height_cm', 'vital_signs'),  # 身高
            '29463-7': ('weight_kg', 'vital_signs'),  # 體重
            '8480-6': ('systolic_bp_mmhg', 'vital_signs'),  # 收縮壓
            '8462-4': ('diastolic_bp_mmhg', 'vital_signs'),  # 舒張壓
            '8867-4': ('pulse_rate_bpm', 'vital_signs'),  # 心率
            '1558-6': ('fasting_glucose_mgdl', 'laboratory_results'),  # 空腹血糖
            '4548-4': ('hba1c_percent', 'laboratory_results'),  # 糖化血色素
            '2093-3': ('total_cholesterol_mgdl', 'laboratory_results'),  # 總膽固醇
            '2085-9': ('hdl_cholesterol_mgdl', 'laboratory_results'),  # HDL
            '18261-8': ('ldl_cholesterol_mgdl', 'laboratory_results'),  # LDL
            '2571-8': ('triglycerides_mgdl', 'laboratory_results'),  # 三酸甘油脂
        }
        
        # 提取 LOINC 編碼
        loinc_code = None
        codings = code.get('coding', [])
        for coding in codings:
            if coding.get('system') == 'http://loinc.org':
                loinc_code = coding.get('code')
                break
        
        if loinc_code in loinc_mapping and value is not None:
            field_name, model_type = loinc_mapping[loinc_code]
            
            try:
                value = float(value)
                
                if model_type == 'vital_signs':
                    vital_signs, created = VitalSigns.objects.get_or_create(
                        health_screening=screening,
                        defaults={}
                    )
                    setattr(vital_signs, field_name, value)
                    vital_signs.save()
                    
                elif model_type == 'laboratory_results':
                    lab_results, created = LaboratoryResults.objects.get_or_create(
                        health_screening=screening,
                        defaults={}
                    )
                    setattr(lab_results, field_name, value)
                    lab_results.save()
                    
            except (ValueError, TypeError):
                pass  # 忽略無法轉換的值
    
    def _process_diagnostic_report(self, report_resource, patient_mapping, encounter_mapping):
        """處理 DiagnosticReport 資源"""
        # 這裡可以添加處理診斷報告的邏輯
        # 暫時只記錄報告存在
        pass


# 傳統視圖函數
@login_required
def dashboard(request):
    """健檢儀表板"""
    # 統計數據
    total_screenings = HealthScreening.objects.count()
    this_month_screenings = HealthScreening.objects.filter(
        screening_date__gte=timezone.now().replace(day=1).date()
    ).count()
    
    # 暫時使用簡化的統計，之後可以基於實際檢查結果來計算
    pending_results = 0  # 可以基於是否有完整檢查結果來計算
    abnormal_results = 0  # 可以基於檢查結果是否異常來計算
    
    # 最近的健檢記錄
    recent_screenings = HealthScreening.objects.select_related(
        'patient'
    ).prefetch_related('vital_signs').order_by('-screening_date')[:10]
    
    context = {
        'total_screenings': total_screenings,
        'this_month_screenings': this_month_screenings,
        'pending_results': pending_results,
        'abnormal_results': abnormal_results,
        'recent_screenings': recent_screenings,
    }
    
    return render(request, 'health_screening/dashboard.html', context)


@login_required
def create_screening(request):
    """創建健檢記錄"""
    if request.method == 'POST':
        try:
            # 獲取基本數據
            patient_id = request.POST.get('patient')
            patient = get_object_or_404(Patient, id=patient_id)
            
            screening_data = {
                'patient': patient,
                'screening_date': request.POST.get('screening_date'),
                'screening_type': request.POST.get('screening_type'),
                'notes': request.POST.get('notes', ''),
            }
            
            # 執行醫師
            provider_id = request.POST.get('provider')
            if provider_id:
                screening_data['provider'] = get_object_or_404(User, id=provider_id)
            
            # 創建健檢記錄
            screening = HealthScreening.objects.create(**screening_data)
            
            # 處理生命體徵
            vital_fields_mapping = {
                'height': 'height_cm',
                'weight': 'weight_kg', 
                'temperature': 'body_temperature_celsius',
                'systolic_pressure': 'systolic_bp_mmhg',
                'diastolic_pressure': 'diastolic_bp_mmhg',
                'heart_rate': 'resting_heart_rate_bpm',
                'respiratory_rate': 'respiratory_rate_per_min',
                'oxygen_saturation': 'oxygen_saturation_percent',
                'waist_circumference': 'waist_circumference_cm'
            }
            
            vital_data = {}
            for form_field, model_field in vital_fields_mapping.items():
                value = request.POST.get(form_field)
                if value:
                    vital_data[model_field] = float(value)
            
            if vital_data:
                vital_data['health_screening'] = screening
                VitalSigns.objects.create(**vital_data)
            
            # 處理檢驗結果
            lab_fields_mapping = {
                'fasting_glucose': 'fasting_glucose_mgdl',
                'total_cholesterol': 'total_cholesterol_mgdl',
                'hdl_cholesterol': 'hdl_cholesterol_mgdl',
                'ldl_cholesterol': 'ldl_cholesterol_mgdl',
                'triglycerides': 'triglycerides_mgdl',
                'hba1c': 'hba1c_percent',
                'alt': 'alt_gpt_ul',
                'ast': 'ast_got_ul',
                'creatinine': 'urine_creatinine_mgdl',
                'uric_acid': 'uric_acid_mgdl'
            }
            
            lab_data = {}
            for form_field, model_field in lab_fields_mapping.items():
                value = request.POST.get(form_field)
                if value:
                    lab_data[model_field] = float(value)
            
            if lab_data:
                lab_data['health_screening'] = screening
                LaboratoryResults.objects.create(**lab_data)
            
            # 處理病史
            history_data = {
                'health_screening': screening,
                'has_diabetes': 'has_diabetes' in request.POST,
                'has_hypertension': 'has_hypertension' in request.POST,
                'has_dyslipidemia': 'has_dyslipidemia' in request.POST,
                'has_coronary_heart_disease': 'has_coronary_heart_disease' in request.POST,
                'has_cerebrovascular_disease': 'has_cerebrovascular_disease' in request.POST,
                'diabetes_treated': 'diabetes_treated' in request.POST,
                'hypertension_treated': 'hypertension_treated' in request.POST,
                'hyperlipidemia_treated': 'hyperlipidemia_treated' in request.POST,
            }
            
            MedicalHistory.objects.create(**history_data)
            
            # 處理生活習慣問卷
            lifestyle_data = {}
            lifestyle_fields = ['smoking_status', 'cigarettes_per_day', 'alcohol_consumption', 'exercise_frequency']
            
            for field in lifestyle_fields:
                value = request.POST.get(field)
                if value:
                    lifestyle_data[field] = value
            
            if lifestyle_data:
                LifestyleQuestionnaire.objects.create(screening=screening, **lifestyle_data)
            
            messages.success(request, '健檢記錄創建成功！')
            return redirect('health_screening:dashboard')
            
        except Exception as e:
            messages.error(request, f'創建失敗: {str(e)}')
    
    # GET 請求
    patients = Patient.objects.filter(is_active=True).order_by('first_name', 'last_name')
    doctors = User.objects.filter(is_staff=True, is_active=True)
    
    context = {
        'patients': patients,
        'doctors': doctors,
        'patient': None,
    }
    
    # 如果URL中指定了患者ID
    patient_id = request.GET.get('patient_id')
    if patient_id:
        try:
            context['patient'] = get_object_or_404(Patient, id=patient_id)
        except:
            pass
    
    return render(request, 'health_screening/create.html', context)


@login_required
def bulk_import(request):
    """批量匯入頁面"""
    # 今日匯入統計
    today = timezone.now().date()
    today_imports = HealthScreening.objects.filter(
        created_at__date=today
    ).count()
    
    # 這裡簡化處理，實際應該記錄匯入錯誤
    today_errors = 0
    
    context = {
        'today_imports': today_imports,
        'today_errors': today_errors,
    }
    
    return render(request, 'health_screening/bulk_import.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def parse_file(request):
    """解析上傳的檔案"""
    try:
        file = request.FILES.get('file')
        if not file:
            return JsonResponse({
                'success': False,
                'error': '沒有上傳檔案'
            })
        
        # 讀取檔案
        if file.name.endswith('.csv'):
            # 嘗試不同編碼讀取 CSV，並設置 dtype 選項避免警告
            encodings = ['utf-8', 'gbk', 'big5', 'cp1252', 'iso-8859-1']
            df = None
            for encoding in encodings:
                try:
                    df = pd.read_csv(file, encoding=encoding, low_memory=False)
                    break
                except (UnicodeDecodeError, UnicodeError):
                    file.seek(0)  # 重置文件指針
                    continue
            
            if df is None:
                return Response({
                    'success': False,
                    'error': '無法讀取 CSV 文件，請檢查文件編碼格式'
                }, status=status.HTTP_400_BAD_REQUEST)
        elif file.name.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file)
        else:
            return JsonResponse({
                'success': False,
                'error': '不支援的檔案格式'
            })
        
        # 將 DataFrame 轉換為字典列表，保留前5行作為預覽
        sample_data = df.head(5).fillna('').to_dict('records')
        headers = df.columns.tolist()
        
        return JsonResponse({
            'success': True,
            'headers': headers,
            'sample_data': sample_data,
            'row_count': len(df),
            'data': df.fillna('').to_dict('records')  # 完整數據用於實際匯入
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def download_template(request):
    """下載範本檔案"""
    format_type = request.GET.get('format', 'excel')
    
    # 定義欄位
    columns = [
        'patient_id', 'screening_date', 'screening_type', 'provider',
        'height', 'weight', 'temperature', 'systolic_pressure', 'diastolic_pressure',
        'heart_rate', 'respiratory_rate', 'oxygen_saturation', 'waist_circumference',
        'fasting_glucose', 'total_cholesterol', 'hdl_cholesterol', 'ldl_cholesterol',
        'triglycerides', 'hba1c', 'alt', 'ast', 'creatinine', 'uric_acid',
        'has_diabetes', 'has_hypertension', 'has_hyperlipidemia', 'has_heart_disease',
        'has_stroke', 'has_cancer', 'family_history', 'smoking_status',
        'cigarettes_per_day', 'alcohol_consumption', 'exercise_frequency'
    ]
    
    # 創建範本數據
    sample_data = {
        'patient_id': ['P001', 'P002'],
        'screening_date': ['2024-01-15', '2024-01-16'],
        'screening_type': ['annual_physical', 'preventive_care'],
        'provider': ['1', '2'],
        'height': [170.0, 165.5],
        'weight': [70.0, 55.2],
        'temperature': [36.5, 36.8],
        'systolic_pressure': [120, 110],
        'diastolic_pressure': [80, 75],
        'heart_rate': [72, 68],
        'respiratory_rate': [16, 18],
        'oxygen_saturation': [98.5, 99.0],
        'waist_circumference': [85.0, 75.5],
        'fasting_glucose': [95.0, 88.5],
        'total_cholesterol': [200.0, 180.3],
        'hdl_cholesterol': [50.0, 60.2],
        'ldl_cholesterol': [120.0, 100.1],
        'triglycerides': [150.0, 120.8],
        'hba1c': [5.5, 5.2],
        'alt': [25.0, 22.1],
        'ast': [28.0, 24.5],
        'creatinine': [1.0, 0.8],
        'uric_acid': [6.0, 4.5],
        'has_diabetes': [False, False],
        'has_hypertension': [False, False],
        'has_hyperlipidemia': [False, False],
        'has_heart_disease': [False, False],
        'has_stroke': [False, False],
        'has_cancer': [False, False],
        'family_history': ['無', '父親有高血壓'],
        'smoking_status': ['never', 'former'],
        'cigarettes_per_day': [0, 0],
        'alcohol_consumption': ['never', 'occasional'],
        'exercise_frequency': ['regularly', 'sometimes']
    }
    
    # 創建 DataFrame
    df = pd.DataFrame(sample_data)
    
    if format_type == 'csv':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="health_screening_template.csv"'
        df.to_csv(response, index=False, encoding='utf-8-sig')
    else:
        # Excel 格式
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="health_screening_template.xlsx"'
        
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='健檢數據', index=False)
    
    return response


@login_required
def screening_list(request):
    """健檢記錄列表"""
    screenings = HealthScreening.objects.select_related(
        'patient', 'provider'
    ).order_by('-screening_date')
    
    # 搜尋功能
    search = request.GET.get('search')
    if search:
        screenings = screenings.filter(
            Q(patient__first_name__icontains=search) |
            Q(patient__last_name__icontains=search) |
            Q(patient__patient_id__icontains=search)
        )
    
    # 分頁
    paginator = Paginator(screenings, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
    }
    
    return render(request, 'health_screening/list.html', context)


@login_required
def screening_detail(request, screening_id):
    """健檢記錄詳情"""
    screening = get_object_or_404(
        HealthScreening.objects.select_related('patient', 'provider'),
        id=screening_id
    )
    
    context = {
        'screening': screening,
    }
    
    return render(request, 'health_screening/detail.html', context)


@login_required
def screening_edit(request, screening_id):
    """編輯健檢記錄"""
    screening = get_object_or_404(HealthScreening, id=screening_id)
    
    if request.method == 'POST':
        try:
            # 更新基本數據
            screening.screening_date = request.POST.get('screening_date')
            screening.screening_type = request.POST.get('screening_type')
            screening.notes = request.POST.get('notes', '')
            
            provider_id = request.POST.get('provider')
            if provider_id:
                screening.provider = get_object_or_404(User, id=provider_id)
            else:
                screening.provider = None
            screening.save()

            # 更新生命體徵
            vital_fields_mapping = {
                'height': 'height_cm',
                'weight': 'weight_kg', 
                'temperature': 'body_temperature_celsius',
                'systolic_pressure': 'systolic_bp_mmhg',
                'diastolic_pressure': 'diastolic_bp_mmhg',
                'heart_rate': 'resting_heart_rate_bpm',
                'respiratory_rate': 'respiratory_rate_per_min',
                'oxygen_saturation': 'oxygen_saturation_percent',
                'waist_circumference': 'waist_circumference_cm'
            }
            vital_data = {}
            for form_field, model_field in vital_fields_mapping.items():
                value = request.POST.get(form_field)
                if value:
                    vital_data[model_field] = float(value)
            
            if vital_data:
                VitalSigns.objects.update_or_create(health_screening=screening, defaults=vital_data)

            # 更新檢驗結果
            lab_fields_mapping = {
                'fasting_glucose': 'fasting_glucose_mgdl',
                'total_cholesterol': 'total_cholesterol_mgdl',
                'hdl_cholesterol': 'hdl_cholesterol_mgdl',
                'ldl_cholesterol': 'ldl_cholesterol_mgdl',
                'triglycerides': 'triglycerides_mgdl',
                'hba1c': 'hba1c_percent',
                'alt': 'alt_gpt_ul',
                'ast': 'ast_got_ul',
                'creatinine': 'urine_creatinine_mgdl',
                'uric_acid': 'uric_acid_mgdl'
            }
            lab_data = {}
            for form_field, model_field in lab_fields_mapping.items():
                value = request.POST.get(form_field)
                if value:
                    lab_data[model_field] = float(value)
            
            if lab_data:
                LaboratoryResults.objects.update_or_create(health_screening=screening, defaults=lab_data)

            # 更新病史
            medical_history_data = {
                'has_diabetes': 'has_diabetes' in request.POST,
                'has_hypertension': 'has_hypertension' in request.POST,
                'has_dyslipidemia': 'has_dyslipidemia' in request.POST,
                'has_coronary_heart_disease': 'has_coronary_heart_disease' in request.POST,
                'has_cerebrovascular_disease': 'has_cerebrovascular_disease' in request.POST,
                'has_cancer': 'has_cancer' in request.POST,
                'diabetes_treated': 'diabetes_treated' in request.POST,
                'hypertension_treated': 'hypertension_treated' in request.POST,
                'hyperlipidemia_treated': 'hyperlipidemia_treated' in request.POST,
            }
            MedicalHistory.objects.update_or_create(health_screening=screening, defaults=medical_history_data)

            # 更新生活習慣問卷
            lifestyle_data = {
                'smoking_status': request.POST.get('smoking_status', ''),
                'cigarettes_per_day': request.POST.get('cigarettes_per_day') or None,
                'quit_smoking_when': request.POST.get('quit_smoking_when', ''),
                'drinking_status': request.POST.get('alcohol_consumption', ''),
                'exercise_score': request.POST.get('exercise_frequency', ''),
            }
            LifestyleQuestionnaire.objects.update_or_create(health_screening=screening, defaults=lifestyle_data)

            messages.success(request, '健檢記錄更新成功！')
            return redirect('health_screening:detail', screening_id=screening.id)

        except Exception as e:
            messages.error(request, f'更新失敗: {str(e)}')

    # GET 請求
    doctors = User.objects.filter(is_staff=True, is_active=True)
    context = {
        'screening': screening,
        'doctors': doctors,
    }
    return render(request, 'health_screening/edit.html', context)
    
    context = {
        'screening': screening,
    }
    
    return render(request, 'health_screening/edit.html', context)


@login_required
def reports(request):
    """統計報告"""
    # 基本統計
    stats = {
        'total_screenings': HealthScreening.objects.count(),
        'this_month': HealthScreening.objects.filter(
            screening_date__gte=timezone.now().replace(day=1).date()
        ).count(),
        'last_month': HealthScreening.objects.filter(
            screening_date__gte=(timezone.now() - timedelta(days=30)).date(),
            screening_date__lt=timezone.now().replace(day=1).date()
        ).count(),
    }
    
    all_patients = Patient.objects.all().order_by('first_name', 'last_name')

    context = {
        'stats': stats,
        'all_patients': all_patients,
    }
    
    return render(request, 'health_screening/reports.html', context)


@login_required  
def download_error_report(request):
    """下載錯誤報告"""
    # 這裡應該實際生成錯誤報告
    response = HttpResponse(content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="error_report.txt"'
    response.write('錯誤報告功能尚未實現')
    return response
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
    
    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser])
    def bulk_import(self, request):
        """批量匯入健檢數據"""
        try:
            file = request.FILES.get('file')
            if not file:
                return Response({'error': '請上傳檔案'}, status=status.HTTP_400_BAD_REQUEST)
            
            # 讀取 Excel 或 CSV 檔案
            if file.name.endswith('.xlsx') or file.name.endswith('.xls'):
                df = pd.read_excel(file)
            elif file.name.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                return Response({'error': '僅支援 Excel (.xlsx, .xls) 或 CSV 檔案'}, 
                              status=status.HTTP_400_BAD_REQUEST)
            
            # 處理數據
            screenings_data = self._process_dataframe(df)
            
            # 使用序列化器驗證和創建
            serializer = BulkHealthScreeningSerializer(data={'screenings': screenings_data})
            if serializer.is_valid():
                result = serializer.save()
                return Response({
                    'message': f'成功匯入 {result["created_count"]} 筆健檢數據',
                    'created_count': result["created_count"]
                }, status=status.HTTP_201_CREATED)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({'error': f'匯入失敗: {str(e)}'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _process_dataframe(self, df):
        """處理 DataFrame 並轉換為 API 格式"""
        screenings_data = []
        
        for index, row in df.iterrows():
            try:
                # 基本健檢資料
                screening_data = {
                    'patient': self._get_or_create_patient(row),
                    'screening_date': self._parse_date(row.get('screening_date', row.get('檢查日期'))),
                    'screening_type': row.get('screening_type', row.get('檢查類型', 'annual_physical')),
                    'age_at_screening': self._safe_int(row.get('age', row.get('年齡'))),
                }
                
                # 生命徵象
                vital_signs = self._extract_vital_signs(row)
                if vital_signs:
                    screening_data['vital_signs'] = vital_signs
                
                # 檢驗結果
                laboratory = self._extract_laboratory_results(row)
                if laboratory:
                    screening_data['laboratory_results'] = laboratory
                
                # 心血管風險指數
                cardiovascular = self._extract_cardiovascular_risk(row)
                if cardiovascular:
                    screening_data['cardiovascular_risk'] = cardiovascular
                
                # 病史
                medical_history = self._extract_medical_history(row)
                if medical_history:
                    screening_data['medical_history'] = medical_history
                
                # 生活方式問卷
                lifestyle = self._extract_lifestyle(row)
                if lifestyle:
                    screening_data['lifestyle'] = lifestyle
                
                screenings_data.append(screening_data)
            
            except Exception as e:
                print(f"處理第 {index + 1} 行時發生錯誤: {str(e)}")
                continue
        
        return screenings_data
    
    def _get_or_create_patient(self, row):
        """獲取或創建患者"""
        # 嘗試通過不同欄位找到患者
        patient_id = row.get('patient_id', row.get('患者ID'))
        if patient_id:
            try:
                return Patient.objects.get(id=patient_id).id
            except Patient.DoesNotExist:
                pass
        
        # 通過姓名尋找
        first_name = row.get('first_name', row.get('名字'))
        last_name = row.get('last_name', row.get('姓氏'))
        if first_name and last_name:
            patient, created = Patient.objects.get_or_create(
                first_name=first_name,
                last_name=last_name,
                defaults={
                    'date_of_birth': self._parse_date(row.get('date_of_birth', row.get('出生日期'))),
                    'gender': row.get('gender', row.get('性別', 'U')),
                }
            )
            return patient.id
        
        raise ValueError("無法識別患者資訊")
    
    def _extract_vital_signs(self, row):
        """提取生命徵象數據"""
        data = {}
        
        # 身高體重
        if row.get('height', row.get('身高')):
            data['height_cm'] = self._safe_float(row.get('height', row.get('身高')))
        if row.get('weight', row.get('體重')):
            data['weight_kg'] = self._safe_float(row.get('weight', row.get('體重')))
        if row.get('bmi', row.get('BMI')):
            data['bmi'] = self._safe_float(row.get('bmi', row.get('BMI')))
        
        # 身體測量
        if row.get('neck_circumference', row.get('頸圍')):
            data['neck_circumference_cm'] = self._safe_float(row.get('neck_circumference', row.get('頸圍')))
        if row.get('chest_circumference', row.get('胸圍')):
            data['chest_circumference_cm'] = self._safe_float(row.get('chest_circumference', row.get('胸圍')))
        if row.get('waist_circumference', row.get('腰圍')):
            data['waist_circumference_cm'] = self._safe_float(row.get('waist_circumference', row.get('腰圍')))
        if row.get('hip_circumference', row.get('臀圍')):
            data['hip_circumference_cm'] = self._safe_float(row.get('hip_circumference', row.get('臀圍')))
        
        # 血壓脈搏
        if row.get('pulse_rate', row.get('脈搏')):
            data['pulse_rate_bpm'] = self._safe_int(row.get('pulse_rate', row.get('脈搏')))
        if row.get('systolic_bp', row.get('收縮壓')):
            data['systolic_bp_mmhg'] = self._safe_int(row.get('systolic_bp', row.get('收縮壓')))
        if row.get('diastolic_bp', row.get('舒張壓')):
            data['diastolic_bp_mmhg'] = self._safe_int(row.get('diastolic_bp', row.get('舒張壓')))
        
        return data if data else None
    
    def _extract_laboratory_results(self, row):
        """提取檢驗結果數據"""
        data = {}
        
        # 血液檢查
        lab_fields = {
            'rbc_count': ['RBC', 'rbc'],
            'rdw_cv_percent': ['RDW-CV%', 'rdw_cv'],
            'wbc_count': ['WBC', 'wbc'],
            'platelet_count': ['Platelet', 'platelet'],
            'monocyte_percent': ['Monocyte%', 'monocyte_percent'],
            'monocyte_absolute': ['Monocyte (×109/L)', 'monocyte_absolute'],
            
            # 血糖相關
            'fasting_glucose_mgdl': ['空腹血糖', 'fasting_glucose'],
            'hba1c_percent': ['HbA1C', 'hba1c'],
            'insulin_uiu_ml': ['Insulin', 'insulin'],
            'homa_ir': ['HOMA-IR', 'homa_ir'],
            'egdr': ['eGDR', 'egdr'],
            
            # 血脂
            'triglycerides_mgdl': ['TG', 'triglycerides', '三酸甘油脂'],
            'total_cholesterol_mgdl': ['TC', 'total_cholesterol', '總膽固醇'],
            'hdl_cholesterol_mgdl': ['HDL-C', 'hdl', 'HDL'],
            'ldl_cholesterol_mgdl': ['LDL-C', 'ldl', 'LDL'],
            'non_hdl_cholesterol_mgdl': ['non-HDL-C', 'non_hdl'],
            
            # 其他生化
            'uric_acid_mgdl': ['uric acid', 'uric_acid', '尿酸'],
            'hs_crp_mgdl': ['hsCRP', 'hs_crp'],
            'alt_gpt_ul': ['ALT/GPT', 'alt', 'gpt'],
            'ast_got_ul': ['AST/GOT', 'ast', 'got'],
            'ggt_ul': ['GGT', 'ggt'],
            'total_protein_gdl': ['TotalProtein', 'total_protein'],
            'albumin_gdl': ['Albumin', 'albumin'],
        }
        
        for field, possible_names in lab_fields.items():
            value = None
            for name in possible_names:
                if row.get(name) is not None:
                    value = self._safe_float(row.get(name))
                    break
            if value is not None:
                data[field] = value
        
        return data if data else None
    
    def _extract_cardiovascular_risk(self, row):
        """提取心血管風險指數"""
        data = {}
        
        risk_fields = {
            'cardiometabolic_index': ['CMI', 'cmi'],
            'atherogenic_risk_plasma': ['ARP', 'arp'],
            'visceral_adiposity_index_women': ['Women VAI', 'women_vai'],
            'visceral_adiposity_index_men': ['Men VAI', 'men_vai'],
            'cvai_female': ['Female CVAI', 'female_cvai'],
            'cvai_male': ['Male CVAI', 'male_cvai'],
            'monocyte_hdl_ratio': ['Mono/HDL-C', 'mono_hdl'],
        }
        
        for field, possible_names in risk_fields.items():
            value = None
            for name in possible_names:
                if row.get(name) is not None:
                    value = self._safe_float(row.get(name))
                    break
            if value is not None:
                data[field] = value
        
        return data if data else None
    
    def _extract_medical_history(self, row):
        """提取病史"""
        data = {}
        
        history_fields = {
            'diabetes_treated': ['DM treated', 'dm_treated'],
            'hypertension_treated': ['Hypertension treated', 'htn_treated'],
            'hyperlipidemia_treated': ['Hyperlipid treated', 'lipid_treated'],
            'hypertension_history': ['Hypertensio HX', 'htn_history'],
            'apoe_e4_positive': ['APOE ε4', 'apoe_e4'],
        }
        
        for field, possible_names in history_fields.items():
            value = None
            for name in possible_names:
                if row.get(name) is not None:
                    value = self._safe_bool(row.get(name))
                    break
            if value is not None:
                data[field] = value
        
        return data if data else None
    
    def _extract_lifestyle(self, row):
        """提取生活方式問卷"""
        data = {}
        
        # 飲食
        diet_value = row.get('DIET', row.get('飲食'))
        if diet_value is not None:
            data['diet_score'] = str(diet_value)
        
        # 運動
        exercise_value = row.get('EXERCISE', row.get('運動'))
        if exercise_value is not None:
            data['exercise_score'] = str(exercise_value)
        
        # 家族史
        family_fields = {
            'family_diabetes': ['Famili HX diabetes', 'family_dm'],
            'family_hypertension': ['Famili HX HTN', 'family_htn'],
            'family_heart_disease': ['Famili HX HEART Disease', 'family_heart'],
            'family_cvd': ['Famili HX CVD', 'family_cvd'],
            'family_cancer': ['Famili HX Cancer', 'family_cancer'],
        }
        
        for field, possible_names in family_fields.items():
            value = None
            for name in possible_names:
                if row.get(name) is not None:
                    value = self._safe_bool(row.get(name))
                    break
            if value is not None:
                data[field] = value
        
        # 疾病史
        disease_fields = {
            'has_diabetes': ['IF DM (Y/N)', 'has_dm'],
            'has_hypertension': ['IF HTN (Y/N)', 'has_htn'],
            'has_dyslipidemia': ['IF Dyslipidemia', 'has_dyslipidemia'],
        }
        
        for field, possible_names in disease_fields.items():
            value = None
            for name in possible_names:
                if row.get(name) is not None:
                    value = self._safe_bool(row.get(name))
                    break
            if value is not None:
                data[field] = value
        
        # 吸菸飲酒
        smoking_fields = {
            'is_current_smoker': ['SmokING daily?', 'current_smoker'],
            'smoking_years': ['How Many Y', 'smoking_years'],
            'cigarettes_per_day': ['How much', 'cigarettes_per_day'],
            'is_former_smoker': ['FORMER Smoker', 'former_smoker'],
        }
        
        for field, possible_names in smoking_fields.items():
            value = None
            for name in possible_names:
                if row.get(name) is not None:
                    if field in ['smoking_years', 'cigarettes_per_day']:
                        value = self._safe_int(row.get(name))
                    else:
                        value = self._safe_bool(row.get(name))
                    break
            if value is not None:
                data[field] = value
        
        return data if data else None
    
    def _safe_float(self, value):
        """安全轉換為浮點數"""
        if value is None or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _safe_int(self, value):
        """安全轉換為整數"""
        if value is None or value == '':
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    def _safe_bool(self, value):
        """安全轉換為布林值"""
        if value is None or value == '':
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ['true', 'yes', 'y', '1', '是', 'true']
        return bool(value)
    
    def _parse_date(self, value):
        """解析日期"""
        if value is None or value == '':
            return None
        if isinstance(value, str):
            try:
                return datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                try:
                    return datetime.strptime(value, '%Y/%m/%d').date()
                except ValueError:
                    return None
        return value
    
    @action(detail=True, methods=['get'])
    def export_pdf(self, request, pk=None):
        """匯出健檢報告 PDF"""
        # TODO: 實現 PDF 匯出功能
        pass
    
    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        """匯出健檢數據為 Excel"""
        # TODO: 實現 Excel 匯出功能
        pass


# Web 頁面視圖
@login_required
def health_screening_dashboard(request):
    """健檢數據儀表板"""
    return render(request, 'health_screening/dashboard.html')


@login_required
def health_screening_input(request):
    """健檢數據輸入頁面"""
    return render(request, 'health_screening/input_form.html')


@login_required
def bulk_import_page(request):
    """批量匯入頁面"""
    return render(request, 'health_screening/bulk_import.html')
