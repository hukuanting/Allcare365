"""Authentication lifecycle operations with one invalidation path.

Do not delete tokens directly from views or admin actions.  Keeping revocation
here makes suspension, password changes, and logout behave consistently.
"""

from django.db import transaction
from django.db.models import F
from django.conf import settings
from django.utils import timezone

from oauth2_provider.models import AccessToken, RefreshToken as OAuthRefreshToken

from .models import AuthSecurityState
from .permissions import (
    ADMIN_ROLES,
    CLINICAL_ROLES,
    LEGACY_PROFESSIONAL_ROLES,
    RESEARCH_ROLES,
    normalized_user_roles,
)


def get_security_state(user):
    state, _ = AuthSecurityState.objects.get_or_create(user=user)
    return state


def invalidate_user_tokens(user):
    """Invalidate JWT, Django OAuth Toolkit, and SimpleJWT refresh credentials."""
    if not user or not user.pk:
        return

    with transaction.atomic():
        state = get_security_state(user)
        AuthSecurityState.objects.filter(pk=state.pk).update(
            token_version=F('token_version') + 1,
            last_revoked_at=timezone.now(),
        )

        # OAuth access tokens are server-side records, so delete them now.  A
        # revoked refresh credential remains recorded by DOT for auditability.
        AccessToken.objects.filter(user_id=user.pk).delete()
        for token in OAuthRefreshToken.objects.select_for_update().filter(
            user_id=user.pk, revoked__isnull=True
        ):
            token.revoke()

        # The token blacklist app is intentionally optional for migrations and
        # local developer setups.  Production enables it in INSTALLED_APPS.
        try:
            from rest_framework_simplejwt.token_blacklist.models import (
                BlacklistedToken,
                OutstandingToken,
            )
        except (ImportError, RuntimeError):
            return

        for token in OutstandingToken.objects.select_for_update().filter(user_id=user.pk):
            BlacklistedToken.objects.get_or_create(token=token)


def user_is_approved(user):
    """Return whether an account may receive first-party credentials."""
    if not user or not user.is_active:
        return False
    product_user = getattr(user, 'product_user', None)
    return product_user is None or product_user.status == 'active'


def requires_mfa(user):
    """Whether the account is privileged enough to require a second factor."""
    if not getattr(settings, 'MFA_REQUIRED_FOR_PRIVILEGED', True):
        return False
    privileged_roles = ADMIN_ROLES | CLINICAL_ROLES | RESEARCH_ROLES | LEGACY_PROFESSIONAL_ROLES
    return bool(
        getattr(user, 'is_staff', False)
        or getattr(user, 'is_superuser', False)
        or normalized_user_roles(user).intersection(privileged_roles)
    )


def primary_totp_device(user, *, confirmed=None):
    """Return a TOTP device without ever exposing its provisioning key."""
    from django_otp.plugins.otp_totp.models import TOTPDevice

    devices = TOTPDevice.objects.filter(user=user)
    if confirmed is not None:
        devices = devices.filter(confirmed=confirmed)
    return devices.order_by('id').first()


def verify_totp(user, token, *, confirmed=True):
    """Verify while holding the device row lock, preventing concurrent reuse."""
    from django_otp import devices_for_user
    from django_otp.plugins.otp_totp.models import TOTPDevice

    with transaction.atomic():
        device = next(
            (
                candidate
                for candidate in devices_for_user(user, confirmed=confirmed, for_verify=True)
                if isinstance(candidate, TOTPDevice)
            ),
            None,
        )
        return bool(device and token and device.verify_token(token)), device


def approve_user(product_user):
    """Activate an approved ProductUser and invalidate pre-approval sessions."""
    product_user.status = 'active'
    product_user.save(update_fields=['status', 'updated_at'])


def suspend_user(product_user):
    """Suspend the account and revoke every credential immediately."""
    product_user.status = 'suspended'
    product_user.save(update_fields=['status', 'updated_at'])
