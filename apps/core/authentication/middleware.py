"""Authentication request normalization for OAuth2/SMART endpoints."""

from django.utils.deprecation import MiddlewareMixin


class OAuthScopeCleanupMiddleware(MiddlewareMixin):
    """Compatibility shim; CSRF and CORS belong to Django's standard middleware.

    Kept importable for deployments with the historical middleware path. It
    deliberately neither bypasses CSRF nor changes CORS response headers.
    """


class SensitiveResponseMiddleware(MiddlewareMixin):
    """Prevent Django dynamic responses from entering browser or proxy caches."""

    def process_response(self, request, response):
        from django.conf import settings

        static_url = getattr(settings, 'STATIC_URL', '/static/') or '/static/'
        if request.path.startswith(static_url):
            return response
        # FHIR also has legacy root-level routes (for example /Patient and
        # /metadata), so cache policy must not depend on a URL prefix allowlist.
        response['Cache-Control'] = 'no-store'
        response['Pragma'] = 'no-cache'
        return response


class SecuritySessionMiddleware(MiddlewareMixin):
    """Revoke browser sessions using the same account version as JWTs.

    Session authentication alone cannot preserve access after suspension or a
    global logout. Missing versions reject sessions created before this release.
    OTP enrollment remains possible for an approved, password-authenticated user.
    """

    def process_request(self, request):
        if not request.user.is_authenticated:
            return None
        from django.contrib.auth import logout
        from .services import get_security_state, user_is_approved

        if (
            not user_is_approved(request.user)
            or request.session.get('auth_security_version')
            != get_security_state(request.user).token_version
        ):
            logout(request)
        return None
