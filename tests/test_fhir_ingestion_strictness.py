import os
import sys
from datetime import date

import pytest


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medical_system.settings")

import django


django.setup()

from apps.clinical.health_screening.ingestion_service import HealthScreeningIngestionService
from apps.clinical.health_screening.models import (
    Encounter,
    HealthScreening,
    LaboratoryResults,
    Observation,
    Problem,
    VitalSigns,
)
from apps.clinical.patients.models import Patient
from apps.integration.fhir_integration.models import FHIRResource, FHIRResourceMapping
from services.disease_risk_engine.repository import DiseaseRiskInputRepository


TEST_SOURCE_NAMESPACE = "test:hospital:strict-ingestion"


def _patient(resource_id, mrn=None, **values):
    resource = {
        "resourceType": "Patient",
        "id": resource_id,
    }
    if mrn:
        resource["identifier"] = [{
            "system": "https://hospital.example/mrn",
            "value": mrn,
        }]
    resource.update(values)
    return resource


def _encounter(resource_id, patient_id):
    return {
        "resourceType": "Encounter",
        "id": resource_id,
        "status": "finished",
        "class": {"code": "AMB", "display": "ambulatory"},
        "subject": {"reference": f"Patient/{patient_id}"},
        "period": {
            "start": "2026-07-18T09:00:00+08:00",
            "end": "2026-07-18T10:00:00+08:00",
        },
    }


def _quantity_observation(resource_id, patient_id, encounter_id, code, value, unit_marker):
    quantity = {
        "value": value,
        "system": "http://unitsofmeasure.org",
    }
    if unit_marker is not None:
        quantity["unit"] = unit_marker
    return {
        "resourceType": "Observation",
        "id": resource_id,
        "status": "final",
        "category": [{"coding": [{"code": "laboratory"}]}],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": code,
                "display": code,
            }]
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "encounter": {"reference": f"Encounter/{encounter_id}"},
        "effectiveDateTime": "2026-07-18T09:30:00+08:00",
        "valueQuantity": quantity,
    }


def _bundle(*resources):
    return {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [{"resource": resource} for resource in resources],
    }


@pytest.mark.django_db
def test_missing_fhir_demographics_remain_absent_and_do_not_erase_persisted_values():
    service = HealthScreeningIngestionService()
    sparse = _patient("sparse-demographics")

    imported = service.import_fhir(
        sparse,
        source_namespace=TEST_SOURCE_NAMESPACE,
    )

    assert imported["error_count"] == 0
    patient = Patient.objects.get(source_record_id="sparse-demographics")
    assert patient.first_name == ""
    assert patient.last_name == ""
    assert patient.date_of_birth is None
    assert patient.sex == ""
    assert patient.medical_record_number is None
    assert patient.status == "unknown"
    assert patient.metadata_json["fhir_patient_id"] == "sparse-demographics"
    assert patient.source_system == "fhir_import"
    assert "1900-01-01" not in str(FHIRResource.objects.get(
        resource_type="Patient",
        resource_id="sparse-demographics",
    ).resource_data)
    assert "Unknown" not in patient.first_name + patient.last_name

    rich = _patient(
        "stable-demographics",
        "STRICT-DEMO-001",
        name=[{"family": "Persisted", "given": ["Truth"]}],
        birthDate="1982-03-04",
        gender="female",
        active=True,
    )
    assert service.import_fhir(
        rich,
        source_namespace=TEST_SOURCE_NAMESPACE,
    )["error_count"] == 0
    assert service.import_fhir(
        _patient("stable-demographics"),
        source_namespace=TEST_SOURCE_NAMESPACE,
    )["error_count"] == 0
    preserved = Patient.objects.get(source_record_id="stable-demographics")
    assert preserved.medical_record_number == "STRICT-DEMO-001"
    assert preserved.first_name == "Truth"
    assert preserved.last_name == "Persisted"
    assert preserved.date_of_birth == date(1982, 3, 4)
    assert preserved.sex == "F"
    assert preserved.status == "active"


