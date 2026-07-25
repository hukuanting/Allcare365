import json
import os
import sys
from datetime import date
from types import SimpleNamespace
from unittest import mock

import django
import pytest


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medical_system.settings")
django.setup()

from django.test import override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.clinical.health_screening.models import HealthScreening, Problem
from apps.clinical.patients.models import Patient
from apps.integration.fhir_integration.projectors.registry import ProjectorRegistry
from apps.integration.fhir_integration.resource_identity import identity
from apps.integration.fhir_integration.models import FHIRResource
from apps.integration.fhir_integration.views import BulkExportViewSet


TOKEN = SimpleNamespace(
    scope="system/*.read",
    application_id="bulk-persisted-client",
    user_id=None,
)


def _patient(*, first_name, mrn, fhir_id, active=True):
    return Patient.objects.create(
        first_name=first_name,
        last_name="BulkExport",
        date_of_birth=date(1984, 3, 2),
        sex="female",
        medical_record_number=mrn,
        metadata_json={"fhir_patient_id": fhir_id},
        is_active=active,
    )


def _persist_group(patients, group_id="example-group"):
    members = [
        {"entity": {"reference": f"Patient/{identity.patient_id(patient)}"}}
        for patient in patients
    ]
    resource, _ = FHIRResource.objects.update_or_create(
        resource_type="Group",
        resource_id=group_id,
        defaults={
            "resource_data": {
                "resourceType": "Group",
                "id": group_id,
                "type": "person",
                "actual": True,
                "quantity": len(members),
                "member": members,
            }
        },
    )
    return resource


def _get(factory, path, *, action, query=None, token=TOKEN, **view_kwargs):
    request = factory.get(path, data=query or {}, HTTP_HOST="testserver")
    force_authenticate(request, token=token)
    view = BulkExportViewSet.as_view({"get": action})
    return view(request, **view_kwargs)


def _kickoff(factory, *, export_type, resource_types):
    if export_type == "group":
        path = "/fhir/R4/Group/example-group/$export"
        response = _get(
            factory,
            path,
            action="export_group",
            query={"_type": ",".join(resource_types)},
            pk="example-group",
        )
    else:
        path = "/fhir/R4/$export"
        response = _get(
            factory,
            path,
            action="export_system",
            query={"_type": ",".join(resource_types)},
        )
    assert response.status_code == 202, response.data
    return response["Content-Location"].rsplit("/", 1)[-1]


def _download(factory, *, job_id, resource_type):
    file_name = f"{resource_type.lower()}.ndjson"
    return _get(
        factory,
        f"/fhir/R4/bulk-download/{job_id}/{file_name}",
        action="download_file",
        job_id=job_id,
        file_name=file_name,
    )


def _ndjson_resources(response):
    assert response.status_code == 200, response.content
    content = response.content.decode("utf-8")
    return [json.loads(line) for line in content.splitlines() if line]


@pytest.mark.django_db
@override_settings(ALLOWED_HOSTS=["testserver"])
def test_group_members_and_ndjson_are_projected_from_the_persisted_bulk_cohort():
    bulk_patient = _patient(
        first_name="PersistedBulk",
        mrn="BULK-HOSPITAL-001",
        fhir_id="persisted-bulk-patient",
    )
    other_patient = _patient(
        first_name="NotInGroup",
        mrn="REGULAR-HOSPITAL-001",
        fhir_id="regular-patient",
    )
    prefix_collision_patient = _patient(
        first_name="PrefixCollision",
        mrn="BULK-NOT-A-MEMBER",
        fhir_id="bulk-prefix-collision",
    )
    _persist_group([bulk_patient])
    HealthScreening.objects.create(patient=bulk_patient, screening_date=date(2026, 7, 18))
    bulk_problem = Problem.objects.create(
        patient=bulk_patient,
        problem_name="Hospital-reviewed asthma",
        date_of_onset=date(2020, 6, 1),
    )
    Problem.objects.create(patient=other_patient, problem_name="Must not leak")

    factory = APIRequestFactory()
    group_response = _get(
        factory,
        "/fhir/R4/Group/example-group",
        action="retrieve",
        pk="example-group",
    )
    assert group_response.status_code == 200
    group_resource = json.loads(group_response.content)
    assert group_resource["member"] == [
        {"entity": {"reference": "Patient/persisted-bulk-patient"}}
    ]
    assert identity.patient_id(prefix_collision_patient) not in json.dumps(group_resource)

    job_id = _kickoff(
        factory,
        export_type="group",
        resource_types=["Patient", "Condition"],
    )
    patient_resources = _ndjson_resources(
        _download(factory, job_id=job_id, resource_type="Patient")
    )
    condition_resources = _ndjson_resources(
        _download(factory, job_id=job_id, resource_type="Condition")
    )

    assert [resource["id"] for resource in patient_resources] == [
        identity.patient_id(bulk_patient)
    ]
    assert patient_resources[0]["identifier"][0]["value"] == "BULK-HOSPITAL-001"
    assert [resource["id"] for resource in condition_resources] == [
        identity.condition_id(bulk_problem)
    ]
    assert condition_resources[0]["subject"]["reference"] == (
        "Patient/persisted-bulk-patient"
    )
    assert condition_resources[0]["code"]["text"] == "Hospital-reviewed asthma"

    serialized = json.dumps(patient_resources + condition_resources)
    for synthetic_marker in (
        "bulk-organization-1",
        "b-obs-",
        "Anytown",
        "Must not leak",
    ):
        assert synthetic_marker not in serialized


