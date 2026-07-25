import os
import sys

import pytest


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medical_system.settings")

import django


django.setup()

from django.contrib.auth.models import Permission, User
from rest_framework.test import APIClient
from fhir.resources.provenance import Provenance as FHIRProvenance
from fhir.resources.riskassessment import RiskAssessment as FHIRRiskAssessment

from apps.clinical.health_screening.ingestion_service import HealthScreeningIngestionService
from apps.clinical.health_screening.models import (
    AIAnalysisResult,
    Encounter,
    HealthScreening,
    Observation,
    QuestionnaireResponse,
)
from apps.clinical.patients.models import Patient
from apps.integration.fhir_integration.models import FHIRResource
from services.disease_risk_engine.algorithm_registry import FHIRResultType, RUNTIME_ALGORITHMS


RUNTIME_MODEL_COUNT = len(RUNTIME_ALGORITHMS)
RISK_ASSESSMENT_MODEL_COUNT = sum(
    item.output_resource == FHIRResultType.RISK_ASSESSMENT for item in RUNTIME_ALGORITHMS
)


TEST_SOURCE_NAMESPACE = "test:hospital:fhir-risk"


def _grant_global_patient_risk_access(user):
    permission = Permission.objects.get(
        content_type__app_label="patients",
        codename="run_all_patient_risk_assessments",
    )
    user.user_permissions.add(permission)
    return User.objects.get(pk=user.pk)


def _patient_resource(patient_id="patient-1", mrn="FHIR-RISK-001"):
    return {
        "resourceType": "Patient",
        "id": patient_id,
        "identifier": [{"system": "https://hospital.example/mrn", "value": mrn}],
        "active": True,
        "name": [{"family": "陳", "given": ["測試"]}],
        "gender": "male",
        "birthDate": "1975-05-20",
    }


def _observation(resource_id, patient_reference, encounter_reference, code, display, value, unit):
    return {
        "resourceType": "Observation",
        "id": resource_id,
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                    }
                ]
            }
        ],
        "code": {"coding": [{"system": "http://loinc.org", "code": code, "display": display}]},
        "subject": {"reference": patient_reference},
        "encounter": {"reference": encounter_reference},
        "effectiveDateTime": "2026-07-12T09:30:00+08:00",
        "valueQuantity": {
            "value": value,
            "unit": unit,
            "system": "http://unitsofmeasure.org",
        },
    }


@pytest.mark.django_db
def test_fhir_bundle_full_url_import_groups_observations_and_allows_patient_risk_analysis():
    patient_full_url = "urn:uuid:11111111-1111-4111-8111-111111111111"
    encounter_full_url = "urn:uuid:22222222-2222-4222-8222-222222222222"
    bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {"fullUrl": patient_full_url, "resource": _patient_resource()},
            {
                "fullUrl": encounter_full_url,
                "resource": {
                    "resourceType": "Encounter",
                    "id": "encounter-1",
                    "status": "finished",
                    "class": {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                        "code": "AMB",
                        "display": "ambulatory",
                    },
                    "subject": {"reference": patient_full_url},
                    "period": {
                        "start": "2026-07-12T09:00:00+08:00",
                        "end": "2026-07-12T10:00:00+08:00",
                    },
                },
            },
            {
                "resource": _observation(
                    "height-1",
                    patient_full_url,
                    encounter_full_url,
                    "8302-2",
                    "Body height",
                    170,
                    "cm",
                )
            },
            {
                "resource": _observation(
                    "weight-1",
                    patient_full_url,
                    encounter_full_url,
                    "29463-7",
                    "Body weight",
                    80,
                    "kg",
                )
            },
        ],
    }

    result = HealthScreeningIngestionService().import_fhir(
        bundle,
        source_namespace=TEST_SOURCE_NAMESPACE,
    )

    assert result["error_count"] == 0
    assert result["created_patients"] == 1
    assert result["created_screenings"] == 1
    assert result["created_observations"] == 2
    assert len(result["patient_ids"]) == 1
    assert result["primary_patient_id"] == result["patient_ids"][0]

    patient = Patient.objects.get(medical_record_number="FHIR-RISK-001")
    assert HealthScreening.objects.filter(patient=patient).count() == 1
    assert Encounter.objects.filter(patient=patient, source_type="fhir_import").count() == 1
    assert Observation.objects.filter(patient=patient, source_type="fhir_import").count() == 2

    user = _grant_global_patient_risk_access(
        User.objects.create_user(username="fhir-risk-clinician", password="password")
    )
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        "/api/health-screening/risk-analysis/",
        {"patient_id": str(patient.id)},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["data_summary"]["data"]["body_height"] == 170.0
    assert response.data["data_summary"]["data"]["body_weight"] == 80.0
    assert response.data["data_summary"]["data"]["bmi"] == 27.68
    assert len(response.data["disease_risk_results"]) == RUNTIME_MODEL_COUNT


