from django.shortcuts import render
from django.contrib.auth.models import User
from django.db.models import Q, Count, F, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from .models import (
    Provider, Facility, Department, UserProfile, AuditLog, SystemSetting
)
from .serializers import (
    ProviderSerializer, ProviderDetailSerializer, FacilitySerializer, FacilityDetailSerializer,
    DepartmentSerializer, DepartmentDetailSerializer, UserProfileSerializer, UserSerializer,
    AuditLogSerializer, SystemSettingSerializer, SystemStatsSerializer,
    DashboardStatsSerializer, UserActivitySerializer, ProviderStatsSerializer,
    FacilityStatsSerializer
)


class ProviderViewSet(viewsets.ModelViewSet):
    """醫療提供者視圖集"""
    queryset = Provider.objects.all()
    serializer_class = ProviderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['provider_type', 'primary_specialty', 'is_active', 'is_accepting_patients']
    
    def get_queryset(self):
        return super().get_queryset().select_related('user')
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProviderDetailSerializer
        return ProviderSerializer
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """活躍的醫療提供者"""
        active_providers = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(active_providers, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_specialization(self, request):
        """按專業分組"""
        specialization = request.query_params.get('specialization')
        if not specialization:
            return Response(
                {'error': '請提供專業類型'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        providers = self.get_queryset().filter(specializations__icontains=specialization)
        serializer = self.get_serializer(providers, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_facility(self, request):
        """按醫療機構查詢"""
        facility_id = request.query_params.get('facility_id')
        if not facility_id:
            return Response(
                {'error': '請提供醫療機構ID'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        providers = self.get_queryset().filter(facility_id=facility_id)
        serializer = self.get_serializer(providers, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """醫療提供者統計"""
        provider = self.get_object()
        
        # 這裡可以添加統計邏輯
        # 例如：預約數量、病患數量、評分等
        
        stats = {
            'provider_id': provider.id,
            'provider_name': provider.get_full_name(),
            'specializations': provider.specializations.split(',') if provider.specializations else [],
            'facility_name': provider.facility.name if provider.facility else None,
            'total_appointments': 0,  # 待實現
            'total_patients': 0,  # 待實現
            'recent_appointments': [],  # 待實現
            'rating': None  # 待實現
        }
        
        serializer = ProviderStatsSerializer(stats)
        return Response(serializer.data)


class FacilityViewSet(viewsets.ModelViewSet):
    """醫療機構視圖集"""
    queryset = Facility.objects.all()
    serializer_class = FacilitySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['facility_type', 'is_active']
    
    def get_queryset(self):
        return super().get_queryset().prefetch_related('departments')
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return FacilityDetailSerializer
        return FacilitySerializer
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """活躍的醫療機構"""
        active_facilities = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(active_facilities, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """按機構類型查詢"""
        facility_type = request.query_params.get('type')
        if not facility_type:
            return Response(
                {'error': '請提供機構類型'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        facilities = self.get_queryset().filter(facility_type=facility_type)
        serializer = self.get_serializer(facilities, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """醫療機構統計"""
        facility = self.get_object()
        
        # 統計邏輯
        total_departments = facility.departments.count()
        total_providers = facility.providers.count()
        
        stats = {
            'facility_id': facility.id,
            'facility_name': facility.name,
            'facility_type': facility.facility_type,
            'total_departments': total_departments,
            'total_providers': total_providers,
            'total_patients': 0,  # 待實現
            'total_appointments': 0,  # 待實現
            'utilization_rate': 0.0,  # 待實現
            'recent_activities': []  # 待實現
        }
        
        serializer = FacilityStatsSerializer(stats)
        return Response(serializer.data)


class DepartmentViewSet(viewsets.ModelViewSet):
    """部門視圖集"""
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['facility', 'is_active']
    
    def get_queryset(self):
        return super().get_queryset().select_related('facility', 'head').prefetch_related('providers')
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return DepartmentDetailSerializer
        return DepartmentSerializer
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """活躍的部門"""
        active_departments = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(active_departments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_facility(self, request):
        """按醫療機構查詢部門"""
        facility_id = request.query_params.get('facility_id')
        if not facility_id:
            return Response(
                {'error': '請提供醫療機構ID'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        departments = self.get_queryset().filter(facility_id=facility_id)
        serializer = self.get_serializer(departments, many=True)
        return Response(serializer.data)


class UserProfileViewSet(viewsets.ModelViewSet):
    """用戶資料視圖集"""
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['role', 'is_active']
    
    def get_queryset(self):
        return super().get_queryset().select_related('user')
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """當前用戶的資料"""
        try:
            profile = request.user.profile
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        except UserProfile.DoesNotExist:
            return Response(
                {'error': '用戶資料不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def by_role(self, request):
        """按角色查詢用戶"""
        role = request.query_params.get('role')
        if not role:
            return Response(
                {'error': '請提供角色'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        profiles = self.get_queryset().filter(role=role)
        serializer = self.get_serializer(profiles, many=True)
        return Response(serializer.data)


class UserViewSet(viewsets.ModelViewSet):
    """用戶視圖集"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'is_staff', 'is_superuser']
    
    def get_queryset(self):
        return super().get_queryset().select_related('profile')
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """活躍用戶"""
        active_users = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(active_users, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recent_logins(self, request):
        """最近登入用戶"""
        recent_users = self.get_queryset().filter(
            last_login__isnull=False
        ).order_by('-last_login')[:20]
        
        serializer = self.get_serializer(recent_users, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def activity(self, request, pk=None):
        """用戶活動記錄"""
        user = self.get_object()
        
        # 獲取用戶的審計日誌
        recent_actions = AuditLog.objects.filter(user=user).order_by('-created_at')[:10]
        
        activity_data = {
            'user_id': user.id,
            'username': user.username,
            'full_name': user.get_full_name(),
            'last_login': user.last_login,
            'login_count': AuditLog.objects.filter(user=user, action='login').count(),
            'recent_actions': AuditLogSerializer(recent_actions, many=True).data
        }
        
        serializer = UserActivitySerializer(activity_data)
        return Response(serializer.data)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """審計日誌視圖集"""
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user', 'action', 'object_type']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 日期範圍篩選
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        return queryset.select_related('user').order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """最近的審計日誌"""
        recent_logs = self.get_queryset()[:50]
        serializer = self.get_serializer(recent_logs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_user(self, request):
        """按用戶查詢日誌"""
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response(
                {'error': '請提供用戶ID'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logs = self.get_queryset().filter(user_id=user_id)
        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)


class SystemSettingViewSet(viewsets.ModelViewSet):
    """系統設定視圖集"""
    queryset = SystemSetting.objects.all()
    serializer_class = SystemSettingSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category', 'is_active']
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """按類別查詢設定"""
        category = request.query_params.get('category')
        if not category:
            return Response(
                {'error': '請提供類別'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        configs = self.get_queryset().filter(category=category)
        serializer = self.get_serializer(configs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """活躍的設定"""
        active_configs = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(active_configs, many=True)
        return Response(serializer.data)


class SystemStatsViewSet(viewsets.ViewSet):
    """系統統計視圖集"""
    permission_classes = [IsAdminUser]
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """系統統計總覽"""
        # 用戶統計
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        
        # 醫療提供者統計
        total_providers = Provider.objects.count()
        active_providers = Provider.objects.filter(is_active=True).count()
        
        # 醫療機構統計
        total_facilities = Facility.objects.count()
        active_facilities = Facility.objects.filter(is_active=True).count()
        
        # 部門統計
        total_departments = Department.objects.count()
        
        # 最近登入
        recent_logins = User.objects.filter(
            last_login__isnull=False
        ).order_by('-last_login')[:10]
        recent_logins_data = UserSerializer(recent_logins, many=True).data
        
        # 最近審計日誌
        recent_audit_logs = AuditLog.objects.order_by('-created_at')[:10]
        recent_audit_logs_data = AuditLogSerializer(recent_audit_logs, many=True).data
        
        # 用戶活動統計
        user_activity = []
        for user in User.objects.filter(is_active=True)[:10]:
            activity = {
                'user_id': user.id,
                'username': user.username,
                'full_name': user.get_full_name(),
                'last_login': user.last_login,
                'login_count': AuditLog.objects.filter(user=user, action='login').count()
            }
            user_activity.append(activity)
        
        # 醫療提供者專業統計
        provider_specializations = Provider.objects.values('specializations').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # 醫療機構類型統計
        facility_types = Facility.objects.values('facility_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        data = {
            'total_users': total_users,
            'active_users': active_users,
            'total_providers': total_providers,
            'active_providers': active_providers,
            'total_facilities': total_facilities,
            'active_facilities': active_facilities,
            'total_departments': total_departments,
            'recent_logins': recent_logins_data,
            'recent_audit_logs': recent_audit_logs_data,
            'user_activity': user_activity,
            'provider_specializations': provider_specializations,
            'facility_types': facility_types
        }
        
        serializer = SystemStatsSerializer(data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """儀表板統計"""
        # 用戶總覽
        users_overview = {
            'total': User.objects.count(),
            'active': User.objects.filter(is_active=True).count(),
            'staff': User.objects.filter(is_staff=True).count(),
            'superuser': User.objects.filter(is_superuser=True).count()
        }
        
        # 醫療提供者總覽
        providers_overview = {
            'total': Provider.objects.count(),
            'active': Provider.objects.filter(is_active=True).count(),
            'by_specialization': Provider.objects.values('specializations').annotate(
                count=Count('id')
            ).order_by('-count')[:5]
        }
        
        # 醫療機構總覽
        facilities_overview = {
            'total': Facility.objects.count(),
            'active': Facility.objects.filter(is_active=True).count(),
            'by_type': Facility.objects.values('facility_type').annotate(
                count=Count('id')
            ).order_by('-count')
        }
        
        # 最近活動
        recent_activities = AuditLog.objects.order_by('-created_at')[:20]
        recent_activities_data = AuditLogSerializer(recent_activities, many=True).data
        
        # 系統健康狀況
        system_health = {
            'uptime': '99.9%',  # 待實現
            'cpu_usage': '45%',  # 待實現
            'memory_usage': '67%',  # 待實現
            'disk_usage': '34%',  # 待實現
            'active_sessions': User.objects.filter(is_active=True).count()
        }
        
        # 審計摘要
        audit_summary = {
            'total_logs': AuditLog.objects.count(),
            'today_logs': AuditLog.objects.filter(
                created_at__date=timezone.now().date()
            ).count(),
            'recent_logins': AuditLog.objects.filter(
                action='login',
                created_at__gte=timezone.now() - timedelta(hours=24)
            ).count()
        }
        
        data = {
            'users_overview': users_overview,
            'providers_overview': providers_overview,
            'facilities_overview': facilities_overview,
            'recent_activities': recent_activities_data,
            'system_health': system_health,
            'audit_summary': audit_summary
        }
        
        serializer = DashboardStatsSerializer(data)
        return Response(serializer.data)
