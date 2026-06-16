"""
權限管理序列化器
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from .auth_models import Role, UserRole, SessionLog, LoginAttempt, APIKey, TwoFactorAuth


class RoleSerializer(serializers.ModelSerializer):
    """角色序列化器"""
    
    class Meta:
        model = Role
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class UserRoleSerializer(serializers.ModelSerializer):
    """用戶角色序列化器"""
    role_name = serializers.CharField(source='role.display_name', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.get_full_name', read_only=True)
    is_valid_now = serializers.SerializerMethodField()
    
    # 嵌套序列化器以提供完整信息
    role = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    
    class Meta:
        model = UserRole
        fields = '__all__'
        read_only_fields = ('assigned_date',)
    
    def get_role(self, obj):
        """返回角色的詳細信息"""
        return {
            'id': obj.role.id,
            'name': obj.role.name,
            'display_name': obj.role.display_name,
            'description': obj.role.description
        }
    
    def get_user(self, obj):
        """返回用戶的詳細信息"""
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            'full_name': obj.user.get_full_name(),
            'email': obj.user.email
        }
    
    def get_is_valid_now(self, obj):
        """檢查角色是否當前有效"""
        return obj.is_valid()
    
    def validate(self, data):
        """驗證用戶角色"""
        if data.get('valid_until') and data.get('valid_from'):
            if data['valid_until'] <= data['valid_from']:
                raise serializers.ValidationError("結束時間必須晚於開始時間")
        return data


class SessionLogSerializer(serializers.ModelSerializer):
    """會話日誌序列化器"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = SessionLog
        fields = '__all__'
    
    def get_duration(self, obj):
        """計算會話持續時間"""
        if obj.logout_time:
            duration = obj.logout_time - obj.login_time
            return str(duration)
        return None


class LoginAttemptSerializer(serializers.ModelSerializer):
    """登入嘗試序列化器"""
    result_display = serializers.CharField(source='get_result_display', read_only=True)
    
    class Meta:
        model = LoginAttempt
        fields = '__all__'


class APIKeySerializer(serializers.ModelSerializer):
    """API金鑰序列化器"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = APIKey
        fields = '__all__'
        read_only_fields = ('key', 'created_at', 'last_used', 'usage_count', 'user')
    
    def get_is_expired(self, obj):
        """檢查API金鑰是否過期"""
        if obj.expires_at:
            from django.utils import timezone
            return obj.expires_at <= timezone.now()
        return False
    
    def create(self, validated_data):
        """創建API金鑰時生成隨機金鑰"""
        import secrets
        validated_data['key'] = secrets.token_urlsafe(48)
        return super().create(validated_data)


class TwoFactorAuthSerializer(serializers.ModelSerializer):
    """雙因子認證序列化器"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = TwoFactorAuth
        fields = '__all__'
        read_only_fields = ('secret_key', 'backup_codes', 'enabled_at', 'last_used')


class UserPermissionSerializer(serializers.ModelSerializer):
    """用戶權限序列化器"""
    full_name = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    permissions_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'full_name', 'is_active', 
            'is_staff', 'is_superuser', 'last_login', 'date_joined',
            'roles', 'permissions_summary'
        ]
    
    def get_full_name(self, obj):
        """獲取完整姓名"""
        return obj.get_full_name() or obj.username
    
    def get_roles(self, obj):
        """獲取用戶角色"""
        user_roles = UserRole.objects.filter(
            user=obj, 
            is_active=True
        ).select_related('role')
        
        return [
            {
                'name': ur.role.name,
                'display_name': ur.role.display_name,
                'valid_until': ur.valid_until,
                'is_valid': ur.is_valid()
            }
            for ur in user_roles
        ]
    
    def get_permissions_summary(self, obj):
        """獲取權限摘要"""
        if obj.is_superuser:
            return {
                'level': 'superuser',
                'description': '超級用戶 - 完全權限'
            }
        
        user_roles = UserRole.objects.filter(
            user=obj, 
            is_active=True
        ).select_related('role')
        
        if not user_roles.exists():
            return {
                'level': 'no_access',
                'description': '無權限'
            }
        
        # 找到最高權限級別
        access_levels = ['none', 'own', 'department', 'facility', 'all']
        highest_level = 'none'
        
        for user_role in user_roles:
            role_level = user_role.role.data_access_level
            if access_levels.index(role_level) > access_levels.index(highest_level):
                highest_level = role_level
        
        level_descriptions = {
            'none': '無資料存取權限',
            'own': '只能存取自己的資料',
            'department': '可存取部門資料',
            'facility': '可存取機構資料',
            'all': '可存取所有資料'
        }
        
        return {
            'level': highest_level,
            'description': level_descriptions.get(highest_level, '未知權限級別'),
            'roles_count': user_roles.count()
        }


