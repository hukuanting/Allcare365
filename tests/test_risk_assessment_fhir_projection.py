import json
import os
import uuid
from datetime import date

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medical_system.settings")
django.setup()

from django.test import TestCase, override_settings
from django.utils import timezone
from fhirclient.models.riskassessment import RiskAssessment as FHIRRiskAssessment

from apps.clinical.patients.models import Patient
from apps.integration.fhir_integration.models import FHIRResource, FHIRResourceMapping
from apps.integration.fhir_integration.resource_identity import identity


@override_settings(FHIR_ALLOW_ANONYMOUS_READ=True, ALLOWED_HOSTS=["testserver"])
class RiskAssessmentFHIRProjectionTests(TestCase):
    def setUp(self):
        self.patient = Patient.objects.create(
            first_name="Risk",
            last_name="Projection",
            date_of_birth=date(1975, 2, 3),
            sex="female",
            medical_record_number="RISK-PROJECTION-001",
            is_active=True,
        )

    @staticmethod
    def _risk_json(patient, resource_id):
        return {
            "resourceType": "RiskAssessment",
            "id": resource_id,
            "status": "final",
            "subject": {"reference": f"Patient/{identity.patient_id(patient)}"},
            "occurrenceDateTime": timezone.now().isoformat(),
            "method": {"text": "Persisted test equation"},
            "prediction": [
                {
                    "outcome": {"text": "cardiovascular-event"},
                    "qualitativeRisk": {"text": "moderate"},
                    "probabilityDecimal": 0.12,
                }
            ],
        }

    def _map_resource(self, patient, resource_data, *, local_id=None):
        persisted = FHIRResource.objects.create(
            resource_type=resource_data["resourceType"],
            resource_id=resource_data["id"],
            origin_namespace="tests:risk-projection:v1",
            resource_data=resource_data,
        )
        mapping = FHIRResourceMapping.objects.create(
            patient=patient,
            fhir_resource_ref=persisted,
            local_table="test_risk_results",
            local_id=local_id or uuid.uuid4(),
            fhir_resource_type=resource_data["resourceType"],
            fhir_resource_id=resource_data["id"],
            fhir_json=resource_data,
            sync_status="mapped",
        )
        return persisted, mapping

    def _map_provenance(self, patient, risk_id):
        resource_id = f"provenance-{risk_id}"
        data = {
            "resourceType": "Provenance",
            "id": resource_id,
            "target": [{"reference": f"RiskAssessment/{risk_id}"}],
            "recorded": timezone.now().isoformat(),
            "agent": [{"who": {"display": "Persisted risk engine"}}],
        }
        return self._map_resource(patient, data)

    def test_read_search_and_revinclude_return_only_persisted_valid_resources(self):
        risk_id = "risk-projection-valid"
        data = self._risk_json(self.patient, risk_id)
        self._map_resource(self.patient, data)
        self._map_provenance(self.patient, risk_id)

        search = self.client.get(
            "/fhir/R4/RiskAssessment",
            {
                "patient": f"Patient/{identity.patient_id(self.patient)}",
                "_revinclude": "Provenance:target",
            },
        )
        self.assertEqual(search.status_code, 200, search.content)
        payload = json.loads(search.content)
        self.assertEqual(payload["total"], 1)
        entries = payload.get("entry", [])
        matches = [entry for entry in entries if entry.get("search", {}).get("mode") == "match"]
        includes = [entry for entry in entries if entry.get("search", {}).get("mode") == "include"]
        self.assertEqual([entry["resource"]["id"] for entry in matches], [risk_id])
        self.assertEqual(
            [entry["resource"]["id"] for entry in includes],
            [f"provenance-{risk_id}"],
        )
        FHIRRiskAssessment(matches[0]["resource"], strict=True)

        read = self.client.get(f"/fhir/R4/RiskAssessment/{risk_id}")
        self.assertEqual(read.status_code, 200, read.content)
        self.assertEqual(json.loads(read.content), data)

    def test_unmapped_inconsistent_and_cross_subject_rows_fail_closed(self):
        valid_id = "risk-only-valid-row"
        self._map_resource(self.patient, self._risk_json(self.patient, valid_id))

        unmapped = self._risk_json(self.patient, "risk-unmapped")
        FHIRResource.objects.create(
            resource_type="RiskAssessment",
            resource_id=unmapped["id"],
            origin_namespace="tests:risk-projection:v1",
            resource_data=unmapped,
        )

        inconsistent = self._risk_json(self.patient, "risk-inconsistent-mapping")
        _, inconsistent_mapping = self._map_resource(self.patient, inconsistent)
        inconsistent_mapping.fhir_json = {**inconsistent, "status": "registered"}
        inconsistent_mapping.save(update_fields=["fhir_json"])

        other_patient = Patient.objects.create(
            first_name="Other",
            last_name="Subject",
            date_of_birth=date(1981, 4, 5),
            sex="male",
            medical_record_number="RISK-PROJECTION-OTHER",
            is_active=True,
        )
        wrong_subject = self._risk_json(other_patient, "risk-wrong-subject")
        self._map_resource(self.patient, wrong_subject)

        response = self.client.get("/fhir/R4/RiskAssessment")
        self.assertEqual(response.status_code, 200, response.content)
        body = json.loads(response.content)
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["entry"][0]["resource"]["id"], valid_id)

        for rejected_id in ("risk-unmapped", "risk-inconsistent-mapping", "risk-wrong-subject"):
            rejected = self.client.get(f"/fhir/R4/RiskAssessment/{rejected_id}")
            self.assertEqual(rejected.status_code, 404, rejected.content)

    def test_conformance_fixture_is_hidden_unless_explicitly_enabled(self):
        visible_id = "risk-clinical"
        self._map_resource(self.patient, self._risk_json(self.patient, visible_id))

        fixture = Patient.objects.create(
            first_name="Certification",
            last_name="Fixture",
            date_of_birth=date(1970, 1, 1),
            sex="female",
            medical_record_number="RISK-CONFORMANCE-FIXTURE",
            is_active=True,
            metadata_json={"clinical_use_prohibited": True},
        )
        fixture_id = "risk-conformance-only"
        self._map_resource(fixture, self._risk_json(fixture, fixture_id))

        default_response = self.client.get("/fhir/R4/RiskAssessment")
        self.assertEqual(default_response.status_code, 200, default_response.content)
        default_ids = {
            entry["resource"]["id"]
            for entry in json.loads(default_response.content).get("entry", [])
        }
        self.assertEqual(default_ids, {visible_id})

        with override_settings(FHIR_INCLUDE_CONFORMANCE_FIXTURES=True):
            conformance_response = self.client.get("/fhir/R4/RiskAssessment")
        self.assertEqual(conformance_response.status_code, 200, conformance_response.content)
        conformance_ids = {
            entry["resource"]["id"]
            for entry in json.loads(conformance_response.content).get("entry", [])
        }
        self.assertEqual(conformance_ids, {visible_id, fixture_id})
