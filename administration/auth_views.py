"""
權限管理視圖
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import models
from django_filters.rest_framework import DjangoFilterBackend

from .auth_models import Role, UserRole, SessionLog, LoginAttempt, APIKey, TwoFactorAuth
from .auth_serializers import (
    RoleSerializer, UserRoleSerializer, SessionLogSerializer, 
    LoginAttemptSerializer, APIKeySerializer, TwoFactorAuthSerializer,
    UserPermissionSerializer
)


class RoleViewSet(viewsets.ModelViewSet):
    """角色管理視圖集"""
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['name', 'is_active']
    
    def get_queryset(self):
        """只有管理員才能查看所有角色"""
        if self.request.user.is_superuser:
            return Role.objects.all()
        else:
            # 一般用戶只能查看自己的角色
            user_roles = UserRole.objects.filter(
                user=self.request.user, 
                is_active=True
            ).values_list('role', flat=True)
            return Role.objects.filter(id__in=user_roles)
    
    @action(detail=False, methods=['get'])
    def available_roles(self, request):
        """獲取可用的角色列表"""
        roles = Role.objects.filter(is_active=True)
        serializer = self.get_serializer(roles, many=True)
        return Response(serializer.data)


class UserRoleViewSet(viewsets.ModelViewSet):
    """用戶角色管理視圖集"""
    queryset = UserRole.objects.all()
    serializer_class = UserRoleSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user', 'role', 'is_active']
    
    def get_queryset(self):
        """根據用戶權限過濾"""
        if self.request.user.is_superuser:
            return UserRole.objects.all().select_related('user', 'role')
        else:
            # 一般用戶只能查看自己的角色
            return UserRole.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """創建用戶角色時設置assigned_by"""
        serializer.save(assigned_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_roles(self, request):
        """獲取當前用戶的角色"""
        user_roles = UserRole.objects.filter(
            user=request.user, 
            is_active=True
        ).filter(
            valid_from__lte=timezone.now()
        ).filter(
            models.Q(valid_until__isnull=True) | 
            models.Q(valid_until__gt=timezone.now())
        )
        
        serializer = self.get_serializer(user_roles, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """停用用戶角色"""
        user_role = self.get_object()
        user_role.is_active = False
        user_role.valid_until = timezone.now()
        user_role.save()
        
        return Response({'status': 'role deactivated'})
    
    def get_serializer_class(self):
        """根據操作類型選擇序列化器"""
        if self.action == 'create':
            from .auth_serializers import UserRoleCreateSerializer
            return UserRoleCreateSerializer
        elif self.action == 'my_roles':
            from .auth_serializers import SimpleUserRoleSerializer
            return SimpleUserRoleSerializer
        return UserRoleSerializer


class SessionLogViewSet(viewsets.ReadOnlyModelViewSet):
    """會話日誌視圖集（只讀）"""
    queryset = SessionLog.objects.all()
    serializer_class = SessionLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user', 'status', 'is_suspicious']
    ordering = ['-login_time']
    
    def get_queryset(self):
        """用戶只能查看自己的會話日誌"""
        if self.request.user.is_superuser:
            return SessionLog.objects.all()
        else:
            return SessionLog.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def active_sessions(self, request):
        """獲取活躍會話"""
        active_sessions = self.get_queryset().filter(status='active')
        serializer = self.get_serializer(active_sessions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def suspicious_activities(self, request):
        """可疑活動（僅管理員）"""
        if not request.user.is_superuser:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        suspicious = SessionLog.objects.filter(is_suspicious=True)
        serializer = self.get_serializer(suspicious, many=True)
        return Response(serializer.data)


class LoginAttemptViewSet(viewsets.ReadOnlyModelViewSet):
    """登入嘗試視圖集（只讀）"""
    queryset = LoginAttempt.objects.all()
    serializer_class = LoginAttemptSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['username', 'result', 'ip_address']
    ordering = ['-attempt_time']
    
    def get_queryset(self):
        """只有管理員才能查看登入嘗試"""
        if not self.request.user.is_superuser:
            return LoginAttempt.objects.filter(username=self.request.user.username)
        return LoginAttempt.objects.all()
    
    @action(detail=False, methods=['get'])
    def failed_attempts(self, request):
        """失敗的登入嘗試"""
        failed = self.get_queryset().exclude(result='success')
        serializer = self.get_serializer(failed, many=True)
        return Response(serializer.data)


class APIKeyViewSet(viewsets.ModelViewSet):
    """API金鑰管理視圖集"""
    queryset = APIKey.objects.all()
    serializer_class = APIKeySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user', 'is_active']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """用戶只能管理自己的API金鑰"""
        if self.request.user.is_superuser:
            return APIKey.objects.all()
        else:
            return APIKey.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """創建API金鑰時設置用戶"""
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def regenerate(self, request, pk=None):
        """重新生成API金鑰"""
        api_key = self.get_object()
        
        # 生成新的金鑰
        import secrets
        api_key.key = secrets.token_urlsafe(48)
        api_key.save()
        
        serializer = self.get_serializer(api_key)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """撤銷API金鑰"""
        api_key = self.get_object()
        api_key.is_active = False
        api_key.save()
        
        return Response({'status': 'api key revoked'})


class TwoFactorAuthViewSet(viewsets.ModelViewSet):
    """雙因子認證管理視圖集"""
    queryset = TwoFactorAuth.objects.all()
    serializer_class = TwoFactorAuthSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """用戶只能管理自己的雙因子認證"""
        return TwoFactorAuth.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def setup(self, request):
        """設置雙因子認證"""
        import pyotp
        import qrcode
        from io import BytesIO
        import base64
        
        user = request.user
        
        # 生成密鑰
        secret = pyotp.random_base32()
        
        # 創建或更新2FA設定
        two_factor, created = TwoFactorAuth.objects.get_or_create(
            user=user,
            defaults={'secret_key': secret}
        )
        
        if not created:
            two_factor.secret_key = secret
            two_factor.save()
        
        # 生成QR碼
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user.email,
            issuer_name="MedicalCare System"
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        qr_image = base64.b64encode(buffer.getvalue()).decode()
        
        return Response({
            'secret': secret,
            'qr_code': f"data:image/png;base64,{qr_image}",
            'backup_codes': self._generate_backup_codes()
        })
    
    @action(detail=False, methods=['post'])
    def verify(self, request):
        """驗證並啟用雙因子認證"""
        import pyotp
        
        token = request.data.get('token')
        if not token:
            return Response(
                {'error': 'Token is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            two_factor = TwoFactorAuth.objects.get(user=request.user)
        except TwoFactorAuth.DoesNotExist:
            return Response(
                {'error': '2FA not set up'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        totp = pyotp.TOTP(two_factor.secret_key)
        
        if totp.verify(token):
            two_factor.is_enabled = True
            two_factor.enabled_at = timezone.now()
            two_factor.backup_codes = self._generate_backup_codes()
            two_factor.save()
            
            return Response({'status': '2FA enabled successfully'})
        else:
            return Response(
                {'error': 'Invalid token'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def disable(self, request):
        """停用雙因子認證"""
        token = request.data.get('token')
        password = request.data.get('password')
        
        if not request.user.check_password(password):
            return Response(
                {'error': 'Invalid password'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            two_factor = TwoFactorAuth.objects.get(user=request.user)
            two_factor.is_enabled = False
            two_factor.secret_key = ''
            two_factor.backup_codes = []
            two_factor.save()
            
            return Response({'status': '2FA disabled successfully'})
        except TwoFactorAuth.DoesNotExist:
            return Response(
                {'error': '2FA not found'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _generate_backup_codes(self):
        """生成備用代碼"""
        import secrets
        return [secrets.token_hex(4).upper() for _ in range(10)]


class UserPermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """用戶權限查看視圖集"""
    queryset = User.objects.all()
    serializer_class = UserPermissionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """只能查看自己的權限"""
        return User.objects.filter(id=self.request.user.id)
    
    @action(detail=False, methods=['get'])
    def my_permissions(self, request):
        """獲取當前用戶的詳細權限"""
        user = request.user
        
        # 獲取用戶角色
        user_roles = UserRole.objects.filter(
            user=user, 
            is_active=True
        ).select_related('role')
        
        # 計算權限
        permissions = self._calculate_user_permissions(user, user_roles)
        
        return Response(permissions)
    
    def _calculate_user_permissions(self, user, user_roles):
        """計算用戶的完整權限"""
        permissions = {
            'is_superuser': user.is_superuser,
            'is_staff': user.is_staff,
            'roles': [],
            'modules': {},
            'data_access_level': 'none',
            'can_access': {}
        }
        
        # 處理角色權限
        highest_access_level = 'none'
        access_levels = ['none', 'own', 'department', 'facility', 'all']
        
        for user_role in user_roles:
            role = user_role.role
            permissions['roles'].append({
                'name': role.name,
                'display_name': role.display_name,
                'valid_until': user_role.valid_until
            })
            
            # 合併模組權限
            for field_name in ['can_access_patients', 'can_access_appointments', 
                              'can_access_medical_records', 'can_access_billing',
                              'can_access_pharmacy', 'can_access_laboratory',
                              'can_access_reports', 'can_access_administration']:
                current_access = permissions['modules'].get(field_name, False)
                role_access = getattr(role, field_name, False)
                permissions['modules'][field_name] = current_access or role_access
            
            # 確定最高資料存取級別
            role_level = role.data_access_level
            if access_levels.index(role_level) > access_levels.index(highest_access_level):
                highest_access_level = role_level
        
        permissions['data_access_level'] = highest_access_level
        
        return permissions
