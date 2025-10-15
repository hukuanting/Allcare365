from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    """
    用戶個人資料擴展模型
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='auth_profile')
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
