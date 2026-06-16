import pytest
import os
import sys


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medical_system.settings")

import django


django.setup()

from django.contrib.auth.models import User
from rest_framework.test import APIClient

from apps.core.authentication.models import ProductUser
from apps.clinical.health_screening.cohort_service import CohortSummaryService
from apps.clinical.health_screening.data_quality_service import DataQualitySummaryService
from apps.clinical.health_screening.ingestion_service import HealthScreeningIngestionService
from apps.clinical.health_screening.management.commands.import_h2u_cvd import Command
from apps.clinical.health_screening.models import HealthScreening, Observation, QuestionnaireResponse
from apps.clinical.health_screening.patients_like_this_service import PatientsLikeThisService
from apps.clinical.patients.models import Patient


def _h2u_row(patient_id="2", source="H002", check_date="2020/3/3", sex="F"):
    return {
        "ID": patient_id,
        "Source": source,
        "BirthDate": "1968/7/5",
        "CheckDate": check_date,
        "SEX": sex,
        "Height": "169.3",
        "Weight": "69.8",
        "Waist": "85.5",
        "PulseRate": "85",
        "FPG": "82",
        "HbA1C": "5.2",
        "WBC": "3.77",
        "SBP": "136",
        "DBP": "84",
        "TG": "65",
        "TC": "194",
        "HDL": "65",
        "LDL": "134",
        "Creatinine": "0.6",
        "HQ_BP_Treat": "FALSE",
        "HQ_SMOKE": "FALSE",
        "HQ_Diabetes": "FALSE",
        "HQ_Diabetes_Treat": "FALSE",
        "HQ_CHD": "FALSE",
        "HQ_arrhythmia": "FALSE",
        "HQ_low_fat_Treat": "FALSE",
        "HQ_Exercise": "",
        "Neck": "",
        "Hip": "",
    }


def _product_user(username="researcher", role="researcher"):
    user = User.objects.create_user(username=username, password="password")
    ProductUser.objects.create(
        auth_user=user,
        display_name=username,
        role=role,
        status="active",
    )
    return user


@pytest.mark.django_db
def test_h2u_dry_run_does_not_create_clinical_source_records():
    result = HealthScreeningIngestionService().bulk_import_rows(
        [_h2u_row()],
        source_type="h2u_cvd_csv",
        original_filename="H2U_cvd_input_update.csv",
        dry_run=True,
        row_transform=Command()._normalize_h2u_row,
    )

    assert result["validated_count"] == 1
    assert Patient.objects.filter(medical_record_number__startswith="H2U-").count() == 0
    assert HealthScreening.objects.count() == 0


@pytest.mark.django_db
def test_h2u_import_is_idempotent_by_encounter_identifier():
    service = HealthScreeningIngestionService()
    transform = Command()._normalize_h2u_row

    first = service.bulk_import_rows(
        [_h2u_row()],
        source_type="h2u_cvd_csv",
        original_filename="H2U_cvd_input_update.csv",
        skip_existing=True,
        row_transform=transform,
    )
    second = service.bulk_import_rows(
        [_h2u_row()],
        source_type="h2u_cvd_csv",
        original_filename="H2U_cvd_input_update.csv",
        skip_existing=True,
        row_transform=transform,
    )

    assert first["success_count"] == 1
    assert second["skipped_count"] == 1
    assert Patient.objects.filter(medical_record_number="H2U-H002-2").count() == 1
    assert HealthScreening.objects.filter(encounter_identifier="H2U-CVD-H002-2-202033").count() == 1
    assert Observation.objects.filter(source_type__startswith="h2u_cvd_csv").exists()
    assert QuestionnaireResponse.objects.filter(source_type="h2u_cvd_csv").count() == 1


@pytest.mark.django_db
def test_cohort_summary_api_requires_authentication():
    client = APIClient()
    response = client.get("/api/health-screening/cohorts/summary/")
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_cohort_summary_api_rejects_patient_role():
    user = _product_user(username="patient_user", role="patient")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/health-screening/cohorts/summary/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_cohort_summary_suppresses_small_cohorts():
    HealthScreeningIngestionService().bulk_import_rows(
        [_h2u_row()],
        source_type="h2u_cvd_csv",
        original_filename="H2U_cvd_input_update.csv",
        skip_existing=True,
        row_transform=Command()._normalize_h2u_row,
    )

    user = _product_user(username="researcher", role="researcher")
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/health-screening/cohorts/summary/", {"sex": "F"})

    assert response.status_code == 200
    assert response.data["privacy"]["suppressed"] is True
    assert response.data["privacy"]["line_level_data_returned"] is False
    assert response.data["cohort_count"] is None
    assert response.data["summary"] == {}


