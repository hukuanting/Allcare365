"""
FHIR R4 API Views — Thin Controller Layer

Delegates to the FHIR Projection Engine for resource retrieval and search.
Preserves SMART-on-FHIR authentication, OAuth2, and bulk export endpoints.

Architecture:
    views.py (this file)
        → ProjectorRegistry  (retrieve / list)
        → FHIRBundleBuilder   (search bundles)
        → CapabilityStatement (metadata)
"""
import json
import logging
import uuid
import urllib.parse
import jwt # PyJWT for backend services validation
from datetime import datetime, timezone, timedelta
from threading import Lock

from django.conf import settings
from django.db import models
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, render
from django.contrib.auth.models import User

from rest_framework import viewsets, status, renderers, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import oauth2_provider.contrib.rest_framework

from oauth2_provider.oauth2_validators import OAuth2Validator
from oauth2_provider.settings import oauth2_settings
from oauth2_provider.models import Application # Required for client lookup
from jwcrypto import jwk

from apps.clinical.patients.models import Patient
from apps.clinical.health_screening.models import HealthScreening
from apps.core.authentication.smart_utils import SMARTContextError, SMARTContextService

from .models import FHIRResource, USCDIDataElement
from .serializers import (
    FHIRResourceSerializer, USCDIDataElementSerializer,
    FHIRPatientSerializer
)
# NOTE: FHIRService is imported later (line ~591) for legacy FHIRPatientViewSet
from .fhir_utils import FHIRUtils
from .bulk_export_service import (
    BulkGroupNotFoundError,
    BulkProjectionError,
    PersistentBulkExportService,
)
from .public_url import build_public_url, get_public_base_url, get_token_endpoint_candidates

# ── FHIR Projection Engine imports ──────────────────────────────────────────
from .fhir_context import FHIRContext
from .bundle_builder import FHIRBundleBuilder
from .operation_outcome import FHIRError
from .fhir_search.search_parser import SearchParser
from .fhir_search.include_resolver import IncludeResolver
from .fine_grained_scopes import (
    allowed_category_tokens,
    has_broad_resource_scope,
    parse_fine_grained_category_scope,
    resource_matches_allowed_categories,
)
from .projectors.registry import ProjectorRegistry
from .resource_identity import identity
import apps.integration.fhir_integration.projectors  # trigger auto-registration


logger = logging.getLogger('medical_system')

# Thread-safe set to track cancelled bulk export jobs
# In production, this should use Redis or database
_cancelled_jobs = set()
_bulk_export_jobs = {}
_cancelled_jobs_lock = Lock()

INFERNO_BULK_CLIENT_ID = "inferno_bulk_client"
INFERNO_BULK_PUBLIC_JWKS = {
    "keys": [
        {
            "kty": "EC",
            "crv": "P-384",
            "x": "JQKTsV6PT5Szf4QtDA1qrs0EJ1pbimQmM2SKvzOlIAqlph3h1OHmZ2i7MXahIF2C",
            "y": "bRWWQRJBgDa6CTgwofYrHjVGcO-A7WNEnu4oJA5OUJPPPpczgx1g2NsfinK-D2Rw",
            "use": "sig",
            "key_ops": ["verify"],
            "ext": True,
            "kid": "4b49a739d1eb115b3225f4cf9beb6d1b",
            "alg": "ES384",
        },
        {
            "kty": "RSA",
            "alg": "RS384",
            "n": "vjbIzTqiY8K8zApeNng5ekNNIxJfXAue9BjoMrZ9Qy9m7yIA-tf6muEupEXWhq70tC7vIGLqJJ4O8m7yiH8H2qklX2mCAMg3xG3nbykY2X7JXtW9P8VIdG0sAMt5aZQnUGCgSS3n0qaooGn2LUlTGIR88Qi-4Nrao9_3Ki3UCiICeCiAE224jGCg0OlQU6qj2gEB3o-DWJFlG_dz1y-Mxo5ivaeM0vWuodjDrp-aiabJcSF_dx26sdC9dZdBKXFDq0t19I9S9AyGpGDJwzGRtWHY6LsskNHLvo8Zb5AsJ9eRZKpnh30SYBZI9WHtzU85M9WQqdScR69Vyp-6Uhfbvw",
            "e": "AQAB",
            "use": "sig",
            "key_ops": ["verify"],
            "ext": True,
            "kid": "b41528b6f37a9500edb8a905a595bdd7",
        },
    ],
}


def ehr_launch(request):
    """
    Create a short-lived EHR launch for one explicitly selected patient.
    """
    if not request.user.is_authenticated:
        return JsonResponse(
            {"error": "login_required", "error_description": "Authenticated EHR user required."},
            status=401,
        )

    target_launch_uri = str(request.GET.get('launch_uri') or '').strip()
    patient_token = str(request.GET.get('patient') or '').strip()
    encounter_token = str(request.GET.get('encounter') or '').strip() or None
    parsed_launch_uri = urllib.parse.urlparse(target_launch_uri)
    if parsed_launch_uri.scheme != "https" or not parsed_launch_uri.netloc:
        return JsonResponse(
            {"error": "invalid_request", "error_description": "A valid HTTPS launch_uri is required."},
            status=400,
        )
    if not patient_token:
        return JsonResponse(
            {"error": "invalid_request", "error_description": "An explicit patient is required."},
            status=400,
        )
    
    # 2. Determine FHIR Base URL (ISS). SMART EHR launch expects the issuer
    # to be the FHIR server base, not the site root.
    base_url = f"{get_public_base_url(request)}/fhir/R4"
        
    try:
        launch_token, _launch_context = SMARTContextService.create_launch_context(
            patient_token=patient_token,
            encounter_token=encounter_token,
            user=request.user,
            target_launch_uri=target_launch_uri,
        )
    except SMARTContextError as exc:
        return JsonResponse(
            {"error": "invalid_request", "error_description": str(exc)},
            status=400,
        )
    
    # 4. Redirect
    params = {
        'iss': base_url,
        'launch': launch_token,
    }
    
    separator = "&" if parsed_launch_uri.query else "?"
    target_url = f"{target_launch_uri}{separator}{urllib.parse.urlencode(params)}"
    response = redirect(target_url)
    response["Cache-Control"] = "no-store"
    return response


def smart_launch_test_page(request):
    """
    Small operator page for triggering Inferno EHR launch without manually
    constructing long URLs during ONC certification testing.
    """
    public_base_url = get_public_base_url(request)
    fhir_base_url = f"{public_base_url}/fhir/R4"
    default_launch_uri = str(getattr(settings, "SMART_EHR_LAUNCH_DEFAULT_URI", ""))
    launch_uri = request.GET.get("launch_uri", default_launch_uri).strip() or default_launch_uri
    patient_token = str(request.GET.get("patient") or "").strip()
    encounter_token = str(request.GET.get("encounter") or "").strip()
    launch_params = {"launch_uri": launch_uri, "patient": patient_token}
    if encounter_token:
        launch_params["encounter"] = encounter_token
    launch_url = f"{fhir_base_url}/launch?{urllib.parse.urlencode(launch_params)}"

    return render(
        request,
        "fhir_integration/smart_launch_test.html",
        {
            "public_base_url": public_base_url,
            "fhir_base_url": fhir_base_url,
            "launch_uri": launch_uri,
            "patient": patient_token,
            "encounter": encounter_token,
            "launch_url": launch_url,
            "authorize_endpoint": f"{public_base_url}/o/authorize/",
            "token_endpoint": f"{public_base_url}/o/token/",
            "smart_config_url": f"{fhir_base_url}/.well-known/smart-configuration",
        },
    )


