import json
import os
import uuid
from datetime import date, timedelta
from urllib.parse import parse_qs, urlparse

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medical_system.settings")
django.setup()

from django.contrib.auth.models import Permission, User
from django.test import TestCase, override_settings
from django.utils import timezone
from oauth2_provider.models import AccessToken, Application

from apps.clinical.patients.models import Patient, PatientPractitionerLink, Practitioner
from apps.core.authentication.models import SmartAccessTokenContext, SmartLaunchContext
from apps.core.authentication.smart_utils import SMARTContextError, SMARTContextService
from apps.integration.fhir_integration.resource_identity import identity
from apps.integration.fhir_integration.models import FHIRResource, FHIRResourceMapping


@override_settings(ALLOWED_HOSTS=["testserver", "example.org"])
class SmartPatientContextSecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="smart-context-clinician", password="test")
        self.application = Application.objects.create(
            user=self.user,
            client_id="smart-context-client",
            client_type="public",
            authorization_grant_type="authorization-code",
            redirect_uris="https://app.example/callback",
            name="SMART Context Test Client",
            algorithm="RS256",
        )
        self.patient_a = Patient.objects.create(
            first_name="Alpha",
            last_name="Patient",
            date_of_birth=date(1980, 1, 1),
            sex="female",
            medical_record_number="SMART-CONTEXT-A",
            is_active=True,
        )
        self.patient_b = Patient.objects.create(
            first_name="Beta",
            last_name="Patient",
            date_of_birth=date(1985, 1, 1),
            sex="male",
            medical_record_number="SMART-CONTEXT-B",
            is_active=True,
        )
        self.practitioner = Practitioner.objects.create(
            user=self.user,
            first_name="SMART",
            last_name="Clinician",
            status="active",
            is_active=True,
        )
        PatientPractitionerLink.objects.create(
            patient=self.patient_a,
            practitioner=self.practitioner,
            status="active",
            is_active=True,
        )

    def _access_token(self, *, value, scope, patient=None):
        token = AccessToken.objects.create(
            user=self.user,
            application=self.application,
            token=value,
            expires=timezone.now() + timedelta(minutes=10),
            scope=scope,
        )
        if patient is not None:
            launch_secret, _launch = SMARTContextService.create_launch_context(
                patient_token=identity.patient_id(patient),
                user=self.user,
                target_launch_uri="https://app.example/launch",
            )
            authorization_context = SMARTContextService.bind_authorization_code(
                authorization_code=f"code-{value}",
                launch_token=launch_secret,
                user=self.user,
                client_id=self.application.client_id,
            )
            SmartAccessTokenContext.objects.create(
                access_token=token,
                authorization_context=authorization_context,
            )
        return token

    def _get(self, path, token, data=None):
        return self.client.get(
            path,
            data or {},
            HTTP_AUTHORIZATION=f"Bearer {token.token}",
        )

    @staticmethod
    def _risk_assessment(patient, resource_id):
        data = {
            "resourceType": "RiskAssessment",
            "id": resource_id,
            "status": "final",
            "subject": {"reference": f"Patient/{identity.patient_id(patient)}"},
            "prediction": [{"outcome": {"text": "test-risk"}}],
        }
        resource = FHIRResource.objects.create(
            resource_type="RiskAssessment",
            resource_id=resource_id,
            origin_namespace="tests:smart-risk:v1",
            resource_data=data,
        )
        FHIRResourceMapping.objects.create(
            patient=patient,
            fhir_resource_ref=resource,
            local_table="test_smart_risk_results",
            local_id=uuid.uuid4(),
            fhir_resource_type="RiskAssessment",
            fhir_resource_id=resource_id,
            fhir_json=data,
            sync_status="mapped",
        )
        return data

    def test_patient_scope_search_and_read_are_forced_to_bound_patient(self):
        token = self._access_token(
            value="patient-bound-token",
            scope="patient/Patient.rs",
            patient=self.patient_a,
        )

        search = self._get("/fhir/R4/Patient", token)
        self.assertEqual(search.status_code, 200, search.content)
        search_body = json.loads(search.content)
        self.assertEqual(search_body["total"], 1)
        self.assertEqual(
            search_body["entry"][0]["resource"]["id"],
            identity.patient_id(self.patient_a),
        )

        own_read = self._get(
            f"/fhir/R4/Patient/{identity.patient_id(self.patient_a)}",
            token,
        )
        self.assertEqual(own_read.status_code, 200, own_read.content)

        cross_read = self._get(
            f"/fhir/R4/Patient/{identity.patient_id(self.patient_b)}",
            token,
        )
        self.assertEqual(cross_read.status_code, 404, cross_read.content)

        cross_search = self._get(
            "/fhir/R4/Patient",
            token,
            {"_id": identity.patient_id(self.patient_b)},
        )
        self.assertEqual(cross_search.status_code, 200, cross_search.content)
        self.assertEqual(json.loads(cross_search.content)["total"], 0)

    def test_patient_scope_without_persisted_context_is_denied_and_inactive(self):
        token = self._access_token(
            value="patient-unbound-token",
            scope="patient/Patient.rs openid",
        )

        response = self._get("/fhir/R4/Patient", token)
        self.assertEqual(response.status_code, 403, response.content)

        introspection = self.client.post("/o/introspect/", {"token": token.token})
        self.assertEqual(introspection.status_code, 200)
        self.assertEqual(json.loads(introspection.content), {"active": False})

    def test_patient_scope_cannot_search_or_read_another_patients_risk(self):
        own_id = "risk-smart-own"
        other_id = "risk-smart-other"
        self._risk_assessment(self.patient_a, own_id)
        self._risk_assessment(self.patient_b, other_id)
        token = self._access_token(
            value="patient-bound-risk-token",
            scope="patient/RiskAssessment.rs",
            patient=self.patient_a,
        )

        search = self._get("/fhir/R4/RiskAssessment", token)
        self.assertEqual(search.status_code, 200, search.content)
        self.assertEqual(
            [
                entry["resource"]["id"]
                for entry in json.loads(search.content).get("entry", [])
            ],
            [own_id],
        )

        cross_search = self._get(
            "/fhir/R4/RiskAssessment",
            token,
            {"subject": f"Patient/{identity.patient_id(self.patient_b)}"},
        )
        self.assertEqual(cross_search.status_code, 200, cross_search.content)
        self.assertEqual(json.loads(cross_search.content)["total"], 0)

        cross_read = self._get(f"/fhir/R4/RiskAssessment/{other_id}", token)
        self.assertEqual(cross_read.status_code, 404, cross_read.content)

    def test_user_scope_remains_unbound_and_emits_only_persisted_fhir_user(self):
        token = self._access_token(
            value="user-scope-token",
            scope="user/Patient.rs openid fhirUser",
        )

        response = self._get("/fhir/R4/Patient", token)
        self.assertEqual(response.status_code, 200, response.content)
        returned_ids = {
            entry["resource"]["id"]
            for entry in json.loads(response.content).get("entry", [])
        }
        self.assertIn(identity.patient_id(self.patient_a), returned_ids)
        self.assertIn(identity.patient_id(self.patient_b), returned_ids)

        introspection = self.client.post("/o/introspect/", {"token": token.token})
        payload = json.loads(introspection.content)
        self.assertTrue(payload["active"])
        self.assertNotIn("patient", payload)
        self.assertEqual(
            payload["fhirUser"],
            f"http://testserver/fhir/R4/Practitioner/{identity.practitioner_id(self.practitioner)}",
        )

    def test_ehr_launch_requires_authenticated_explicit_resolvable_patient(self):
        launch_uri = "https://app.example/launch"
        patient_id = identity.patient_id(self.patient_a)

        anonymous = self.client.get(
            "/fhir/R4/launch",
            {"launch_uri": launch_uri, "patient": patient_id},
        )
        self.assertEqual(anonymous.status_code, 401)

        self.client.force_login(self.user)
        missing_patient = self.client.get("/fhir/R4/launch", {"launch_uri": launch_uri})
        self.assertEqual(missing_patient.status_code, 400)
        unknown_patient = self.client.get(
            "/fhir/R4/launch",
            {"launch_uri": launch_uri, "patient": "does-not-exist"},
        )
        self.assertEqual(unknown_patient.status_code, 400)
        unauthorized_patient = self.client.get(
            "/fhir/R4/launch",
            {"launch_uri": launch_uri, "patient": identity.patient_id(self.patient_b)},
        )
        self.assertEqual(unauthorized_patient.status_code, 400)

        response = self.client.get(
            "/fhir/R4/launch",
            {"launch_uri": launch_uri, "patient": patient_id},
        )
        self.assertEqual(response.status_code, 302, response.content)
        launch_secret = parse_qs(urlparse(response["Location"]).query)["launch"][0]
        persisted = SMARTContextService.resolve_launch_context(launch_secret, user=self.user)
        self.assertEqual(persisted.patient_id, self.patient_a.id)
        self.assertFalse(
            SmartLaunchContext.objects.filter(token_digest=launch_secret).exists(),
            "Only a digest of the opaque launch secret may be stored.",
        )

    def test_launch_context_is_single_use(self):
        launch_secret, _launch = SMARTContextService.create_launch_context(
            patient_token=identity.patient_id(self.patient_a),
            user=self.user,
            target_launch_uri="https://app.example/launch",
        )
        SMARTContextService.bind_authorization_code(
            authorization_code="first-code",
            launch_token=launch_secret,
            user=self.user,
            client_id=self.application.client_id,
        )

        with self.assertRaises(SMARTContextError):
            SMARTContextService.bind_authorization_code(
                authorization_code="second-code",
                launch_token=launch_secret,
                user=self.user,
                client_id=self.application.client_id,
            )

    def test_dedicated_global_permission_allows_authorized_cross_care_launch(self):
        permission = Permission.objects.get(codename="launch_any_patient_smart_context")
        self.user.user_permissions.add(permission)
        self.client.force_login(self.user)

        response = self.client.get(
            "/fhir/R4/launch",
            {
                "launch_uri": "https://app.example/launch",
                "patient": identity.patient_id(self.patient_b),
            },
        )
        self.assertEqual(response.status_code, 302, response.content)
