import json
import logging
import time
from urllib.parse import parse_qs, urlencode, urlparse

from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse, QueryDict
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView

from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from oauth2_provider.views import AuthorizationView, TokenView
from oauth2_provider.settings import oauth2_settings
from oauth2_provider.models import AccessToken, Application, RefreshToken as OAuthRefreshToken
from jwcrypto import jwk

from .serializers import UserSerializer, RegisterSerializer, LoginSerializer
from .smart_utils import SMARTContextError, SMARTContextService
from apps.integration.fhir_integration.fine_grained_scopes import (
    granular_scope_selection_options,
    is_granular_scope_for_resource,
)
from apps.integration.fhir_integration.public_url import get_public_base_url

logger = logging.getLogger('medical_system')

PROFILE_SCOPE_RESOURCE_TYPES = {
    'BodyWeight',
    'BodyHeight',
    'BodyTemperature',
    'HeartRate',
    'RespiratoryRate',
    'PulseOximetry',
    'BMI',
    'SmokingStatus',
    'HeadCircumference',
}


def _extract_resource_type(scope: str):
    if '/' not in scope or '.' not in scope:
        return None
    return scope.split('/', 1)[1].split('.', 1)[0]


def _normalize_url(url: str) -> str:
    return (url or "").rstrip("/")


def _smart_audience_candidates(request) -> set[str]:
    base_url = get_public_base_url(request)
    candidates = {
        f"{base_url}/fhir/R4",
        f"{base_url}/fhir",
    }
    return {_normalize_url(candidate) for candidate in candidates}


def _is_valid_smart_aud(request, aud: str) -> bool:
    return _normalize_url(aud) in _smart_audience_candidates(request)


def _json_oauth_error(error: str, description: str, status_code: int = 400) -> HttpResponse:
    response = HttpResponse(
        json.dumps({"error": error, "error_description": description}),
        status=status_code,
        content_type="application/json",
    )
    response["Cache-Control"] = "no-store"
    response["Pragma"] = "no-cache"
    return response


def _oidc_signing_kid() -> str:
    key = jwk.JWK.from_pem(oauth2_settings.OIDC_RSA_PRIVATE_KEY.encode("utf8"))
    return key.thumbprint()