@pytest.mark.django_db
def test_source_identity_is_idempotent_patient_scoped_and_maps_standalone_encounters():
    service = HealthScreeningIngestionService()
    bundle = _bundle(
        _patient(
            "patient-one",
            "STRICT-IDENTITY-001",
            name=[{"family": "One", "given": ["Patient"]}],
            birthDate="1970-01-01",
        ),
        _patient(
            "patient-two",
            "STRICT-IDENTITY-002",
            name=[{"family": "Two", "given": ["Patient"]}],
            birthDate="1980-01-01",
        ),
        _encounter("encounter-one", "patient-one"),
        _encounter("encounter-two", "patient-two"),
        _quantity_observation(
            "observation-one",
            "patient-one",
            "encounter-one",
            "2160-0",
            1.0,
            "mg/dL",
        ),
        _quantity_observation(
            "observation-two",
            "patient-two",
            "encounter-two",
            "2160-0",
            2.0,
            "mg/dL",
        ),
    )

    first = service.import_fhir(bundle, source_namespace=TEST_SOURCE_NAMESPACE)
    second = service.import_fhir(bundle, source_namespace=TEST_SOURCE_NAMESPACE)

    assert first["error_count"] == second["error_count"] == 0
    assert Patient.objects.filter(source_system="fhir_import").count() == 2
    assert HealthScreening.objects.count() == 2
    assert Encounter.objects.filter(source_type="fhir_import").count() == 2
    assert Observation.objects.filter(source_type="fhir_import").count() == 2
    assert FHIRResourceMapping.objects.filter(sync_status="synced").count() == 6

    first_patient = Patient.objects.get(source_record_id="patient-one")
    second_patient = Patient.objects.get(source_record_id="patient-two")
    first_observation = Observation.objects.get(source_payload_json__id="observation-one")
    second_observation = Observation.objects.get(source_payload_json__id="observation-two")
    assert first_observation.patient_id == first_patient.id
    assert first_observation.encounter.patient_id == first_patient.id
    assert second_observation.patient_id == second_patient.id
    assert second_observation.encounter.patient_id == second_patient.id

    for resource_type, resource_id, local_object, patient in (
        ("Patient", "patient-one", first_patient, first_patient),
        ("Patient", "patient-two", second_patient, second_patient),
        ("Encounter", "encounter-one", first_observation.encounter, first_patient),
        ("Encounter", "encounter-two", second_observation.encounter, second_patient),
        ("Observation", "observation-one", first_observation, first_patient),
        ("Observation", "observation-two", second_observation, second_patient),
    ):
        mapping = FHIRResourceMapping.objects.get(
            fhir_resource_type=resource_type,
            fhir_resource_id=resource_id,
        )
        assert mapping.patient_id == patient.id
        assert mapping.local_table == local_object._meta.db_table
        assert mapping.local_id == local_object.id
        assert mapping.fhir_resource_ref.resource_data["id"] == resource_id
        assert mapping.last_synced_at is not None


@pytest.mark.django_db
def test_encounter_without_observations_is_persisted_mapped_and_idempotent():
    patient_resource = _patient(
        "standalone-encounter-patient",
        "STRICT-STANDALONE-ENC-001",
        birthDate="1990-01-01",
    )
    encounter_resource = _encounter(
        "standalone-encounter",
        "standalone-encounter-patient",
    )
    bundle = _bundle(patient_resource, encounter_resource)
    service = HealthScreeningIngestionService()

    first = service.import_fhir(bundle, source_namespace=TEST_SOURCE_NAMESPACE)
    second = service.import_fhir(bundle, source_namespace=TEST_SOURCE_NAMESPACE)

    assert first["error_count"] == second["error_count"] == 0
    patient = Patient.objects.get(source_record_id="standalone-encounter-patient")
    encounter = Encounter.objects.get(
        patient=patient,
        metadata_json__fhir_encounter_id="standalone-encounter",
    )
    assert HealthScreening.objects.filter(patient=patient).count() == 1
    assert Encounter.objects.filter(patient=patient).count() == 1
    assert not Observation.objects.filter(patient=patient).exists()
    mapping = FHIRResourceMapping.objects.get(
        fhir_resource_type="Encounter",
        fhir_resource_id="standalone-encounter",
    )
    assert mapping.local_id == encounter.id
    assert mapping.local_table == Encounter._meta.db_table
    assert mapping.patient_id == patient.id


