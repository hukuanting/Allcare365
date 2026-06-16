import json
import os
import sys
import time
import base64
import hashlib
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import django


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medical_system.settings")

from django.apps import apps

if not apps.ready:
    django.setup()

from django.conf import settings
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone
from oauth2_provider.models import AccessToken, Application, RefreshToken as OAuthRefreshToken

from apps.core.authentication.views import _build_id_token
from apps.clinical.patients.models import Patient
from apps.integration.fhir_integration.fine_grained_scopes import (
    allowed_category_tokens,
    fine_grained_scope_descriptions,
    resource_matches_allowed_categories,
)
from apps.integration.fhir_integration.views import FHIRBaseMixin, FHIRScopePermission


class SmartVisualInspectionContractTests(TestCase):
    def setUp(self):
        self.user, _ = User.objects.get_or_create(username="inferno_user")
        self.user.set_password("test")
        self.user.save()
        self.application, _ = Application.objects.update_or_create(
            client_id="inferno_public_client",
            defaults={
                "user": self.user,
                "client_type": "public",
                "authorization_grant_type": "authorization-code",
                "redirect_uris": "https://inferno.healthit.gov/suites/custom/smart/redirect",
                "name": "Inferno Public Client",
                "algorithm": "RS256",
            },
        )
        self.ehr_application, _ = Application.objects.update_or_create(
            client_id="inferno_client_id",
            defaults={
                "user": self.user,
                "client_type": "confidential",
                "authorization_grant_type": "authorization-code",
                "client_secret": "inferno_client_secret",
                "redirect_uris": "https://inferno.healthit.gov/suites/custom/smart/redirect",
                "name": "Inferno Default SMART App",
                "algorithm": "RS256",
            },
        )
        self.asymmetric_application, _ = Application.objects.update_or_create(
            client_id="inferno_asymmetric_client",
            defaults={
                "user": self.user,
                "client_type": "confidential",
                "authorization_grant_type": "authorization-code",
                "client_secret": "private-key-jwt-not-used",
                "redirect_uris": "https://inferno.healthit.gov/suites/custom/smart/redirect",
                "name": "Inferno Asymmetric Standalone Client",
                "algorithm": "RS256",
            },
        )
        Patient.objects.get_or_create(
            medical_record_number="ONC-TEST-001",
            defaults={
                "first_name": "Allcare",
                "last_name": "Test",
                "date_of_birth": date(1980, 1, 1),
                "sex": "female",
                "is_active": True,
            },
        )
        AccessToken.objects.filter(token="visual-token").delete()

    def _public_pkce_token_response(self):
        verifier = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~1234567890"
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode("ascii")).digest()
        ).rstrip(b"=").decode("ascii")
        authorize_params = {
            "response_type": "code",
            "client_id": self.application.client_id,
            "redirect_uri": "https://inferno.healthit.gov/suites/custom/smart/redirect",
            "scope": "launch/patient openid fhirUser offline_access patient/Patient.rs",
            "state": "state",
            "aud": "https://example.org/fhir/R4",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }

        self.client.force_login(self.user)
        authorize_response = self.client.post(
            "/o/authorize/",
            {**authorize_params, "allow": "Authorize"},
            secure=True,
            HTTP_HOST="example.org",
        )
        self.assertEqual(authorize_response.status_code, 302)
        code = parse_qs(urlparse(authorize_response["Location"]).query)["code"][0]

        return self.client.post(
            "/o/token/",
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": "https://inferno.healthit.gov/suites/custom/smart/redirect",
                "client_id": self.application.client_id,
                "code_verifier": verifier,
            },
            secure=True,
            HTTP_HOST="example.org",
        )

    def _ehr_patient_scope_token_response(self):
        verifier = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~1234567890"
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode("ascii")).digest()
        ).rstrip(b"=").decode("ascii")
        authorize_params = {
            "response_type": "code",
            "client_id": self.ehr_application.client_id,
            "redirect_uri": "https://inferno.healthit.gov/suites/custom/smart/redirect",
            "scope": "launch openid fhirUser offline_access patient/Patient.rs",
            "state": "state",
            "aud": "https://example.org/fhir/R4",
            "launch": "ehr-launch-context",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }

        self.client.force_login(self.user)
        authorize_response = self.client.post(
            "/o/authorize/",
            {**authorize_params, "allow": "Authorize"},
            secure=True,
            HTTP_HOST="example.org",
        )
        self.assertEqual(authorize_response.status_code, 302)
        code = parse_qs(urlparse(authorize_response["Location"]).query)["code"][0]

        return self.client.post(
            "/o/token/",
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": "https://inferno.healthit.gov/suites/custom/smart/redirect",
                "client_id": self.ehr_application.client_id,
                "client_secret": "inferno_client_secret",
                "code_verifier": verifier,
            },
            secure=True,
            HTTP_HOST="example.org",
        )

    def _granular_scope_selection_token_response(self):
        verifier = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~1234567890"
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode("ascii")).digest()
        ).rstrip(b"=").decode("ascii")
        condition_granular_scope = (
            "patient/Condition.rs?category="
            "http://terminology.hl7.org/CodeSystem/condition-category|problem-list-item"
        )
        observation_granular_scope = (
            "patient/Observation.rs?category="
            "http://terminology.hl7.org/CodeSystem/observation-category|laboratory"
        )
        authorize_params = {
            "response_type": "code",
            "client_id": self.ehr_application.client_id,
            "redirect_uri": "https://inferno.healthit.gov/suites/custom/smart/redirect",
            "scope": "launch/patient openid fhirUser offline_access patient/Patient.rs patient/Condition.rs patient/Observation.rs",
            "state": "state",
            "aud": "https://example.org/fhir/R4",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }

        self.client.force_login(self.user)
        authorize_response = self.client.post(
            "/o/authorize/",
            {
                **authorize_params,
                "scope": (
                    "launch/patient openid fhirUser offline_access patient/Patient.rs "
                    f"patient/Condition.rs patient/Observation.rs {condition_granular_scope} {observation_granular_scope}"
                ),
                "allow": "Authorize",
            },
            secure=True,
            HTTP_HOST="example.org",
        )
        self.assertEqual(authorize_response.status_code, 302, authorize_response.content)
        code = parse_qs(urlparse(authorize_response["Location"]).query)["code"][0]

        return self.client.post(
            "/o/token/",
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": "https://inferno.healthit.gov/suites/custom/smart/redirect",
                "client_id": self.ehr_application.client_id,
                "client_secret": "inferno_client_secret",
                "code_verifier": verifier,
            },
            secure=True,
            HTTP_HOST="example.org",
        )

    @override_settings(PUBLIC_BASE_URL="https://example.org", ALLOWED_HOSTS=["testserver", "example.org"])
    def test_invalid_aud_parameter_is_rejected(self):
        response = self.client.get(
            "/o/authorize/",
            {
                "response_type": "code",
                "client_id": self.application.client_id,
                "redirect_uri": "https://inferno.healthit.gov/suites/custom/smart/redirect",
                "scope": "launch/patient openid fhirUser patient/Patient.rs",
                "state": "state",
                "aud": "https://wrong.example/fhir/R4",
            },
            HTTP_HOST="example.org",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content)["error"], "invalid_request")

    @override_settings(PUBLIC_BASE_URL="https://example.org", ALLOWED_HOSTS=["example.org"])
    def test_smart_discovery_declares_public_client_oidc_support(self):
        response = self.client.get("/.well-known/smart-configuration", secure=True, HTTP_HOST="example.org")
        self.assertEqual(response.status_code, 200)

        body = json.loads(response.content)
        self.assertEqual(body["issuer"], "https://example.org/o")
        self.assertIn("client-public", body["capabilities"])
        self.assertIn("sso-openid-connect", body["capabilities"])
        self.assertIn("none", body["token_endpoint_auth_methods_supported"])
        self.assertIn("S256", body["code_challenge_methods_supported"])
        self.assertIn("RS256", body["id_token_signing_alg_values_supported"])
        self.assertIn(
            "patient/Observation.rs?category=http://terminology.hl7.org/CodeSystem/observation-category|laboratory",
            body["scopes_supported"],
        )

    @override_settings(PUBLIC_BASE_URL="https://example.org", ALLOWED_HOSTS=["example.org"])
    def test_public_onc_api_documentation_endpoint_declares_base_urls(self):
        response = self.client.get(
            "/onc-certification/api-documentation/",
            secure=True,
            HTTP_HOST="example.org",
        )
        self.assertEqual(response.status_code, 200)

        body = json.loads(response.content)
        self.assertEqual(body["service_base_urls"]["fhir_r4"], "https://example.org/fhir/R4")
        self.assertEqual(
            body["service_base_urls"]["bulk_group_export"],
            "https://example.org/fhir/R4/Group/example-group/$export",
        )
        self.assertEqual(
            body["security_attestations"]["refresh_token_minimum_lifetime_seconds"],
            7776000,
        )

    def test_refresh_token_lifetime_supports_three_month_minimum(self):
        self.assertGreaterEqual(settings.OAUTH2_PROVIDER["REFRESH_TOKEN_EXPIRE_SECONDS"], 7776000)
        self.assertGreaterEqual(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].days, 90)

    @override_settings(PUBLIC_BASE_URL="https://example.org", ALLOWED_HOSTS=["testserver", "example.org"])
    def test_fine_grained_scopes_render_in_authorization_page(self):
        fine_scope = (
            "patient/Observation.rs?category="
            "http://terminology.hl7.org/CodeSystem/observation-category|laboratory"
        )
        self.assertIn(fine_scope, fine_grained_scope_descriptions())

        self.client.force_login(self.user)
        response = self.client.get(
            "/o/authorize/",
            {
                "response_type": "code",
                "client_id": self.application.client_id,
                "redirect_uri": "https://inferno.healthit.gov/suites/custom/smart/redirect",
                "scope": f"launch/patient openid fhirUser offline_access {fine_scope}",
                "state": "state",
                "aud": "https://example.org/fhir/R4",
                "code_challenge": "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~",
                "code_challenge_method": "S256",
            },
            secure=True,
            HTTP_HOST="example.org",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertContains(response, fine_scope)

    @override_settings(PUBLIC_BASE_URL="https://example.org", ALLOWED_HOSTS=["testserver", "example.org"])
    def test_offline_access_authorization_notice_is_present(self):
        self.client.force_login(self.user)
        response = self.client.get(
            "/o/authorize/",
            {
                "response_type": "code",
                "client_id": self.application.client_id,
                "redirect_uri": "https://inferno.healthit.gov/suites/custom/smart/redirect",
                "scope": "launch/patient openid fhirUser offline_access patient/Patient.rs",
                "state": "state",
                "aud": "https://example.org/fhir/R4",
                "code_challenge": "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~",
                "code_challenge_method": "S256",
            },
            secure=True,
            HTTP_HOST="example.org",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertContains(response, "Granting offline access allows this application to receive refresh tokens")

    @override_settings(PUBLIC_BASE_URL="https://example.org", ALLOWED_HOSTS=["testserver", "example.org"])
    def test_resource_level_condition_observation_request_shows_granular_options(self):
        self.client.force_login(self.user)
        response = self.client.get(
            "/o/authorize/",
            {
                "response_type": "code",
                "client_id": self.ehr_application.client_id,
                "redirect_uri": "https://inferno.healthit.gov/suites/custom/smart/redirect",
                "scope": (
                    "launch/patient openid fhirUser offline_access "
                    "patient/Condition.rs patient/Observation.rs patient/Patient.rs"
                ),
                "state": "state",
                "aud": "https://example.org/fhir/R4",
                "code_challenge": "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~",
                "code_challenge_method": "S256",
            },
            secure=True,
            HTTP_HOST="example.org",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertContains(
            response,
            "patient/Condition.rs?category=http://terminology.hl7.org/CodeSystem/condition-category|problem-list-item",
        )
        self.assertContains(
            response,
            "patient/Observation.rs?category=http://terminology.hl7.org/CodeSystem/observation-category|laboratory",
        )
        self.assertContains(
            response,
            "patient/Observation.rs?category=http://terminology.hl7.org/CodeSystem/observation-category|procedure",
        )

    def test_fine_grained_category_scopes_authorize_and_filter_resources(self):
        observation_scope = (
            "patient/Observation.rs?category="
            "http://terminology.hl7.org/CodeSystem/observation-category|laboratory"
        )
        permission = FHIRScopePermission()

        self.assertTrue(permission._check_scopes("Observation", [observation_scope]))
        self.assertEqual(
            allowed_category_tokens([observation_scope], "Observation"),
            {("http://terminology.hl7.org/CodeSystem/observation-category", "laboratory")},
        )
        self.assertTrue(
            resource_matches_allowed_categories(
                {
                    "resourceType": "Observation",
                    "category": [
                        {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                    "code": "laboratory",
                                }
                            ]
                        }
                    ],
                },
                {("http://terminology.hl7.org/CodeSystem/observation-category", "laboratory")},
            )
        )

    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_projected_observation_search_filters_by_granular_category_scope(self):
        observation_scope = (
            "patient/Observation.rs?category="
            "http://terminology.hl7.org/CodeSystem/observation-category|laboratory"
        )
        lab_observation = {
            "resourceType": "Observation",
            "id": "lab-1",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "laboratory",
                        }
                    ]
                }
            ],
        }
        vital_observation = {
            "resourceType": "Observation",
            "id": "vital-1",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "vital-signs",
                        }
                    ]
                }
            ],
        }
        projector = SimpleNamespace(
            query=lambda patient_id, search_params, context: ["row"],
            project_batch=lambda items, context: [vital_observation, lab_observation],
        )

        class FakeBundleBuilder:
            def __init__(self, context):
                self.context = context

            def build_searchset(self, primary_resources, included_resources, total, request_url):
                return {
                    "resourceType": "Bundle",
                    "type": "searchset",
                    "total": total,
                    "ids": [resource["id"] for resource in primary_resources],
                }

        request = RequestFactory().get(
            "/fhir/R4/Observation",
            {"patient": "00000000-0000-4000-a000-000000000001"},
        )
        request.query_params = request.GET
        request.data = {}
        request.auth = SimpleNamespace(scope=observation_scope)

        with patch("apps.integration.fhir_integration.views.ProjectorRegistry.has", return_value=True), \
             patch("apps.integration.fhir_integration.views.ProjectorRegistry.get", return_value=projector), \
             patch("apps.integration.fhir_integration.views.FHIRContext.from_request", return_value=SimpleNamespace(include_tracker=None)), \
             patch("apps.integration.fhir_integration.views.SearchParser.parse", return_value=SimpleNamespace(params={}, rev_includes=[])), \
             patch("apps.integration.fhir_integration.views.IncludeResolver.resolve", return_value=[]), \
             patch("apps.integration.fhir_integration.views.FHIRBundleBuilder", FakeBundleBuilder):
            response = FHIRBaseMixin()._projected_search_response(request, "Observation")

        body = json.loads(response.content)
        self.assertEqual(body["ids"], ["lab-1"])
        self.assertEqual(body["total"], 1)

    def test_projected_observation_read_rejects_resource_outside_granular_scope(self):
        observation_scope = (
            "patient/Observation.rs?category="
            "http://terminology.hl7.org/CodeSystem/observation-category|laboratory"
        )
        vital_observation = {
            "resourceType": "Observation",
            "id": "vital-1",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "vital-signs",
                        }
                    ]
                }
            ],
        }
        projector = SimpleNamespace(
            query=lambda patient_id, search_params, context: ["row"],
            project_batch=lambda items, context: [vital_observation],
        )
        request = RequestFactory().get("/fhir/R4/Observation/vital-1")
        request.auth = SimpleNamespace(scope=observation_scope)

        with patch("apps.integration.fhir_integration.views.ProjectorRegistry.has", return_value=True), \
             patch("apps.integration.fhir_integration.views.ProjectorRegistry.get", return_value=projector), \
             patch("apps.integration.fhir_integration.views.FHIRContext.from_request", return_value=SimpleNamespace()):
            response = FHIRBaseMixin()._projected_read_response(request, "Observation", "vital-1")

        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            resource_matches_allowed_categories(
                {
                    "resourceType": "Observation",
                    "category": [
                        {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                    "code": "vital-signs",
                                }
                            ]
                        }
                    ],
                },
                {("http://terminology.hl7.org/CodeSystem/observation-category", "laboratory")},
            )
        )

    def test_asymmetric_client_uses_supported_oidc_id_token_signing_algorithm(self):
        app = Application.objects.get(client_id="inferno_asymmetric_client")
        self.assertEqual(app.client_type, "confidential")
        self.assertEqual(app.authorization_grant_type, "authorization-code")
        self.assertEqual(app.algorithm, "RS256")

    @override_settings(ALLOWED_HOSTS=["testserver"])
    def test_revocation_and_introspection_aliases(self):
        token = AccessToken.objects.create(
            user=self.user,
            application=self.application,
            token="visual-token",
            expires=timezone.now() + timedelta(minutes=10),
            scope="patient/Patient.rs openid fhirUser",
        )

        active_response = self.client.post("/o/introspect/", {"token": token.token})
        active_payload = json.loads(active_response.content)
        self.assertEqual(active_response.status_code, 200)
        self.assertTrue(active_payload["active"])
        self.assertEqual(active_payload["client_id"], self.application.client_id)
        self.assertEqual(active_payload["sub"], str(self.user.id))
        self.assertEqual(active_payload["iss"], "http://testserver/o")
        self.assertEqual(active_payload["patient"], "00000000-0000-4000-a000-000000000001")
        self.assertTrue(active_payload["fhirUser"].endswith("/fhir/R4/Practitioner/example-practitioner"))

        revoke_response = self.client.post("/o/revoke/", {"token": token.token})
        self.assertEqual(revoke_response.status_code, 200)

        inactive_response = self.client.post("/o/introspect/", {"token": token.token})
        inactive_payload = json.loads(inactive_response.content)
        self.assertEqual(inactive_response.status_code, 200)
        self.assertFalse(inactive_payload["active"])

    @override_settings(PUBLIC_BASE_URL="https://example.org", ALLOWED_HOSTS=["testserver", "example.org"])
    def test_openid_token_contains_fhir_user_claim(self):
        request = RequestFactory().post(
            "/o/token/",
            {
                "client_id": self.application.client_id,
                "scope": "openid fhirUser patient/Patient.rs",
            },
            HTTP_HOST="example.org",
        )
        id_token = _build_id_token(
            request,
            {"scope": "openid fhirUser patient/Patient.rs", "expires_in": 300},
        )

        header, payload, signature = id_token.split(".")
        self.assertTrue(header)
        self.assertTrue(signature)

        body = json.loads(
            __import__("base64").urlsafe_b64decode(payload + "=" * (-len(payload) % 4)).decode()
        )
        self.assertEqual(body["iss"], "https://example.org/o")
        self.assertEqual(body["aud"], self.application.client_id)
        self.assertEqual(body["fhirUser"], "https://example.org/fhir/R4/Practitioner/example-practitioner")
        self.assertGreater(body["exp"], int(time.time()))

    @override_settings(PUBLIC_BASE_URL="https://example.org", ALLOWED_HOSTS=["testserver", "example.org"])
    def test_public_standalone_pkce_token_exchange_returns_id_token(self):
        token_response = self._public_pkce_token_response()

        self.assertEqual(token_response.status_code, 200, token_response.content)
        body = json.loads(token_response.content)
        self.assertIn("access_token", body)
        self.assertEqual(body["token_type"], "Bearer")
        self.assertIn("id_token", body)
        self.assertIn("patient", body)
        self.assertEqual(token_response["Cache-Control"], "no-store")
        self.assertEqual(token_response["Pragma"], "no-cache")

        id_token_payload = body["id_token"].split(".")[1]
        id_token_claims = json.loads(
            base64.urlsafe_b64decode(
                id_token_payload + "=" * (-len(id_token_payload) % 4)
            ).decode("utf-8")
        )
        self.assertEqual(id_token_claims["iss"], "https://example.org/o")
        self.assertEqual(id_token_claims["aud"], self.application.client_id)
        self.assertEqual(
            id_token_claims["fhirUser"],
            "https://example.org/fhir/R4/Practitioner/example-practitioner",
        )

    @override_settings(PUBLIC_BASE_URL="https://example.org", ALLOWED_HOSTS=["testserver", "example.org"])
    def test_ehr_launch_with_patient_scopes_returns_patient_context(self):
        token_response = self._ehr_patient_scope_token_response()

        self.assertEqual(token_response.status_code, 200, token_response.content)
        body = json.loads(token_response.content)
        self.assertEqual(body["token_type"], "Bearer")
        self.assertEqual(body["patient"], "00000000-0000-4000-a000-000000000001")
        self.assertIn("patient/Patient.rs", body["scope"].split())
        self.assertIn("id_token", body)
        self.assertEqual(token_response["Cache-Control"], "no-store")
        self.assertEqual(token_response["Pragma"], "no-cache")

    @override_settings(PUBLIC_BASE_URL="https://example.org", ALLOWED_HOSTS=["testserver", "example.org"])
    def test_granular_scope_selection_token_omits_resource_level_condition_observation(self):
        token_response = self._granular_scope_selection_token_response()

        self.assertEqual(token_response.status_code, 200, token_response.content)
        body = json.loads(token_response.content)
        received_scopes = set(body["scope"].split())
        self.assertIn("patient/Patient.rs", received_scopes)
        self.assertNotIn("patient/Condition.rs", received_scopes)
        self.assertNotIn("patient/Observation.rs", received_scopes)
        self.assertIn(
            "patient/Condition.rs?category=http://terminology.hl7.org/CodeSystem/condition-category|problem-list-item",
            received_scopes,
        )
        self.assertIn(
            "patient/Observation.rs?category=http://terminology.hl7.org/CodeSystem/observation-category|laboratory",
            received_scopes,
        )

    @override_settings(PUBLIC_BASE_URL="https://example.org", ALLOWED_HOSTS=["testserver", "example.org"])
    def test_access_token_revocation_blocks_refresh_token_reuse(self):
        token_response = self._public_pkce_token_response()
        self.assertEqual(token_response.status_code, 200, token_response.content)
        token_body = json.loads(token_response.content)

        revoke_response = self.client.post(
            "/o/revoke/",
            {"token": token_body["access_token"], "token_type_hint": "access_token"},
            secure=True,
            HTTP_HOST="example.org",
        )
        self.assertEqual(revoke_response.status_code, 200)

        refresh_token = OAuthRefreshToken.objects.get(token=token_body["refresh_token"])
        refresh_token.refresh_from_db()
        self.assertIsNotNone(refresh_token.revoked)

        refresh_response = self.client.post(
            "/o/token/",
            {
                "grant_type": "refresh_token",
                "refresh_token": token_body["refresh_token"],
                "client_id": self.application.client_id,
            },
            secure=True,
            HTTP_HOST="example.org",
        )
        self.assertNotEqual(refresh_response.status_code, 200, refresh_response.content)

    @override_settings(
        PUBLIC_BASE_URL="https://example.org",
        ALLOWED_HOSTS=["testserver", "example.org"],
        FHIR_ALLOW_ANONYMOUS_READ=True,
    )
    def test_invalid_bearer_token_does_not_fallback_to_anonymous_fhir_read(self):
        response = self.client.get(
            "/fhir/R4/Patient/00000000-0000-4000-a000-000000000001",
            secure=True,
            HTTP_HOST="example.org",
            HTTP_AUTHORIZATION="Bearer revoked-or-missing-token",
        )

        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    django.setup()