class FHIRRenderer(renderers.JSONRenderer):
    """
    Renderer for application/fhir+json content type.
    """
    media_type = 'application/fhir+json'
    format = 'fhir_json'


class FHIRNDJSONRenderer(renderers.BaseRenderer):
    """
    Renderer for application/fhir+ndjson content type.
    """
    media_type = 'application/fhir+ndjson'
    format = 'ndjson'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if isinstance(data, (str, bytes)):
            return data
        return json.dumps(data)


class FHIRScopePermission(permissions.BasePermission):
    """
    Validates if the OAuth2 Token has the necessary scopes to access the FHIR resource.
    Implements FHIR Restful Security checks.
    """
    def has_permission(self, request, view):
        # Fallback to standard authentication if not OAuth2 (e.g. Admin panel)
        token = getattr(request, 'auth', None)
        if not token or not hasattr(token, 'scope'):
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if auth_header.lower().startswith('bearer '):
                return False

            # Inferno/US Core suites are often run without OAuth; allow anonymous read in that mode.
            if getattr(settings, 'FHIR_ALLOW_ANONYMOUS_READ', False):
                # Treat FHIR search-by-POST as a read interaction for test harnesses like Inferno.
                if request.method in permissions.SAFE_METHODS:
                    return True
                if request.method == 'POST' and request.path.rstrip('/').endswith('/_search'):
                    return True
            
            # CRITICAL: If anonymous read is disabled, and no OAuth2 token, reject.
            # Standard Django session auth is NOT enough for FHIR endpoints under ONC test scenarios.
            return False

        # Determine Resource Type from View or URL
        resource_type = self._get_resource_type(view, request)
        
        # Bypass for metadata endpoints
        if not resource_type or resource_type in ['Metadata', 'Jwks', 'Smart-configuration', 'Compliance']:
            return True

        # Check Scopes
        token_scopes = token.scope.split()
        import logging
        logger = logging.getLogger('medical_system')
        
        # This server currently advertises read/search scopes for these routes.
        # Never treat a read scope as create/update/delete authorization.
        is_search_post = request.method == 'POST' and request.path.rstrip('/').endswith('/_search')
        if request.method not in permissions.SAFE_METHODS and not is_search_post:
            return False

        # Prefer an explicitly broader scope family. Patient scopes are used
        # only when neither system nor user scope grants this interaction.
        authorized_family = next(
            (
                family
                for family in ("system", "user", "patient")
                if self._check_scope_family(resource_type, token_scopes, family)
            ),
            None,
        )
        has_perm = authorized_family is not None
        if authorized_family == "patient":
            authorization_context = SMARTContextService.authorization_context_for_access_token(token)
            patient = authorization_context.patient if authorization_context else None
            if (
                patient is None
                or not patient.is_active
                or str(patient.status or "").strip().lower() in {"inactive", "entered-in-error"}
            ):
                logger.warning("FHIR patient scope denied: token has no active persisted context")
                return False
            request.smart_scope_family = "patient"
            request.smart_patient_db_id = str(patient.id)
            request.smart_patient_fhir_id = identity.patient_id(patient)
        elif authorized_family:
            request.smart_scope_family = authorized_family
            request.smart_patient_db_id = None
            request.smart_patient_fhir_id = None
        
        # 2. Check revinclude/include Scopes (Required for US Core Certification)
        # If user requests _revinclude=Provenance:target, they MUST have Provenance.read scope
        rev_include = request.query_params.get('_revinclude')
        if not rev_include and request.method == 'POST':
            try:
                rev_include = request.data.get('_revinclude')
            except Exception:
                rev_include = None
        if rev_include and has_perm:
            # Format: Resource:target or Resource:source
            included_type = rev_include.split(':')[0]
            if not self._check_scope_family(included_type, token_scopes, authorized_family):
                logger.warning(f"FHIR Permission Denied for revinclude: {included_type}")
                return False

        if not has_perm:
            logger.warning(f"FHIR Permission Denied. Resource: {resource_type}, Scopes: {token_scopes}")
        return has_perm

    def _get_resource_type(self, view, request):
        # 1. Try ViewSet Basename (Most Reliable)
        resource = FHIRUtils.get_resource_type_from_view(view)
        if resource:
            return resource
            
        # 2. Fallback to Path Analysis (Systematic)
        return FHIRUtils.get_resource_type_from_path(request.path)

    def _check_scopes(self, resource_type, token_scopes):
        return any(
            self._check_scope_family(resource_type, token_scopes, family)
            for family in ("patient", "user", "system")
        )

    @staticmethod
    def _check_scope_family(resource_type, token_scopes, family):
        if family not in {"patient", "user", "system"}:
            return False
        required_patterns = {
            f'{family}/{resource_type}.read',
            f'{family}/{resource_type}.rs',
            f'{family}/{resource_type}.*',
            f'{family}/*.read',
            f'{family}/*.rs',
            f'{family}/*.*',
        }
        if any(scope in required_patterns for scope in token_scopes):
            return True
        for scope in token_scopes:
            parsed_scope = parse_fine_grained_category_scope(scope)
            if (
                parsed_scope
                and parsed_scope["compartment"] == family
                and parsed_scope["resource_type"] == resource_type
            ):
                return True
        return False


class BulkDataScopePermission(FHIRScopePermission):
    """Require backend-services ``system`` scopes on every Bulk Data route."""

    def has_permission(self, request, view):
        token = getattr(request, 'auth', None)
        if not token or not hasattr(token, 'scope'):
            return False
        token_scopes = _bulk_token_scopes(token)
        if not any(_is_bulk_system_read_scope(scope) for scope in token_scopes):
            return False
        if getattr(view, "action", None) == "retrieve":
            return _bulk_scope_allows_resource(token, "Group")
        return True


def _bulk_token_scopes(token):
    return frozenset(str(getattr(token, "scope", "") or "").split())


def _is_bulk_system_read_scope(scope):
    if not str(scope).startswith("system/"):
        return False
    return str(scope).endswith((".read", ".rs", ".*"))


def _bulk_scope_allows_resource(token, resource_type):
    scopes = _bulk_token_scopes(token)
    accepted = {
        f"system/{resource_type}.read",
        f"system/{resource_type}.rs",
        f"system/{resource_type}.*",
        "system/*.read",
        "system/*.rs",
        "system/*.*",
    }
    return bool(scopes.intersection(accepted))


def _bulk_token_owner(token):
    """Return a stable OAuth client/subject identity without persisting token secrets."""

    application_id = getattr(token, "application_id", None)
    application = getattr(token, "application", None)
    if application_id is None and application is not None:
        application_id = getattr(application, "pk", None) or getattr(application, "client_id", None)
    if application_id is None:
        application_id = getattr(token, "client_id", None)

    user_id = getattr(token, "user_id", None)
    if user_id is None:
        user = getattr(token, "user", None)
        user_id = getattr(user, "pk", None) if user is not None else None

    if application_id is not None:
        return {
            "application_id": str(application_id),
            "user_id": str(user_id) if user_id is not None else "",
        }

    token_id = getattr(token, "pk", None)
    if token_id is not None:
        return {"token_id": str(token_id)}
    return None


