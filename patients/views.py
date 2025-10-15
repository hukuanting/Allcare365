from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
import json
from .models import Patient, HistoryData, EmployerData, PatientAllergy, PatientMedication, PatientVitals, InsuranceData, HistoryData, PatientDocument
from encounters.models import Encounter

# REST Framework imports
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from .serializers import PatientSerializer

class PatientViewSet(viewsets.ModelViewSet):
    """患者管理 REST API ViewSet"""
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [AllowAny]  # 暫時允許所有用戶訪問，用於測試
    authentication_classes = []  # 暫時移除所有認證要求
    
    def destroy(self, request, *args, **kwargs):
        """自定義刪除方法，使用軟刪除"""
        try:
            instance = self.get_object()
            patient_name = instance.full_name
            patient_id = instance.id
            
            print(f"正在軟刪除患者: {patient_id} - {patient_name}")
            
            # 使用軟刪除（設置 is_active = False）
            instance.is_active = False
            instance.save()
            
            print(f"患者 {patient_id} - {patient_name} 軟刪除成功")
            
            # 返回成功響應
            return Response(
                {'message': f'患者 {patient_name} 已成功刪除'},
                status=status.HTTP_204_NO_CONTENT
            )
            
        except Exception as e:
            print(f"軟刪除患者時發生錯誤: {e}")
            return Response(
                {'error': f'刪除失敗: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get_queryset(self):
        """自定義查詢集合，支援搜索，只返回活躍患者"""
        queryset = Patient.objects.filter(is_active=True)  # 只顯示活躍患者
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(medical_record_number__icontains=search)
            )
        return queryset.order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        """重寫list方法，提供分頁和統計"""
        queryset = self.filter_queryset(self.get_queryset())
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'results': serializer.data,
            'count': queryset.count()
        })

@login_required
def patient_list_view(request):
    """患者列表頁面視圖"""
    return render(request, 'patients/patient_list.html')


@login_required
def patient_detail_view(request, patient_id):
    """患者詳細頁面視圖"""
    patient = get_object_or_404(Patient, id=patient_id)
    
    # 獲取相關數據
    encounters = Encounter.objects.filter(patient=patient).order_by('-encounter_date')[:10]  # 最近10次看診
    allergies = PatientAllergy.objects.filter(patient=patient)
    medications = PatientMedication.objects.filter(patient=patient)
    vitals = PatientVitals.objects.filter(patient=patient).order_by('-measurement_date')[:10] # 最近10次生命體徵
    insurance_data = InsuranceData.objects.filter(patient=patient)
    history_data = HistoryData.objects.filter(patient=patient).first()
    employer_data = EmployerData.objects.filter(patient=patient)
    documents = PatientDocument.objects.filter(patient=patient).order_by('-document_date')[:10]
    
    context = {
        'patient': patient,
        'encounters': encounters,
        'allergies': allergies,
        'medications': medications,
        'vitals': vitals,
        'insurance_data': insurance_data,
        'history_data': history_data,
        'employer_data': employer_data,
        'documents': documents,
    }
    return render(request, 'patients/patient_detail.html', context)


@login_required
def patient_api_list(request):
    """患者列表API（用於前端AJAX請求）"""
    # 獲取查詢參數
    search = request.GET.get('search', '')
    gender = request.GET.get('gender', '')
    status = request.GET.get('status', '')
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 10))
    
    # 構建查詢
    queryset = Patient.objects.all()
    
    if search:
        queryset = queryset.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(medical_record_number__icontains=search) |
            Q(phone_mobile__icontains=search) |
            Q(email__icontains=search)
        )
    
    if gender:
        queryset = queryset.filter(gender=gender)
    
    if status == 'active':
        queryset = queryset.filter(is_active=True)
    elif status == 'inactive':
        queryset = queryset.filter(is_active=False)
    
    # 分頁
    paginator = Paginator(queryset, per_page)
    patients_page = paginator.get_page(page)
    
    # 構建返回數據
    patients_data = []
    for patient in patients_page:
        patients_data.append({
            'id': str(patient.id),
            'first_name': patient.first_name,
            'last_name': patient.last_name,
            'date_of_birth': patient.date_of_birth.strftime('%Y-%m-%d'),
            'gender': patient.gender,
            'phone_mobile': patient.phone_mobile or '',
            'email': patient.email or '',
            'medical_record_number': getattr(patient, 'medical_record_number', '') or '',
            'is_active': patient.is_active,
            'created_at': patient.created_at.strftime('%Y-%m-%d'),
        })
    
    return JsonResponse({
        'patients': patients_data,
        'pagination': {
            'current_page': page,
            'total_pages': paginator.num_pages,
            'total_items': paginator.count,
            'has_next': patients_page.has_next(),
            'has_previous': patients_page.has_previous(),
        }
    })


