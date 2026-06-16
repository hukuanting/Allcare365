from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone
from .models import (
    Provider, Facility, Department, UserProfile, AuditLog, SystemSetting
)


class ProviderSerializer(serializers.ModelSerializer):
    """醫療提供者序列化器"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    specializations_display = serializers.CharField(source='get_specializations_display', read_only=True)
    
    class Meta:
        model = Provider
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def validate_license_number(self, value):
        """驗證執照號碼"""
        if value and len(value) < 5:
            raise serializers.ValidationError("執照號碼長度不能少於5位")
        return value
    
    def validate_phone(self, value):
        """驗證電話號碼"""
        if value and not value.replace('-', '').replace('(', '').replace(')', '').replace(' ', '').isdigit():
            raise serializers.ValidationError("電話號碼格式無效")
        return value


class FacilitySerializer(serializers.ModelSerializer):
    """醫療機構序列化器"""
    departments_count = serializers.SerializerMethodField()
    providers_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Facility
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def get_departments_count(self, obj):
        """獲取部門數量"""
        return obj.departments.count()
    
    def get_providers_count(self, obj):
        """獲取醫療提供者數量"""
        return obj.providers.count()
    
    def validate_phone(self, value):
        """驗證電話號碼"""
        if value and not value.replace('-', '').replace('(', '').replace(')', '').replace(' ', '').isdigit():
            raise serializers.ValidationError("電話號碼格式無效")
        return value


class DepartmentSerializer(serializers.ModelSerializer):
    """部門序列化器"""
    facility_name = serializers.CharField(source='facility.name', read_only=True)
    head_name = serializers.CharField(source='head.get_full_name', read_only=True)
    providers_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Department
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def get_providers_count(self, obj):
        """獲取部門醫療提供者數量"""
        return obj.providers.count()


class UserProfileSerializer(serializers.ModelSerializer):
    """用戶資料序列化器"""
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    is_active = serializers.BooleanField(source='user.is_active', read_only=True)
    last_login = serializers.DateTimeField(source='user.last_login', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class UserSerializer(serializers.ModelSerializer):
    """用戶序列化器"""
    profile = UserProfileSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_active', 'is_staff', 'is_superuser', 'last_login',
            'date_joined', 'profile', 'full_name'
        ]
        read_only_fields = ('last_login', 'date_joined')
    
    def get_full_name(self, obj):
        """獲取完整姓名"""
        return obj.get_full_name() or obj.username
    
    def validate_email(self, value):
        """驗證電子郵件"""
        if value and User.objects.filter(email=value).exclude(id=self.instance.id if self.instance else None).exists():
            raise serializers.ValidationError("此電子郵件已被使用")
        return value


class AuditLogSerializer(serializers.ModelSerializer):
    """審計日誌序列化器"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = '__all__'
        read_only_fields = ('created_at',)


class SystemSettingSerializer(serializers.ModelSerializer):
    """系統設定序列化器"""
    
    class Meta:
        model = SystemSetting
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def validate_key(self, value):
        """驗證設定鍵"""
        if value and not value.replace('_', '').replace('-', '').isalnum():
            raise serializers.ValidationError("設定鍵只能包含字母、數字、底線和連字符")
        return value


class ProviderDetailSerializer(serializers.ModelSerializer):
    """醫療提供者詳細序列化器"""
    facility = FacilitySerializer(read_only=True)
    departments = DepartmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Provider
        fields = '__all__'


class FacilityDetailSerializer(serializers.ModelSerializer):
    """醫療機構詳細序列化器"""
    departments = DepartmentSerializer(many=True, read_only=True)
    providers = ProviderSerializer(many=True, read_only=True)
    
    class Meta:
        model = Facility
        fields = '__all__'


class DepartmentDetailSerializer(serializers.ModelSerializer):
    """部門詳細序列化器"""
    facility = FacilitySerializer(read_only=True)
    head = ProviderSerializer(read_only=True)
    providers = ProviderSerializer(many=True, read_only=True)
    
    class Meta:
        model = Department
        fields = '__all__'


class SystemStatsSerializer(serializers.Serializer):
    """系統統計序列化器"""
    total_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    total_providers = serializers.IntegerField()
    active_providers = serializers.IntegerField()
    total_facilities = serializers.IntegerField()
    active_facilities = serializers.IntegerField()
    total_departments = serializers.IntegerField()
    recent_logins = serializers.ListField()
    recent_audit_logs = serializers.ListField()
    user_activity = serializers.ListField()
    provider_specializations = serializers.ListField()
    facility_types = serializers.ListField()


class DashboardStatsSerializer(serializers.Serializer):
    """儀表板統計序列化器"""
    users_overview = serializers.DictField()
    providers_overview = serializers.DictField()
    facilities_overview = serializers.DictField()
    recent_activities = serializers.ListField()
    system_health = serializers.DictField()
    audit_summary = serializers.DictField()


class UserActivitySerializer(serializers.Serializer):
    """用戶活動序列化器"""
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    full_name = serializers.CharField()
    last_login = serializers.DateTimeField()
    login_count = serializers.IntegerField()
    recent_actions = serializers.ListField()


class ProviderStatsSerializer(serializers.Serializer):
    """醫療提供者統計序列化器"""
    provider_id = serializers.IntegerField()
    provider_name = serializers.CharField()
    specializations = serializers.ListField()
    facility_name = serializers.CharField()
    total_appointments = serializers.IntegerField()
    total_patients = serializers.IntegerField()
    recent_appointments = serializers.ListField()
    rating = serializers.DecimalField(max_digits=3, decimal_places=2, required=False)


class FacilityStatsSerializer(serializers.Serializer):
    """醫療機構統計序列化器"""
    facility_id = serializers.IntegerField()
    facility_name = serializers.CharField()
    facility_type = serializers.CharField()
    total_departments = serializers.IntegerField()
    total_providers = serializers.IntegerField()
    total_patients = serializers.IntegerField()
    total_appointments = serializers.IntegerField()
    utilization_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    recent_activities = serializers.ListField()
