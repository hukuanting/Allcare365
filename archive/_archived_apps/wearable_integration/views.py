"""
Healthcare 365 穿戴式裝置實時數據API
處理實時生命體徵數據和風險分析
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
import logging

from .models import (
    WearableDevice, PatientWearableAssignment, 
    RealTimeVitalSigns, RealTimeRiskAnalysis, RealTimeAlert,
    DataStreamSession
)
from .realtime_risk_engine import RealTimeRiskEngine
from .unified_data_architecture import UnifiedDataManager, RealTimeRiskAnalyzer
from patients.models import Patient
from django.db import models

logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()


@api_view(['POST'])
@permission_classes([AllowAny])
def receive_vital_signs(request):
    """接收穿戴式裝置的實時生命體徵數據"""
    try:
        data = request.data
        
        # 驗證必要欄位
        required_fields = ['device_id', 'patient_mrn', 'timestamp']
        for field in required_fields:
            if field not in data:
                return Response({
                    'success': False,
                    'error': f'缺少必要欄位: {field}'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # 使用統一數據管理器處理數據
        data_manager = UnifiedDataManager()
        save_result = data_manager.save_wearable_data_to_vitals(
            patient_mrn=data['patient_mrn'],
            device_id=data['device_id'],
            wearable_data=data
        )
        
        if not save_result['success']:
            return Response({
                'success': False,
                'error': save_result['error']
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # 獲取保存的記錄
        patient = Patient.objects.get(id=save_result['patient_id'])
        vital_signs = RealTimeVitalSigns.objects.get(id=save_result['vital_record_id'])
        device = WearableDevice.objects.get(device_id=data['device_id'])
        
        # 更新設備最後連線時間
        device.last_seen = timezone.now()
        device.status = 'active'
        device.save(update_fields=['last_seen', 'status'])
        
        # 執行實時風險分析 - 使用新的統一分析器
        risk_analyzer = RealTimeRiskAnalyzer()
        risk_results = risk_analyzer.analyze_patient_risk(patient.id, 'basic_vitals')

        # 保存風險分析結果到數據庫
        if risk_results and 'error' not in risk_results:
            RealTimeRiskAnalysis.objects.create(
                patient=patient,
                device=device,
                vital_signs=vital_signs,
                risk_type=risk_results.get('risk_algorithm', 'basic_vitals'),
                risk_level=risk_results.get('risk_level', 'unknown'),
                risk_score=risk_results.get('risk_score', 0.0),
                risk_percentage=risk_results.get('risk_percentage', 0.0),
                contributing_factors=risk_results.get('data_used', {}),
                recommendations=risk_results.get('recommendations', []),
                # alert_triggered=... # 根據需要設置
                # trend_direction=... # 根據需要設置
                # confidence_score=... # 根據需要設置
            )

        # 發送實時數據到前端
        real_time_data = {
            'type': 'vital_signs_update',
            'patient_id': patient.id,
            'patient_name': patient.full_name,
            'device_id': device.device_id,
            'timestamp': vital_signs.timestamp.isoformat(),
            'vital_signs': {
                'heart_rate': vital_signs.heart_rate,
                'systolic_bp': vital_signs.systolic_bp,
                'diastolic_bp': vital_signs.diastolic_bp,
                'oxygen_saturation': vital_signs.oxygen_saturation,
                'respiration_rate': vital_signs.respiration_rate,
                'skin_temperature': vital_signs.skin_temperature,
                'posture': vital_signs.posture
            },
            'risk_analysis': []
        }
        
        # 添加風險分析結果
        if risk_results and 'error' not in risk_results:
            real_time_data['risk_analysis'].append({
                'risk_type': 'Basic Vitals',
                'risk_level': risk_results.get('risk_level', 'unknown'),
                'risk_percentage': risk_results.get('risk_percentage', 0),
                'data_completeness': risk_results.get('data_completeness', 0),
                'data_sources': risk_results.get('data_sources', {})
            })
        
        # 廣播到WebSocket
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"patient_{patient.id}",
                {
                    'type': 'send_real_time_data',
                    'data': real_time_data
                }
            )
        
        return Response({
            'success': True,
            'message': '數據接收成功',
            'save_result': save_result,
            'vital_signs_id': vital_signs.id,
            'risk_analysis': risk_results if 'error' not in risk_results else None,
            'risk_analysis_error': risk_results.get('error') if 'error' in risk_results else None
        })
        
    except Exception as e:
        logger.error(f"接收生命體徵數據失敗: {str(e)}")
        return Response({
            'success': False,
            'error': f'處理失敗: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_real_time_data(request, patient_mrn):
    """獲取患者的最新實時數據"""
    try:
        patient = Patient.objects.get(medical_record_number=patient_mrn)
        
        # 獲取最新的生命體徵數據
        latest_vitals = RealTimeVitalSigns.objects.filter(
            patient=patient
        ).order_by('-timestamp').first()
        
        # 獲取最新的風險分析
        latest_risks = RealTimeRiskAnalysis.objects.filter(
            patient=patient
        ).order_by('-analysis_timestamp')[:5]
        
        # 獲取活躍警報
        active_alerts = RealTimeAlert.objects.filter(
            patient=patient,
            status='active'
        ).order_by('-triggered_at')[:10]
        
        response_data = {
            'patient_id': patient.id,
            'patient_name': patient.full_name,
            'last_update': latest_vitals.timestamp.isoformat() if latest_vitals else None,
            'vital_signs': None,
            'risk_analysis': [],
            'active_alerts': []
        }
        
        if latest_vitals:
            response_data['vital_signs'] = {
                'timestamp': latest_vitals.timestamp.isoformat(),
                'heart_rate': latest_vitals.heart_rate,
                'systolic_bp': latest_vitals.systolic_bp,
                'diastolic_bp': latest_vitals.diastolic_bp,
                'oxygen_saturation': latest_vitals.oxygen_saturation,
                'respiration_rate': latest_vitals.respiration_rate,
                'skin_temperature': latest_vitals.skin_temperature,
                'posture': latest_vitals.posture,
                'device_id': latest_vitals.device.device_id
            }
        
        for risk in latest_risks:
            response_data['risk_analysis'].append({
                'risk_type': risk.get_risk_type_display(),
                'risk_level': risk.get_risk_level_display(),
                'risk_percentage': risk.risk_percentage,
                'timestamp': risk.analysis_timestamp.isoformat(),
                'contributing_factors': risk.contributing_factors,
                'recommendations': risk.recommendations
            })
        
        for alert in active_alerts:
            response_data['active_alerts'].append({
                'id': alert.id,
                'title': alert.title,
                'message': alert.message,
                'priority': alert.get_priority_display(),
                'triggered_at': alert.triggered_at.isoformat()
            })
        
        return Response(response_data)
        
    except Patient.DoesNotExist:
        return Response({
            'error': '找不到患者'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"獲取實時數據失敗: {str(e)}")
        return Response({
            'error': f'獲取數據失敗: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_unified_risk_analysis(request, patient_mrn):
    """獲取患者的統一風險分析 - 基於最新數據"""
    try:
        patient = Patient.objects.get(medical_record_number=patient_mrn)
        algorithm = request.GET.get('algorithm', 'basic_vitals')

        risk_analyzer = RealTimeRiskAnalyzer()
        analysis_result = risk_analyzer.analyze_patient_risk(patient.id, algorithm)        
        if 'error' in analysis_result:
            return Response({
                'error': analysis_result['error']
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response(analysis_result)
        
    except Exception as e:
        logger.error(f"統一風險分析失敗: {str(e)}")
        return Response({
            'error': f'風險分析失敗: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_patient_data_summary(request, patient_mrn):
    """獲取患者的統一數據摘要"""
    try:
        data_manager = UnifiedDataManager()
        
        # 獲取患者基本信息
        patient = Patient.objects.get(medical_record_number=patient_mrn)
        
        # 獲取綜合風險分析所需的欄位
        comprehensive_fields = ['height', 'weight', 'hba1c', 'egfr', 'blood_pressure', 'heart_rate']
        patient_data = data_manager.get_patient_latest_data(patient.id, comprehensive_fields)
        
        # 獲取最新的實時數據
        latest_realtime = RealTimeVitalSigns.objects.filter(
            patient=patient
        ).order_by('-timestamp').first()
        
        summary = {
            'patient': {
                'id': patient.id,
                'name': patient.full_name,
                'mrn': patient.medical_record_number
            },
            'latest_data': patient_data['data'],
            'data_sources': patient_data['sources'],
            'data_completeness': patient_data['completeness'],
            'latest_realtime_timestamp': latest_realtime.timestamp if latest_realtime else None,
            'has_active_wearable': latest_realtime is not None and (
                timezone.now() - latest_realtime.timestamp
            ).total_seconds() < 300  # 5分鐘內有數據
        }
        
        return Response(summary)
        
    except Patient.DoesNotExist:
        return Response({
            'error': '患者不存在'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"獲取患者數據摘要失敗: {str(e)}")
        return Response({
            'error': f'獲取摘要失敗: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_uscdi_data_classes(request):
    """獲取 USCDI v6 支援的數據類別"""
    try:
        from fhir_integration.uscdi_v6_mappings import USCDIv6Mapper
        
        mapper = USCDIv6Mapper()
        data_classes = mapper.USCDI_V6_DATA_CLASSES
        
        return Response({
            'uscdi_version': 'v6',
            'data_classes': data_classes,
            'wearable_supported_classes': [
                'vital_signs',
                'demographics', 
                'functional_status'
            ]
        })
        
    except Exception as e:
        logger.error(f"獲取 USCDI 數據類別失敗: {str(e)}")
        return Response({
            'error': f'獲取數據類別失敗: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)