@login_required
def patient_statistics(request):
    """患者統計數據API"""
    from django.utils import timezone
    from datetime import timedelta
    
    # 計算統計數據
    total_patients = Patient.objects.count()
    active_patients = Patient.objects.filter(is_active=True).count()
    
    # 本月新增患者
    this_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_patients = Patient.objects.filter(created_at__gte=this_month_start).count()
    
    # 需要關注的患者（這裡用示例邏輯）
    critical_patients = 0  # 根據實際業務邏輯計算
    
    return JsonResponse({
        'total_patients': total_patients,
        'active_patients': active_patients,
        'new_patients': new_patients,
        'critical_patients': critical_patients,
    })


@login_required
def patient_create(request):
    """創建新患者API"""
    if request.method == 'POST':
        try:
            import json
            from datetime import datetime
            data = json.loads(request.body)
            
            # 驗證必填字段
            required_fields = ['first_name', 'last_name', 'date_of_birth', 'gender']
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({
                        'success': False,
                        'error': f'必填字段 {field} 不能為空'
                    }, status=400)
            
            # 處理日期字段
            try:
                date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': '出生日期格式不正確，請使用 YYYY-MM-DD 格式'
                }, status=400)
            
            # 創建患者
            patient = Patient.objects.create(
                first_name=data['first_name'],
                last_name=data['last_name'],
                middle_name=data.get('middle_name', ''),
                date_of_birth=date_of_birth,
                gender=data['gender'],
                phone_home=data.get('phone_home', ''),
                phone_mobile=data.get('phone_mobile', ''),
                phone_work=data.get('phone_work', ''),
                email=data.get('email', ''),
                address_line1=data.get('address_line1', ''),
                address_line2=data.get('address_line2', ''),
                city=data.get('city', ''),
                state=data.get('state', ''),
                postal_code=data.get('postal_code', ''),
                country=data.get('country', 'Taiwan'),
                blood_type=data.get('blood_type', ''),
                emergency_contact_name=data.get('emergency_contact_name', ''),
                emergency_contact_phone=data.get('emergency_contact_phone', ''),
                emergency_contact_relationship=data.get('emergency_contact_relationship', ''),
                occupation=data.get('occupation', ''),
                marital_status=data.get('marital_status', ''),
                additional_notes=data.get('additional_notes', ''),
                created_by=request.user
            )
            
            return JsonResponse({
                'success': True,
                'patient': {
                    'id': str(patient.id),
                    'full_name': patient.full_name,
                    'medical_record_number': patient.medical_record_number,
                    'age': patient.age,
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': '僅支援 POST 請求'
    }, status=405)


# ===== 根據RECONSTRUCTION_GUIDE.md建議新增的API端點 =====

@login_required
def patient_advanced_search(request):
    """高級患者搜索API"""
    if request.method == 'GET':
        from .services import EnhancedPatientService
        
        search_params = {
            'name': request.GET.get('name'),
            'ssn': request.GET.get('ssn'),
            'date_of_birth': request.GET.get('date_of_birth'),
            'phone': request.GET.get('phone'),
            'medical_record_number': request.GET.get('medical_record_number'),
            'gender': request.GET.get('gender'),
            'age_min': request.GET.get('age_min'),
            'age_max': request.GET.get('age_max'),
        }
        
        # 移除空值
        search_params = {k: v for k, v in search_params.items() if v}
        
        if not search_params:
            return JsonResponse({
                'success': False,
                'error': '請提供至少一個搜索條件'
            }, status=400)
        
        try:
            # 將age參數轉換為整數
            if search_params.get('age_min'):
                search_params['age_min'] = int(search_params['age_min'])
            if search_params.get('age_max'):
                search_params['age_max'] = int(search_params['age_max'])
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': '年齡參數必須為數字'
            }, status=400)
        
        results = EnhancedPatientService.advanced_patient_search(search_params)
        
        patients_data = []
        for patient in results[:50]:  # 限制結果數量
            patients_data.append({
                'id': str(patient.id),
                'full_name': patient.full_name,
                'date_of_birth': str(patient.date_of_birth),
                'age': patient.age,
                'gender': patient.get_gender_display(),
                'phone_mobile': patient.phone_mobile,
                'medical_record_number': patient.medical_record_number,
                'status': patient.get_status_display() if hasattr(patient, 'get_status_display') else 'Active',
            })
        
        return JsonResponse({
            'success': True,
            'patients': patients_data,
            'total_found': len(patients_data)
        })
    
    return JsonResponse({
        'success': False,
        'error': '僅支援 GET 請求'
    }, status=405)