@pytest.mark.django_db
def test_duplicate_or_conflicting_patient_identity_fails_closed():
    duplicate_values = {
        "first_name": "Duplicate",
        "last_name": "MRN",
        "date_of_birth": date(1975, 1, 1),
        "medical_record_number": "DUPLICATE-STRICT-MRN",
        "metadata_json": {
            "fhir_mrn_system": "https://hospital.example/mrn",
            "fhir_source_namespace": TEST_SOURCE_NAMESPACE,
        },
    }
    Patient.objects.create(**duplicate_values)
    Patient.objects.create(**duplicate_values)

    service = HealthScreeningIngestionService()
    duplicate_result = service.import_fhir(
        _patient("ambiguous-patient", "DUPLICATE-STRICT-MRN"),
        source_namespace=TEST_SOURCE_NAMESPACE,
    )

    assert duplicate_result["error_count"] == 1
    assert "multiple local patients" in duplicate_result["errors"][0]
    assert not FHIRResource.objects.filter(
        resource_type="Patient",
        resource_id="ambiguous-patient",
    ).exists()

    source_patient = Patient.objects.create(
        first_name="Source",
        last_name="Identity",
        date_of_birth=date(1970, 1, 1),
        medical_record_number="SOURCE-MRN",
        metadata_json={
            "fhir_patient_id": "stable-source-id",
            "fhir_mrn_system": "https://hospital.example/mrn",
            "fhir_source_namespace": TEST_SOURCE_NAMESPACE,
        },
    )
    other_patient = Patient.objects.create(
        first_name="Other",
        last_name="Identity",
        date_of_birth=date(1980, 1, 1),
        medical_record_number="OTHER-MRN",
        metadata_json={
            "fhir_mrn_system": "https://hospital.example/mrn",
            "fhir_source_namespace": TEST_SOURCE_NAMESPACE,
        },
    )
    conflict_result = service.import_fhir(
        _patient("stable-source-id", "OTHER-MRN"),
        source_namespace=TEST_SOURCE_NAMESPACE,
    )

    assert conflict_result["error_count"] == 1
    assert "conflicts with MRN" in conflict_result["errors"][0]
    source_patient.refresh_from_db()
    other_patient.refresh_from_db()
    assert source_patient.medical_record_number == "SOURCE-MRN"
    assert other_patient.metadata_json.get("fhir_patient_id") is None


@pytest.mark.django_db
def test_reused_observation_logical_id_cannot_overwrite_another_patient_source():
    service = HealthScreeningIngestionService()
    shared_observation_id = "patient-owned-observation"
    first_bundle = _bundle(
        _patient("owner-one", "STRICT-OWNER-001", birthDate="1970-01-01"),
        _quantity_observation(
            shared_observation_id,
            "owner-one",
            "owner-one-context",
            "2160-0",
            1.0,
            "mg/dL",
        ),
    )
    second_bundle = _bundle(
        _patient("owner-two", "STRICT-OWNER-002", birthDate="1980-01-01"),
        _quantity_observation(
            shared_observation_id,
            "owner-two",
            "owner-two-context",
            "2160-0",
            2.0,
            "mg/dL",
        ),
    )

    assert service.import_fhir(
        first_bundle,
        source_namespace=TEST_SOURCE_NAMESPACE,
    )["error_count"] == 0
    with pytest.raises(ValueError, match="owned by another patient/source"):
        service.import_fhir(
            second_bundle,
            source_namespace=TEST_SOURCE_NAMESPACE,
        )

    first_patient = Patient.objects.get(source_record_id="owner-one")
    observation = Observation.objects.get(source_payload_json__id=shared_observation_id)
    persisted = FHIRResource.objects.get(
        resource_type="Observation",
        resource_id=shared_observation_id,
    )
    mapping = FHIRResourceMapping.objects.get(
        fhir_resource_type="Observation",
        fhir_resource_id=shared_observation_id,
    )
    assert observation.patient_id == first_patient.id
    assert mapping.patient_id == first_patient.id
    assert persisted.resource_data["subject"]["reference"] == "Patient/owner-one"
    assert not Patient.objects.filter(source_record_id="owner-two").exists()


