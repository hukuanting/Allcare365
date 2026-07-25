import base64
import os
import sys
from datetime import date
from io import StringIO

import pytest


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medical_system.settings")

import django


django.setup()

from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone
from fhirclient.models.bundle import Bundle as FHIRBundle
from fhirclient.models.documentreference import DocumentReference as FHIRDocumentReference
from fhirclient.models.patient import Patient as FHIRPatient

from apps.clinical.patients.models import Patient, PatientDocument
from apps.integration.fhir_integration.fhir_context import FHIRContext
from apps.integration.fhir_integration.models import FHIRResource
from apps.integration.fhir_integration.operation_outcome import (
    FHIRBadRequest,
    FHIRNotSupported,
    FHIRServerError,
)
from apps.integration.fhir_integration.projectors.document_reference import (
    DocumentReferenceProjector,
)
from apps.integration.fhir_integration.projectors.patient import PatientProjector
from apps.integration.fhir_integration.resource_identity import identity
from apps.integration.fhir_integration.services import FHIRService


@pytest.mark.django_db
def test_patient_projection_uses_absent_semantics_without_fabricating_values():
    patient = Patient.objects.create(
        first_name="",
        last_name="",
        date_of_birth=date(2001, 2, 3),
        sex="",
        country="",
        preferred_language="",
        medical_record_number=None,
    )

    resource = PatientProjector().project(patient, FHIRContext())
    FHIRPatient(resource, strict=True)

    assert resource["birthDate"] == "2001-02-03"
    assert resource["_gender"]["extension"][0]["valueCode"] == "unknown"
    for field in (
        "identifier",
        "name",
        "telecom",
        "gender",
        "address",
        "communication",
        "extension",
        "deceasedDateTime",
        "link",
        "multipleBirthBoolean",
    ):
        assert field not in resource

    serialized = str(resource)
    for fake_value in (
        "1980-01-01",
        "Unknown",
        "555-555-5555",
        "123 Main St",
        "PreviousName",
        "White",
        "Apache",
    ):
        assert fake_value not in serialized

    # Defensive coverage for legacy rows imported before date_of_birth became required.
    patient.date_of_birth = None
    without_birth_date = PatientProjector().project(patient, FHIRContext())
    FHIRPatient(without_birth_date, strict=True)
    assert "birthDate" not in without_birth_date
    assert without_birth_date["_birthDate"]["extension"][0]["valueCode"] == "unknown"

    patient.date_of_death = date(2024, 4, 5)
    with_persisted_death_date = PatientProjector().project(patient, FHIRContext())
    FHIRPatient(with_persisted_death_date, strict=True)
    assert with_persisted_death_date["deceasedDateTime"] == "2024-04-05"


@pytest.mark.django_db
def test_patient_identifier_system_comes_only_from_persisted_provenance():
    without_system = Patient.objects.create(
        first_name="Local",
        last_name="Identifier",
        medical_record_number="LOCAL-MRN-001",
    )
    with_system = Patient.objects.create(
        first_name="Imported",
        last_name="Identifier",
        medical_record_number="IMPORTED-MRN-001",
        metadata_json={"fhir_mrn_system": "https://hospital.example/mrn"},
    )

    local_resource = PatientProjector().project(without_system, FHIRContext())
    imported_resource = PatientProjector().project(with_system, FHIRContext())

    assert local_resource["identifier"] == [{"value": "LOCAL-MRN-001"}]
    assert imported_resource["identifier"] == [{
        "system": "https://hospital.example/mrn",
        "value": "IMPORTED-MRN-001",
    }]
    assert "smarthealthit" not in str(local_resource)
    assert list(
        PatientProjector().query(
            None,
            {"identifier": "https://hospital.example/mrn|IMPORTED-MRN-001"},
            FHIRContext(),
        )
    ) == [with_system]
    assert not PatientProjector().query(
        None,
        {"identifier": "https://other.example/mrn|IMPORTED-MRN-001"},
        FHIRContext(),
    ).exists()


@pytest.mark.django_db
def test_conformance_patients_are_hidden_from_normal_fhir_search_by_default():
    fixture = Patient.objects.create(
        first_name="Golden",
        last_name="Fixture",
        medical_record_number="GOLDEN-HIDDEN-001",
        metadata_json={"synthetic": True, "clinical_use_prohibited": True},
    )
    projector = PatientProjector()

    assert fixture not in list(projector.query(None, {}, FHIRContext()))
    with override_settings(FHIR_INCLUDE_CONFORMANCE_FIXTURES=True):
        assert fixture in list(projector.query(None, {}, FHIRContext()))


