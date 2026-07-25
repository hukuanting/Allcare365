import os
import sys
from datetime import date

import django
import pytest


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medical_system.settings")
django.setup()


from django.test import override_settings
from rest_framework.test import APIClient

from apps.clinical.health_screening.models import HealthScreening, Problem
from apps.clinical.patients.models import Patient
from apps.integration.fhir_integration.resource_identity import identity


def _create_patient(*, first_name, mrn, fhir_id=None, patient_id=None):
    metadata = {"fhir_patient_id": fhir_id} if fhir_id else {}
    values = {
        "first_name": first_name,
        "last_name": "Identity",
        "date_of_birth": date(1980, 1, 1),
        "sex": "female",
        "medical_record_number": mrn,
        "metadata_json": metadata,
    }
    if patient_id is not None:
        values["id"] = patient_id
    return Patient.objects.create(**values)


def _bundle_resources(response):
    assert response.status_code == 200, response.content
    payload = response.json()
    return [entry["resource"] for entry in payload.get("entry", [])]


@pytest.mark.django_db
@override_settings(FHIR_ALLOW_ANONYMOUS_READ=True, ALLOWED_HOSTS=["testserver"])
def test_projected_fhir_searches_keep_multiple_patients_distinct_and_exact():
    first = _create_patient(
        first_name="First",
        mrn="FHIR-IDENTITY-001",
        fhir_id="hospital-patient-one",
    )
    second = _create_patient(
        first_name="Second",
        mrn="FHIR-IDENTITY-002",
        fhir_id="hospital-patient-two",
    )
    HealthScreening.objects.create(patient=first, screening_date=date(2026, 7, 1))
    HealthScreening.objects.create(patient=second, screening_date=date(2026, 7, 2))
    first_problem = Problem.objects.create(patient=first, problem_name="First condition")
    second_problem = Problem.objects.create(patient=second, problem_name="Second condition")

    client = APIClient()

    patient_resources = _bundle_resources(client.get("/fhir/R4/Patient"))
    assert {resource["id"] for resource in patient_resources} == {
        "hospital-patient-one",
        "hospital-patient-two",
    }

    condition_resources = _bundle_resources(client.get("/fhir/R4/Condition"))
    assert {resource["id"] for resource in condition_resources} == {
        identity.condition_id(first_problem),
        identity.condition_id(second_problem),
    }
    assert {resource["subject"]["reference"] for resource in condition_resources} == {
        "Patient/hospital-patient-one",
        "Patient/hospital-patient-two",
    }

    isolated_resources = _bundle_resources(
        client.get(
            "/fhir/R4/Condition",
            {"patient": "Patient/hospital-patient-two"},
        )
    )
    assert [resource["id"] for resource in isolated_resources] == [
        identity.condition_id(second_problem)
    ]
    assert isolated_resources[0]["subject"]["reference"] == "Patient/hospital-patient-two"


@pytest.mark.django_db
@override_settings(FHIR_ALLOW_ANONYMOUS_READ=True, ALLOWED_HOSTS=["testserver"])
def test_unknown_patient_tokens_fail_closed_for_search_and_read():
    _create_patient(first_name="Existing", mrn="FHIR-IDENTITY-EXISTING")
    client = APIClient()

    resources = _bundle_resources(
        client.get("/fhir/R4/Condition", {"patient": "Patient/not-a-patient"})
    )
    assert resources == []

    response = client.get("/fhir/R4/Patient/not-a-patient")
    assert response.status_code == 404
    assert response.json()["resourceType"] == "OperationOutcome"

    assert identity.resolve_patient_db_id("not-a-patient") is None
    assert identity.resolve_patient_db_id("onc-patient-1") is None
    assert identity.resolve_patient_db_id("1") is None


@pytest.mark.django_db
def test_patient_identity_uses_only_unique_persisted_fhir_ids_and_preserves_onc_uuid():
    first = _create_patient(
        first_name="DuplicateOne",
        mrn="FHIR-IDENTITY-DUP-001",
        fhir_id="duplicated-logical-id",
    )
    second = _create_patient(
        first_name="DuplicateTwo",
        mrn="FHIR-IDENTITY-DUP-002",
        fhir_id="duplicated-logical-id",
    )
    onc_patient = _create_patient(
        first_name="ONC",
        mrn="FHIR-IDENTITY-ONC",
        patient_id=identity.SINGLE_PATIENT_FHIR_ID,
    )

    assert identity.patient_id(first) == str(first.id)
    assert identity.patient_id(second) == str(second.id)
    assert identity.resolve_patient_db_id("duplicated-logical-id") is None

    assert identity.patient_id(onc_patient) == identity.SINGLE_PATIENT_FHIR_ID
    assert identity.resolve_patient_db_id(identity.SINGLE_PATIENT_FHIR_ID) == str(onc_patient.id)


@pytest.mark.django_db
@override_settings(FHIR_ALLOW_ANONYMOUS_READ=True, ALLOWED_HOSTS=["testserver"])
def test_patient_identifier_search_never_silently_selects_one_duplicate():
    first = _create_patient(first_name="DuplicateMrnOne", mrn="DUPLICATE-MRN")
    second = _create_patient(first_name="DuplicateMrnTwo", mrn="DUPLICATE-MRN")

    resources = _bundle_resources(
        APIClient().get("/fhir/R4/Patient", {"identifier": "DUPLICATE-MRN"})
    )

    assert {resource["id"] for resource in resources} == {
        identity.patient_id(first),
        identity.patient_id(second),
    }
