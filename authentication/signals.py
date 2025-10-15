from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    創建或更新用戶個人資料
    """
    if created:
        try:
            UserProfile.objects.get_or_create(user=instance)
            logger.info(f'Created profile for user: {instance.username}')
        except Exception as e:
            logger.error(f'Error creating profile for user {instance.username}: {str(e)}')
    else:
        # 確保個人資料存在
        try:
            UserProfile.objects.get_or_create(user=instance)
        except Exception as e:
            logger.error(f'Error ensuring profile for user {instance.username}: {str(e)}')

@receiver(post_delete, sender=User)
def delete_user_profile(sender, instance, **kwargs):
    """
    刪除用戶時記錄日誌
    """
    logger.info(f'User deleted: {instance.username}')