@pytest.mark.django_db
def test_fhir_service_projects_persisted_onc_patient_and_provenance_only():
    call_command("seed_onc_patient", stdout=StringIO())
    patient = Patient.objects.get(medical_record_number="ONC-2026-001")

    resource = PatientProjector().project(patient, FHIRContext())
    FHIRPatient(resource, strict=True)
    assert resource["id"] == identity.patient_id(patient)
    assert resource["name"] == [{"use": "official", "family": "Hu", "given": ["Justin"]}]
    assert resource["birthDate"] == "1985-01-01"
    assert resource["gender"] == "male"
    assert resource["telecom"] == [
        {"system": "phone", "value": "15558675309", "use": "mobile"},
        {"system": "email", "value": "justin.hu@example.com"},
    ]
    assert resource["address"] == [{
        "use": "home",
        "line": ["123 Interoperability Lane"],
        "city": "Boston",
        "state": "MA",
        "postalCode": "02134",
        "country": "US",
    }]
    assert resource["communication"][0]["language"]["coding"][0]["code"] == "en-US"
    extension_values = {
        item["url"]: item["extension"][0].get("valueString")
        for item in resource["extension"]
    }
    assert extension_values == {
        "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race": "Asian",
        "http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity": "Not Hispanic or Latino",
    }
    assert "deceasedDateTime" not in resource

    provenance_id = "prov-onc-patient-persisted"
    target_reference = f"Patient/{identity.patient_id(patient)}"
    FHIRResource.objects.create(
        resource_type="Provenance",
        resource_id=provenance_id,
        resource_data={
            "resourceType": "Provenance",
            "id": provenance_id,
            "target": [{"reference": target_reference}],
            "recorded": timezone.now().isoformat(),
            "agent": [{
                "type": {"coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/provenance-participant-type",
                    "code": "author",
                }]},
                "who": {"reference": target_reference},
            }],
        },
    )

    service = FHIRService()
    bundle = service.create_search_bundle(
        [patient],
        "Patient",
        rev_includes=["Provenance:target"],
    )
    FHIRBundle(bundle, strict=True)
    assert bundle["total"] == 1
    assert [entry["search"]["mode"] for entry in bundle["entry"]] == ["match", "include"]
    projected_patient, provenance = [entry["resource"] for entry in bundle["entry"]]
    assert projected_patient["id"] == identity.patient_id(patient)
    assert provenance["resourceType"] == "Provenance"
    assert provenance["id"] == provenance_id
    assert provenance["target"] == [{"reference": target_reference}]
    assert not hasattr(service, "get_mock_resources")
    assert not hasattr(service, "get_mock_resources_for_patient")

    docs = DocumentReferenceProjector().query(
        identity.patient_id(patient),
        {},
        FHIRContext(patient_id=identity.patient_id(patient)),
    )
    assert len(docs) == PatientDocument.objects.filter(patient=patient, is_active=True).count() == 3
    for doc in docs:
        FHIRDocumentReference(
            DocumentReferenceProjector().project(doc, FHIRContext()),
            strict=True,
        )


@pytest.mark.django_db
def test_document_reference_query_returns_only_persisted_active_notes():
    patient = Patient.objects.create(
        first_name="Persisted",
        last_name="Notes",
        date_of_birth=date(1992, 5, 6),
        sex="female",
        country="",
        preferred_language="",
        metadata_json={"fhir_patient_id": "persisted-note-patient"},
    )
    patient_fhir_id = identity.patient_id(patient)
    projector = DocumentReferenceProjector()
    context = FHIRContext(patient_id=patient_fhir_id)

    assert list(projector.query(patient_fhir_id, {}, context)) == []

    persisted = PatientDocument.objects.create(
        patient=patient,
        note_type="progress",
        content="This content was persisted by the hospital.",
        document_date=timezone.now(),
    )
    PatientDocument.objects.create(
        patient=patient,
        note_type="procedure",
        content="Inactive persisted note.",
        document_date=timezone.now(),
        is_active=False,
    )

    rows = list(projector.query(patient_fhir_id, {}, context))
    assert rows == [persisted]
    resource = projector.project(rows[0], context)
    FHIRDocumentReference(resource, strict=True)
    assert base64.b64decode(resource["content"][0]["attachment"]["data"]).decode() == (
        "This content was persisted by the hospital."
    )
    assert "reqdoc-" not in str(resource)
    assert "generated for US Core" not in str(resource)


def test_fhir_service_failures_are_operation_outcomes_without_mock_fallback():
    service = FHIRService()

    with pytest.raises(FHIRNotSupported) as unsupported:
        service.create_search_bundle([], "SyntheticResource")
    assert unsupported.value.to_operation_outcome()["resourceType"] == "OperationOutcome"

    with pytest.raises(FHIRBadRequest) as invalid_provenance:
        service.create_provenance_for_resource({"resourceType": "Patient"})
    assert invalid_provenance.value.to_operation_outcome()["issue"][0]["code"] == "invalid"

    with pytest.raises(FHIRServerError) as projection_failure:
        service._create_basic_patient_resource(object())
    outcome = projection_failure.value.to_operation_outcome()
    assert outcome["resourceType"] == "OperationOutcome"
    assert "no synthetic fallback" in outcome["issue"][0]["diagnostics"]