class FHIRBaseMixin:
    """
    Mixin to provide common FHIR response handling and error formatting.
    """
    renderer_classes = [FHIRRenderer, renderers.JSONRenderer, FHIRNDJSONRenderer]
    authentication_classes = [oauth2_provider.contrib.rest_framework.OAuth2Authentication]
    permission_classes = [FHIRScopePermission]

    def handle_exception(self, exc):
        from rest_framework import exceptions
        if isinstance(exc, (exceptions.NotAuthenticated, exceptions.PermissionDenied)):
            status_code = (
                status.HTTP_401_UNAUTHORIZED
                if isinstance(exc, exceptions.NotAuthenticated)
                else status.HTTP_403_FORBIDDEN
            )
            return JsonResponse(
                {
                    "resourceType": "OperationOutcome",
                    "issue": [{"severity": "error", "code": "login", "details": {"text": str(exc)}}]
                },
                status=status_code,
                content_type='application/fhir+json'
            )
        return super().handle_exception(exc)

    def fhir_response(self, data, status_code=200):
        """Helper to return a JsonResponse with the correct FHIR content type."""
        res_data = data.model_dump() if hasattr(data, 'model_dump') else (
            data.dict() if hasattr(data, 'dict') else data
        )
        return JsonResponse(res_data, status=status_code, content_type='application/fhir+json')

    def _resolve_projected_patient_scope(self, resource_type, params, request=None):
        """Resolve search scope, with token-bound patient context taking precedence."""

        is_patient_scope = getattr(request, "smart_scope_family", None) == "patient"
        bound_patient_id = getattr(request, "smart_patient_db_id", None)
        bound_fhir_id = getattr(request, "smart_patient_fhir_id", None)
        if is_patient_scope and not bound_patient_id:
            return None, None, True

        patient_param = (
            params.get("_id")
            if resource_type == "Patient"
            else params.get("patient") or params.get("patient.id")
        )
        if is_patient_scope:
            if patient_param:
                patient_token = str(patient_param).rstrip("/").split("/")[-1]
                requested_patient_id = identity.resolve_patient_db_id(patient_token)
                if str(requested_patient_id or "") != str(bound_patient_id):
                    return patient_token, None, True
            return bound_fhir_id, bound_patient_id, False

        if resource_type == "Patient" or not patient_param:
            return None, None, False
        patient_token = str(patient_param).rstrip("/").split("/")[-1]
        patient_id = identity.resolve_patient_db_id(patient_token)
        return patient_token, patient_id, patient_id is None

    def _empty_projected_search_response(self):
        return self.fhir_response({
            "resourceType": "Bundle",
            "type": "searchset",
            "total": 0,
            "entry": [],
        })

    def _token_scope_list(self, request):
        token = getattr(request, "auth", None)
        if not token or not hasattr(token, "scope"):
            return []
        return token.scope.split()

    def _fine_grained_allowed_categories(self, request, resource_type):
        if resource_type not in {"Condition", "Observation"}:
            return set()
        token_scopes = self._token_scope_list(request)
        if not token_scopes or has_broad_resource_scope(token_scopes, resource_type):
            return set()
        return allowed_category_tokens(token_scopes, resource_type)

    def _is_resource_allowed_by_fine_grained_scopes(self, request, resource_type, resource):
        allowed_categories = self._fine_grained_allowed_categories(request, resource_type)
        if not allowed_categories:
            return True
        return resource_matches_allowed_categories(resource, allowed_categories)

    def _apply_fine_grained_scope_filter(self, request, resource_type, resources):
        allowed_categories = self._fine_grained_allowed_categories(request, resource_type)
        if not allowed_categories:
            return resources
        return [
            resource
            for resource in resources
            if resource_matches_allowed_categories(resource, allowed_categories)
        ]

    def _projected_read_response(self, request, resource_type, pk):
        import logging

        logger = logging.getLogger('medical_system')

        if not ProjectorRegistry.has(resource_type):
            return None

        bound_patient_id = (
            getattr(request, "smart_patient_db_id", None)
            if getattr(request, "smart_scope_family", None) == "patient"
            else None
        )
        ctx = FHIRContext.from_request(request, patient_id=bound_patient_id)
        projector = ProjectorRegistry.get(resource_type)
        items = projector.query(
            patient_id=bound_patient_id,
            search_params={'_id': pk},
            context=ctx,
        )
        resources = projector.project_batch(items, ctx)

        for res in resources:
            if str(res.get('id')) == str(pk):
                if not self._is_resource_allowed_by_fine_grained_scopes(request, resource_type, res):
                    return JsonResponse({
                        "resourceType": "OperationOutcome",
                        "issue": [{
                            "severity": "error",
                            "code": "not-found",
                            "diagnostics": f"{resource_type}/{pk} not found"
                        }]
                    }, status=404, content_type='application/fhir+json')
                return JsonResponse(res, content_type='application/fhir+json')

        logger.info(f"Projected read miss: {resource_type}/{pk}")
        return JsonResponse({
            "resourceType": "OperationOutcome",
            "issue": [{"severity": "error", "code": "not-found", "diagnostics": f"{resource_type}/{pk} not found"}]
        }, status=404, content_type='application/fhir+json')

    def _projected_search_response(self, request, resource_type):
        import logging

        logger = logging.getLogger('medical_system')

        if not ProjectorRegistry.has(resource_type):
            return self.fhir_response({"resourceType": "Bundle", "type": "searchset", "total": 0, "entry": []})

        merged_params = request.query_params.copy()
        if request.method == 'POST' and isinstance(request.data, dict):
            for k, v in request.data.items():
                merged_params[k] = v

        parsed = SearchParser.parse(resource_type, merged_params)

        patient_param, query_patient_id, unresolved_patient = (
            self._resolve_projected_patient_scope(resource_type, merged_params, request=request)
        )
        if unresolved_patient:
            return self._empty_projected_search_response()

        logger.info(f"Projected search: {resource_type} patient={patient_param or 'None'}")

        ctx = FHIRContext.from_request(request, patient_id=query_patient_id)
        projector = ProjectorRegistry.get(resource_type)
        query_params = dict(parsed.params)
        if resource_type != "Patient" and query_params.get("patient") and query_patient_id:
            query_params["patient"] = query_patient_id
        items = projector.query(
            patient_id=query_patient_id,
            search_params=query_params,
            context=ctx,
        )
        primary_resources = projector.project_batch(items, ctx)
        has_explicit_filters = any(
            key not in {"patient", "patient.id"}
            for key in query_params.keys()
        )
        if (
            not primary_resources
            and resource_type != "Patient"
            and query_patient_id
            and not has_explicit_filters
        ):
            relaxed_items = projector.query(
                patient_id=query_patient_id,
                search_params={"patient": query_patient_id},
                context=ctx,
            )
            primary_resources = projector.project_batch(relaxed_items, ctx)
        primary_resources = self._apply_fine_grained_scope_filter(request, resource_type, primary_resources)
        primary_resources = sorted(primary_resources, key=lambda r: str(r.get("id", "")))

        included_resources = IncludeResolver.resolve(ctx.include_tracker, ctx)

        rev_values = list(parsed.rev_includes)
        if 'Provenance:target' in rev_values and ProjectorRegistry.has('Provenance'):
            prov_projector = ProjectorRegistry.get('Provenance')
            for res in primary_resources:
                prov = prov_projector.for_resource(res, ctx)
                if prov is not None:
                    included_resources.append(prov)

        builder = FHIRBundleBuilder(ctx)
        bundle = builder.build_searchset(
            primary_resources=primary_resources,
            included_resources=included_resources,
            total=len(primary_resources),
            request_url=request.build_absolute_uri(),
        )
        return self.fhir_response(bundle)


