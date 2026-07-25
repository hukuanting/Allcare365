from datetime import timedelta
import os
import sys

import pytest


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medical_system.settings")

import django


django.setup()

from django.contrib.auth.models import Permission, User
from django.utils import timezone
from rest_framework.test import APIClient

from apps.clinical.health_screening.models import AIAnalysisJob, AIAnalysisResult, HealthScreening
from apps.clinical.health_screening.golden_patient import (
    EXPECTED_EXECUTABLE_RISK_ALGORITHMS,
    GoldenPatientSeeder,
)
from apps.clinical.patients.access_policy import PatientRiskAccessPolicy
from apps.clinical.patients.clinical_scope import (
    GOLDEN_DEMO_SOURCE_SYSTEM,
)
from apps.clinical.patients.models import Patient, PatientPractitionerLink, Practitioner
from apps.integration.fhir_integration.models import AuditLog, FHIRResource


def _patient(mrn="ACCESS-001"):
    return Patient.objects.create(
        first_name="Access",
        last_name="Patient",
        medical_record_number=mrn,
    )


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _golden_demo_patient():
    seeded = GoldenPatientSeeder().seed()
    return Patient.objects.get(id=seeded.patient_id)


def _response_items(response):
    payload = response.json()
    return payload["results"] if isinstance(payload, dict) and "results" in payload else payload


def _practitioner_link(user, patient, **link_overrides):
    practitioner, _ = Practitioner.objects.get_or_create(
        user=user,
        defaults={
            "identifier": f"practitioner-{user.pk}",
            "first_name": "Risk",
            "last_name": "Clinician",
            "status": "active",
        },
    )
    defaults = {
        "status": "active",
        "start_at": timezone.now() - timedelta(days=1),
        "end_at": timezone.now() + timedelta(days=1),
    }
    defaults.update(link_overrides)
    return PatientPractitionerLink.objects.create(
        patient=patient,
        practitioner=practitioner,
        **defaults,
    )


def _assert_no_risk_side_effects(patient):
    assert not AIAnalysisJob.objects.filter(patient=patient).exists()
    assert not AIAnalysisResult.objects.filter(patient=patient).exists()
    assert not AuditLog.objects.filter(patient=patient, action="disease_risk_assess").exists()
    assert not FHIRResource.objects.filter(
        resource_type__in=("RiskAssessment", "Observation", "Provenance")
    ).exists()


@pytest.mark.django_db
def test_unlinked_user_gets_403_on_all_risk_endpoints_before_any_write():
    patient = _patient()
    screening = HealthScreening.objects.create(patient=patient)
    user = User.objects.create_user(username="unlinked-risk-user", password="password")
    client = _client(user)

    requests = (
        (client.post, "/api/health-screening/risk-analysis/", {"patient_id": str(patient.id)}),
        (client.post, "/api/health-screening/disease-risk/", {"patient_id": str(patient.id)}),
        (
            client.get,
            f"/api/health-screening/screenings/{screening.id}/risk-analysis/",
            None,
        ),
        (
            client.post,
            f"/api/health-screening/screenings/{screening.id}/calculate_comprehensive_risk/",
            {},
        ),
    )
    for request_method, url, payload in requests:
        response = request_method(url, payload, format="json") if payload is not None else request_method(url)
        assert response.status_code == 403
        _assert_no_risk_side_effects(patient)


@pytest.mark.django_db
def test_current_linked_practitioner_can_run_risk_by_exact_mrn():
    patient = _patient(mrn="ACCESS-LINKED")
    user = User.objects.create_user(username="linked-risk-user", password="password")
    _practitioner_link(user, patient)

    response = _client(user).post(
        "/api/health-screening/risk-analysis/",
        {"patient_id": patient.medical_record_number},
        format="json",
    )

    assert response.status_code == 200
    assert AIAnalysisJob.objects.filter(patient=patient, requested_by_user=user).count() == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "link_overrides",
    (
        {"status": "inactive"},
        {"is_active": False},
        {
            "start_at": timezone.now() - timedelta(days=2),
            "end_at": timezone.now() - timedelta(seconds=1),
        },
        {
            "start_at": timezone.now() + timedelta(days=1),
            "end_at": timezone.now() + timedelta(days=2),
        },
    ),
)
def test_inactive_or_out_of_period_care_link_is_denied(link_overrides):
    patient = _patient()
    user = User.objects.create_user(username="invalid-link-user", password="password")
    _practitioner_link(user, patient, **link_overrides)

    response = _client(user).post(
        "/api/health-screening/risk-analysis/",
        {"patient_id": str(patient.id)},
        format="json",
    )

    assert response.status_code == 403
    _assert_no_risk_side_effects(patient)


@pytest.mark.django_db
def test_current_link_explicit_risk_deny_takes_precedence():
    patient = _patient()
    user = User.objects.create_user(username="denied-link-user", password="password")
    _practitioner_link(user, patient, permissions_json={"risk_analysis": False})
    _practitioner_link(
        user,
        patient,
        link_type="consulting",
        permissions_json={"risk_analysis": "allow"},
    )

    response = _client(user).post(
        "/api/health-screening/risk-analysis/",
        {"patient_id": str(patient.id)},
        format="json",
    )

    assert response.status_code == 403
    _assert_no_risk_side_effects(patient)


