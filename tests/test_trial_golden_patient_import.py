"""Verify the delivered file through public import and risk APIs in the test DB."""
import hashlib
import json
import os
from collections import Counter
from pathlib import Path

import pytest
from django.contrib.auth.models import Permission, User
from django.test import override_settings
from fhirclient.models.bundle import Bundle
from rest_framework.test import APIClient
from apps.clinical.health_screening.golden_patient import GOLDEN_REQUIRED_SNAPSHOT_FIELDS
from apps.clinical.patients.models import Patient

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts/golden_patient/golden_patient.fhir.json"

@pytest.mark.parametrize("input_format", ["json", "xml"])
@pytest.mark.django_db
@override_settings(FHIR_DEFAULT_ORIGIN_NAMESPACE="allcare365:local-ui-import:v1")
def test_delivered_trial_bundle_import_and_all_runtime_models(input_format):
    raw = ARTIFACT.read_bytes()
    bundle = json.loads(raw)
    Bundle(bundle, strict=True)
    full_urls = [entry["fullUrl"] for entry in bundle["entry"]]
    assert len(full_urls) == len(set(full_urls))
    user = User.objects.create_user(username="synthetic-trial-verifier")
    for app, code in [("health_screening", "import_clinical_records"), ("patients", "run_all_patient_risk_assessments")]:
        user.user_permissions.add(Permission.objects.get(content_type__app_label=app, codename=code))
    client = APIClient()
    client.force_authenticate(user=User.objects.get(pk=user.pk))
    payload = bundle if input_format == "json" else ARTIFACT.with_suffix(".xml").read_text(encoding="utf-8")
    imported = client.post("/api/health-screening/fhir-import/", {"fhir_data": payload, "format": input_format}, format="json")
    assert imported.status_code == 201, imported.data
    assert imported.data["error_count"] == 0
    assert imported.data["created_patients"] == 1
    patient = Patient.objects.get(medical_record_number="SYNTHETIC-GOLDEN-20261010-001")
    response = client.post("/api/health-screening/risk-analysis/", {"patient_id": str(patient.id)}, format="json")
    assert response.status_code == 200, response.data
    result = response.data
    snapshot = result["data_summary"]["data"]
    missing = sorted(field for field in GOLDEN_REQUIRED_SNAPSHOT_FIELDS if snapshot.get(field) is None)
    assert not missing, missing
    assert not result["data_summary"]["missing_data"]
    summary = result["execution_summary"]
    assert summary["executable_models"] == 82
    assert summary["insufficient_data_models"] == 0
    assert summary["all_executable_models_resolved"] is True
    assert snapshot["former_smoker"] is True
    assert snapshot["ever_smoker"] is True
    assert snapshot["is_smoker"] is False
    assert snapshot["ast_uln"] == 40
    # The export contains only synthetic input, never precomputed risk outputs.
    assert set(entry["resource"]["resourceType"] for entry in bundle["entry"]) == {"Patient", "Encounter", "Observation", "Condition", "QuestionnaireResponse"}
    report = {
        "scope": "Synthetic fixture; isolated security-test database; public import and risk APIs. No development database writes or browser acceptance test.",
        "bundle_sha256": hashlib.sha256(raw).hexdigest(),
        "source_sha256": {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in ("apps/clinical/health_screening/golden_patient.py", "services/disease_risk_engine/repository.py", "services/disease_risk_engine/runtime_calculators.py", "services/disease_risk_engine/algorithm_registry.py", "artifacts/golden_patient/build_bundle.py")},
        "evaluation_date": result["data_summary"]["sources"]["_snapshot"]["evaluation_date"],
        "algorithm_catalog_version": result["algorithm_catalog_version"],
        "model_version": result["model_version"],
        "resource_counts": dict(Counter(entry["resource"]["resourceType"] for entry in bundle["entry"])),
        "required_snapshot_fields": sorted(GOLDEN_REQUIRED_SNAPSHOT_FIELDS),
        "required_snapshot_field_count": len(GOLDEN_REQUIRED_SNAPSHOT_FIELDS),
        "missing_required_snapshot_fields": missing,
        "execution_summary": summary,
        "not_applicable": [{key: item.get(key) for key in ("algorithm", "applicability", "applicability_reason", "recommendation_text")} for item in result["disease_risk_results"] if item["applicability"] != "applicable"],
        "input_snapshot": snapshot,
        "results": [{key: item.get(key) for key in ("algorithm", "model_version", "risk_score", "risk_percentage", "risk_category", "applicability", "missing_data")} for item in result["disease_risk_results"]],
    }
    if os.environ.get("EXPORT_TRIAL_GOLDEN_REPORT") == "1" and input_format == "json":
        ARTIFACT.with_name("verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
