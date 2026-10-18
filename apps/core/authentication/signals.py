from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import m2m_changed, post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import Group, Permission, User
from .models import AuthSecurityState, ProductUser, UserProfile
from .services import invalidate_user_tokens
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
            AuthSecurityState.objects.get_or_create(user=instance)
            logger.info('Created authentication profile and security state.')
        except Exception as e:
            logger.error(f'Error creating profile for user {instance.username}: {str(e)}')
    else:
        # 確保個人資料存在
        try:
            UserProfile.objects.get_or_create(user=instance)
        except Exception as e:
            logger.error(f'Error ensuring profile for user {instance.username}: {str(e)}')


@receiver(pre_save, sender=User)
def mark_user_security_changes(sender, instance, **kwargs):
    """Detect credential and account-state changes made outside our API."""
    if not instance.pk:
        instance._invalidate_auth_tokens = False
        return
    previous = User.objects.filter(pk=instance.pk).values(
        'password', 'is_active', 'is_staff', 'is_superuser'
    ).first()
    instance._invalidate_auth_tokens = bool(
        previous and (
            previous['password'] != instance.password
            or previous['is_active'] != instance.is_active
            or previous['is_staff'] != instance.is_staff
            or previous['is_superuser'] != instance.is_superuser
        )
    )


@receiver(post_save, sender=User)
def revoke_tokens_after_user_security_change(sender, instance, created, **kwargs):
    if not created and getattr(instance, '_invalidate_auth_tokens', False):
        invalidate_user_tokens(instance)


@receiver(user_logged_in)
def bind_session_to_auth_security_version(sender, request, user, **kwargs):
    """A browser session is valid only for the credential generation that made it."""
    if request is not None:
        request.session['auth_security_version'] = AuthSecurityState.objects.get_or_create(
            user=user
        )[0].token_version


@receiver(post_save, sender=ProductUser)
def synchronize_product_account_status(sender, instance, created, **kwargs):
    """Product approval is the source of truth for first-party account status."""
    desired_active = instance.status == 'active'
    user = instance.auth_user
    if user.is_active != desired_active:
        user.is_active = desired_active
        user.save(update_fields=['is_active'])
    elif created and desired_active:
        # Attaching a privileged product role to an existing active user must
        # revoke server-side OAuth grants as well as old first-party sessions.
        invalidate_user_tokens(user)
    elif not created and getattr(instance, '_invalidate_auth_tokens', False):
        # Role elevation must force fresh credentials (and therefore MFA where
        # required).  Status changes may occur while auth_user is already
        # inactive, in which case the User signal would not otherwise run.
        invalidate_user_tokens(user)


@receiver(pre_save, sender=ProductUser)
def mark_product_user_security_changes(sender, instance, **kwargs):
    if not instance.pk:
        instance._invalidate_auth_tokens = False
        return
    previous = ProductUser.objects.filter(pk=instance.pk).values('role', 'status').first()
    instance._invalidate_auth_tokens = bool(
        previous and (
            previous['role'] != instance.role or previous['status'] != instance.status
        )
    )


@receiver(pre_save, sender=UserProfile)
def mark_legacy_profile_role_change(sender, instance, **kwargs):
    if not instance.pk:
        instance._invalidate_auth_tokens = False
        return
    previous = UserProfile.objects.filter(pk=instance.pk).values('role').first()
    instance._invalidate_auth_tokens = bool(previous and previous['role'] != instance.role)


@receiver(post_save, sender=UserProfile)
def revoke_after_legacy_profile_role_change(sender, instance, created, **kwargs):
    if not created and getattr(instance, '_invalidate_auth_tokens', False):
        invalidate_user_tokens(instance.user)


def _users_affected_by_membership_change(instance):
    if isinstance(instance, User):
        return [instance.pk]
    if isinstance(instance, Group):
        return list(instance.user_set.values_list('pk', flat=True))
    if isinstance(instance, Permission):
        direct = instance.user_set.values_list('pk', flat=True)
        inherited = User.objects.filter(groups__permissions=instance).values_list('pk', flat=True)
        return list(set(direct).union(inherited))
    return []


@receiver(m2m_changed, sender=User.groups.through)
@receiver(m2m_changed, sender=User.user_permissions.through)
@receiver(m2m_changed, sender=Group.permissions.through)
def revoke_after_membership_or_permission_change(sender, instance, action, **kwargs):
    """Revoke on either direction of Django's User/Group/Permission M2Ms."""
    if action.startswith('pre_'):
        # Removal/clear loses the reverse relation before post_* runs.
        instance._auth_security_affected_user_ids = _users_affected_by_membership_change(instance)
        if kwargs.get('pk_set'):
            if isinstance(instance, User):
                instance._auth_security_affected_user_ids = [instance.pk]
            elif isinstance(instance, Group) and kwargs.get('reverse'):
                instance._auth_security_affected_user_ids = list(kwargs['pk_set'])
            elif isinstance(instance, Permission) and kwargs.get('reverse'):
                if sender == Group.permissions.through:
                    instance._auth_security_affected_user_ids = list(
                        User.objects.filter(groups__pk__in=kwargs['pk_set'])
                        .values_list('pk', flat=True)
                        .distinct()
                    )
                else:
                    instance._auth_security_affected_user_ids = list(kwargs['pk_set'])
        return
    if action not in {'post_add', 'post_remove', 'post_clear'}:
        return
    user_ids = getattr(instance, '_auth_security_affected_user_ids', None)
    if user_ids is None:
        user_ids = _users_affected_by_membership_change(instance)
    for user in User.objects.filter(pk__in=set(user_ids)).iterator():
        invalidate_user_tokens(user)
    if hasattr(instance, '_auth_security_affected_user_ids'):
        delattr(instance, '_auth_security_affected_user_ids')

@receiver(post_delete, sender=User)
def delete_user_profile(sender, instance, **kwargs):
    """
    刪除用戶時記錄日誌
    """
    logger.info('User deleted.')