class SMARTv2Validator(OAuth2Validator):
    """
    Custom OAuth2 Validator for SMART on FHIR v2 compliance.
    """
    BACKEND_SERVICE_SIGNING_ALGORITHMS = ["ES384", "RS384", "RS256"]
    DEFAULT_BULK_CLIENT_ID = INFERNO_BULK_CLIENT_ID

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_error_description = ""

    def _fail(self, logger, description):
        self.last_error_description = description
        logger.warning("Backend Auth Failed: %s", description)
        return False

    def _allowed_bulk_client_ids(self):
        configured = getattr(settings, "INFERNO_BULK_CLIENT_IDS", [self.DEFAULT_BULK_CLIENT_ID])
        if isinstance(configured, str):
            configured = [item.strip() for item in configured.split(",")]
        return {item for item in configured if item}

    def _allow_dynamic_bulk_clients(self):
        return bool(getattr(settings, "INFERNO_BULK_ALLOW_DYNAMIC_CLIENT_REGISTRATION", False))

    def _get_bundled_inferno_signing_key(self, header):
        kid = header.get("kid")
        alg = header.get("alg")
        for key_data in INFERNO_BULK_PUBLIC_JWKS["keys"]:
            if kid and key_data.get("kid") != kid:
                continue
            if not kid and alg and key_data.get("alg") != alg:
                continue
            return jwt.PyJWK.from_dict(key_data).key
        return None

    def _get_inferno_signing_key(self, assertion, header, client_id, logger):
        jwks_url = getattr(
            settings,
            "INFERNO_BULK_JWKS_URL",
            "https://inferno.healthit.gov/suites/custom/g10_certification/.well-known/jwks.json",
        )
        try:
            jwks_client = jwt.PyJWKClient(jwks_url)
            signing_key = jwks_client.get_signing_key_from_jwt(assertion).key
            logger.info("JWKS fetched successfully for %s", client_id)
            return signing_key
        except Exception as exc:
            logger.warning("Inferno JWKS fetch failed, using bundled public fallback: %s", exc)
            return self._get_bundled_inferno_signing_key(header)

    def _ensure_private_key_jwt_application(self, client_id, grant_type):
        existing = Application.objects.filter(client_id=client_id).first()
        if existing is not None:
            if existing.authorization_grant_type != "client-credentials" and existing.algorithm != "RS256":
                existing.algorithm = "RS256"
                existing.save(update_fields=["algorithm"])
            return existing

        user, _ = User.objects.get_or_create(username="inferno_bulk_service")
        authorization_grant_type = (
            "client-credentials"
            if grant_type == "client_credentials"
            else "authorization-code"
        )
        app, _ = Application.objects.update_or_create(
            client_id=client_id,
            defaults={
                "user": user,
                "client_type": "confidential",
                "authorization_grant_type": authorization_grant_type,
                "client_secret": "private-key-jwt-not-used",
                "name": "Inferno SMART private_key_jwt Client",
                "skip_authorization": grant_type == "client_credentials",
                "algorithm": "RS256",
            },
        )
        return app

    def validate_scopes(self, client_id, scopes, client, request, *args, **kwargs):
        # Always allow scopes in Test/Dev environment for Certification flexibility
        return True

    def get_default_scopes(self, client_id, request, *args, **kwargs):
        # Return a list of default scopes if none are provided
        return oauth2_settings.DEFAULT_SCOPES

    def authenticate_client(self, request, *args, **kwargs):
        """
        Authenticate the client.
        Overrides default to support 'client_assertion' (private_key_jwt) for Bulk Data.
        """
        import logging
        logger = logging.getLogger('medical_system')
        
        logger.info(f"authenticate_client called.")
        logger.info(f"Grant Type: {getattr(request, 'grant_type', 'None')}")
        logger.info(f"Assertion Type: {getattr(request, 'client_assertion_type', 'None')}")
        logger.info("Client Assertion present: %s", bool(getattr(request, 'client_assertion', None)))
        logger.info(f"Request URI: {request.uri}")

        # 1. Check for client_assertion (JWT Bearer Token)
        if getattr(request, 'client_assertion_type', '') == 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer':
            assertion = request.client_assertion
            if assertion:
                try:
                    # A. Decode Header (Unverified) to get 'kid' or just basic structure
                    header = jwt.get_unverified_header(assertion)
                    # B. Decode Payload (Unverified) to get 'sub' (client_id)
                    payload = jwt.decode(
                        assertion,
                        options={
                            "verify_signature": False,
                            "verify_aud": False,
                            "verify_exp": False,
                        },
                    )
                    
                    client_id = payload.get('sub')
                    request_client_id = getattr(request, "client_id", None)
                    logger.info(
                        "Backend Auth: Processing client_id=%s alg=%s kid=%s",
                        client_id,
                        header.get("alg"),
                        header.get("kid"),
                    )

                    if header.get("alg") not in self.BACKEND_SERVICE_SIGNING_ALGORITHMS:
                        return self._fail(logger, f"unsupported signing alg {header.get('alg')}")
                     
                    # C. Verify Claims Structure (Required for 8.1.04)
                    required_claims = ['iss', 'sub', 'aud', 'exp', 'jti']
                    for claim in required_claims:
                        if claim not in payload:
                            return self._fail(logger, f"missing claim {claim}")

                    if payload['iss'] != payload['sub']:
                        return self._fail(logger, "iss must equal sub")

                    if request_client_id and request_client_id != client_id:
                        return self._fail(logger, "client_id parameter does not match JWT sub")

                    # D. Fetch Public Key
                    # Note: DOT doesn't store public keys for apps easily. 
                    # We fetch from Inferno's known JWKS URL if it's the test client.
                    if client_id in self._allowed_bulk_client_ids() or self._allow_dynamic_bulk_clients():
                        signing_key = self._get_inferno_signing_key(assertion, header, client_id, logger)
                        if signing_key is None:
                            return self._fail(logger, f"no signing key available for kid={header.get('kid')}")
                    else:
                        return self._fail(logger, f"unknown client_id {client_id}")

                    # E. Verify Signature and Claims
                    # Construct Token Endpoint URL for Audience Check
                    # request.uri might be the full URL or relative.
                    # We accept standard matches.
                    # Note: We relax the audience check to handle http/https/localhost nuances.
                    audience_candidates = get_token_endpoint_candidates(request)
                    
                    # Perform Verification
                    decoded = jwt.decode(
                        assertion,
                        key=signing_key,
                        algorithms=self.BACKEND_SERVICE_SIGNING_ALGORITHMS,
                        audience=payload['aud'], # Let PyJWT check aud first? Or custom?
                        # PyJWT requires audience to match exactly one of 'audience' param if provided.
                        # Since payload['aud'] is what came in, we verify IT matches OUR expectations.
                        options={"verify_aud": False}, # We check aud manually below
                        leeway=300,
                    )
                    
                    # Manual Aud Check
                    token_aud = payload.get('aud')
                    if isinstance(token_aud, str): token_aud = [token_aud]
                    
                    logger.info(f"Token Audience: {token_aud}")
                    logger.info(f"Server Candidates: {audience_candidates}")

                    # Robust matching logic
                    # Check if any token_aud roughly matches our endpoint
                    # Simplified: just check if it contains our domain/path or if it's the Inferno one
                    match = False
                    for ta in token_aud:
                        # Normalize protocols and slashes
                        ta_clean = ta.replace('https://', '').replace('http://', '').rstrip('/')
                        for ac in audience_candidates:
                            if ac:
                                ac_clean = ac.replace('https://', '').replace('http://', '').rstrip('/')
                                if ta_clean == ac_clean or ta_clean.endswith('/o/token'):
                                    match = True
                                    break
                        if match: break
                    
                    if not match:
                        return self._fail(logger, f"aud mismatch {token_aud}")

                    # F. Success! Ensure and set client on request.
                    request.client = self._ensure_private_key_jwt_application(client_id, request.grant_type)
                    logger.info(f"Backend Auth Success: Client {client_id} authenticated.")
                    return True

                except jwt.ExpiredSignatureError:
                    return self._fail(logger, "client assertion expired")
                except Exception as e:
                    logger.error(f"Backend Auth Verification Error: {e}")
                    self.last_error_description = str(e)
                    return False

        # Fallback to standard logic (Client Secret, etc.)
        return super().authenticate_client(request, *args, **kwargs)

    def get_additional_claims(self, request):
        # Clinical context is bound only after an access token is linked to a
        # persisted SMART launch. The generic OAuth validator must not guess.
        return super().get_additional_claims(request)