@pytest.mark.django_db
def test_cohort_summary_returns_aggregate_only_when_threshold_met():
    rows = [_h2u_row(patient_id=str(1000 + index), source="H010") for index in range(12)]
    HealthScreeningIngestionService().bulk_import_rows(
        rows,
        source_type="h2u_cvd_csv",
        original_filename="H2U_cvd_input_update.csv",
        skip_existing=True,
        row_transform=Command()._normalize_h2u_row,
    )

    summary = CohortSummaryService().summarize({"sex": "F", "sbp_min": "130"}, minimum_cell_count=10)

    assert summary["privacy"]["suppressed"] is False
    assert summary["privacy"]["line_level_data_returned"] is False
    assert summary["cohort_count"] == 12
    assert summary["summary"]["features"]["sbp"]["count"] == 12
    assert summary["summary"]["features"]["sbp"]["mean"] == 136.0
    assert "screening_ids" not in summary


@pytest.mark.django_db
def test_cohort_summary_fhir_returns_measure_report_without_members():
    rows = [_h2u_row(patient_id=str(4000 + index), source="H040") for index in range(12)]
    HealthScreeningIngestionService().bulk_import_rows(
        rows,
        source_type="h2u_cvd_csv",
        original_filename="H2U_cvd_input_update.csv",
        skip_existing=True,
        row_transform=Command()._normalize_h2u_row,
    )

    user = _product_user(username="fhir_researcher", role="researcher")
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/health-screening/cohorts/summary/fhir/", {"sex": "F", "sbp_min": "130"})

    assert response.status_code == 200
    assert response["Content-Type"] == "application/fhir+json"
    report = response.json()
    serialized = str(report)
    assert report["resourceType"] == "MeasureReport"
    assert report["type"] == "summary"
    assert report["group"][0]["population"][0]["count"] == 12
    assert "Patient/" not in serialized
    assert "member" not in serialized


@pytest.mark.django_db
def test_cohort_summary_fhir_rejects_patient_role():
    user = _product_user(username="fhir_patient", role="patient")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/health-screening/cohorts/summary/fhir/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_data_quality_summary_reports_h2u_feature_coverage():
    rows = [_h2u_row(patient_id=str(2000 + index), source="H020") for index in range(3)]
    HealthScreeningIngestionService().bulk_import_rows(
        rows,
        source_type="h2u_cvd_csv",
        original_filename="H2U_cvd_input_update.csv",
        skip_existing=True,
        row_transform=Command()._normalize_h2u_row,
    )

    summary = DataQualitySummaryService().summarize(dataset="h2u_cvd_csv")

    assert summary["record_counts"]["screenings"] == 3
    assert summary["record_counts"]["patients"] == 3
    assert summary["feature_coverage"]["sbp"]["present"] == 3
    assert summary["feature_coverage"]["hba1c"]["coverage"] == 1.0
    assert summary["duplicates"]["duplicate_encounter_identifiers"] == 0
    assert summary["readiness"]["label"] in {"research_ready", "usable_with_caveats"}


@pytest.mark.django_db
def test_data_quality_summary_api_requires_authentication():
    client = APIClient()
    response = client.get("/api/health-screening/data-quality/summary/")
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_patients_like_this_api_requires_authentication():
    client = APIClient()
    response = client.get("/api/health-screening/cohorts/patients-like-this/", {"age": "52", "sex": "F", "sbp": "136"})
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_patients_like_this_suppresses_small_matches():
    HealthScreeningIngestionService().bulk_import_rows(
        [_h2u_row()],
        source_type="h2u_cvd_csv",
        original_filename="H2U_cvd_input_update.csv",
        skip_existing=True,
        row_transform=Command()._normalize_h2u_row,
    )

    result = PatientsLikeThisService().find(
        {"age": "52", "sex": "F", "sbp": "136", "hba1c": "5.2"},
        minimum_cell_count=10,
    )

    assert result["privacy"]["suppressed"] is True
    assert result["privacy"]["line_level_data_returned"] is False
    assert result["matched_count"] is None
    assert result["summary"] == {}


@pytest.mark.django_db
def test_patients_like_this_returns_aggregate_only_when_threshold_met():
    rows = [_h2u_row(patient_id=str(3000 + index), source="H030") for index in range(12)]
    HealthScreeningIngestionService().bulk_import_rows(
        rows,
        source_type="h2u_cvd_csv",
        original_filename="H2U_cvd_input_update.csv",
        skip_existing=True,
        row_transform=Command()._normalize_h2u_row,
    )

    result = PatientsLikeThisService().find(
        {"age": "51", "sex": "F", "sbp": "136", "hba1c": "5.2", "ldl": "134"},
        minimum_cell_count=10,
    )

    assert result["privacy"]["suppressed"] is False
    assert result["privacy"]["line_level_data_returned"] is False
    assert result["matched_count"] == 12
    assert result["average_similarity"] is not None
    assert result["summary"]["features"]["sbp"]["count"] == 12
    assert result["summary"]["features"]["sbp"]["mean"] == 136.0
    assert "screening_ids" not in result
    assert "patient_ids" not in result