@login_required
def patient_balance(request, patient_id):
    """獲取患者財務餘額API"""
    try:
        from .services import EnhancedPatientService
        balance = EnhancedPatientService.get_patient_balance(patient_id)
        return JsonResponse({
            'success': True,
            'patient_id': patient_id,
            'balance': float(balance),
            'currency': 'TWD'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def patient_summary_report(request, patient_id):
    """生成患者摘要報告API"""
    try:
        from .services import PatientReportService
        report = PatientReportService.generate_patient_summary_report(patient_id)
        return JsonResponse({
            'success': True,
            'report': report
        })
    except Patient.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': '患者不存在'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@csrf_exempt
def patient_insurance_create(request, patient_id):
    """創建患者保險信息API"""
    if request.method == 'POST':
        try:
            from .services import InsuranceManagementService
            data = json.loads(request.body)
            
            # 驗證必填字段
            required_fields = ['type', 'provider', 'policy_number', 'subscriber_last_name', 'subscriber_first_name', 'subscriber_relationship']
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({
                        'success': False,
                        'error': f'必填字段 {field} 不能為空'
                    }, status=400)
            
            insurance = InsuranceManagementService.create_insurance_data(patient_id, data)
            
            return JsonResponse({
                'success': True,
                'insurance': {
                    'id': str(insurance.id),
                    'type': insurance.get_type_display(),
                    'provider': insurance.provider,
                    'policy_number': insurance.policy_number
                }
            })
            
        except Patient.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': '患者不存在'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': '僅支援 POST 請求'
    }, status=405)