@pytest.mark.django_db
@override_settings(ALLOWED_HOSTS=["testserver"])
def test_empty_bulk_cohort_exports_an_empty_file_without_fallback_patients():
    _patient(
        first_name="Ordinary",
        mrn="REGULAR-ONLY-001",
        fhir_id="ordinary-patient",
    )
    _persist_group([])
    factory = APIRequestFactory()

    group_response = _get(
        factory,
        "/fhir/R4/Group/example-group",
        action="retrieve",
        pk="example-group",
    )
    group_resource = json.loads(group_response.content)
    assert group_resource["quantity"] == 0
    assert group_resource["member"] == []

    job_id = _kickoff(factory, export_type="group", resource_types=["Patient"])
    response = _download(factory, job_id=job_id, resource_type="Patient")
    assert response.status_code == 200
    assert response.content == b""


@pytest.mark.django_db
@override_settings(ALLOWED_HOSTS=["testserver"])
def test_system_export_includes_all_and_only_active_persisted_patients():
    first = _patient(
        first_name="SystemOne",
        mrn="SYSTEM-001",
        fhir_id="system-patient-one",
    )
    second = _patient(
        first_name="SystemTwo",
        mrn="BULK-SYSTEM-002",
        fhir_id="system-patient-two",
    )
    _patient(
        first_name="Inactive",
        mrn="SYSTEM-INACTIVE",
        fhir_id="inactive-system-patient",
        active=False,
    )
    factory = APIRequestFactory()

    job_id = _kickoff(factory, export_type="system", resource_types=["Patient"])
    resources = _ndjson_resources(
        _download(factory, job_id=job_id, resource_type="Patient")
    )

    assert {resource["id"] for resource in resources} == {
        identity.patient_id(first),
        identity.patient_id(second),
    }


@pytest.mark.django_db
@override_settings(ALLOWED_HOSTS=["testserver"])
def test_projector_failure_returns_operation_outcome_without_partial_ndjson():
    patient = _patient(
        first_name="ProjectionFailure",
        mrn="BULK-FAIL-001",
        fhir_id="bulk-failure-patient",
    )
    _persist_group([patient])
    Problem.objects.create(patient=patient, problem_name="Persisted condition")
    factory = APIRequestFactory()
    job_id = _kickoff(factory, export_type="group", resource_types=["Condition"])
    projector = ProjectorRegistry.get("Condition")

    with mock.patch.object(
        projector,
        "project_batch",
        side_effect=RuntimeError("projection failed"),
    ):
        response = _download(factory, job_id=job_id, resource_type="Condition")

    assert response.status_code == 500
    payload = json.loads(response.content)
    assert payload["resourceType"] == "OperationOutcome"
    assert payload["issue"][0]["code"] == "exception"
    assert b"Persisted condition" not in response.content


@pytest.mark.django_db
@override_settings(ALLOWED_HOSTS=["testserver"])
@pytest.mark.parametrize("scope", ["patient/*.read", "user/*.read", "patient/Group.read"])
def test_bulk_export_rejects_patient_and_user_scopes(scope):
    factory = APIRequestFactory()
    token = SimpleNamespace(scope=scope, application_id="wrong-scope-client", user_id=None)

    response = _get(
        factory,
        "/fhir/R4/$export",
        action="export_system",
        query={"_type": "Patient"},
        token=token,
    )

    assert response.status_code == 403


@pytest.mark.django_db
@override_settings(ALLOWED_HOSTS=["testserver"])
def test_bulk_export_requires_system_scope_for_every_requested_resource_type():
    factory = APIRequestFactory()
    patient_only = SimpleNamespace(
        scope="system/Patient.read",
        application_id="patient-only-client",
        user_id=None,
    )

    response = _get(
        factory,
        "/fhir/R4/$export",
        action="export_system",
        query={"_type": "Patient,Observation"},
        token=patient_only,
    )

    assert response.status_code == 403
    assert b"Observation" in response.content


@pytest.mark.django_db
@override_settings(ALLOWED_HOSTS=["testserver"])
def test_bulk_job_status_download_and_cancel_are_bound_to_the_creating_oauth_client():
    _patient(
        first_name="OwnerBound",
        mrn="SYSTEM-OWNER-001",
        fhir_id="system-owner-patient",
    )
    factory = APIRequestFactory()
    job_id = _kickoff(factory, export_type="system", resource_types=["Patient"])
    other_client = SimpleNamespace(
        scope="system/*.read",
        application_id="different-bulk-client",
        user_id=None,
    )

    status_response = _get(
        factory,
        f"/fhir/R4/bulk-status/{job_id}",
        action="job_status",
        token=other_client,
        job_id=job_id,
    )
    download_response = _get(
        factory,
        f"/fhir/R4/bulk-download/{job_id}/patient.ndjson",
        action="download_file",
        token=other_client,
        job_id=job_id,
        file_name="patient.ndjson",
    )
    cancel_request = factory.delete(
        f"/fhir/R4/bulk-status/{job_id}",
        HTTP_HOST="testserver",
    )
    force_authenticate(cancel_request, token=other_client)
    cancel_response = BulkExportViewSet.as_view({"delete": "cancel_job"})(
        cancel_request,
        job_id=job_id,
    )

    assert status_response.status_code == 403
    assert download_response.status_code == 403
    assert cancel_response.status_code == 403

    owner_status = _get(
        factory,
        f"/fhir/R4/bulk-status/{job_id}",
        action="job_status",
        job_id=job_id,
    )
    assert owner_status.status_code == 200
