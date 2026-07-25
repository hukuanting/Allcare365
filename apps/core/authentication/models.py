from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid


class SmartLaunchContext(models.Model):
    """Short-lived, single-use context created by an authenticated EHR launch."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token_digest = models.CharField(max_length=64, unique=True, editable=False)
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.PROTECT,
        related_name='smart_launch_contexts',
    )
    encounter = models.ForeignKey(
        'health_screening.HealthScreening',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='smart_launch_contexts',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='smart_launch_contexts',
    )
    target_launch_uri = models.URLField(max_length=1000, blank=True, default='')
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'smart_launch_contexts'
        indexes = [models.Index(fields=['expires_at', 'consumed_at'])]


class SmartAuthorizationContext(models.Model):
    """Patient context bound to one OAuth authorization code, never to a session default."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    authorization_code_digest = models.CharField(max_length=64, unique=True, editable=False)
    launch_context = models.OneToOneField(
        SmartLaunchContext,
        on_delete=models.PROTECT,
        related_name='authorization_context',
    )
    patient = models.ForeignKey(
        'patients.Patient',
        on_delete=models.PROTECT,
        related_name='smart_authorization_contexts',
    )
    encounter = models.ForeignKey(
        'health_screening.HealthScreening',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='smart_authorization_contexts',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='smart_authorization_contexts',
    )
    application = models.ForeignKey(
        'oauth2_provider.Application',
        on_delete=models.PROTECT,
        related_name='smart_authorization_contexts',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    exchanged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'smart_authorization_contexts'
        indexes = [models.Index(fields=['patient', 'application'])]


class SmartAccessTokenContext(models.Model):
    """Exact patient context for an issued OAuth access token."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    access_token = models.OneToOneField(
        'oauth2_provider.AccessToken',
        on_delete=models.CASCADE,
        related_name='smart_patient_context',
    )
    authorization_context = models.ForeignKey(
        SmartAuthorizationContext,
        on_delete=models.PROTECT,
        related_name='access_token_contexts',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'smart_access_token_contexts'


class SmartRefreshTokenContext(models.Model):
    """Refresh-token link that carries the original patient context forward."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    refresh_token = models.OneToOneField(
        'oauth2_provider.RefreshToken',
        on_delete=models.CASCADE,
        related_name='smart_patient_context',
    )
    authorization_context = models.ForeignKey(
        SmartAuthorizationContext,
        on_delete=models.PROTECT,
        related_name='refresh_token_contexts',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'smart_refresh_token_contexts'


class ProductUser(models.Model):
    """產品使用者主檔，連接 Django auth_user 與 AllCare365 角色權限。"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    auth_user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='product_user')
    display_name = models.CharField(max_length=200)
    role = models.CharField(max_length=50, default='patient')
    status = models.CharField(max_length=50, default='active')
    organization_name = models.CharField(max_length=200, blank=True, default='')
    metadata_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'
        db_table_comment = '產品使用者主檔；保存 AllCare365 角色、狀態與 auth_user 對應。FHIR 對應：Practitioner/Patient/RelatedPerson 視角色投影。'
        indexes = [
            models.Index(fields=['role', 'status']),
            models.Index(fields=['organization_name']),
        ]

    def __str__(self):
        return self.display_name

class UserProfile(models.Model):
    """
    用戶個人資料擴展模型
    """
    ROLE_CHOICES = (
        ('professional', 'Professional (View A)'),
        ('patient', 'Patient (View B)'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='auth_profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='patient', verbose_name='角色')
    phone = models.CharField(max_length=20, blank=True, verbose_name='電話號碼')
    address = models.TextField(blank=True, verbose_name='地址')
    date_of_birth = models.DateField(null=True, blank=True, verbose_name='出生日期')
    emergency_contact = models.CharField(max_length=100, blank=True, verbose_name='緊急聯絡人')
    emergency_phone = models.CharField(max_length=20, blank=True, verbose_name='緊急聯絡人電話')
    notes = models.TextField(blank=True, verbose_name='備註')
    
    # 系統欄位
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='創建時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    
    class Meta:
        verbose_name = '用戶個人資料'
        verbose_name_plural = '用戶個人資料'
    
    def __str__(self):
        return f'{self.user.username} 的個人資料'

class LoginHistory(models.Model):
    """
    登入歷史記錄
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_history')
    login_time = models.DateTimeField(auto_now_add=True, verbose_name='登入時間')
    ip_address = models.GenericIPAddressField(verbose_name='IP地址')
    user_agent = models.TextField(verbose_name='瀏覽器資訊')
    is_successful = models.BooleanField(default=True, verbose_name='是否成功')
    logout_time = models.DateTimeField(null=True, blank=True, verbose_name='登出時間')
    
    class Meta:
        verbose_name = '登入歷史'
        verbose_name_plural = '登入歷史'
        ordering = ['-login_time']
    
    def __str__(self):
        return f'{self.user.username} - {self.login_time.strftime("%Y-%m-%d %H:%M:%S")}'

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    當創建新用戶時自動創建個人資料
    """
    if created:
        UserProfile.objects.create(user=instance)
