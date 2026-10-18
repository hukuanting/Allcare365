import pytest
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import override_settings
from django.utils import timezone
from rest_framework.request import Request
from rest_framework.test import APIClient, APIRequestFactory
from django.http import HttpResponse
from django_otp.oath import TOTP
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIClient

from apps.core.authentication.jwt_authentication import (
    TOKEN_VERSION_CLAIM,
    ApprovedSessionAuthentication,
    VersionedJWTAuthentication,
    VersionedRefreshToken,
)
from apps.core.authentication.models import ProductUser
from apps.core.authentication.services import invalidate_user_tokens
from apps.core.authentication.signals import bind_session_to_auth_security_version
from apps.core.authentication.views import CustomAuthorizationView


def _totp_token(device, *, at=None):
    generator = TOTP(
        device.bin_key,
        step=device.step,
        t0=device.t0,
        digits=device.digits,
        drift=device.drift,
    )
    generator.time = (at or timezone.now()).timestamp()
    return f'{generator.token():0{device.digits}d}'


@pytest.mark.django_db
def test_public_registration_creates_active_viewer_account():
    response = APIClient().post(
        '/api/auth/register/',
        {
            'username': 'pending-user',
            'email': 'pending@example.test',
            'password': 'A-long-enough-password-123!',
            'password2': 'A-long-enough-password-123!',
            'first_name': 'Pending',
            'last_name': 'User',
        },
        format='json',
    )

    assert response.status_code == 201
    assert 'access' not in response.data
    user = User.objects.get(username='pending-user')
    assert user.is_active
    assert user.product_user.status == 'active'
    assert user.product_user.role == 'viewer'
    assert not user.is_staff
    assert not user.is_superuser


@pytest.mark.django_db
def test_logout_invalidation_rejects_existing_access_token():
    user = User.objects.create_user('approved-user', password='A-long-enough-password-123!')
    ProductUser.objects.create(
        auth_user=user, display_name='Approved user', role='patient', status='active'
    )
    refresh = VersionedRefreshToken.for_user(user)
    access = refresh.access_token
    user.auth_security_state.refresh_from_db()
    assert access[TOKEN_VERSION_CLAIM] == user.auth_security_state.token_version

    invalidate_user_tokens(user)

    with pytest.raises(AuthenticationFailed):
        VersionedJWTAuthentication().get_user(access)


@pytest.mark.django_db
def test_password_change_invalidates_existing_access_token():
    user = User.objects.create_user('password-user', password='A-long-enough-password-123!')
    ProductUser.objects.create(
        auth_user=user, display_name='Password user', role='patient', status='active'
    )
    access = VersionedRefreshToken.for_user(user).access_token

    user.set_password('Different-long-enough-password-456!')
    user.save()

    with pytest.raises(AuthenticationFailed):
        VersionedJWTAuthentication().get_user(access)


@pytest.mark.django_db
def test_revocation_invalidates_browser_session_generation():
    user = User.objects.create_user('session-user', password='A-long-enough-password-123!')
    ProductUser.objects.create(
        auth_user=user, display_name='Session user', role='patient', status='active'
    )
    raw_request = APIRequestFactory().get('/api/auth/profile/')
    SessionMiddleware(lambda request: None).process_request(raw_request)
    raw_request.session.save()
    raw_request.user = user
    bind_session_to_auth_security_version(sender=User, request=raw_request, user=user)

    authenticated = ApprovedSessionAuthentication().authenticate(Request(raw_request))
    assert authenticated[0] == user

    invalidate_user_tokens(user)
    with pytest.raises(AuthenticationFailed):
        ApprovedSessionAuthentication().authenticate(Request(raw_request))


@pytest.mark.django_db
@override_settings(MFA_REQUIRED_FOR_PRIVILEGED=True)
def test_privileged_jwt_requires_mfa_claim():
    user = User.objects.create_user('clinical-user', password='A-long-enough-password-123!')
    ProductUser.objects.create(
        auth_user=user, display_name='Clinical user', role='clinician', status='active'
    )

    password_only_access = VersionedRefreshToken.for_user(user).access_token
    with pytest.raises(AuthenticationFailed, match='Multi-factor'):
        VersionedJWTAuthentication().get_user(password_only_access)

    mfa_access = VersionedRefreshToken.for_user(user, mfa_verified=True).access_token
    assert VersionedJWTAuthentication().get_user(mfa_access) == user


@pytest.mark.django_db
@override_settings(MFA_REQUIRED_FOR_PRIVILEGED=True)
def test_role_elevation_revokes_existing_credential_generation():
    user = User.objects.create_user('elevated-user', password='A-long-enough-password-123!')
    product_user = ProductUser.objects.create(
        auth_user=user, display_name='Elevated user', role='patient', status='active'
    )
    old_access = VersionedRefreshToken.for_user(user).access_token
    version_before = user.auth_security_state.token_version

    product_user.role = 'clinician'
    product_user.save(update_fields=['role', 'updated_at'])

    user.auth_security_state.refresh_from_db()
    assert user.auth_security_state.token_version > version_before
    with pytest.raises(AuthenticationFailed):
        VersionedJWTAuthentication().get_user(old_access)


