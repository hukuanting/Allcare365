import json
import os
import sys
import uuid
from datetime import date

import django
import pytest


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medical_system.settings")
django.setup()


from django.utils import timezone

from apps.clinical.health_screening.models import (
    ClinicalTestResult,
    HealthScreening,
    HealthStatusAssessment,
    LaboratoryResults,
    Procedure,
    VitalSigns,
)
from apps.clinical.patients.models import AdvanceDirective, Patient
from apps.integration.fhir_integration.fhir_context import FHIRContext
from apps.integration.fhir_integration.projectors.observation import ObservationProjector
from apps.integration.fhir_integration.resource_identity import identity


def _patient(mrn):
    return Patient.objects.create(
        first_name="Observation",
        last_name="Source",
        date_of_birth=date(1980, 1, 1),
        sex="female",
        medical_record_number=mrn,
    )


def _screening(patient, screening_date=date(2026, 7, 20)):
    return HealthScreening.objects.create(
        patient=patient,
        screening_date=screening_date,
    )


def _projected(patient, search_params=None):
    context = FHIRContext(patient_id=str(patient.id))
    projector = ObservationProjector()
    rows = projector.query(str(patient.id), search_params or {}, context)
    return projector.project_batch(rows, context)


def _coding_codes(resource):
    return {
        coding["code"]
        for coding in resource.get("code", {}).get("coding", [])
        if coding.get("code")
    }


def _resource_with_code(resources, code):
    return next(resource for resource in resources if code in _coding_codes(resource))


@pytest.mark.django_db
def test_missing_vital_fields_do_not_create_inferred_values_or_room_air():
    patient = _patient("OBS-NO-FAB-VITAL-MISSING")
    screening = _screening(patient)
    VitalSigns.objects.create(
        health_screening=screening,
        systolic_blood_pressure=123,
        body_height=180,
        body_weight=80,
        pulse_oximetry=98,
    )

    resources = _projected(patient)
    codes = set().union(*(_coding_codes(resource) for resource in resources))

    assert {"8302-2", "29463-7", "2708-6"}.issubset(codes)
    assert codes.isdisjoint({
        "39156-5",  # Calculated BMI
        "9843-4",   # Fabricated head circumference
        "8289-1",   # Fabricated head circumference percentile
        "59576-9",  # Fabricated BMI percentile
        "77606-2",  # Fabricated weight-for-length percentile
        "96607-7",  # Fabricated average BP panel
        "85354-9",  # Incomplete blood pressure panel
    })

    pulse_ox = _resource_with_code(resources, "2708-6")
    assert "component" not in pulse_ox
    assert "encounter" not in pulse_ox
    assert "enc-placeholder" not in json.dumps(resources)


@pytest.mark.django_db
def test_persisted_vitals_project_exact_values_without_bp_mutation():
    patient = _patient("OBS-NO-FAB-VITAL-REAL")
    screening = _screening(patient)
    VitalSigns.objects.create(
        id=uuid.UUID("00000000-0000-4000-a000-000000000001"),
        health_screening=screening,
        systolic_blood_pressure=123,
        diastolic_blood_pressure=77,
        average_blood_pressure=91,
        pulse_oximetry=97.5,
        inhaled_oxygen_concentration=35,
        head_circumference_percentile=51.25,
        bmi_percentile=63.5,
        weight_for_length_percentile=42.75,
    )

    resources = _projected(patient)
    blood_pressure = _resource_with_code(resources, "85354-9")
    components = {
        component["code"]["coding"][0]["code"]: component
        for component in blood_pressure["component"]
    }
    assert components["8480-6"]["valueQuantity"]["value"] == 123.0
    assert components["8462-4"]["valueQuantity"]["value"] == 77.0
    assert all("dataAbsentReason" not in component for component in components.values())

    expected_values = {
        "8478-0": 91.0,
        "8289-1": 51.25,
        "59576-9": 63.5,
        "77606-2": 42.75,
    }
    for code, expected in expected_values.items():
        assert _resource_with_code(resources, code)["valueQuantity"]["value"] == expected

    pulse_ox = _resource_with_code(resources, "2708-6")
    assert len(pulse_ox["component"]) == 1
    oxygen = pulse_ox["component"][0]
    assert oxygen["code"]["coding"][0]["code"] == "3150-0"
    assert oxygen["valueQuantity"]["value"] == 35.0
    assert "3151-8" not in json.dumps(pulse_ox)