class CustomAuthorizationView(AuthorizationView):
    """
    Custom Authorization View that handles SMART on FHIR v2 specifics.
    
    Key Features:
    1. Handles POST-based launch sequences (converts to GET for Django OAuth Toolkit).
    2. Normalizes whitespace in scopes.
    3. Prevents 'Duplicate client_id' errors during POST-to-GET conversion.
    """

    def dispatch(self, request, *args, **kwargs):
        """
        Pre-process the request before it reaches OAuth2 validation.
        """
        # Feature: SMART v2 POST Launch Support
        # Inferno sends authorization params via POST, but DOT expects GET (standard OAuth2 code flow).
        if request.method == 'POST' and 'response_type' in request.POST and 'allow' not in request.POST:
            logger.info("Handling SMART v2 POST-based Launch Request")
            
            # 1. Copy POST data to a mutable dictionary
            data = request.POST.copy()
            
            # 2. Normalize Scopes (removes weird newlines/tabs from Inferno)
            if 'scope' in data:
                data['scope'] = SMARTContextService.normalize_scopes(data['scope'])
            
            # 3. Convert to GET Request
            request.GET = data
            request.method = 'GET'
            request.META['REQUEST_METHOD'] = 'GET'
            request.META['QUERY_STRING'] = urlencode(data, doseq=True)
            
            # 4. CRITICAL FIX: Clear POST data
            # OAuthLib checks both GET params and POST body. If we move params to GET
            # but leave them in POST, OAuthLib sees duplicates and raises FatalClientError.
            # We must explicitly clear the POST container.
            request.POST = QueryDict('')
            
            logger.debug(f"Converted POST launch to GET. Scopes normalized.")

        # Handle standard GET requests (just normalize scopes)
        elif request.method == 'GET' and 'scope' in request.GET:
            request.GET._mutable = True
            request.GET['scope'] = SMARTContextService.normalize_scopes(request.GET['scope'])
            request.GET._mutable = False
            
            # CRITICAL FIX: Update QUERY_STRING for GET requests too!
            # Downstream libraries (like OAuthLib via DOT) might parse the raw URI or QUERY_STRING directly.
            # If we only update request.GET, they might still see the dirty scopes with newlines/tabs.
            new_params = request.GET.copy()
            request.META['QUERY_STRING'] = urlencode(new_params, doseq=True)

        aud = request.GET.get("aud") or request.POST.get("aud")
        if aud and not _is_valid_smart_aud(request, aud):
            logger.warning("Rejecting SMART authorize request with invalid aud=%s", aud)
            return _json_oauth_error(
                "invalid_request",
                "Invalid aud parameter. Expected this server's FHIR base URL.",
            )

        request_data = request.GET if request.method == "GET" else request.POST
        requested_scope = SMARTContextService.normalize_scopes(request_data.get("scope", ""))
        launch_token = request_data.get("launch", "")
        if launch_token:
            try:
                SMARTContextService.resolve_launch_context(
                    launch_token,
                    user=request.user if request.user.is_authenticated else None,
                )
            except SMARTContextError as exc:
                return _json_oauth_error("invalid_request", str(exc))
        elif SMARTContextService.has_patient_scopes(requested_scope) or "launch" in requested_scope.split():
            return _json_oauth_error(
                "invalid_request",
                "Patient-scoped authorization requires an explicit persisted EHR launch context.",
            )

        return super().dispatch(request, *args, **kwargs)

    def create_authorization_response(self, request, scopes, credentials, allow):
        """Persist the launch-to-code link before returning the code to the app."""

        response_data = super().create_authorization_response(
            request=request,
            scopes=scopes,
            credentials=credentials,
            allow=allow,
        )
        uri, _headers, _body, status_code = response_data
        launch_token = request.POST.get("launch") or request.GET.get("launch")
        if allow and launch_token and 300 <= status_code < 400:
            code_values = parse_qs(urlparse(uri).query).get("code") or []
            if not code_values:
                raise SMARTContextError("OAuth authorization response did not contain a code.")
            SMARTContextService.bind_authorization_code(
                authorization_code=code_values[0],
                launch_token=launch_token,
                user=request.user,
                client_id=credentials.get("client_id") or "",
            )
        return response_data

    def get_context_data(self, **kwargs):
        """
        Injects necessary context for the authorization template (authorize.html).
        """
        context = super().get_context_data(**kwargs)
        
        # Robustly retrieve params (prioritizing the cleaned request.GET).
        # If DOT re-renders the form after POST validation, preserve POST params too.
        data = self.request.GET.copy()
        if not data and self.request.method == "POST":
            data = self.request.POST.copy()
        
        # Prepare Scopes for UI (Checkboxes)
        scope_string = data.get("scope", "")
        requested_scopes = set(scope_string.split())
        
        # Show requested scopes and SMART v2 granular alternatives for ONC 9.28.
        all_defined_scopes = oauth2_settings.SCOPES
        display_scopes = set()
        granular_defaults = set()
        for scope in requested_scopes:
            granular_options = granular_scope_selection_options(scope)
            if granular_options:
                display_scopes.add(scope)
                display_scopes.update(granular_options)
                granular_defaults.update(granular_options)
            else:
                display_scopes.add(scope)
        if not display_scopes:
            display_scopes = set(oauth2_settings.DEFAULT_SCOPES or [])

        # Standalone patient launch should never show user/* scopes.
        if 'launch/patient' in display_scopes:
            display_scopes = {s for s in display_scopes if not s.startswith('user/')}

        scopes_list = []
        for scope in sorted(list(display_scopes)):
            desc = all_defined_scopes.get(scope)
            if not desc:
                if '.rs' in scope or '.read' in scope:
                    prefix = "Patient" if scope.startswith('patient/') else "User"
                    res_name = scope.split('/')[-1].split('.')[0]
                    desc = f"Read {res_name} ({prefix})"
                else:
                    desc = scope
            
            scopes_list.append({
                'key': scope, 
                'description': desc,
                'checked': (
                    'checked'
                    if scope in requested_scopes - {
                        'patient/Condition.rs',
                        'patient/Condition.read',
                        'patient/Observation.rs',
                        'patient/Observation.read',
                    }
                    or scope in granular_defaults
                    else ''
                )
            })
        
        context['scopes_list'] = scopes_list
        context['hidden_scopes'] = '' # Clear this
        context['offline_access_requested'] = 'offline_access' in display_scopes
        
        # Prepare Hidden Fields for Persistence
        # We manually render these to ensure all custom params survive the form submit
        oauth_params = []
        for key, value in data.items():
            if key != 'scope':  # Scope is handled by the UI explicitly
                oauth_params.append({'name': key, 'value': value})
        context['oauth_params'] = oauth_params
        context['authorize_action'] = self.request.get_full_path()
        
        return context

    def form_valid(self, form):
        # Force the scope from POST into cleaned_data to ensure we honor user selection
        if 'scope' in self.request.POST:
            user_scope = self.request.POST.get('scope')
            
            # Keep user-selected scopes stable and standards-aligned.
            selected_scopes = []
            for scope in user_scope.split():
                if scope not in selected_scopes:
                    selected_scopes.append(scope)

            # Standalone patient launch must not mint user/* scopes.
            if 'launch/patient' in selected_scopes:
                selected_scopes = [s for s in selected_scopes if not s.startswith('user/')]

            selected_scopes = self._remove_resource_level_scopes_when_granular_selected(selected_scopes)

            # Filter profile-labeled scopes (e.g. patient/BMI.rs) from minted tokens.
            selected_scopes = [
                s for s in selected_scopes
                if _extract_resource_type(s) not in PROFILE_SCOPE_RESOURCE_TYPES
            ]

            user_scope = ' '.join(selected_scopes)
            form.cleaned_data['scope'] = user_scope
            logger.info(f"CustomAuthorizationView finalized scopes: {user_scope}")
             
        return super().form_valid(form)

    @staticmethod
    def _remove_resource_level_scopes_when_granular_selected(selected_scopes):
        cleaned_scopes = []
        has_condition_granular = any(
            is_granular_scope_for_resource(scope, "Condition")
            for scope in selected_scopes
        )
        has_observation_granular = any(
            is_granular_scope_for_resource(scope, "Observation")
            for scope in selected_scopes
        )
        for scope in selected_scopes:
            if has_condition_granular and scope in {
                "patient/Condition.rs",
                "patient/Condition.read",
                "user/Condition.rs",
                "user/Condition.read",
            }:
                continue
            if has_observation_granular and scope in {
                "patient/Observation.rs",
                "patient/Observation.read",
                "user/Observation.rs",
                "user/Observation.read",
            }:
                continue
            cleaned_scopes.append(scope)
        return cleaned_scopes

    def post(self, request, *args, **kwargs):
        """
        Handle the user's decision (Allow/Deny).
        """
        logger.info(f"CustomAuthorizationView POST received. Scopes in POST: {request.POST.get('scope')}")

        # Consent form submissions must keep the original OAuth parameters.
        # Inferno links carry these in the query string; if hidden fields are
        # stripped or a template re-render loses them, merge them back before DOT
        # validates the authorization form.
        oauth_keys = {
            "response_type",
            "client_id",
            "redirect_uri",
            "state",
            "code_challenge",
            "code_challenge_method",
            "aud",
            "launch",
            "nonce",
            "prompt",
        }
        if request.GET:
            post_data = request.POST.copy()
            changed = False
            for key in oauth_keys:
                if key not in post_data and key in request.GET:
                    post_data[key] = request.GET.get(key)
                    changed = True
            if "scope" not in post_data and "scope" in request.GET:
                post_data["scope"] = request.GET.get("scope")
                changed = True
            if changed:
                request.POST = post_data

        # Normalize scope one last time before final processing
        if 'scope' in request.POST:
            request.POST._mutable = True
            request.POST['scope'] = SMARTContextService.normalize_scopes(request.POST['scope'])
            request.POST._mutable = False
            
        return super().post(request, *args, **kwargs)


