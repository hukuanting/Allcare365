import os
import sys
import unittest
import uuid

import django
from django.conf import settings


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medical_system.settings")

if not settings.configured:
    settings.configure(
        INSTALLED_APPS=[
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "apps.clinical.patients",
            "apps.clinical.health_screening",
            "apps.integration.fhir_integration",
        ],
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        SECRET_KEY="test",
        USE_TZ=True,
    )
    django.setup()


import apps.integration.fhir_integration.projectors  # noqa: F401
from apps.integration.fhir_integration.capability_statement import generate_capability_statement
from apps.integration.fhir_integration.fhir_context import FHIRContext
from apps.integration.fhir_integration.g10_testkit import build_g10_single_patient_contract
from apps.integration.fhir_integration.projectors.document_reference import DocumentReferenceProjector
from apps.integration.fhir_integration.projectors.observation import ObservationProjector, _ObservationRow
from apps.integration.fhir_integration.projectors.registry import ProjectorRegistry
from apps.integration.fhir_integration.projection_contracts import all_projection_contracts
from apps.integration.fhir_integration.uscore_capability import extract_us_core_capability


class USCoreProjectionContractTests(unittest.TestCase):
    def test_capability_extraction_contains_required_resources(self):
        extracted = extract_us_core_capability()
        for resource_type in (
            "Patient",
            "Condition",
            "Coverage",
            "DiagnosticReport",
            "Observation",
            "MedicationRequest",
            "Encounter",
            "DocumentReference",
        ):
            self.assertIn(resource_type, extracted.resource_types)

    def test_projection_contracts_expose_deterministic_searches(self):
        contracts = all_projection_contracts()
        self.assertIn("_id", contracts["Patient"].deterministic_search_params)
        self.assertIn("identifier", contracts["Patient"].deterministic_search_params)
        self.assertIn("patient", contracts["Observation"].deterministic_search_params)
        self.assertIn("category", contracts["Observation"].deterministic_search_params)

    def test_capability_statement_is_contract_driven(self):
        capability = generate_capability_statement("https://example.org/fhir")
        self.assertIn("http://hl7.org/fhir/us/core/CapabilityStatement/us-core-server", capability["instantiates"])
        resources = {entry["type"]: entry for entry in capability["rest"][0]["resource"]}
        self.assertIn("Patient", resources)
        self.assertIn("Observation", resources)
        self.assertTrue(resources["Patient"]["supportedProfile"])
        self.assertTrue(any(param["name"] == "_id" for param in resources["Patient"]["searchParam"]))
        self.assertTrue(any(param["name"] == "patient" for param in resources["Observation"]["searchParam"]))
        self.assertTrue(any(param["name"] == "status" for param in resources["Procedure"]["searchParam"]))
        self.assertTrue(any(param["name"] == "authored" for param in resources["ServiceRequest"]["searchParam"]))
        self.assertTrue(any(param["name"] == "code" for param in resources["ServiceRequest"]["searchParam"]))

    def test_capability_statement_lists_required_missing_profiles(self):
        capability = generate_capability_statement("https://example.org/fhir")
        resources = {entry["type"]: entry for entry in capability["rest"][0]["resource"]}
        self.assertIn("AllergyIntolerance", resources)
        self.assertIn("CarePlan", resources)
        self.assertIn("MedicationDispense", resources)
        self.assertIn("Specimen", resources)
        self.assertIn(
            "http://hl7.org/fhir/us/core/StructureDefinition/us-core-allergyintolerance",
            resources["AllergyIntolerance"]["supportedProfile"],
        )
        self.assertIn(
            "http://hl7.org/fhir/us/core/StructureDefinition/us-core-careplan",
            resources["CarePlan"]["supportedProfile"],
        )
        self.assertIn(
            "http://hl7.org/fhir/us/core/StructureDefinition/us-core-medicationdispense",
            resources["MedicationDispense"]["supportedProfile"],
        )
        self.assertIn(
            "http://hl7.org/fhir/us/core/StructureDefinition/us-core-specimen",
            resources["Specimen"]["supportedProfile"],
        )
        self.assertIn(
            "http://hl7.org/fhir/us/core/StructureDefinition/us-core-observation-occupation",
            resources["Observation"]["supportedProfile"],
        )

    def test_g10_contract_records_justin_hu_as_golden_patient(self):
        contract = build_g10_single_patient_contract()
        self.assertEqual(contract["manifest"]["golden_patient_name"], "Justin Hu")
        self.assertEqual(
            contract["manifest"]["golden_patient_id"],
            "00000000-0000-4000-a000-000000000001",
        )
        self.assertIn("Observation", contract["resources"])
        self.assertIn("Condition", contract["resources"])

    def test_pediatric_bmi_for_age_projection_has_value_quantity_slice(self):
        patient = type("PatientStub", (), {"id": "00000000-0000-4000-a000-000000000001"})()
        row = _ObservationRow(
            source=(72.0, "unit_percent", "bmi_percentile", "us-core-pediatric-bmi-for-age"),
            source_type="vitals",
            patient=patient,
            patient_id=str(patient.id),
            effective_dt="2026-04-01",
            obs_id_suffix="bmi_percentile-398a5de5-4c08-4327-b451-29076cd6e328",
        )

        resource = ObservationProjector().project(row, FHIRContext(patient_id=str(patient.id)))

        self.assertIn("http://hl7.org/fhir/us/core/StructureDefinition/pediatric-bmi-for-age", resource["meta"]["profile"])
        self.assertIn("-pbmi-", resource["id"])
        self.assertEqual(resource["code"]["coding"][0]["code"], "59576-9")
        self.assertEqual(resource["valueQuantity"]["value"], 72.0)
        self.assertEqual(resource["valueQuantity"]["system"], "http://unitsofmeasure.org")
        self.assertEqual(resource["valueQuantity"]["code"], "%")

    def test_smoking_status_quantity_projection_has_value_quantity_slice(self):
        patient = type("PatientStub", (), {"id": "00000000-0000-4000-a000-000000000001"})()
        assessment = type("AssessmentStub", (), {"id": "65adb19d-982d-473a-ab3e-444b4a997c0c"})()
        row = _ObservationRow(
            source=assessment,
            source_type="smoking_quantity",
            patient=patient,
            patient_id=str(patient.id),
            effective_dt="2026-04-01",
            obs_id_suffix="smoking-pack-years",
        )

        resource = ObservationProjector().project(row, FHIRContext(patient_id=str(patient.id)))

        self.assertIn("http://hl7.org/fhir/us/core/StructureDefinition/us-core-smokingstatus", resource["meta"]["profile"])
        self.assertEqual(resource["code"]["coding"][0]["code"], "401201003")
        self.assertEqual(resource["valueQuantity"]["value"], 20.0)
        self.assertEqual(resource["valueQuantity"]["system"], "http://unitsofmeasure.org")
        self.assertEqual(resource["valueQuantity"]["code"], "{pack-years}")

    def test_provenance_projection_includes_author_and_transmitter_agents(self):
        target = {
            "resourceType": "ServiceRequest",
            "id": "sreq-test",
            "meta": {"lastUpdated": "2026-04-08T10:00:00Z"},
        }

        resource = ProjectorRegistry.get("Provenance").project(target, FHIRContext())
        agent_codes = {
            coding["code"]
            for agent in resource["agent"]
            for coding in agent["type"]["coding"]
        }

        self.assertEqual(resource["target"][0]["reference"], "ServiceRequest/sreq-test")
        self.assertLessEqual(len(resource["id"]), 64)
        self.assertIn("author", agent_codes)
        self.assertIn("transmitter", agent_codes)
        self.assertTrue(all("onBehalfOf" in agent for agent in resource["agent"]))
        self.assertEqual(resource["entity"][0]["role"], "source")

    def test_document_reference_attachment_url_uses_valid_uuid_uri(self):
        doc = type("DocStub", (), {"id": "reqdoc-11502-2"})()

        url = DocumentReferenceProjector._attachment_url(doc)
        prefix, value = url.rsplit(":", 1)

        self.assertEqual(prefix, "urn:uuid")
        self.assertEqual(str(uuid.UUID(value)), value)


if __name__ == "__main__":
    unittest.main()