@pytest.mark.django_db
def test_assessment_text_is_preserved_without_pack_years_or_pregnancy_intent():
    patient = _patient("OBS-NO-FAB-ASSESSMENT")
    screening = _screening(patient)
    HealthStatusAssessment.objects.create(
        health_screening=screening,
        smoking_status="Current smoker",
        pregnancy_status="Pregnant",
        physical_activity="Walking 45 minutes three times weekly",
        disability_status="Uses a wheelchair",
    )

    resources = _projected(patient)
    codes = set().union(*(_coding_codes(resource) for resource in resources))

    assert "401201003" not in codes
    assert "86645-9" not in codes
    physical_activity = _resource_with_code(resources, "89555-7")
    disability = _resource_with_code(resources, "89571-4")
    pregnancy = _resource_with_code(resources, "82810-3")
    assert physical_activity["valueString"] == "Walking 45 minutes three times weekly"
    assert "valueQuantity" not in physical_activity
    assert disability["valueString"] == "Uses a wheelchair"
    assert "valueCodeableConcept" not in disability
    assert pregnancy["valueCodeableConcept"]["text"] == "Pregnant"
    assert all("performer" not in resource for resource in resources)
    assert "20.0" not in json.dumps(resources)
    assert "enc-placeholder" not in json.dumps(resources)


@pytest.mark.django_db
def test_labs_and_clinical_results_use_only_persisted_values():
    patient = _patient("OBS-NO-FAB-RESULTS")
    screening = _screening(patient)
    LaboratoryResults.objects.create(
        health_screening=screening,
        test_name="Total Cholesterol",
        value_result="215",
        result_unit="mg/dL",
        result_status="final",
        result_interpretation="high",
    )
    LaboratoryResults.objects.create(
        health_screening=screening,
        test_name="C-reactive protein",
        value_result="8.2",
        result_unit="mg/L",
        result_status="final",
    )
    LaboratoryResults.objects.create(
        health_screening=screening,
        test_name="Pending test",
        value_result="Pending",
        result_status="final",
    )
    LaboratoryResults.objects.create(
        health_screening=screening,
        test_name="Glucose",
        value_result="95",
        result_status="",
    )
    ClinicalTestResult.objects.create(
        health_screening=screening,
        test_name="Neurologic reflex exam",
        result_value="Brisk and symmetric",
        test_date=timezone.now(),
        interpretation="Within documented baseline",
    )
    Procedure.objects.create(patient=patient, procedure_name="Electrocardiogram")

    resources = _projected(patient)
    resources_by_text = {
        resource.get("code", {}).get("text"): resource
        for resource in resources
        if resource.get("code", {}).get("text")
    }

    cholesterol = resources_by_text["Total Cholesterol"]
    assert cholesterol["valueQuantity"]["value"] == 215.0
    assert "valueCodeableConcept" not in cholesterol
    assert cholesterol["interpretation"] == [{"text": "high"}]
    assert "note" not in cholesterol
    assert "specimen" not in cholesterol
    assert "method" not in cholesterol

    crp = resources_by_text["C-reactive protein"]
    assert "coding" not in crp["code"]
    assert crp["valueQuantity"]["value"] == 8.2
    assert "interpretation" not in crp

    clinical = resources_by_text["Neurologic reflex exam"]
    assert "coding" not in clinical["code"]
    assert clinical["valueString"] == "Brisk and symmetric"
    assert clinical["interpretation"] == [{"text": "Within documented baseline"}]
    assert "performer" not in clinical

    serialized = json.dumps(resources)
    assert "Pending test" not in serialized
    assert '"text": "Glucose"' not in serialized
    assert "No acute findings" not in serialized
    assert "enc-placeholder" not in serialized


@pytest.mark.django_db
def test_preference_produces_one_observation_without_invented_context():
    patient = _patient("OBS-NO-FAB-PREFERENCE")
    AdvanceDirective.objects.create(
        patient=patient,
        care_experience_preference="Prefers a quiet room",
    )

    resources = _projected(patient)

    assert len(resources) == 1
    assert resources[0]["valueString"] == "Prefers a quiet room"
    assert "valueCodeableConcept" not in resources[0]
    assert "encounter" not in resources[0]
    assert "performer" not in resources[0]