@pytest.mark.django_db
def test_source_namespace_prevents_cross_source_takeover_even_for_identical_payload():
    bundle = _bundle(
        _patient(
            "namespace-patient",
            "STRICT-NAMESPACE-001",
            birthDate="1970-01-01",
        )
    )
    service = HealthScreeningIngestionService()

    assert service.import_fhir(bundle, source_namespace="hospital-a")["error_count"] == 0
    with pytest.raises(ValueError, match="source namespace hospital-a, not hospital-b"):
        service.import_fhir(bundle, source_namespace="hospital-b")

    patient = Patient.objects.get(source_record_id="namespace-patient")
    mapping = FHIRResourceMapping.objects.get(
        fhir_resource_type="Patient",
        fhir_resource_id="namespace-patient",
    )
    persisted = FHIRResource.objects.get(
        resource_type="Patient",
        resource_id="namespace-patient",
    )
    assert patient.metadata_json["fhir_source_namespace"] == "hospital-a"
    assert mapping.metadata_json["source_namespace"] == "hospital-a"
    assert persisted.origin_namespace == "hospital-a"


@pytest.mark.django_db
def test_fhir_import_requires_explicit_or_configured_source_namespace():
    with pytest.raises(ValueError, match="source_namespace is required"):
        HealthScreeningIngestionService().import_fhir(
            _patient("missing-source-namespace")
        )

    assert not Patient.objects.filter(source_record_id="missing-source-namespace").exists()
    assert not FHIRResource.objects.exists()


@pytest.mark.django_db
def test_unmapped_resource_ownership_uses_persisted_origin_not_payload_equality():
    resource = {
        "resourceType": "Organization",
        "id": "shared-organization",
        "name": "Hospital A",
    }
    service = HealthScreeningIngestionService()

    assert service.import_fhir(
        resource,
        source_namespace="hospital-a",
    )["error_count"] == 0
    assert service.import_fhir(
        {**resource, "name": "Hospital A - renamed"},
        source_namespace="hospital-a",
    )["error_count"] == 0
    with pytest.raises(ValueError, match="source namespace hospital-a, not hospital-b"):
        service.import_fhir(
            {**resource, "name": "Hospital A - renamed"},
            source_namespace="hospital-b",
        )

    persisted = FHIRResource.objects.get(
        resource_type="Organization",
        resource_id="shared-organization",
    )
    assert persisted.origin_namespace == "hospital-a"
    assert persisted.resource_data["name"] == "Hospital A - renamed"
    assert not FHIRResourceMapping.objects.filter(
        fhir_resource_type="Organization",
        fhir_resource_id="shared-organization",
    ).exists()


@pytest.mark.django_db
def test_naked_mrn_value_does_not_merge_without_system_and_source_provenance():
    legacy_patient = Patient.objects.create(
        first_name="Legacy",
        last_name="Patient",
        medical_record_number="SHARED-MRN-VALUE",
    )

    result = HealthScreeningIngestionService().import_fhir(
        _patient("provenanced-patient", "SHARED-MRN-VALUE"),
        source_namespace=TEST_SOURCE_NAMESPACE,
    )

    assert result["error_count"] == 0
    imported_patient = Patient.objects.get(source_record_id="provenanced-patient")
    assert imported_patient.id != legacy_patient.id
    assert imported_patient.metadata_json["fhir_mrn_system"] == "https://hospital.example/mrn"
    assert imported_patient.metadata_json["fhir_source_namespace"] == TEST_SOURCE_NAMESPACE