from apps.integration.fhir_integration.views import SMARTv2Validator
import jwt
from datetime import datetime, timedelta, timezone
import uuid


def _build_id_token(request, token_response: dict, authorization_context=None) -> str:
    scope = token_response.get("scope") or request.POST.get("scope") or request.GET.get("scope") or ""
    if "openid" not in scope.split():
        return ""

    base_url = get_public_base_url(request)
    now = int(time.time())
    expires_in = int(token_response.get("expires_in") or 300)
    client_id = request.POST.get("client_id") or request.GET.get("client_id") or ""
    access_token = None
    access_value = token_response.get("access_token")
    if access_value:
        access_token = AccessToken.objects.select_related("user", "application").filter(
            token=access_value
        ).first()
    token_user = authorization_context.user if authorization_context is not None else (
        access_token.user if access_token is not None else None
    )
    if token_user is None or not client_id:
        return ""

    claims = {
        "iss": f"{base_url}/o",
        "sub": str(token_user.pk),
        "aud": client_id,
        "iat": now,
        "exp": now + expires_in,
    }
    smart_context = SMARTContextService.get_token_response_context(base_url, authorization_context)
    if authorization_context is not None:
        claims["patient"] = smart_context["patient"]
    if "fhirUser" in scope.split() and smart_context.get("fhirUser"):
        claims["fhirUser"] = smart_context["fhirUser"]

    return jwt.encode(
        claims,
        oauth2_settings.OIDC_RSA_PRIVATE_KEY,
        algorithm="RS256",
        headers={"kid": _oidc_signing_kid()},
    )


