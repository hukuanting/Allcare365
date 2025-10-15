"""
MedicalCare System 權限管理系統
實現角色基礎存取控制 (RBAC)
"""

from django.db import models
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
import uuid


class Role(models.Model):
    """系統角色定義"""
    ROLE_CHOICES = [
        ('superadmin', 'Super Administrator'),
        ('admin', 'Administrator'),
        ('doctor', 'Doctor'),
        ('nurse', 'Nurse'),
        ('nurse_practitioner', 'Nurse Practitioner'),
        ('physician_assistant', 'Physician Assistant'),
        ('receptionist', 'Receptionist'),
        ('billing_staff', 'Billing Staff'),
        ('lab_technician', 'Lab Technician'),
        ('pharmacist', 'Pharmacist'),
        ('patient', 'Patient'),
        ('read_only', 'Read Only User'),
    ]
    
    name = models.CharField(max_length=50, choices=ROLE_CHOICES, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # 權限設定
    permissions = models.ManyToManyField(Permission, blank=True)
    
    # 模組存取權限
    can_access_patients = models.BooleanField(default=False)
    can_access_appointments = models.BooleanField(default=False)
    can_access_medical_records = models.BooleanField(default=False)
    can_access_billing = models.BooleanField(default=False)
    can_access_pharmacy = models.BooleanField(default=False)
    can_access_laboratory = models.BooleanField(default=False)
    can_access_reports = models.BooleanField(default=False)
    can_access_administration = models.BooleanField(default=False)
    
    # 資料權限級別
    DATA_ACCESS_CHOICES = [
        ('none', 'No Access'),
        ('own', 'Own Data Only'),
        ('department', 'Department Data'),
        ('facility', 'Facility Data'),
        ('all', 'All Data'),
    ]
    data_access_level = models.CharField(max_length=20, choices=DATA_ACCESS_CHOICES, default='own')
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'auth_roles'
    
    def __str__(self):
        return self.display_name


class UserRole(models.Model):
    """使用者角色關聯"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_users')
    
    # 指派詳情
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_roles')
    assigned_date = models.DateTimeField(default=timezone.now)
    
    # 有效期
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True)
    
    # 限制條件
    facility_restriction = models.ForeignKey(
        'administration.Facility', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        help_text="限制存取特定醫療機構"
    )
    department_restriction = models.ForeignKey(
        'administration.Department', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        help_text="限制存取特定部門"
    )
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'auth_user_roles'
        unique_together = ['user', 'role', 'facility_restriction']
    
    def __str__(self):
        return f"{self.user.username} - {self.role.display_name}"
    
    def is_valid(self):
        """檢查角色是否仍然有效"""
        now = timezone.now()
        return (
            self.is_active and 
            self.valid_from <= now and 
            (self.valid_until is None or self.valid_until > now)
        )


class PermissionGroup(models.Model):
    """權限群組"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(Permission)
    
    class Meta:
        db_table = 'auth_permission_groups'
    
    def __str__(self):
        return self.name


class DataAccessRule(models.Model):
    """資料存取規則"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # 適用的模型
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    
    # 規則類型
    RULE_TYPE_CHOICES = [
        ('allow', 'Allow'),
        ('deny', 'Deny'),
    ]
    rule_type = models.CharField(max_length=10, choices=RULE_TYPE_CHOICES)
    
    # 條件
    field_name = models.CharField(max_length=100, help_text="模型欄位名稱")
    field_value = models.CharField(max_length=200, help_text="欄位值或變數")
    
    # 適用角色
    roles = models.ManyToManyField(Role)
    
    # 優先級（數字越高優先級越高）
    priority = models.IntegerField(default=0)
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'auth_data_access_rules'
        ordering = ['-priority']
    
    def __str__(self):
        return f"{self.name} ({self.rule_type})"


class SessionLog(models.Model):
    """會話日誌"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='session_logs')
    session_key = models.CharField(max_length=40)
    
    # 登入資訊
    login_time = models.DateTimeField(default=timezone.now)
    logout_time = models.DateTimeField(null=True, blank=True)
    
    # 網路資訊
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    
    # 狀態
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('logged_out', 'Logged Out'),
        ('expired', 'Expired'),
        ('terminated', 'Terminated'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # 安全標記
    is_suspicious = models.BooleanField(default=False)
    failure_count = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'auth_session_logs'
        indexes = [
            models.Index(fields=['user', 'login_time']),
            models.Index(fields=['session_key']),
            models.Index(fields=['is_suspicious']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.login_time}"


class LoginAttempt(models.Model):
    """登入嘗試記錄"""
    username = models.CharField(max_length=150)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    
    # 結果
    SUCCESS_CHOICES = [
        ('success', 'Success'),
        ('invalid_credentials', 'Invalid Credentials'),
        ('account_locked', 'Account Locked'),
        ('account_disabled', 'Account Disabled'),
        ('mfa_required', 'MFA Required'),
        ('mfa_failed', 'MFA Failed'),
    ]
    result = models.CharField(max_length=20, choices=SUCCESS_CHOICES)
    
    attempt_time = models.DateTimeField(default=timezone.now)
    
    # 額外資訊
    notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'auth_login_attempts'
        indexes = [
            models.Index(fields=['username', 'attempt_time']),
            models.Index(fields=['ip_address', 'attempt_time']),
            models.Index(fields=['result']),
        ]
    
    def __str__(self):
        return f"{self.username} - {self.result} - {self.attempt_time}"


class APIKey(models.Model):
    """API金鑰管理"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_keys')
    
    # 金鑰資訊
    name = models.CharField(max_length=100, help_text="金鑰名稱/用途")
    key = models.CharField(max_length=64, unique=True)
    
    # 權限設定
    scopes = models.JSONField(default=list, help_text="API範圍權限")
    
    # 限制設定
    ip_whitelist = models.JSONField(default=list, blank=True, help_text="IP白名單")
    rate_limit = models.IntegerField(default=1000, help_text="每小時請求限制")
    
    # 狀態
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # 使用統計
    usage_count = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'auth_api_keys'
        indexes = [
            models.Index(fields=['key']),
            models.Index(fields=['user']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"


class TwoFactorAuth(models.Model):
    """雙因子認證設定"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='two_factor')
    
    # 設定
    is_enabled = models.BooleanField(default=False)
    secret_key = models.CharField(max_length=32, blank=True)
    
    # 備用代碼
    backup_codes = models.JSONField(default=list, blank=True)
    
    # 設定時間
    enabled_at = models.DateTimeField(null=True, blank=True)
    last_used = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'auth_two_factor'
    
    def __str__(self):
        return f"{self.user.username} - MFA {'Enabled' if self.is_enabled else 'Disabled'}"


# 預設角色配置
DEFAULT_ROLES = {
    'superadmin': {
        'display_name': '超級管理員',
        'description': '系統超級管理員，擁有所有權限',
        'permissions': 'all',
        'data_access_level': 'all',
        'modules': {
            'can_access_patients': True,
            'can_access_appointments': True,
            'can_access_medical_records': True,
            'can_access_billing': True,
            'can_access_pharmacy': True,
            'can_access_laboratory': True,
            'can_access_reports': True,
            'can_access_administration': True,
        }
    },
    'admin': {
        'display_name': '管理員',
        'description': '系統管理員，擁有大部分管理權限',
        'data_access_level': 'facility',
        'modules': {
            'can_access_patients': True,
            'can_access_appointments': True,
            'can_access_medical_records': True,
            'can_access_billing': True,
            'can_access_pharmacy': True,
            'can_access_laboratory': True,
            'can_access_reports': True,
            'can_access_administration': True,
        }
    },
    'doctor': {
        'display_name': '醫生',
        'description': '醫生，可以查看和編輯病患資料、開立處方',
        'data_access_level': 'facility',
        'modules': {
            'can_access_patients': True,
            'can_access_appointments': True,
            'can_access_medical_records': True,
            'can_access_billing': False,
            'can_access_pharmacy': True,
            'can_access_laboratory': True,
            'can_access_reports': True,
            'can_access_administration': False,
        }
    },
    'nurse': {
        'display_name': '護士',
        'description': '護士，可以查看病患資料、記錄生命徵象',
        'data_access_level': 'department',
        'modules': {
            'can_access_patients': True,
            'can_access_appointments': True,
            'can_access_medical_records': True,
            'can_access_billing': False,
            'can_access_pharmacy': False,
            'can_access_laboratory': True,
            'can_access_reports': False,
            'can_access_administration': False,
        }
    },
    'receptionist': {
        'display_name': '櫃台人員',
        'description': '櫃台人員，負責預約管理和基本病患資料',
        'data_access_level': 'facility',
        'modules': {
            'can_access_patients': True,
            'can_access_appointments': True,
            'can_access_medical_records': False,
            'can_access_billing': True,
            'can_access_pharmacy': False,
            'can_access_laboratory': False,
            'can_access_reports': False,
            'can_access_administration': False,
        }
    },
    'billing_staff': {
        'display_name': '計費人員',
        'description': '計費人員，負責帳務和保險理賠',
        'data_access_level': 'facility',
        'modules': {
            'can_access_patients': True,
            'can_access_appointments': False,
            'can_access_medical_records': False,
            'can_access_billing': True,
            'can_access_pharmacy': False,
            'can_access_laboratory': False,
            'can_access_reports': True,
            'can_access_administration': False,
        }
    },
    'patient': {
        'display_name': '病患',
        'description': '病患，只能查看自己的資料',
        'data_access_level': 'own',
        'modules': {
            'can_access_patients': True,  # Only own data
            'can_access_appointments': True,  # Only own appointments
            'can_access_medical_records': True,  # Only own records
            'can_access_billing': True,  # Only own billing
            'can_access_pharmacy': True,  # Only own prescriptions
            'can_access_laboratory': True,  # Only own lab results
            'can_access_reports': False,
            'can_access_administration': False,
        }
    }
}
