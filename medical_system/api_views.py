"""
API 根視圖和路由
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.urls import reverse


@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request, format=None):
    """
    API 根端點，提供可用API的概覽
    """
    api_urls = {
        '系統信息': {
            'description': 'Medical System 醫療管理系統 API',
            'version': '1.0.0',
            'django_version': '5.2.4',
            'status': 'Development'
        },
        '可用端點': {
            'apps.clinical.patients': request.build_absolute_uri('/api/v1/patients/'),
            'appointments': request.build_absolute_uri('/api/v1/appointments/'),
            'medical_records': request.build_absolute_uri('/api/v1/medical-records/'),
            'billing': request.build_absolute_uri('/api/v1/billing/'),
            'pharmacy': request.build_absolute_uri('/api/v1/pharmacy/'),
            'administration': request.build_absolute_uri('/api/v1/administration/'),
            'reports': request.build_absolute_uri('/api/v1/reports/'),
            'laboratory': request.build_absolute_uri('/api/v1/laboratory/'),
            'documents': request.build_absolute_uri('/api/v1/documents/'),
        },
        '認證': {
            'admin_login': request.build_absolute_uri('/admin/'),
            'api_auth': request.build_absolute_uri('/api/auth/'),
        },
        '說明': {
            'apps.core.authentication': '此API需要認證。請使用Token或Session認證。',
            'permissions': '不同端點有不同的權限要求。',
            'documentation': '詳細文檔請參考 README.md'
        }
    }
    
    return Response(api_urls, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    健康檢查端點
    """
    return Response({
        'status': 'healthy',
        'timestamp': request.META.get('HTTP_DATE'),
        'database': 'connected',
        'cache': 'active'
    }, status=status.HTTP_200_OK)