@pytest.mark.django_db
def test_patient_level_risk_analysis_does_not_require_a_health_screening():
    result = HealthScreeningIngestionService().import_fhir(
        _patient_resource(
            patient_id="demographics-only",
            mrn="FHIR-RISK-DEMOGRAPHICS",
        ),
        source_namespace=TEST_SOURCE_NAMESPACE,
    )
    patient = Patient.objects.get(medical_record_number="FHIR-RISK-DEMOGRAPHICS")
    assert result["primary_patient_id"] == str(patient.id)
    assert not HealthScreening.objects.filter(patient=patient).exists()

    user = _grant_global_patient_risk_access(
        User.objects.create_user(username="demographics-risk-clinician", password="password")
    )
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        "/api/health-screening/risk-analysis/",
        {"patient_id": str(patient.id)},
        format="json",
    )

    assert response.status_code == 200
    assert len(response.data["disease_risk_results"]) == RUNTIME_MODEL_COUNT
    assert response.data["data_summary"]["missing_data"]
    assert all(result["clinical_system"] for result in response.data["disease_risk_results"])
    gated = [
        result
        for result in response.data["disease_risk_results"]
        if result["governance_status"] == "clinical_review_required"
    ]
    assert gated == []

    persisted_results = AIAnalysisResult.objects.filter(patient=patient)
    assert persisted_results.count() == RUNTIME_MODEL_COUNT
    assert all(result.confidence_score is None for result in persisted_results)

    risk_assessments = FHIRResource.objects.filter(resource_type="RiskAssessment")
    assert risk_assessments.count() == RISK_ASSESSMENT_MODEL_COUNT
    assert all(resource.resource_data["status"] == "final" for resource in risk_assessments)


@pytest.mark.django_db
def test_fhir_bundle_real_inputs_produce_all_three_prevent_outputs_without_substitution():
    patient_full_url = "urn:uuid:33333333-3333-4333-8333-333333333333"
    encounter_full_url = "urn:uuid:44444444-4444-4444-8444-444444444444"
    observations = [
        ("sbp", "8480-6", "Systolic blood pressure", 160, "mmHg"),
        ("bmi", "39156-5", "Body mass index", 35, "kg/m2"),
        ("tc", "2093-3", "Total cholesterol", 200, "mg/dL"),
        ("hdl", "2085-9", "HDL cholesterol", 45, "mg/dL"),
        ("creatinine", "2160-0", "Creatinine", 1.0, "mg/dL"),
    ]
    bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {
                "fullUrl": patient_full_url,
                "resource": _patient_resource(patient_id="prevent-patient", mrn="FHIR-PREVENT-001"),
            },
            {
                "fullUrl": encounter_full_url,
                "resource": {
                    "resourceType": "Encounter",
                    "id": "prevent-encounter",
                    "status": "finished",
                    "class": {"code": "AMB"},
                    "subject": {"reference": patient_full_url},
                    "period": {"start": "2026-07-12T09:00:00+08:00"},
                },
            },
            *[
                {
                    "resource": _observation(
                        resource_id,
                        patient_full_url,
                        encounter_full_url,
                        code,
                        display,
                        value,
                        unit,
                    )
                }
                for resource_id, code, display, value, unit in observations
            ],
            {
                "resource": {
                    "resourceType": "QuestionnaireResponse",
                    "id": "prevent-required-flags",
                    "status": "completed",
                    "subject": {"reference": patient_full_url},
                    "authored": "2026-07-12T09:30:00+08:00",
                    "questionnaire": "Questionnaire/prevent-intake",
                    "item": [
                        {"linkId": "anti_hypertensive_drugs", "answer": [{"valueBoolean": True}]},
                            {"linkId": "statin_use", "answer": [{"valueBoolean": False}]},
                            {"linkId": "has_diabetes", "answer": [{"valueBoolean": True}]},
                            {"linkId": "is_smoker", "answer": [{"valueBoolean": False}]},
                            {"linkId": "chd_history", "answer": [{"valueBoolean": False}]},
                            {"linkId": "cvd_history", "answer": [{"valueBoolean": False}]},
                                {"linkId": "pvd_history", "answer": [{"valueBoolean": False}]},
                                {"linkId": "ascvd_history", "answer": [{"valueBoolean": False}]},
                                {"linkId": "stroke_tia_history", "answer": [{"valueBoolean": False}]},
                                {"linkId": "heart_failure_history", "answer": [{"valueBoolean": False}]},
                    ],
                }
            },
        ],
    }

    imported = HealthScreeningIngestionService().import_fhir(
        bundle,
        source_namespace=TEST_SOURCE_NAMESPACE,
    )
    patient = Patient.objects.get(medical_record_number="FHIR-PREVENT-001")

    assert imported["error_count"] == 0
    assert imported["created_questionnaire_responses"] == 1
    assert QuestionnaireResponse.objects.filter(patient=patient, source_type="fhir_import").exists()

    user = _grant_global_patient_risk_access(
        User.objects.create_user(username="prevent-clinician", password="password")
    )
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        "/api/health-screening/risk-analysis/",
        {"patient_id": str(patient.id)},
        format="json",
    )

    assert response.status_code == 200
    prevent_results = [
        result
        for result in response.data["disease_risk_results"]
        if result["algorithm"].startswith("aha_prevent_")
    ]
    assert len(prevent_results) == 3
    assert all(result["risk_score"] is not None for result in prevent_results)
    assert all(result["risk_percentage"].endswith("%") for result in prevent_results)
    assert response.data["data_summary"]["data"]["egfr"] > 0
    assert response.data["data_summary"]["sources"]["egfr"]["formula"] == "CKD-EPI-creatinine-2021"
    assert FHIRResource.objects.filter(resource_type="RiskAssessment").count() >= 3
    assert FHIRResource.objects.filter(resource_type="Provenance").count() >= 3
    for resource in FHIRResource.objects.filter(resource_type="RiskAssessment"):
        FHIRRiskAssessment(**resource.resource_data)
    for resource in FHIRResource.objects.filter(resource_type="Provenance"):
        FHIRProvenance(**resource.resource_data)
