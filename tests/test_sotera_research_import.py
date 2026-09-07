import io
import json
import zipfile

import pandas as pd
import pytest
from django.contrib.auth.models import User
from fhirclient.models.observation import Observation as FHIRObservation
from fhirclient.models.provenance import Provenance as FHIRProvenance
from rest_framework.test import APIClient

from apps.core.authentication.models import ProductUser
from apps.clinical.health_screening.models import (
    AIAnalysisJob,
    AIAnalysisResult,
    DataImportBatch,
    Observation,
)
from apps.clinical.health_screening.sotera_research import (
    DATASET_NAME,
    SoteraResearchSessionService,
)
from apps.clinical.health_screening.sotera_report_service import (
    SoteraResearchReportService,
)
from apps.clinical.patients.models import Patient
from apps.integration.fhir_integration.models import FHIRResourceMapping


def _parquet_bytes(frame):
    buffer = io.BytesIO()
    frame.to_parquet(buffer, index=False)
    return buffer.getvalue()


def _session_archive(tmp_path):
    archive_path = tmp_path / "source-identifiers-must-not-be-persisted.zip"
    manifest = {
        "schema_version": 2,
        "status": "processed",
        "hid": 123456,
        "session_guid": "private-source-session-guid",
        "unix_start": 1_700_000_000,
        "unix_stop": 1_700_000_010,
        "duration_sec": 10,
        "units": {"HR": "bpm", "POSTURE": "code", "ECG_II": "mV"},
    }
    numerics = pd.DataFrame(
        [
            {
                "unix_ts": 1_700_000_001,
                "signal": "HR",
                "value": 80.0,
                "label": None,
                "device_id": 901150,
                "is_event": False,
                "is_valid": True,
            },
            {
                "unix_ts": 1_700_000_002,
                "signal": "HR",
                "value": 0.0,
                "label": None,
                "device_id": 901150,
                "is_event": False,
                "is_valid": False,
            },
            {
                "unix_ts": 1_700_000_003,
                "signal": "POSTURE",
                "value": 2.0,
                "label": "upright",
                "device_id": 901150,
                "is_event": True,
                "is_valid": False,
            },
        ]
    )
    coverage = pd.DataFrame(
        [
            {
                "signal": "ECG_II",
                "n_samples": 100,
                "n_channels": 1,
                "fs_nominal": 10.0,
                "n_segments": 1,
                "covered_sec": 10.0,
                "longest_segment_sec": 10.0,
                "unix_ts_min": 1_700_000_000.0,
                "unix_ts_max": 1_700_000_010.0,
                "n_duplicate_ts": 0,
                "n_nan": 0,
                "n_inf": 0,
                "parquet_bytes": 1000,
            }
        ]
    )
    calibration = pd.DataFrame(
        [{"quality_flag": "good", "has_waveform": True}]
    )
    waveform = pd.DataFrame(
        {
            "unix_ts": [1_700_000_000.0, 1_700_000_000.1],
            "device_id": [901150, 901150],
            "value": [0.1, 0.2],
        }
    )

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        archive.writestr("numerics.parquet", _parquet_bytes(numerics))
        archive.writestr("signal_coverage.parquet", _parquet_bytes(coverage))
        archive.writestr("cal_events.parquet", _parquet_bytes(calibration))
        archive.writestr("waveforms/ECG_II.parquet", _parquet_bytes(waveform))
    return archive_path


@pytest.mark.django_db
def test_sotera_dry_run_is_aggregate_only_and_does_not_write(tmp_path):
    archive_path = _session_archive(tmp_path)

    result = SoteraResearchSessionService(archive_path).run(commit=False)

    assert result["committed"] is False
    assert result["numeric_summary"]["source_rows"] == 3
    assert result["numeric_summary"]["planned_observations"] == 2
    assert result["numeric_summary"]["excluded_rows"] == 1
    assert result["waveform_summary"]["raw_samples"] == 100
    assert result["waveform_summary"]["raw_waveforms_imported"] is False
    assert result["planned_database_observations"] == 3
    assert Patient.objects.filter(source_system=DATASET_NAME).count() == 0
    assert DataImportBatch.objects.count() == 0


@pytest.mark.django_db
def test_sotera_commit_is_pseudonymous_fhir_traceable_and_idempotent(tmp_path):
    archive_path = _session_archive(tmp_path)
    service = SoteraResearchSessionService(archive_path)

    first = service.run(commit=True)
    second = service.run(commit=True)

    assert first["committed"] is True
    assert first["idempotent"] is False
    assert first["imported_numeric_observations"] == 2
    assert first["imported_waveform_metadata_observations"] == 1
    assert second["idempotent"] is True
    assert Patient.objects.filter(source_system=DATASET_NAME).count() == 1
    assert Observation.objects.filter(
        patient_id=first["patient_id"],
        source_type__startswith="sotera_research_parquet",
    ).count() == 3
    assert DataImportBatch.objects.filter(id=first["batch_id"]).count() == 1
    assert AIAnalysisJob.objects.filter(id=first["analysis_job_id"]).count() == 1
    analysis_result = AIAnalysisResult.objects.get(id=first["analysis_result_id"])
    assert analysis_result.result_json["quality"]["scope"] == "technical_data_quality_only"
    assert analysis_result.result_json["waveform_summary"]["raw_waveforms_imported"] is False

    patient = Patient.objects.get(id=first["patient_id"])
    persisted_identity = json.dumps(
        {
            "source_record_id": patient.source_record_id,
            "medical_record_number": patient.medical_record_number,
            "metadata": patient.metadata_json,
        }
    )
    assert "123456" not in persisted_identity
    assert "private-source-session-guid" not in persisted_identity

    mappings = FHIRResourceMapping.objects.filter(
        local_table="ai_analysis_results",
        local_id=analysis_result.id,
    )
    assert mappings.count() == 2
    FHIRObservation(
        mappings.get(fhir_resource_type="Observation").fhir_json,
        strict=True,
    )
    FHIRProvenance(
        mappings.get(fhir_resource_type="Provenance").fhir_json,
        strict=True,
    )


@pytest.mark.django_db
def test_sotera_report_endpoint_is_research_only_and_separates_ao_status(tmp_path):
    archive_path = _session_archive(tmp_path)
    imported = SoteraResearchSessionService(archive_path).run(commit=True)

    anonymous_response = APIClient().get(
        "/api/health-screening/research/continuous-signals/latest/"
    )
    assert anonymous_response.status_code in (401, 403)

    user = User.objects.create_user(username="sotera-researcher", password="password")
    ProductUser.objects.create(
        auth_user=user,
        display_name="Sotera Researcher",
        role="researcher",
        status="active",
    )
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/health-screening/research/continuous-signals/latest/")

    assert response.status_code == 200
    assert response.data["available"] is True
    assert response.data["import"]["database_observations"] == 3
    assert response.data["fhir"]["quality_result_traceable"] is True
    assert response.data["ao_readiness"] == {
        "status": "not_run",
        "model_runs": 0,
        "outputs": 0,
        "ground_truth_records": 0,
        "current_conclusion": "No AO model run or AO output is present in the current system database.",
    }
    assert response.data["source"]["session_pseudonym"].startswith("session-")
    assert str(imported["patient_id"]) not in str(response.data)


@pytest.mark.django_db
def test_sotera_report_service_returns_unavailable_without_import():
    report = SoteraResearchReportService().latest()

    assert report == {
        "available": False,
        "dataset": DATASET_NAME,
        "message": "No imported Sotera research session is available.",
    }