def _revoke_authorization_grant(token_value: str) -> None:
    """
    Revoke the patient/user's authorization grant for the requesting app.

    Inferno 9.3 revokes an app's access and then verifies that refresh fails.
    Revoking only the submitted access token is insufficient because the paired
    refresh token could still mint a new access token.
    """
    if not token_value:
        return

    access_token = (
        AccessToken.objects.select_related("user", "application")
        .filter(token=token_value)
        .first()
    )
    refresh_token = (
        OAuthRefreshToken.objects.select_related("user", "application", "access_token")
        .filter(token=token_value)
        .first()
    )

    user_id = None
    application_id = None
    if access_token is not None:
        user_id = access_token.user_id
        application_id = access_token.application_id
    elif refresh_token is not None:
        user_id = refresh_token.user_id
        application_id = refresh_token.application_id

    with transaction.atomic():
        if user_id and application_id:
            refresh_tokens = list(
                OAuthRefreshToken.objects.select_for_update()
                .filter(user_id=user_id, application_id=application_id, revoked__isnull=True)
            )
            for token in refresh_tokens:
                token.revoke()

            AccessToken.objects.filter(user_id=user_id, application_id=application_id).delete()
            return

        for token in OAuthRefreshToken.objects.select_for_update().filter(token=token_value, revoked__isnull=True):
            token.revoke()
        AccessToken.objects.filter(token=token_value).delete()


