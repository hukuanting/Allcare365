"""Authentication request normalization for OAuth2/SMART endpoints."""

from django.utils.deprecation import MiddlewareMixin


class OAuthScopeCleanupMiddleware(MiddlewareMixin):
    """Keep legacy CSRF handling and response CORS without fabricating context."""

    def process_request(self, request):
        if request.path == '/o/authorize/' and request.method == 'POST':
            setattr(request, '_dont_enforce_csrf_checks', True)
        return None

    def process_response(self, request, response):
        # Patient/encounter context is added only by CustomTokenView after a
        # persisted launch -> authorization code -> access token link exists.
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Authorization, Content-Type, Accept"
        return response