@pytest.mark.django_db
def test_missing_or_wrong_fhir_units_stay_untrusted_without_legacy_sidecars():
    patient_id = "strict-unit-patient"
    encounter_id = "strict-unit-encounter"
    blood_pressure = {
        "resourceType": "Observation",
        "id": "strict-unit-blood-pressure",
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "85354-9"}]},
        "subject": {"reference": f"Patient/{patient_id}"},
        "encounter": {"reference": f"Encounter/{encounter_id}"},
        "effectiveDateTime": "2026-07-18T09:30:00+08:00",
        "component": [
            {
                "code": {"coding": [{"system": "http://loinc.org", "code": "8480-6"}]},
                "valueQuantity": {"value": 120},
            },
            {
                "code": {"coding": [{"system": "http://loinc.org", "code": "8462-4"}]},
                "valueQuantity": {"value": 80, "unit": "kPa"},
            },
        ],
    }
    bundle = _bundle(
        _patient(patient_id, "STRICT-UNIT-IMPORT-001", birthDate="1970-01-01"),
        _encounter(encounter_id, patient_id),
        _quantity_observation(
            "strict-unit-glucose",
            patient_id,
            encounter_id,
            "2345-7",
            100,
            None,
        ),
        _quantity_observation(
            "strict-unit-cholesterol",
            patient_id,
            encounter_id,
            "2093-3",
            200,
            "kg",
        ),
        blood_pressure,
    )

    result = HealthScreeningIngestionService().import_fhir(
        bundle,
        source_namespace=TEST_SOURCE_NAMESPACE,
    )

    assert result["error_count"] == 0
    patient = Patient.objects.get(source_record_id=patient_id)
    glucose = Observation.objects.get(source_payload_json__id="strict-unit-glucose")
    cholesterol = Observation.objects.get(source_payload_json__id="strict-unit-cholesterol")
    bp = Observation.objects.get(source_payload_json__id="strict-unit-blood-pressure")
    assert glucose.value_unit == ""
    assert cholesterol.value_unit == "kg"
    assert [component["unit"] for component in bp.component_json] == ["", "kPa"]
    assert not VitalSigns.objects.filter(health_screening__patient=patient).exists()
    assert not LaboratoryResults.objects.filter(health_screening__patient=patient).exists()

    snapshot = DiseaseRiskInputRepository().build_snapshot(patient)
    for field in (
        "fasting_glucose",
        "total_cholesterol",
        "systolic_bp",
        "diastolic_bp",
    ):
        assert field not in snapshot.data
        assert field not in snapshot.sources


@pytest.mark.django_db
def test_condition_requires_source_code_and_missing_status_stays_unknown():
    patient = _patient("condition-patient", "STRICT-CONDITION-001")
    valid_condition = {
        "resourceType": "Condition",
        "id": "condition-with-code",
        "subject": {"reference": "Patient/condition-patient"},
        "code": {"coding": [{"system": "http://snomed.info/sct", "code": "38341003"}]},
    }
    invalid_condition = {
        "resourceType": "Condition",
        "id": "condition-without-code",
        "subject": {"reference": "Patient/condition-patient"},
    }

    result = HealthScreeningIngestionService().import_fhir(
        _bundle(patient, valid_condition, invalid_condition),
        source_namespace=TEST_SOURCE_NAMESPACE,
    )

    assert result["error_count"] == 1
    assert result["success_count"] == 0
    assert "Condition.code" in result["errors"][0]
    assert not Patient.objects.filter(source_record_id="condition-patient").exists()
    assert not Problem.objects.exists()
    assert not FHIRResourceMapping.objects.exists()
    assert not FHIRResource.objects.filter(
        resource_id__in={"condition-patient", "condition-with-code", "condition-without-code"}
    ).exists()


@pytest.mark.django_db
def test_fhir_logical_id_is_unique_within_resource_type_not_globally():
    shared_id = "same-logical-id"
    bundle = _bundle(
        _patient(shared_id, "STRICT-COMPOSITE-ID-001", birthDate="1970-01-01"),
        _quantity_observation(
            shared_id,
            shared_id,
            "unbundled-context",
            "2160-0",
            1.0,
            "mg/dL",
        ),
    )

    result = HealthScreeningIngestionService().import_fhir(
        bundle,
        source_namespace=TEST_SOURCE_NAMESPACE,
    )

    assert result["error_count"] == 0
    assert FHIRResource.objects.filter(resource_id=shared_id).count() == 2
    assert set(
        FHIRResource.objects.filter(resource_id=shared_id).values_list(
            "resource_type",
            flat=True,
        )
    ) == {"Patient", "Observation"}
