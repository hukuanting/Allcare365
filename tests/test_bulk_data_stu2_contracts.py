import os
import sys
import unittest
import json
from types import SimpleNamespace

import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medical_system.settings")

from django.apps import apps

if not apps.ready:
    django.setup()

from django.test import TestCase, override_settings
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.integration.fhir_integration.capability_statement import generate_capability_statement
from apps.integration.fhir_integration.projectors.registry import ProjectorRegistry
from apps.integration.fhir_integration.models import FHIRResource
from apps.integration.fhir_integration.public_url import get_public_base_url
from apps.integration.fhir_integration.views import BulkExportViewSet, SMARTv2Validator


class BulkDataSTU2ContractTests(TestCase):
    def setUp(self):
        FHIRResource.objects.create(
            resource_type="Group",
            resource_id="example-group",
            resource_data={
                "resourceType": "Group",
                "id": "example-group",
                "type": "person",
                "actual": True,
                "quantity": 0,
                "member": [],
            },
        )

    def _request(self, path, query=None):
        factory = APIRequestFactory()
        request = factory.get(
            path,
            data=query or {},
            HTTP_HOST="example.org",
            wsgi_url_scheme="https",
        )
        return Request(request)

    @override_settings(PUBLIC_BASE_URL="https://example.org", ALLOWED_HOSTS=["example.org"])
    def test_bulk_urls_preserve_r4_base_path(self):
        request = self._request("/fhir/R4/Group/example-group/$export")
        view = BulkExportViewSet()

        self.assertEqual(
            view._bulk_url(request, "bulk-status/job-1"),
            "https://example.org/fhir/R4/bulk-status/job-1",
        )
        self.assertEqual(
            view._bulk_url(request, "bulk-download/job-1/patient.ndjson"),
            "https://example.org/fhir/R4/bulk-download/job-1/patient.ndjson",
        )

    def test_type_parameter_limits_manifest_resources(self):
        request = self._request(
            "/fhir/R4/Group/example-group/$export",
            {"_type": "Patient,Observation"},
        )
        view = BulkExportViewSet()

        resource_types, unsupported = view._requested_resource_types(request)

        self.assertEqual(resource_types, ["Patient", "Observation"])
        self.assertEqual(unsupported, [])

    def test_type_parameter_rejects_non_persisted_fixture_resources(self):
        request = self._request(
            "/fhir/R4/Group/example-group/$export",
            {"_type": "Endpoint,Organization"},
        )

        resource_types, unsupported = BulkExportViewSet()._requested_resource_types(request)

        self.assertEqual(resource_types, [])
        self.assertEqual(unsupported, ["Endpoint", "Organization"])

    @override_settings(PUBLIC_BASE_URL="https://example.org", ALLOWED_HOSTS=["example.org"])
    def test_group_export_kickoff_and_status_manifest(self):
        factory = APIRequestFactory()
        token = SimpleNamespace(
            scope="system/*.read",
            application_id="bulk-contract-client",
            user_id=None,
        )
        kickoff_request = factory.get(
            "/fhir/R4/Group/example-group/$export",
            {"_type": "Patient"},
            HTTP_HOST="example.org",
            wsgi_url_scheme="https",
        )
        force_authenticate(kickoff_request, token=token)
        kickoff_view = BulkExportViewSet.as_view({"get": "export_group"})

        kickoff_response = kickoff_view(kickoff_request, pk="example-group")

        self.assertEqual(kickoff_response.status_code, 202)
        content_location = kickoff_response["Content-Location"]
        self.assertIn("/fhir/R4/bulk-status/group-export-example-group-", content_location)

        job_id = content_location.rsplit("/", 1)[-1]
        status_request = factory.get(
            f"/fhir/R4/bulk-status/{job_id}",
            HTTP_HOST="example.org",
            wsgi_url_scheme="https",
        )
        force_authenticate(status_request, token=token)
        status_view = BulkExportViewSet.as_view({"get": "job_status"})

        status_response = status_view(status_request, job_id=job_id)
        manifest = json.loads(status_response.content)

        self.assertEqual(status_response.status_code, 200)
        self.assertTrue(manifest["requiresAccessToken"])
        self.assertEqual([entry["type"] for entry in manifest["output"]], ["Patient"])
        self.assertTrue(manifest["output"][0]["url"].endswith(f"/fhir/R4/bulk-download/{job_id}/patient.ndjson"))

    @override_settings(
        PUBLIC_BASE_URL="https://example.org",
        ALLOWED_HOSTS=["example.org"],
        FHIR_ALLOW_ANONYMOUS_READ=True,
    )
    def test_group_export_rejects_anonymous_request(self):
        factory = APIRequestFactory()
        request = factory.get(
            "/fhir/R4/Group/example-group/$export",
            HTTP_HOST="example.org",
            wsgi_url_scheme="https",
        )
        view = BulkExportViewSet.as_view({"get": "export_group"})

        response = view(request, pk="example-group")

        self.assertIn(response.status_code, (401, 403))

    def test_bulk_advertises_only_registered_persisted_projectors(self):
        resource_types = BulkExportViewSet.SUPPORTED_RESOURCE_TYPES

        self.assertIn("Patient", resource_types)
        self.assertIn("Encounter", resource_types)
        for resource_type in resource_types:
            self.assertTrue(ProjectorRegistry.has(resource_type), resource_type)

        # Registered singleton/template projectors and unregistered historical
        # fixture types are not safe persisted Bulk Data sources.
        for resource_type in (
            "Endpoint",
            "Location",
            "Media",
            "Organization",
            "Practitioner",
            "PractitionerRole",
            "Provenance",
            "QuestionnaireResponse",
        ):
            self.assertNotIn(resource_type, resource_types)

    def test_backend_services_accepts_inferno_signing_algorithms(self):
        algorithms = SMARTv2Validator.BACKEND_SERVICE_SIGNING_ALGORITHMS

        self.assertIn("ES384", algorithms)
        self.assertIn("RS384", algorithms)

    @override_settings(
        PUBLIC_BASE_URL="",
        ALLOWED_HOSTS=["cloudflare.example"],
        OAUTH2_PROVIDER={"OIDC_ISS_ENDPOINT": ""},
    )
    def test_public_base_url_is_request_derived_for_cloudflare(self):
        factory = APIRequestFactory()
        request = factory.get(
            "/fhir/R4/metadata",
            HTTP_HOST="cloudflare.example",
            HTTP_X_FORWARDED_PROTO="https",
        )

        self.assertEqual(get_public_base_url(request), "https://cloudflare.example")

    @override_settings(PUBLIC_BASE_URL="", OAUTH2_PROVIDER={"OIDC_ISS_ENDPOINT": ""})
    def test_public_base_url_accepts_oauth_mock_request(self):
        request = SimpleNamespace(
            uri="https://cloudflare.example/o/token/",
            META={},
        )

        self.assertEqual(get_public_base_url(request), "https://cloudflare.example")

    def test_backend_services_has_bundled_inferno_public_keys(self):
        validator = SMARTv2Validator()

        ec_key = validator._get_bundled_inferno_signing_key({
            "kid": "4b49a739d1eb115b3225f4cf9beb6d1b",
            "alg": "ES384",
        })
        rsa_key = validator._get_bundled_inferno_signing_key({
            "kid": "b41528b6f37a9500edb8a905a595bdd7",
            "alg": "RS384",
        })

        self.assertIsNotNone(ec_key)
        self.assertIsNotNone(rsa_key)

    @override_settings(INFERNO_BULK_ALLOW_DYNAMIC_CLIENT_REGISTRATION=True)
    def test_backend_services_allows_dynamic_inferno_client_ids(self):
        validator = SMARTv2Validator()

        self.assertTrue(validator._allow_dynamic_bulk_clients())

    def test_capability_statement_declares_group_export_operation(self):
        capability = generate_capability_statement("https://example.org/fhir/R4")
        resources = {entry["type"]: entry for entry in capability["rest"][0]["resource"]}

        self.assertIn("Group", resources)
        operations = resources["Group"].get("operation", [])
        self.assertTrue(any(op["name"] == "$export" for op in operations))
        self.assertTrue(any(op["definition"].endswith("/group-export") for op in operations))


if __name__ == "__main__":
    unittest.main()