@pytest.mark.django_db
def test_reverse_group_membership_change_revokes_affected_user():
    user = User.objects.create_user('group-user', password='A-long-enough-password-123!')
    ProductUser.objects.create(
        auth_user=user, display_name='Group user', role='patient', status='active'
    )
    group = Group.objects.create(name='researcher')
    version_before = user.auth_security_state.token_version

    group.user_set.add(user)

    user.auth_security_state.refresh_from_db()
    assert user.auth_security_state.token_version > version_before


@pytest.mark.django_db
@override_settings(MFA_REQUIRED_FOR_PRIVILEGED=True, REST_FRAMEWORK={
    'DEFAULT_THROTTLE_RATES': {'auth_login': '20/minute', 'auth_register': '20/minute', 'auth_token_refresh': '20/minute'},
})
def test_totp_enrollment_and_login_do_not_allow_code_reuse():
    user = User.objects.create_user('totp-clinician', password='A-long-enough-password-123!')
    ProductUser.objects.create(
        auth_user=user, display_name='TOTP clinician', role='clinician', status='active'
    )
    client = APIClient()
    credentials = {'username': user.username, 'password': 'A-long-enough-password-123!'}

    clock = timezone.now().replace(microsecond=0)
    # django-otp's TOTP and throttle clocks are both frozen, then advanced.
    with patch('django_otp.oath.time', side_effect=lambda: clock.timestamp()), patch(
        'django_otp.models.timezone.now', side_effect=lambda: clock
    ):
        enrollment = client.post('/api/auth/mfa/enroll/', credentials, format='json')
        assert enrollment.status_code == 200
        assert enrollment.data['provisioning_uri'].startswith('otpauth://totp/')
        device = TOTPDevice.objects.get(user=user, confirmed=False)

        rejected = client.post(
            '/api/auth/mfa/verify/', {**credentials, 'otp_token': '000000'}, format='json'
        )
        assert rejected.status_code == 401
        assert not TOTPDevice.objects.get(pk=device.pk).confirmed

        clock += timedelta(seconds=2)  # first django-otp throttle delay is one second
        verified = client.post(
            '/api/auth/mfa/verify/',
            {**credentials, 'otp_token': _totp_token(device, at=clock)},
            format='json',
        )
        assert verified.status_code == 200
        assert 'access' in verified.data

        # The enrollment token was consumed; a fresh time step is required.
        replay = client.post(
            '/api/auth/login/',
            {**credentials, 'otp_token': _totp_token(device, at=clock)}, format='json'
        )
        assert replay.status_code == 401
        clock += timedelta(seconds=device.step)
        successful_login = client.post(
            '/api/auth/login/',
            {**credentials, 'otp_token': _totp_token(device, at=clock)},
            format='json',
        )
        assert successful_login.status_code == 200


@pytest.mark.django_db
@override_settings(MFA_REQUIRED_FOR_PRIVILEGED=True)
def test_oauth_authorize_requires_verified_otp_session_for_privileged_user():
    user = User.objects.create_user('oauth-clinician', password='A-long-enough-password-123!')
    ProductUser.objects.create(
        auth_user=user, display_name='OAuth clinician', role='clinician', status='active'
    )
    factory = APIRequestFactory()
    request = factory.get('/o/authorize/?response_type=code&client_id=missing')
    SessionMiddleware(lambda request: None).process_request(request)
    request.session.save()
    request.user = user

    denied = CustomAuthorizationView.as_view()(request)
    assert denied.status_code == 403

    user.is_verified = lambda: True
    accepted_request = factory.get('/o/authorize/?response_type=code&client_id=missing')
    SessionMiddleware(lambda request: None).process_request(accepted_request)
    accepted_request.session.save()
    accepted_request.user = user
    with patch('oauth2_provider.views.AuthorizationView.dispatch', return_value=HttpResponse('oauth')) as dispatch:
        response = CustomAuthorizationView.as_view()(accepted_request)
    assert response.status_code == 200
    dispatch.assert_called_once()


@pytest.mark.django_db
@override_settings(MFA_REQUIRED_FOR_PRIVILEGED=False)
def test_rotated_refresh_tokens_remain_tracked_and_can_rotate_again():
    from rest_framework_simplejwt.tokens import RefreshToken
    from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
    from apps.core.authentication.jwt_authentication import VersionedTokenRefreshSerializer

    user = User.objects.create_user("rotation-user")
    ProductUser.objects.create(auth_user=user, display_name="Rotation user", role="viewer", status="active")
    current = str(VersionedRefreshToken.for_user(user))
    previous = []
    for _ in range(3):
        serializer = VersionedTokenRefreshSerializer(data={"refresh": current})
        serializer.is_valid(raise_exception=True)
        previous.append(current)
        current = serializer.validated_data["refresh"]
        rotated = RefreshToken(current)
        assert OutstandingToken.objects.filter(jti=rotated["jti"], user=user).exists()
        assert VersionedJWTAuthentication().get_user(rotated.access_token) == user
    for revoked in previous:
        serializer = VersionedTokenRefreshSerializer(data={"refresh": revoked})
        from rest_framework_simplejwt.exceptions import TokenError
        with pytest.raises(TokenError):
            serializer.is_valid(raise_exception=True)