@pytest.mark.django_db
def test_explicit_global_permission_can_run_any_patient_risk_assessment():
    patient = _patient()
    user = User.objects.create_user(username="global-risk-user", password="password")
    permission = Permission.objects.get(
        content_type__app_label="patients",
        codename="run_all_patient_risk_assessments",
    )
    user.user_permissions.add(permission)
    # Avoid a stale ``_perm_cache`` if the user instance was inspected earlier.
    user = User.objects.get(pk=user.pk)

    response = _client(user).post(
        "/api/health-screening/risk-analysis/",
        {"patient_id": str(patient.id)},
        format="json",
    )

    assert response.status_code == 200
    assert AIAnalysisJob.objects.filter(patient=patient, requested_by_user=user).count() == 1
    assert user.has_perm(PatientRiskAccessPolicy.GLOBAL_PERMISSION)


@pytest.mark.django_db
def test_patient_picker_explicitly_adds_only_the_marked_golden_demo_patient():
    clinical = _patient(mrn="CLINICAL-LIST-001")
    golden = _golden_demo_patient()
    other_fixture = Patient.objects.create(
        first_name="Other",
        last_name="Fixture",
        medical_record_number="OTHER-FIXTURE-001",
        source_system="certification-suite",
        metadata_json={"synthetic": True, "clinical_use_prohibited": True},
    )
    user = User.objects.create_user(username="patient-picker-user", password="password")
    client = _client(user)

    default_response = client.get("/api/patients/")
    demo_response = client.get("/api/patients/?include_demo=true")

    assert default_response.status_code == 200
    assert demo_response.status_code == 200
    default_ids = {item["id"] for item in _response_items(default_response)}
    demo_items = _response_items(demo_response)
    demo_ids = {item["id"] for item in demo_items}
    assert str(clinical.id) in default_ids
    assert str(golden.id) not in default_ids
    assert str(other_fixture.id) not in default_ids
    assert str(golden.id) in demo_ids
    assert str(other_fixture.id) not in demo_ids
    golden_payload = next(item for item in demo_items if item["id"] == str(golden.id))
    assert golden_payload["is_demo_patient"] is True
    assert golden_payload["demo_label"] == "Golden Patient（展示用合成病患）"
    assert client.get(f"/api/patients/{golden.id}/").status_code == 404


@pytest.mark.django_db
def test_authenticated_user_can_run_only_the_exact_golden_demo_without_care_link():
    golden = _golden_demo_patient()
    fake_golden = Patient.objects.create(
        first_name="Not",
        last_name="Golden",
        medical_record_number="GOLDEN-LOOKALIKE-001",
        source_system=GOLDEN_DEMO_SOURCE_SYSTEM,
        metadata_json={"synthetic": True, "clinical_use_prohibited": True},
    )
    user = User.objects.create_user(username="golden-demo-user", password="password")
    client = _client(user)

    response = client.post(
        "/api/health-screening/risk-analysis/",
        {"patient_id": str(golden.id)},
        format="json",
    )
    fhir_output_count = FHIRResource.objects.filter(
        resource_type__in=("RiskAssessment", "Observation", "Provenance")
    ).count()
    fake_response = client.post(
        "/api/health-screening/risk-analysis/",
        {"patient_id": str(fake_golden.id)},
        format="json",
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["disease_risk_results"]) == len(EXPECTED_EXECUTABLE_RISK_ALGORITHMS)
    assert payload["algorithm_catalog"]["counts"]["total_models"] == len(EXPECTED_EXECUTABLE_RISK_ALGORITHMS)
    execution = payload["execution_summary"]
    assert execution["runtime_catalog_models"] == len(EXPECTED_EXECUTABLE_RISK_ALGORITHMS)
    assert execution["executable_models"] == len(EXPECTED_EXECUTABLE_RISK_ALGORITHMS)
    assert execution["calculated_models"] == 39
    assert execution["insufficient_data_models"] == 0
    assert execution["not_applicable_models"] == 3
    assert execution["governance_gated_models"] == 0
    assert execution["resolved_models"] == len(EXPECTED_EXECUTABLE_RISK_ALGORITHMS)
    assert execution["all_executable_models_resolved"] is True
    assert set(execution["calculated_algorithm_ids"]) | set(
        execution["not_applicable_algorithm_ids"]
    ) == EXPECTED_EXECUTABLE_RISK_ALGORITHMS
    assert execution["insufficient_data_algorithm_ids"] == []
    assert execution["governance_gated_algorithm_ids"] == []
    assert AIAnalysisJob.objects.filter(patient=golden, requested_by_user=user).count() == 1
    assert fake_response.status_code == 404
    assert not AIAnalysisJob.objects.filter(patient=fake_golden).exists()
    assert not AIAnalysisResult.objects.filter(patient=fake_golden).exists()
    assert not AuditLog.objects.filter(
        patient=fake_golden,
        action="disease_risk_assess",
    ).exists()
    assert FHIRResource.objects.filter(
        resource_type__in=("RiskAssessment", "Observation", "Provenance")
    ).count() == fhir_output_count


@pytest.mark.django_db
def test_authenticated_user_can_read_complete_non_conflicted_model_catalog():
    user = User.objects.create_user(username="risk-catalog-user", password="password")

    response = _client(user).get("/api/health-screening/risk-algorithms/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["counts"]["total_models"] == len(EXPECTED_EXECUTABLE_RISK_ALGORITHMS)
    algorithms = [
        algorithm
        for system in payload["systems"]
        for algorithm in system["algorithms"]
    ]
    assert len(algorithms) == len(EXPECTED_EXECUTABLE_RISK_ALGORITHMS)
    assert all("formula" not in algorithm for algorithm in algorithms)