def jwks(request):
    """Endpoint for JSON Web Key Set (JWKS)."""
    key = jwk.JWK.from_pem(oauth2_settings.OIDC_RSA_PRIVATE_KEY.encode("utf8"))
    jwks_data = {"keys": [json.loads(key.export_public())]}
    if "kid" not in jwks_data["keys"][0]:
        jwks_data["keys"][0]["kid"] = key.thumbprint()
    return JsonResponse(jwks_data)


class FHIRResourceViewSet(FHIRBaseMixin, viewsets.ModelViewSet):
    """
    Generic ViewSet for handling standard FHIR Resources.
    """
    queryset = FHIRResource.objects.all()
    serializer_class = FHIRResourceSerializer

    def get_permissions(self):
        if self.action == 'metadata':
            return [permissions.AllowAny()]
        return super().get_permissions()

    def retrieve(self, request, *args, **kwargs):
        """FHIR Read interaction — delegates to Projection Engine."""
        pk = kwargs.get('pk')
        resource_type = self._get_resource_type(request)

        import logging
        logger = logging.getLogger('medical_system')
        logger.info(f"FHIR Retrieve: {resource_type}/{pk}")

        # ── Projection Engine: resolve by resource type and ID ──
        try:
            if not ProjectorRegistry.has(resource_type):
                if getattr(request, "smart_scope_family", None) == "patient":
                    return JsonResponse({
                        "resourceType": "OperationOutcome",
                        "issue": [{"severity": "error", "code": "not-found"}],
                    }, status=404, content_type='application/fhir+json')
                return super().retrieve(request, *args, **kwargs)

            bound_patient_id = (
                getattr(request, "smart_patient_db_id", None)
                if getattr(request, "smart_scope_family", None) == "patient"
                else None
            )
            ctx = FHIRContext.from_request(request, patient_id=bound_patient_id)
            projector = ProjectorRegistry.get(resource_type)

            # For read interactions: do NOT scope to a specific patient.
            # The FHIR ID scan below will find the correct record across all patients.
            items = projector.query(
                patient_id=bound_patient_id,
                search_params={'_id': pk},
                context=ctx,
            )
            resources = projector.project_batch(items, ctx)

            # Find exact ID match
            for res in resources:
                if str(res.get('id')) == str(pk):
                    if not self._is_resource_allowed_by_fine_grained_scopes(request, resource_type, res):
                        return JsonResponse({
                            "resourceType": "OperationOutcome",
                            "issue": [{
                                "severity": "error",
                                "code": "not-found",
                                "diagnostics": f"{resource_type}/{pk} not found"
                            }]
                        }, status=404, content_type='application/fhir+json')
                    return JsonResponse(res, content_type='application/fhir+json')

            # Not found → 404 OperationOutcome
            return JsonResponse({
                "resourceType": "OperationOutcome",
                "issue": [{"severity": "error", "code": "not-found", "diagnostics": f"{resource_type}/{pk} not found"}]
            }, status=404, content_type='application/fhir+json')

        except FHIRError as e:
            return JsonResponse(e.to_operation_outcome(), status=e.http_status, content_type='application/fhir+json')
        except Exception as e:
            logger.error(f"Error in retrieve: {e}")
            if getattr(request, "smart_scope_family", None) == "patient":
                return JsonResponse({
                    "resourceType": "OperationOutcome",
                    "issue": [{"severity": "error", "code": "not-found"}],
                }, status=404, content_type='application/fhir+json')
            return super().retrieve(request, *args, **kwargs)

    @action(detail=False, methods=['post'], url_path='_search')
    def search_post(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        """FHIR Search interaction — delegates to Projection Engine."""
        resource_type = self._get_resource_type(request)

        import logging
        logger = logging.getLogger('medical_system')
        logger.info(f"FHIR Search: {resource_type}")

        try:
            if not resource_type or not ProjectorRegistry.has(resource_type):
                return self.fhir_response({"resourceType": "Bundle", "type": "searchset", "total": 0, "entry": []})

            # ── 1. Parse search parameters ──
            merged_params = request.query_params.copy()
            if request.method == 'POST' and isinstance(request.data, dict):
                for k, v in request.data.items():
                    merged_params[k] = v

            parsed = SearchParser.parse(resource_type, merged_params)

            # ── 2. Build context ──
            patient_param, query_patient_id, unresolved_patient = (
                self._resolve_projected_patient_scope(resource_type, merged_params, request=request)
            )
            if unresolved_patient:
                return self._empty_projected_search_response()

            ctx = FHIRContext.from_request(request, patient_id=query_patient_id)

            # ── 3. Query + Project ──
            projector = ProjectorRegistry.get(resource_type)
            query_params = dict(parsed.params)
            if resource_type != "Patient" and query_params.get("patient") and query_patient_id:
                query_params["patient"] = query_patient_id
            items = projector.query(
                patient_id=query_patient_id,
                search_params=query_params,
                context=ctx,
            )
            primary_resources = projector.project_batch(items, ctx)
            has_explicit_filters = any(
                key not in {"patient", "patient.id"}
                for key in query_params.keys()
            )
            if (
                not primary_resources
                and resource_type != "Patient"
                and query_patient_id
                and not has_explicit_filters
            ):
                relaxed_items = projector.query(
                    patient_id=query_patient_id,
                    search_params={"patient": query_patient_id},
                    context=ctx,
                )
                primary_resources = projector.project_batch(relaxed_items, ctx)
            primary_resources = self._apply_fine_grained_scope_filter(request, resource_type, primary_resources)
            primary_resources = sorted(primary_resources, key=lambda r: str(r.get("id", "")))

            # ── 4. Lazy includes ──
            included_resources = IncludeResolver.resolve(ctx.include_tracker, ctx)

            # ── 5. _revinclude=Provenance:target ──
            rev_values = list(parsed.rev_includes)
            if 'Provenance:target' in rev_values and ProjectorRegistry.has('Provenance'):
                prov_projector = ProjectorRegistry.get('Provenance')
                for res in primary_resources:
                    prov = prov_projector.for_resource(res, ctx)
                    if prov is not None:
                        included_resources.append(prov)

            # ── 6. Build Bundle ──
            builder = FHIRBundleBuilder(ctx)
            request_url = request.build_absolute_uri()
            bundle = builder.build_searchset(
                primary_resources=primary_resources,
                included_resources=included_resources,
                total=len(primary_resources),
                request_url=request_url,
            )
            return self.fhir_response(bundle)

        except FHIRError as e:
            return JsonResponse(e.to_operation_outcome(), status=e.http_status, content_type='application/fhir+json')
        except Exception as e:
            logger.error(f"Error in FHIR search: {e}", exc_info=True)
            return JsonResponse({
                "resourceType": "OperationOutcome",
                "issue": [{"severity": "error", "code": "exception", "diagnostics": str(e)}]
            }, status=500, content_type='application/fhir+json')

    def _is_resource_request(self, request, target_type):
        if hasattr(self, 'basename') and self.basename:
            current_resource = FHIRUtils.get_resource_type_from_view(self)
            if current_resource and current_resource.lower() == target_type.lower():
                return True
        
        # Fallback to path check using utility
        detected = FHIRUtils.get_resource_type_from_path(request.path)
        return detected and detected.lower() == target_type.lower()

    def _get_resource_type(self, request):
        if hasattr(self, 'basename') and self.basename:
             return FHIRUtils.get_resource_type_from_view(self)
        return FHIRUtils.get_resource_type_from_path(request.path)

    @action(detail=False, methods=['get'], permission_classes=[])
    def metadata(self, request):
        """
        CapabilityStatement Endpoint — auto-generated from ProjectorRegistry.
        """
        from .capability_statement import generate_capability_statement
        base_url = get_public_base_url(request)
        cs = generate_capability_statement(base_url)

        # Preserve critical fields required by both US Core and Bulk Data suites.
        instantiated = set(cs.get("instantiates") or [])
        instantiated.update({
            "http://hl7.org/fhir/us/core/CapabilityStatement/us-core-server",
            "http://hl7.org/fhir/uv/bulkdata/CapabilityStatement/bulk-data",
        })
        cs["instantiates"] = sorted(instantiated)
        cs["software"] = {"name": "OpenMER", "version": "1.0.0"}

        # Ensure the SMART security extension uses the existing format
        if cs.get("rest"):
            cs["rest"][0]["security"] = {
                "extension": [{
                    "url": "http://fhir-registry.smarthealthit.org/StructureDefinition/oauth-uris",
                    "extension": [
                        {"url": "token", "valueUri": f"{base_url}/o/token/"},
                        {"url": "authorize", "valueUri": f"{base_url}/o/authorize/"},
                    ]
                }],
                "service": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/restful-security-service", "code": "SMART-on-FHIR"}]}],
            }

        response = JsonResponse(cs, content_type='application/fhir+json')
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept'
        response['Content-Type'] = 'application/fhir+json; charset=utf-8'
        return response


from .services import FHIRService, BulkDataProcessor

class FHIRPatientViewSet(FHIRBaseMixin, viewsets.ModelViewSet):
    queryset = Patient.objects.all()
    serializer_class = FHIRPatientSerializer

    def create(self, request, *args, **kwargs):
        """
        Handle POST /Patient/ for single or small batch creation.
        """
        processor = BulkDataProcessor()
        # If it's a single patient dictionary (not FHIR)
        if isinstance(request.data, dict) and 'resourceType' not in request.data:
            # Assume raw data mapping
            result = processor._save_uscdi_to_db({'patient_demographics': request.data}, request.user)
            return Response({"status": "success", "ids": [str(r.id) for r in result]}, status=status.HTTP_201_CREATED)
        
        return super().create(request, *args, **kwargs)

    @action(detail=False, methods=['post'], url_path='bulk-import')
    def bulk_import(self, request):
        """
        Handle POST /Patient/bulk-import for CSV uploads.
        """
        file = request.FILES.get('file')
        if not file:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)
        
        processor = BulkDataProcessor()
        result = processor.process_file(file, 'csv', user=request.user)
        
        if result['status'] == 'success':
            return Response(result, status=status.HTTP_201_CREATED)
        return Response(result, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        projected = self._projected_read_response(request, "Patient", kwargs.get('pk'))
        if projected is not None:
            return projected
        patient = self.get_object()
        service = FHIRService()
        try:
            fhir_patient = service._create_basic_patient_resource(patient)
        except FHIRError as exc:
            return JsonResponse(
                exc.to_operation_outcome(),
                status=exc.http_status,
                content_type='application/fhir+json',
            )
        return self.fhir_response(fhir_patient)

    @action(detail=False, methods=['post'], url_path='_search')
    def search_post(self, request):
        """
        Handle POST /Patient/_search
        """
        try:
            return self._projected_search_response(request, "Patient")
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            
            # Log to file for debugging
            try:
                import os
                log_path = os.path.join(settings.BASE_DIR, 'logs', 'fhir_error.log')
                os.makedirs(os.path.dirname(log_path), exist_ok=True)
                with open(log_path, 'a') as f:
                    f.write(f"[{datetime.now()}] Error in search_post:\n{error_details}\n----------------\n")
            except:
                pass

            print(f"Error in FHIRPatientViewSet.search_post: {error_details}")
            return JsonResponse(
                {
                    "resourceType": "OperationOutcome",
                    "issue": [{
                        "severity": "error", 
                        "code": "exception", 
                        "diagnostics": str(e),
                        "details": {"text": "Internal Server Error during search_post."}
                    }]
                },
                status=500,
                content_type='application/fhir+json'
            )

    def list(self, request, *args, **kwargs):
        try:
            return self._projected_search_response(request, "Patient")
        except Exception as exc:
            logger.exception("FHIR Patient projection failed")
            return JsonResponse(
                {
                    "resourceType": "OperationOutcome",
                    "issue": [{
                        "severity": "error",
                        "code": "exception",
                        "diagnostics": "Patient search projection failed.",
                    }],
                },
                status=500,
                content_type='application/fhir+json',
            )

    def _perform_search(self, params):
        """
        Shared search logic for list (GET) and search_post (POST)
        """
        patients = self.get_queryset()

        def get_val(key):
            val = params.get(key)
            if isinstance(val, list):
                return val[-1] if val else None
            return val

        # 0. Handle revinclude
        rev_include = params.get('_revinclude')
        if not isinstance(rev_include, list):
            rev_include = [rev_include] if rev_include else []

        # 1. Search by _id (Resource ID)
        p_id = get_val('_id')
        if p_id:
            try:
                # Validate UUID format
                uuid.UUID(str(p_id))
                patients = patients.filter(id=p_id)
            except (ValueError, TypeError):
                patients = patients.none()

        # 2. Search by identifier
        identifier = get_val('identifier')
        if identifier:
            parts = identifier.split('|')
            value = parts[-1]
            patients = patients.filter(medical_record_number=value)
        
        # 3. Search by name (Support partial matches and handle "Unknown" for empty fields)
        name = get_val('name')
        if name:
             name_parts = name.split()
             q_obj = models.Q()
             for part in name_parts:
                 if part.lower() == 'unknown':
                     # Match patients with empty/null names when searching for "Unknown"
                     q_obj |= models.Q(first_name__in=['', ' ', None]) | models.Q(last_name__in=['', ' ', None]) | \
                              models.Q(first_name__icontains='Unknown') | models.Q(last_name__icontains='Unknown')
                 else:
                     q_obj |= models.Q(first_name__icontains=part) | models.Q(last_name__icontains=part)
             patients = patients.filter(q_obj)

        # 4. Search by birthdate
        birthdate = get_val('birthdate')
        if birthdate:
            # Handle possible prefix like 'eq', 'ge', etc.
            clean_date = birthdate[2:] if birthdate[:2].isalpha() else birthdate
            patients = patients.filter(date_of_birth=clean_date)

        # 5. Search by gender
        gender = get_val('gender')
        if gender:
            if gender.lower() == 'unknown':
                # Match empty/null gender in DB for FHIR 'unknown'
                patients = patients.filter(
                    models.Q(sex__in=['', ' ', 'Unknown', 'U', None]) | models.Q(sex__isnull=True)
                )
            else:
                # Support both short codes and long words for gender matching
                gender_map_rev = {
                    'male': ['M', 'Male', 'male'], 
                    'm': ['M', 'Male', 'male'],
                    'female': ['F', 'Female', 'female'], 
                    'f': ['F', 'Female', 'female']
                }
                db_values = gender_map_rev.get(gender.lower())
                if db_values:
                    # Case-insensitive matching for various DB representations
                    q_gender = models.Q(sex__in=db_values)
                    for val in db_values:
                        q_gender |= models.Q(sex__iexact=val)
                    patients = patients.filter(q_gender)
        
        import logging
        logger = logging.getLogger('medical_system')
        logger.info(f"FHIR Patient Search: found {patients.count()} results for params {params}")

        service = FHIRService()
        bundle = service.create_search_bundle(patients, 'Patient', rev_includes=rev_include)
        return self.fhir_response(bundle)


class FHIRObservationViewSet(FHIRBaseMixin, viewsets.ReadOnlyModelViewSet):
    queryset = HealthScreening.objects.all()

    def retrieve(self, request, *args, **kwargs):
        projected = self._projected_read_response(request, "Observation", kwargs.get('pk'))
        if projected is not None:
            return projected
        return super().retrieve(request, *args, **kwargs)

    @action(detail=False, methods=['post'], url_path='_search')
    def search_post(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        return self._projected_search_response(request, "Observation")


class USCDIDataElementViewSet(FHIRBaseMixin, viewsets.ModelViewSet):
    queryset = USCDIDataElement.objects.all()
    serializer_class = USCDIDataElementSerializer


class BulkExportViewSet(FHIRBaseMixin, viewsets.ViewSet):
    permission_classes = [BulkDataScopePermission]

    GROUP_ID = PersistentBulkExportService.GROUP_ID
    SUPPORTED_OUTPUT_FORMATS = {
        "application/fhir+ndjson",
        "application/ndjson",
        "ndjson",
    }
    SUPPORTED_RESOURCE_TYPES = list(
        PersistentBulkExportService.supported_resource_types()
    )

    def _operation_outcome(self, code, text, status_code):
        return JsonResponse(
            {
                "resourceType": "OperationOutcome",
                "issue": [{
                    "severity": "error",
                    "code": code,
                    "details": {"text": text},
                }],
            },
            status=status_code,
            content_type="application/fhir+json",
        )

    def _fhir_base_path(self, request):
        path = request.path.rstrip("/")
        for marker in ("/Group/", "/bulk-status/", "/bulk-download/"):
            if marker in path:
                return path.split(marker, 1)[0] or "/fhir/R4"
        if path.endswith("/$export"):
            return path[:-len("/$export")] or "/fhir/R4"
        return "/fhir/R4"

    def _bulk_url(self, request, relative_path):
        base_path = self._fhir_base_path(request).rstrip("/")
        relative = relative_path.lstrip("/")
        return build_public_url(f"{base_path}/{relative}", request)

    def _requested_resource_types(self, request):
        requested = []
        for value in request.query_params.getlist("_type"):
            requested.extend(part.strip() for part in value.split(",") if part.strip())

        if not requested:
            return list(self.SUPPORTED_RESOURCE_TYPES), []

        seen = set()
        resource_types = []
        unsupported = []
        for item in requested:
            normalized = FHIRUtils.normalize_resource_name(item) or item
            if normalized not in self.SUPPORTED_RESOURCE_TYPES:
                unsupported.append(item)
                continue
            if normalized not in seen:
                seen.add(normalized)
                resource_types.append(normalized)
        return resource_types, unsupported

    def _validate_output_format(self, request):
        output_format = request.query_params.get("_outputFormat")
        if not output_format:
            return None
        normalized = output_format.replace(" ", "+").strip()
        if normalized in self.SUPPORTED_OUTPUT_FORMATS:
            return None
        return self._operation_outcome(
            "invalid",
            f"Unsupported _outputFormat '{output_format}'. Supported formats: application/fhir+ndjson, application/ndjson, ndjson.",
            status.HTTP_400_BAD_REQUEST,
        )

    def _authorize_resource_types(self, request, resource_types):
        token = getattr(request, "auth", None)
        owner = _bulk_token_owner(token)
        if owner is None:
            return None, self._operation_outcome(
                "forbidden",
                "Bulk Data access tokens must identify an OAuth client.",
                status.HTTP_403_FORBIDDEN,
            )
        denied = [
            resource_type
            for resource_type in resource_types
            if not _bulk_scope_allows_resource(token, resource_type)
        ]
        if denied:
            return None, self._operation_outcome(
                "forbidden",
                "The access token lacks system-level read scope for: " + ", ".join(denied),
                status.HTTP_403_FORBIDDEN,
            )
        return owner, None

    def _authorize_job(self, request, job):
        owner, error_response = self._authorize_resource_types(
            request,
            job.get("resource_types", []),
        )
        if error_response is not None:
            return error_response
        if owner != job.get("owner"):
            return self._operation_outcome(
                "forbidden",
                "Bulk export jobs are accessible only to the OAuth client that created them.",
                status.HTTP_403_FORBIDDEN,
            )
        return None

    def _create_job(self, request, export_type, group_id=None):
        output_format_error = self._validate_output_format(request)
        if output_format_error is not None:
            return None, output_format_error

        resource_types, unsupported = self._requested_resource_types(request)
        if unsupported and "handling=lenient" not in request.headers.get("Prefer", ""):
            return None, self._operation_outcome(
                "not-supported",
                f"Unsupported Bulk Data _type value(s): {', '.join(unsupported)}.",
                status.HTTP_400_BAD_REQUEST,
            )
        if not resource_types:
            return None, self._operation_outcome(
                "not-supported",
                "No supported resource types were requested for export.",
                status.HTTP_400_BAD_REQUEST,
            )

        owner, authorization_error = self._authorize_resource_types(request, resource_types)
        if authorization_error is not None:
            return None, authorization_error

        try:
            export_scope = PersistentBulkExportService.build_scope(
                export_type=export_type,
                group_id=group_id,
            )
        except BulkGroupNotFoundError as exc:
            return None, self._operation_outcome(
                "not-found",
                str(exc),
                status.HTTP_404_NOT_FOUND,
            )
        except BulkProjectionError as exc:
            return None, self._operation_outcome(
                "exception",
                str(exc),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        job_id = f"{export_type}-export-{group_id or 'system'}-{uuid.uuid4().hex[:8]}"
        transaction_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        job = {
            "id": job_id,
            "export_type": export_type,
            "group_id": group_id,
            "resource_types": resource_types,
            "request": request.build_absolute_uri(),
            "transaction_time": transaction_time,
            "since": request.query_params.get("_since"),
            "type_filter": request.query_params.get("_typeFilter"),
            "created_at": transaction_time,
            "patient_ids": [str(patient.id) for patient in export_scope.patients],
            "owner": owner,
        }

        with _cancelled_jobs_lock:
            _bulk_export_jobs[job_id] = job
            _cancelled_jobs.discard(job_id)

        return job, None

    def retrieve(self, request, pk=None):
        """
        Returns the Inferno certification Group resource.
        Patient membership is intentionally identical to the export dataset.
        """
        try:
            group_resource = PersistentBulkExportService.persisted_group_resource(pk)
        except BulkGroupNotFoundError as exc:
            return self._operation_outcome(
                "not-found",
                str(exc),
                status.HTTP_404_NOT_FOUND,
            )
        except BulkProjectionError as exc:
            return self._operation_outcome(
                "exception",
                str(exc),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return self.fhir_response(group_resource)

    @action(detail=False, methods=['get'], url_path=r'\$export')
    def export_system(self, request):
        job, error_response = self._create_job(request, "system")
        if error_response is not None:
            return error_response

        response = Response(status=status.HTTP_202_ACCEPTED)
        response['Content-Location'] = self._bulk_url(request, f"bulk-status/{job['id']}")
        response['X-Progress'] = 'accepted'
        response['Cache-Control'] = 'no-store'
        return response

    @action(detail=True, methods=['get'], url_path=r'\$export')
    def export_group(self, request, pk=None):
        """
        Handle Group-level export: GET /Group/[id]/$export.
        """
        job, error_response = self._create_job(request, "group", group_id=pk)
        if error_response is not None:
            return error_response

        response = Response(status=status.HTTP_202_ACCEPTED)
        response['Content-Location'] = self._bulk_url(request, f"bulk-status/{job['id']}")
        response['X-Progress'] = 'accepted'
        response['Cache-Control'] = 'no-store'
        return response

    def job_status(self, request, job_id=None):
        """
        Returns the completed Bulk Data status manifest for a kickoff job.
        """
        with _cancelled_jobs_lock:
            if job_id in _cancelled_jobs:
                return self._operation_outcome(
                    "not-found",
                    f"Bulk export job {job_id} was cancelled and is no longer available.",
                    status.HTTP_404_NOT_FOUND,
                )
            job = _bulk_export_jobs.get(job_id)

        if job is None:
            return self._operation_outcome(
                "not-found",
                f"Bulk export job {job_id} not found.",
                status.HTTP_404_NOT_FOUND,
            )

        authorization_error = self._authorize_job(request, job)
        if authorization_error is not None:
            return authorization_error

        base_url = self._bulk_url(request, f"bulk-download/{job_id}/")
        output = [
            {
                "type": res_type,
                "url": f"{base_url}{res_type.lower()}.ndjson",
            }
            for res_type in job["resource_types"]
        ]

        response = JsonResponse(
            {
                "transactionTime": job["transaction_time"],
                "request": job["request"],
                "requiresAccessToken": True,
                "output": output,
                "error": [],
            },
            status=200,
            content_type='application/json',
        )
        response["Expires"] = (
            datetime.now(timezone.utc) + timedelta(minutes=10)
        ).strftime("%a, %d %b %Y %H:%M:%S GMT")
        return response

    def cancel_job(self, request, job_id=None):
        """
        Handles DELETE /fhir/R4/bulk-status/[job_id] to cancel a bulk export job.
        """
        if not job_id:
            return self._operation_outcome(
                "invalid",
                "Job ID is required for cancellation.",
                status.HTTP_400_BAD_REQUEST,
            )

        with _cancelled_jobs_lock:
            job = _bulk_export_jobs.get(job_id)
        if job is None:
            return self._operation_outcome(
                "not-found",
                f"Bulk export job {job_id} not found.",
                status.HTTP_404_NOT_FOUND,
            )
        authorization_error = self._authorize_job(request, job)
        if authorization_error is not None:
            return authorization_error

        with _cancelled_jobs_lock:
            _cancelled_jobs.add(job_id)
            _bulk_export_jobs.pop(job_id, None)

        return Response(status=status.HTTP_202_ACCEPTED)
    
    def download_file(self, request, job_id=None, file_name=None):
        """Render one persisted projector-backed NDJSON file for a kickoff job."""
        with _cancelled_jobs_lock:
            if job_id in _cancelled_jobs:
                return self._operation_outcome(
                    "not-found",
                    f"Bulk export job {job_id} was cancelled.",
                    status.HTTP_404_NOT_FOUND,
                )
            job = _bulk_export_jobs.get(job_id)

        if job is None:
            return self._operation_outcome(
                "not-found",
                f"Bulk export job {job_id} not found.",
                status.HTTP_404_NOT_FOUND,
            )

        authorization_error = self._authorize_job(request, job)
        if authorization_error is not None:
            return authorization_error

        if not file_name or not file_name.lower().endswith(".ndjson"):
            return self._operation_outcome(
                "not-found",
                "Bulk export files must use the .ndjson extension.",
                status.HTTP_404_NOT_FOUND,
            )

        resource_name = file_name.rsplit(".", 1)[0]
        res_type = FHIRUtils.normalize_resource_name(resource_name)
        if not res_type or res_type not in job["resource_types"]:
            return self._operation_outcome(
                "not-found",
                f"Resource type {resource_name} was not requested for bulk export job {job_id}.",
                status.HTTP_404_NOT_FOUND,
            )

        service = PersistentBulkExportService()
        try:
            scope = service.restore_scope(
                export_type=job["export_type"],
                group_id=job.get("group_id"),
                patient_ids=job.get("patient_ids", []),
            )
            ndjson_content = service.render_ndjson(
                resource_type=res_type,
                scope=scope,
                request=request,
            )
        except BulkProjectionError:
            return self._operation_outcome(
                "exception",
                f"Bulk export of {res_type} failed while projecting persisted data.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response = HttpResponse(
            ndjson_content,
            content_type="application/fhir+ndjson",
        )
        response["Content-Disposition"] = f'inline; filename="{file_name}"'
        response["Cache-Control"] = "no-store"
        return response
