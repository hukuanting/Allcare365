from django.contrib.auth.models import User
from django.db import transaction
from rest_framework.exceptions import AuthenticationFailed
from rest_framework import serializers
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenObtainSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.utils import datetime_from_epoch
from django.contrib.auth.models import update_last_login
from rest_framework.authentication import SessionAuthentication

from .services import get_security_state, requires_mfa, user_is_approved, verify_totp


TOKEN_VERSION_CLAIM = 'token_version'


class VersionedRefreshToken(RefreshToken):
    """A refresh token bound to the server-side security version."""

    @classmethod
    def for_user(cls, user, *, mfa_verified=False):
        token = super().for_user(user)
        token[TOKEN_VERSION_CLAIM] = get_security_state(user).token_version
        token['mfa'] = bool(mfa_verified)
        return token


class VersionedJWTAuthentication(JWTAuthentication):
    """Reject tokens issued before logout, suspension, or password change."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if not user_is_approved(user):
            raise AuthenticationFailed('User account is not active.', code='user_inactive')
        version = validated_token.get(TOKEN_VERSION_CLAIM)
        if version is None or version != get_security_state(user).token_version:
            raise AuthenticationFailed('Token has been revoked.', code='token_revoked')
        if requires_mfa(user) and not validated_token.get('mfa', False):
            raise AuthenticationFailed('Multi-factor authentication is required.', code='mfa_required')
        return user


class ApprovedSessionAuthentication(SessionAuthentication):
    """Apply approval, revocation, and MFA checks to browser API sessions."""

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        user, auth = result
        if not user_is_approved(user):
            raise AuthenticationFailed('User account is not active.', code='user_inactive')
        if request.session.get('auth_security_version') != get_security_state(user).token_version:
            raise AuthenticationFailed('Session has been revoked.', code='token_revoked')
        if requires_mfa(user) and not getattr(user, 'is_verified', lambda: False)():
            raise AuthenticationFailed('Multi-factor authentication is required.', code='mfa_required')
        return user, auth


class VersionedTokenObtainPairSerializer(TokenObtainPairSerializer):
    token_class = VersionedRefreshToken
    otp_token = serializers.CharField(
        required=False, write_only=True, trim_whitespace=True
    )

    @classmethod
    def get_token(cls, user):
        return VersionedRefreshToken.for_user(user)

    def validate(self, attrs):
        # Authenticate and verify MFA before constructing a refresh token.  The
        # parent pair serializer mints a token first, which would let repeated
        # bad OTP attempts fill OutstandingToken.
        TokenObtainSerializer.validate(self, attrs)
        if not user_is_approved(self.user):
            raise AuthenticationFailed('No active account found with the given credentials.')
        otp_token = attrs.get('otp_token')
        mfa_verified = False
        if requires_mfa(self.user):
            verified, device = verify_totp(self.user, otp_token)
            if not device:
                raise AuthenticationFailed('Multi-factor enrollment is required.', code='mfa_enrollment_required')
            if not verified:
                raise AuthenticationFailed('Invalid multi-factor authentication code.', code='mfa_required')
            mfa_verified = True
        refresh = VersionedRefreshToken.for_user(self.user, mfa_verified=mfa_verified)
        data = {'refresh': str(refresh), 'access': str(refresh.access_token)}
        if api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, self.user)
        return data


class VersionedTokenRefreshSerializer(TokenRefreshSerializer):
    """Do not rotate a credential for a suspended or globally revoked account."""

    def validate(self, attrs):
        refresh = RefreshToken(attrs['refresh'])
        user_id = refresh.get(api_settings.USER_ID_CLAIM)
        user = User.objects.filter(pk=user_id).first()
        if not user or not user_is_approved(user):
            raise AuthenticationFailed('Token is no longer valid.', code='token_revoked')
        if refresh.get(TOKEN_VERSION_CLAIM) != get_security_state(user).token_version:
            raise AuthenticationFailed('Token has been revoked.', code='token_revoked')
        if requires_mfa(user) and not refresh.get('mfa', False):
            raise AuthenticationFailed('Multi-factor authentication is required.', code='mfa_required')
        # Rotation and blacklisting must serialize on the outstanding token row;
        # otherwise two concurrent refresh requests can both mint successors.
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

        with transaction.atomic():
            outstanding = OutstandingToken.objects.select_for_update().filter(
                jti=refresh.get('jti')
            ).first()
            if outstanding is None:
                raise AuthenticationFailed('Token is no longer valid.', code='token_revoked')
            data = super().validate(attrs)
            if api_settings.ROTATE_REFRESH_TOKENS and data.get("refresh"):
                # Older SimpleJWT releases rotate without recording the successor.
                # Keep it in the same transaction as revocation of its predecessor.
                successor = RefreshToken(data["refresh"])
                OutstandingToken.objects.get_or_create(
                    jti=successor[api_settings.JTI_CLAIM],
                    defaults={
                        "user": user,
                        "token": data["refresh"],
                        "created_at": datetime_from_epoch(successor["iat"]),
                        "expires_at": datetime_from_epoch(successor["exp"]),
                    },
                )
            return data
