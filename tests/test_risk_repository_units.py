import os
import sys
from datetime import date

import pytest
from django.utils import timezone


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medical_system.settings")

import django


django.setup()

from apps.clinical.health_screening.models import (
    Encounter,
    HealthScreening,
    LaboratoryResults,
    Observation,
    Problem,
    QuestionnaireResponse,
    VitalSigns,
)
from apps.clinical.patients.models import Patient
from apps.integration.fhir_integration.models import FHIRResource, FHIRResourceMapping
from services.disease_risk_engine.formula_catalog import calculate_metabolic_syndrome
from services.disease_risk_engine.repository import DiseaseRiskInputRepository


def _patient(mrn):
    return Patient.objects.create(
        first_name="Unit",
        last_name="Boundary",
        date_of_birth=date(1970, 1, 1),
        sex="M",
        medical_record_number=mrn,
    )


def _observation(patient, field, code, value, unit, **extra):
    return Observation.objects.create(
        patient=patient,
        observation_type=field,
        category="laboratory",
        code=code,
        value_quantity=value,
        value_unit=unit,
        effective_at=timezone.now(),
        **extra,
    )


@pytest.mark.django_db
def test_repository_normalizes_explicit_compatible_observation_units():
    patient = _patient("UNIT-CONVERSION-001")
    definitions = [
        ("fasting_glucose", "1558-6", 5.5, "mmol/L"),
        ("total_cholesterol", "2093-3", 5.0, "mmol/L"),
        ("hdl_cholesterol", "2085-9", 1.2, "mmol/L"),
        ("triglycerides", "2571-8", 2.0, "mmol/L"),
        ("creatinine", "2160-0", 88.4, "umol/L"),
        ("albumin", "1751-7", 42.0, "g/L"),
        ("body_height", "8302-2", 1.7, "m"),
        ("waist_circumference", "8280-0", 0.9, "m"),
        ("hip_circumference", "56074-8", 1.0, "m"),
    ]
    for definition in definitions:
        _observation(patient, *definition)

    snapshot = DiseaseRiskInputRepository().build_snapshot(patient)

    assert snapshot.data["fasting_glucose"] == pytest.approx(99.085745)
    assert snapshot.data["total_cholesterol"] == pytest.approx(193.3488)
    assert snapshot.data["hdl_cholesterol"] == pytest.approx(46.403712)
    assert snapshot.data["triglycerides"] == pytest.approx(177.14)
    assert snapshot.data["creatinine"] == pytest.approx(1.0)
    assert snapshot.data["albumin"] == pytest.approx(4.2)
    assert snapshot.data["body_height"] == pytest.approx(170.0)
    assert snapshot.data["waist_circumference"] == pytest.approx(90.0)
    assert snapshot.data["hip_circumference"] == pytest.approx(100.0)
    assert snapshot.sources["fasting_glucose"]["original_unit"] == "mmol/L"
    assert snapshot.sources["fasting_glucose"]["normalized_unit"] == "mg/dL"
    assert snapshot.sources["fasting_glucose"]["unit_conversion"] == "glucose_mmol_per_l_to_mg_per_dl"


@pytest.mark.django_db
def test_repository_rejects_wrong_or_missing_product_observation_units_and_bp_component_units():
    patient = _patient("UNIT-REJECTION-001")
    _observation(patient, "fasting_glucose", "1558-6", 100, "kg")
    _observation(patient, "total_cholesterol", "2093-3", 200, "")
    Observation.objects.create(
        patient=patient,
        observation_type="blood_pressure",
        code="85354-9",
        component_json=[
            {"code": "8480-6", "value": 120, "unit": "kPa"},
            {"code": "8462-4", "value": 80, "unit": ""},
        ],
    )

    snapshot = DiseaseRiskInputRepository().build_snapshot(patient)

    assert "fasting_glucose" not in snapshot.data
    assert "total_cholesterol" not in snapshot.data
    assert "systolic_bp" not in snapshot.data
    assert "diastolic_bp" not in snapshot.data


@pytest.mark.django_db
def test_repository_normalizes_bp_components_only_with_compatible_units():
    patient = _patient("UNIT-BP-001")
    Observation.objects.create(
        patient=patient,
        observation_type="blood_pressure",
        code="85354-9",
        component_json=[
            {"code": "8480-6", "value": 122, "unit": "mmHg"},
            {"code": "8462-4", "value": 78, "unit": "mm[Hg]"},
        ],
    )

    snapshot = DiseaseRiskInputRepository().build_snapshot(patient)

    assert snapshot.data["systolic_bp"] == 122
    assert snapshot.data["diastolic_bp"] == 78
    assert snapshot.sources["systolic_bp"]["normalized_unit"] == "mm[Hg]"
    assert snapshot.sources["diastolic_bp"]["normalized_unit"] == "mm[Hg]"


