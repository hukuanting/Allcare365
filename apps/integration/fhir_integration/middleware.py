from django.conf import settings
import logging

logger = logging.getLogger('medical_system')

class DynamicBaseURLMiddleware:
    """
    Middleware that dynamically updates the PUBLIC_BASE_URL and 
    OIDC_ISS_ENDPOINT settings based on the current request, 
    particularly useful when serving via Cloudflare Tunnel.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if hasattr(request, 'build_absolute_uri'):
            host = request.get_host()
            forwarded_proto = request.META.get("HTTP_X_FORWARDED_PROTO", "").split(",")[0].strip().lower()
            
            # If the request comes through a public tunnel or explicit HTTPS proxy
            if forwarded_proto == 'https':
                base_url = f"https://{host}"
                
                # Update PUBLIC_BASE_URL globally
                settings.PUBLIC_BASE_URL = base_url
                
                # Update OIDC Issuer endpoint globally (important for SMART jwt signing/validation)
                if hasattr(settings, 'OAUTH2_PROVIDER'):
                    # Need to modify the dictionary in place or reassign it
                    oauth_settings = settings.OAUTH2_PROVIDER
                    oauth_settings['OIDC_ISS_ENDPOINT'] = f"{base_url}/o"
                    # Set the updated nested dict back
                    settings.OAUTH2_PROVIDER = oauth_settings

        response = self.get_response(request)
        return response