@pytest.mark.django_db
def test_patients_like_this_uses_trend_features_when_available():
    rows = []
    for index in range(12):
        baseline = _h2u_row(patient_id=str(5000 + index), source="H050", check_date="2020/1/1")
        baseline.update({"SBP": "150", "HbA1C": "6.4", "LDL": "160"})
        follow_up = _h2u_row(patient_id=str(5000 + index), source="H050", check_date="2020/7/1")
        follow_up.update({"SBP": "136", "HbA1C": "5.8", "LDL": "132"})
        rows.extend([baseline, follow_up])

    HealthScreeningIngestionService().bulk_import_rows(
        rows,
        source_type="h2u_cvd_csv",
        original_filename="H2U_cvd_input_update.csv",
        skip_existing=True,
        row_transform=Command()._normalize_h2u_row,
    )

    result = PatientsLikeThisService().find(
        {
            "age": "52",
            "sex": "F",
            "sbp": "136",
            "hba1c": "5.8",
            "ldl": "132",
            "sbp_delta": "-14",
            "hba1c_delta": "-0.6",
            "ldl_delta": "-28",
            "limit": "12",
        },
        minimum_cell_count=10,
    )

    assert result["privacy"]["suppressed"] is False
    assert result["matched_count"] == 12
    assert result["matching_model"]["version"] == "v2"
    assert result["reference_profile"]["trends"]["sbp_delta"] == -14.0
    assert result["summary"]["trends"]["sbp_delta"]["count"] == 12
    assert result["summary"]["trends"]["sbp_delta"]["mean"] == -14.0
    assert result["summary"]["trends"]["hba1c_delta"]["mean"] == -0.6
    assert "screening_ids" not in result
    assert "patient_ids" not in result


@pytest.mark.django_db
def test_research_report_requires_approval_before_artifact_release():
    rows = [_h2u_row(patient_id=str(6000 + index), source="H060") for index in range(12)]
    HealthScreeningIngestionService().bulk_import_rows(
        rows,
        source_type="h2u_cvd_csv",
        original_filename="H2U_cvd_input_update.csv",
        skip_existing=True,
        row_transform=Command()._normalize_h2u_row,
    )

    researcher = _product_user(username="report_researcher", role="researcher")
    approver = _product_user(username="report_admin", role="admin")
    client = APIClient()
    client.force_authenticate(user=researcher)

    create_response = client.post(
        "/api/health-screening/research-reports/",
        {
            "title": "Female elevated SBP aggregate",
            "report_type": "cohort_summary",
            "query_params": {"sex": "F", "sbp_min": "130"},
        },
        format="json",
    )

    assert create_response.status_code == 201
    report_id = create_response.data["id"]
    assert create_response.data["status"] == "requested"
    assert create_response.data["artifact_available"] is False
    assert create_response.data["privacy_json"]["line_level_data_returned"] is False

    locked_response = client.get(f"/api/health-screening/research-reports/{report_id}/artifact/")
    assert locked_response.status_code == 403

    researcher_approval = client.post(f"/api/health-screening/research-reports/{report_id}/approve/", {}, format="json")
    assert researcher_approval.status_code == 403

    client.force_authenticate(user=approver)
    approve_response = client.post(
        f"/api/health-screening/research-reports/{report_id}/approve/",
        {"approval_note": "Aggregate output approved"},
        format="json",
    )
    assert approve_response.status_code == 200
    assert approve_response.data["status"] == "approved"
    assert approve_response.data["artifact_available"] is True

    artifact_response = client.get(f"/api/health-screening/research-reports/{report_id}/artifact/")
    assert artifact_response.status_code == 200
    serialized = str(artifact_response.data)
    assert artifact_response.data["cohort_count"] == 12
    assert "Patient/" not in serialized
    assert "member" not in serialized
    assert "screening_ids" not in serialized


@pytest.mark.django_db
def test_research_report_can_release_approved_fhir_measure_report():
    rows = [_h2u_row(patient_id=str(7000 + index), source="H070") for index in range(12)]
    HealthScreeningIngestionService().bulk_import_rows(
        rows,
        source_type="h2u_cvd_csv",
        original_filename="H2U_cvd_input_update.csv",
        skip_existing=True,
        row_transform=Command()._normalize_h2u_row,
    )

    researcher = _product_user(username="fhir_report_researcher", role="researcher")
    approver = _product_user(username="fhir_report_admin", role="admin")
    client = APIClient()
    client.force_authenticate(user=researcher)
    create_response = client.post(
        "/api/health-screening/research-reports/",
        {
            "title": "FHIR aggregate report",
            "report_type": "cohort_measure_report",
            "query_params": {"sex": "F", "sbp_min": "130"},
        },
        format="json",
    )
    assert create_response.status_code == 201
    report_id = create_response.data["id"]

    client.force_authenticate(user=approver)
    assert client.post(f"/api/health-screening/research-reports/{report_id}/approve/", {}, format="json").status_code == 200

    artifact_response = client.get(f"/api/health-screening/research-reports/{report_id}/artifact/")
    assert artifact_response.status_code == 200
    assert artifact_response["Content-Type"] == "application/fhir+json"
    report = artifact_response.json()
    assert report["resourceType"] == "MeasureReport"
    assert report["group"][0]["population"][0]["count"] == 12