@pytest.mark.django_db
def test_missing_fhir_quantity_unit_cannot_reenter_through_legacy_sidecar():
    patient = _patient("UNIT-FHIR-MISSING-001")
    screening = HealthScreening.objects.create(patient=patient)
    encounter = Encounter.objects.create(patient=patient, source_screening=screening)
    LaboratoryResults.objects.create(
        health_screening=screening,
        test_name="Glucose",
        value_result="100",
        result_unit="mg/dL",
    )
    _observation(
        patient,
        "fasting_glucose",
        "1558-6",
        100,
        "mg/dL",
        encounter=encounter,
        source_type="fhir_import",
        source_payload_json={
            "resourceType": "Observation",
            "id": "missing-unit-glucose",
            "valueQuantity": {"value": 100},
        },
    )

    snapshot = DiseaseRiskInputRepository().build_snapshot(patient)

    assert "fasting_glucose" not in snapshot.data
    assert "fasting_glucose" not in snapshot.sources


@pytest.mark.django_db
def test_only_typed_legacy_schema_values_are_assumed_canonical():
    patient = _patient("UNIT-LEGACY-001")
    screening = HealthScreening.objects.create(patient=patient)
    VitalSigns.objects.create(
        health_screening=screening,
        systolic_blood_pressure=118,
        body_height=171,
        body_weight=72,
    )
    LaboratoryResults.objects.create(
        health_screening=screening,
        test_name="Glucose",
        value_result="96",
        result_unit="",
    )

    snapshot = DiseaseRiskInputRepository().build_snapshot(patient)

    assert snapshot.data["systolic_bp"] == 118
    assert snapshot.data["body_height"] == 171
    assert "fasting_glucose" not in snapshot.data
    assert snapshot.sources["systolic_bp"]["unit_handling"] == "legacy_schema_contract"
    assert snapshot.sources["systolic_bp"]["normalized_unit"] == "mm[Hg]"
    assert "fasting_glucose" not in snapshot.sources


@pytest.mark.django_db
@pytest.mark.parametrize("generic_code", ["2339-0", "2345-7"])
def test_generic_fhir_glucose_cannot_satisfy_a_fasting_input(generic_code):
    patient = _patient(f"FHIR-GENERIC-GLUCOSE-{generic_code}")
    _observation(
        patient,
        "fasting_glucose",
        generic_code,
        101,
        "mg/dL",
        source_type="fhir_import",
        source_payload_json={
            "resourceType": "Observation",
            "id": f"generic-glucose-{generic_code}",
            "code": {"coding": [{"system": "http://loinc.org", "code": generic_code}]},
            "valueQuantity": {"value": 101, "unit": "mg/dL", "code": "mg/dL"},
        },
    )

    snapshot = DiseaseRiskInputRepository().build_snapshot(patient)

    assert "fasting_glucose" not in snapshot.data


@pytest.mark.django_db
def test_fhir_questionnaire_matching_uses_exact_link_ids():
    patient = _patient("FHIR-QUESTIONNAIRE-EXACT-001")
    QuestionnaireResponse.objects.create(
        patient=patient,
        source_type="fhir_import",
        response_json={"free_text_family_diabetes_comment": True},
        metadata_json={"fhir_resource_id": "questionnaire-exact-001"},
    )

    snapshot = DiseaseRiskInputRepository().build_snapshot(patient)

    assert "family_history_diabetes" not in snapshot.data


@pytest.mark.django_db
def test_resolved_cardiovascular_condition_remains_positive_history_with_fhir_provenance():
    patient = _patient("CVD-HISTORY-001")
    problem = Problem.objects.create(
        patient=patient,
        problem_name="Prior myocardial infarction",
        status="resolved",
    )
    resource = FHIRResource.objects.create(
        resource_type="Condition",
        resource_id="prior-mi-001",
        origin_namespace="hospital-a",
        resource_data={
            "resourceType": "Condition",
            "id": "prior-mi-001",
            "subject": {"reference": f"Patient/{patient.id}"},
            "code": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "22298006",
                        "display": "Myocardial infarction",
                    }
                ]
            },
        },
    )
    FHIRResourceMapping.objects.create(
        patient=patient,
        fhir_resource_ref=resource,
        local_table=Problem._meta.db_table,
        local_id=problem.id,
        fhir_resource_type="Condition",
        fhir_resource_id=resource.resource_id,
        fhir_json=resource.resource_data,
        sync_status="synced",
    )

    snapshot = DiseaseRiskInputRepository().build_snapshot(patient)

    assert snapshot.data["cvd_history"] is True
    assert snapshot.data["chd_history"] is True
    assert snapshot.sources["cvd_history"]["fhir_references"] == ["Condition/prior-mi-001"]


def test_generic_lipid_lowering_therapy_does_not_add_two_metabolic_components():
    result = calculate_metabolic_syndrome(
        {
            "sex": "M",
            "waist_circumference": 80,
            "fasting_glucose": 90,
            "systolic_bp": 110,
            "diastolic_bp": 70,
            "hdl_cholesterol": 60,
            "triglycerides": 100,
            "has_diabetes": False,
            "prediabetes": False,
            "anti_hypertensive_drugs": False,
            "has_hypertension": False,
            # This extra field is used by other algorithms but deliberately
            # does not satisfy HDL- or triglyceride-specific MetS treatment.
            "using_lipid_lowering_drugs": True,
        }
    )

    assert result.score == 0
    assert result.evidence["low_hdl"] is False
    assert result.evidence["high_triglycerides"] is False