class UserCreateSerializer(serializers.ModelSerializer):
    """用戶創建序列化器"""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    roles = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name', 
            'password', 'password_confirm', 'is_active', 'roles'
        ]
    
    def validate(self, data):
        """驗證密碼"""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("密碼不匹配")
        return data
    
    def validate_password(self, value):
        """驗證密碼強度"""
        if len(value) < 8:
            raise serializers.ValidationError("密碼至少需要8個字符")
        
        if not any(c.isupper() for c in value):
            raise serializers.ValidationError("密碼必須包含至少一個大寫字母")
        
        if not any(c.islower() for c in value):
            raise serializers.ValidationError("密碼必須包含至少一個小寫字母")
        
        if not any(c.isdigit() for c in value):
            raise serializers.ValidationError("密碼必須包含至少一個數字")
        
        return value
    
    def create(self, validated_data):
        """創建用戶並指派角色"""
        roles = validated_data.pop('roles', [])
        validated_data.pop('password_confirm')
        
        user = User.objects.create_user(**validated_data)
        
        # 指派角色
        for role_name in roles:
            try:
                role = Role.objects.get(name=role_name, is_active=True)
                UserRole.objects.create(
                    user=user,
                    role=role,
                    assigned_by=self.context['request'].user
                )
            except Role.DoesNotExist:
                pass  # 忽略不存在的角色
        
        return user


class PasswordChangeSerializer(serializers.Serializer):
    """密碼修改序列化器"""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    new_password_confirm = serializers.CharField(required=True)
    
    def validate_old_password(self, value):
        """驗證舊密碼"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("舊密碼不正確")
        return value
    
    def validate(self, data):
        """驗證新密碼"""
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError("新密碼不匹配")
        return data
    
    def validate_new_password(self, value):
        """驗證新密碼強度"""
        if len(value) < 8:
            raise serializers.ValidationError("密碼至少需要8個字符")
        
        if not any(c.isupper() for c in value):
            raise serializers.ValidationError("密碼必須包含至少一個大寫字母")
        
        if not any(c.islower() for c in value):
            raise serializers.ValidationError("密碼必須包含至少一個小寫字母")
        
        if not any(c.isdigit() for c in value):
            raise serializers.ValidationError("密碼必須包含至少一個數字")
        
        return value
    
    def save(self):
        """保存新密碼"""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class SimpleUserRoleSerializer(serializers.ModelSerializer):
    """簡化的用戶角色序列化器 - 用於my_roles端點"""
    
    class Meta:
        model = UserRole
        fields = ['id', 'user', 'role', 'assigned_date', 'valid_from', 'valid_until', 'is_active']


class UserRoleCreateSerializer(serializers.ModelSerializer):
    """用戶角色創建序列化器"""
    
    class Meta:
        model = UserRole
        fields = ['user', 'role', 'valid_from', 'valid_until', 'is_active']
        
    def validate(self, data):
        """驗證用戶角色"""
        if data.get('valid_until') and data.get('valid_from'):
            if data['valid_until'] <= data['valid_from']:
                raise serializers.ValidationError("結束時間必須晚於開始時間")
        return data