@login_required
def patient_insurance_list(request, patient_id):
    """獲取患者保險信息列表API"""
    try:
        from .services import InsuranceManagementService
        insurance_list = InsuranceManagementService.get_active_insurance(patient_id)
        
        insurance_data = []
        for insurance in insurance_list:
            insurance_data.append({
                'id': str(insurance.id),
                'type': insurance.get_type_display(),
                'provider': insurance.provider,
                'plan_name': insurance.plan_name,
                'policy_number': insurance.policy_number,
                'group_number': insurance.group_number,
                'subscriber_name': f"{insurance.subscriber_first_name} {insurance.subscriber_last_name}",
                'subscriber_relationship': insurance.subscriber_relationship,
                'effective_date': str(insurance.effective_date) if insurance.effective_date else None,
                'expiration_date': str(insurance.expiration_date) if insurance.expiration_date else None,
                'copay': float(insurance.copay) if insurance.copay else None,
                'deductible': float(insurance.deductible) if insurance.deductible else None,
            })
        
        return JsonResponse({
            'success': True,
            'insurance_data': insurance_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def patient_history_detail(request, patient_id):
    """獲取患者病史詳情API"""
    try:
        history = HistoryData.objects.filter(patient_id=patient_id, is_active=True).first()
        
        if not history:
            return JsonResponse({
                'success': True,
                'history': None,
                'message': '該患者暫無病史記錄'
            })
        
        history_data = {
            'id': str(history.id),
            'medical_history': history.medical_history,
            'family_history': history.family_history,
            'social_history': history.social_history,
            'tobacco': history.tobacco,
            'tobacco_details': history.tobacco_details,
            'alcohol': history.alcohol,
            'alcohol_details': history.alcohol_details,
            'exercise': history.exercise,
            'diet': history.diet,
            'gravida': history.gravida,
            'para': history.para,
            'abortions': history.abortions,
            'miscarriages': history.miscarriages,
            'coffee_consumption': history.coffee_consumption,
            'recreational_drugs': history.recreational_drugs,
            'updated_at': history.updated_at.isoformat()
        }
        
        return JsonResponse({
            'success': True,
            'history': history_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@csrf_exempt
def patient_history_update(request, patient_id):
    """更新患者病史API"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # 獲取或創建病史記錄
            history, created = HistoryData.objects.get_or_create(
                patient_id=patient_id,
                defaults={
                    'medical_history': data.get('medical_history', ''),
                    'family_history': data.get('family_history', ''),
                    'social_history': data.get('social_history', ''),
                    'tobacco': data.get('tobacco', ''),
                    'tobacco_details': data.get('tobacco_details', ''),
                    'alcohol': data.get('alcohol', ''),
                    'alcohol_details': data.get('alcohol_details', ''),
                    'exercise': data.get('exercise', ''),
                    'diet': data.get('diet', ''),
                    'gravida': data.get('gravida'),
                    'para': data.get('para'),
                    'abortions': data.get('abortions'),
                    'miscarriages': data.get('miscarriages'),
                    'coffee_consumption': data.get('coffee_consumption', ''),
                    'recreational_drugs': data.get('recreational_drugs', ''),
                    'created_by': request.user
                }
            )
            
            if not created:
                # 更新現有記錄
                for field in ['medical_history', 'family_history', 'social_history', 'tobacco', 
                             'tobacco_details', 'alcohol', 'alcohol_details', 'exercise', 'diet',
                             'gravida', 'para', 'abortions', 'miscarriages', 'coffee_consumption', 
                             'recreational_drugs']:
                    if field in data:
                        setattr(history, field, data[field])
                history.updated_by = request.user
                history.save()
            
            return JsonResponse({
                'success': True,
                'message': '病史記錄已成功更新',
                'created': created
            })
            
        except Patient.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': '患者不存在'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': '僅支援 POST 請求'
    }, status=405)


@login_required
@csrf_exempt
def patient_employer_create(request, patient_id):
    """創建患者雇主信息API"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # 驗證必填字段
            required_fields = ['employer_name']
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({
                        'success': False,
                        'error': f'必填字段 {field} 不能為空'
                    }, status=400)
            
            patient = Patient.objects.get(id=patient_id)
            
            # 如果設為當前雇主，將其他雇主設為非當前
            if data.get('is_current_employer', False):
                EmployerData.objects.filter(
                    patient=patient,
                    is_current_employer=True
                ).update(is_current_employer=False)
            
            employer = EmployerData.objects.create(
                patient=patient,
                employer_name=data['employer_name'],
                employer_address=data.get('employer_address', ''),
                employer_city=data.get('employer_city', ''),
                employer_state=data.get('employer_state', ''),
                employer_postal_code=data.get('employer_postal_code', ''),
                employer_country=data.get('employer_country', ''),
                employer_phone=data.get('employer_phone', ''),
                employer_fax=data.get('employer_fax', ''),
                employer_email=data.get('employer_email', ''),
                position=data.get('position', ''),
                department=data.get('department', ''),
                employment_start_date=data.get('employment_start_date'),
                employment_end_date=data.get('employment_end_date'),
                contact_person=data.get('contact_person', ''),
                contact_phone=data.get('contact_phone', ''),
                is_current_employer=data.get('is_current_employer', True),
                created_by=request.user
            )
            
            return JsonResponse({
                'success': True,
                'employer': {
                    'id': str(employer.id),
                    'employer_name': employer.employer_name,
                    'position': employer.position,
                    'is_current_employer': employer.is_current_employer
                }
            })
            
        except Patient.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': '患者不存在'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': '僅支援 POST 請求'
    }, status=405)


@login_required
def patient_employer_list(request, patient_id):
    """獲取患者雇主信息列表API"""
    try:
        employers = EmployerData.objects.filter(patient_id=patient_id, is_active=True)
        
        employer_data = []
        for employer in employers:
            employer_data.append({
                'id': str(employer.id),
                'employer_name': employer.employer_name,
                'employer_address': employer.employer_address,
                'employer_phone': employer.employer_phone,
                'position': employer.position,
                'department': employer.department,
                'employment_start_date': str(employer.employment_start_date) if employer.employment_start_date else None,
                'employment_end_date': str(employer.employment_end_date) if employer.employment_end_date else None,
                'contact_person': employer.contact_person,
                'contact_phone': employer.contact_phone,
                'is_current_employer': employer.is_current_employer,
            })
        
        return JsonResponse({
            'success': True,
            'employers': employer_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@csrf_exempt
def patient_duplicate_check(request):
    """重複患者檢測API"""
    if request.method == 'POST':
        try:
            from .services import EnhancedPatientService
            data = json.loads(request.body)
            
            duplicates = EnhancedPatientService.detect_duplicate_patients(data)
            
            duplicate_data = []
            for duplicate in duplicates:
                duplicate_data.append({
                    'id': str(duplicate.id),
                    'full_name': duplicate.full_name,
                    'date_of_birth': str(duplicate.date_of_birth),
                    'medical_record_number': duplicate.medical_record_number,
                    'phone_mobile': duplicate.phone_mobile,
                    'similarity_score': 85  # 這裡可以實現更複雜的相似度算法
                })
            
            return JsonResponse({
                'success': True,
                'duplicates': duplicate_data,
                'has_duplicates': len(duplicate_data) > 0
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'error': '僅支援 POST 請求'
    }, status=405)