class CustomTokenView(TokenView):
    """
    Custom Token View for SMART on FHIR.
    """
    def post(self, request, *args, **kwargs):
        # 1. Handle Backend Services (Bulk Data) with Manual Trigger
        # This ensures our SMARTv2Validator logic is actually used even if oauthlib config is strict.
        if request.POST.get('grant_type') == 'client_credentials' and request.POST.get('client_assertion_type') == 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer':
            
            validator = SMARTv2Validator()
            # Adapt Django's request fields to the oauthlib validator contract.
            class OAuthLibRequestAdapter:
                def __init__(self, d):
                    self.grant_type = d.get('grant_type')
                    self.client_id = d.get('client_id')
                    self.client_assertion_type = d.get('client_assertion_type')
                    self.client_assertion = d.get('client_assertion')
                    self.uri = request.build_absolute_uri()
                    self.client = None
            
            oauth_request = OAuthLibRequestAdapter(request.POST)
            
            if validator.authenticate_client(oauth_request):
                # Authentication Success! Issue Token manually to ensure control.
                # This aligns with "Systematic" - we used the Validator to check, now we Use the Model to issue.
                app = oauth_request.client
                expires = datetime.now(timezone.utc) + timedelta(seconds=300)
                requested_scope = SMARTContextService.normalize_scopes(
                    request.POST.get('scope') or 'system/*.read'
                )
                if not requested_scope or any(
                    not scope.startswith("system/") for scope in requested_scope.split()
                ):
                    return _json_oauth_error(
                        "invalid_scope",
                        "Backend-services tokens may contain only system scopes.",
                    )
                token = AccessToken.objects.create(
                    user=app.user,
                    application=app,
                    expires=expires,
                    token=str(uuid.uuid4()).replace('-', ''),
                    scope=requested_scope
                )
                response = HttpResponse(
                    json.dumps({
                        "access_token": token.token,
                        "token_type": "bearer",
                        "expires_in": 300,
                        "scope": token.scope
                    }),
                    status=200,
                    content_type='application/json'
                )
                response['Cache-Control'] = 'no-store'
                response['Pragma'] = 'no-cache'
                return response
            else:
                # Validation Failed (Signature, Claims, etc.)
                response = HttpResponse(
                    json.dumps({
                        "error": "invalid_client",
                        "error_description": validator.last_error_description or "Client authentication failed",
                    }),
                    status=400,
                    content_type='application/json'
                )
                response['Cache-Control'] = 'no-store'
                response['Pragma'] = 'no-cache'
                return response

        # 2. Standard Flow for everything else
        try:
            authorization_context = self._preflight_authorization_context(request)
            # DOT version compatibility: create_token_response returns (url, headers, body, status) or (headers, body, status)
            response_data = self.create_token_response(request)
            if len(response_data) == 4:
                url, headers, body, status = response_data
            else:
                headers, body, status = response_data
            
            # 2. Inject SMART Context on Success (HTTP 200)
            if status == 200:
                try:
                    data = json.loads(body)
                    
                    base_url = get_public_base_url(request)
                    authorization_context = SMARTContextService.bind_token_response(
                        token_payload=data,
                        authorization_context=authorization_context,
                    )
                    smart_context = SMARTContextService.get_token_response_context(
                        base_url,
                        authorization_context,
                    )
                    data.update(smart_context)
                    data.pop("id_token", None)
                    id_token = _build_id_token(request, data, authorization_context)
                    if id_token:
                        data["id_token"] = id_token
                     
                    body = json.dumps(data)
                    logger.info("SMART Context injected into token response.")
                    
                except Exception:
                    logger.exception("Failed to bind issued token to SMART context")
                    self._discard_issued_tokens(locals().get("data", {}))
                    return _json_oauth_error(
                        "server_error",
                        "The token could not be bound to its persisted SMART context.",
                        status_code=500,
                    )
            
            # 3. Construct Final Response
            response = HttpResponse(content=body, status=status, content_type='application/json')
            for k, v in headers.items():
                response[k] = v
            
            # Add cache control headers as required by SMART/OAuth2 best practices
            response['Cache-Control'] = 'no-store'
            response['Pragma'] = 'no-cache'
                
            return response
            
        except SMARTContextError as exc:
            logger.warning("SMART token exchange rejected: %s", exc)
            return _json_oauth_error("invalid_grant", str(exc))
        except Exception:
            logger.exception("Critical error in token exchange")
            return _json_oauth_error(
                "server_error",
                "Token exchange failed.",
                status_code=500,
            )

    @staticmethod
    def _preflight_authorization_context(request):
        grant_type = request.POST.get("grant_type")
        if grant_type == "authorization_code":
            code = request.POST.get("code", "")
            context = SMARTContextService.authorization_context_for_code(code)
            grant_scope = SMARTContextService.grant_scope_for_code(code)
            if SMARTContextService.has_patient_scopes(grant_scope) and context is None:
                raise SMARTContextError(
                    "The patient-scoped authorization code has no persisted launch context."
                )
            return context
        if grant_type == "refresh_token":
            refresh_value = request.POST.get("refresh_token", "")
            context = SMARTContextService.authorization_context_for_refresh(refresh_value)
            original_scope = SMARTContextService.refresh_scope(refresh_value)
            if SMARTContextService.has_patient_scopes(original_scope) and context is None:
                raise SMARTContextError(
                    "The patient-scoped refresh token has no persisted launch context."
                )
            return context
        return None

    @staticmethod
    def _discard_issued_tokens(token_payload):
        refresh_value = token_payload.get("refresh_token")
        access_value = token_payload.get("access_token")
        with transaction.atomic():
            if refresh_value:
                OAuthRefreshToken.objects.filter(token=refresh_value).delete()
            if access_value:
                AccessToken.objects.filter(token=access_value).delete()


@method_decorator(csrf_exempt, name="dispatch")
class SmartRevocationView(View):
    """RFC 7009-compatible token revocation alias exposed at /o/revoke/."""

    def post(self, request, *args, **kwargs):
        token_value = request.POST.get("token", "")
        _revoke_authorization_grant(token_value)

        response = HttpResponse(status=200)
        response["Cache-Control"] = "no-store"
        response["Pragma"] = "no-cache"
        return response


@method_decorator(csrf_exempt, name="dispatch")
class SmartIntrospectionView(View):
    """RFC 7662-compatible token introspection alias exposed at /o/introspect/."""

    def post(self, request, *args, **kwargs):
        token_value = request.POST.get("token", "")
        now = datetime.now(timezone.utc)
        access_token = (
            AccessToken.objects.select_related("application", "user")
            .filter(token=token_value, expires__gt=now)
            .first()
        )

        if not access_token:
            return HttpResponse(
                json.dumps({"active": False}),
                status=200,
                content_type="application/json",
            )

        authorization_context = SMARTContextService.authorization_context_for_access_token(
            access_token
        )
        if (
            SMARTContextService.has_patient_scopes(access_token.scope)
            and authorization_context is None
        ):
            return HttpResponse(
                json.dumps({"active": False}),
                status=200,
                content_type="application/json",
            )

        payload = {
            "active": True,
            "scope": access_token.scope,
            "client_id": access_token.application.client_id if access_token.application else "",
            "token_type": "bearer",
            "exp": int(access_token.expires.timestamp()),
            "iat": int(access_token.created.timestamp()) if access_token.created else None,
            "sub": str(access_token.user_id) if access_token.user_id else "",
        }
        base_url = get_public_base_url(request)
        payload["iss"] = f"{base_url}/o"
        if authorization_context is not None:
            smart_context = SMARTContextService.get_token_response_context(
                base_url,
                authorization_context,
            )
            for key in ("patient", "encounter", "fhirUser"):
                if smart_context.get(key):
                    payload[key] = smart_context[key]
        else:
            fhir_user = SMARTContextService.fhir_user_reference(base_url, access_token.user)
            if fhir_user:
                payload["fhirUser"] = fhir_user
        payload = {key: value for key, value in payload.items() if value not in (None, "")}
        response = HttpResponse(json.dumps(payload), status=200, content_type="application/json")
        response["Cache-Control"] = "no-store"
        response["Pragma"] = "no-cache"
        return response


# --- Standard Auth Views (Unchanged Logic, Cleaned up) ---

class RegisterAPIView(generics.GenericAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            "user": UserSerializer(user, context=self.get_serializer_context()).data,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)


class LoginAPIView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            refresh = RefreshToken.for_user(user)
            return Response({
                "user": UserSerializer(user, context={'request': request}).data,
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            })
        else:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        return Response({"detail": "Successfully logged out"}, status=status.HTTP_205_RESET_CONTENT)


class ProfileAPIView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer
    def get_object(self):
        return self.request.user


class RegisterView(CreateView):
    form_class = UserCreationForm
    template_name = 'auth/register.html'
    success_url = reverse_lazy('authentication:login')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Registration successful. Please login.')
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, 'Registration failed.')
        return super().form_invalid(form)
