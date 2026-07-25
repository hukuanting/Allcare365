import os
import sys
import math
from io import StringIO

import pytest


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medical_system.settings")

import django


django.setup()

from django.core.management import call_command
from fhirclient.models.bundle import Bundle as FHIRBundle
from fhirclient.models.provenance import Provenance as FHIRProvenance
from fhirclient.models.observation import Observation as FHIRObservation
from fhirclient.models.riskassessment import RiskAssessment as FHIRRiskAssessment

from apps.clinical.health_screening.golden_patient import (
    EXPECTED_RISK_ALGORITHMS,
    EXPECTED_EXECUTABLE_RISK_ALGORITHMS,
    EXPECTED_GATED_RISK_ALGORITHMS,
    GOLDEN_FIXTURE_KEY,
    GOLDEN_EXPECTED_RISK_VECTORS,
    GOLDEN_PATIENT_MRN,
    GOLDEN_SOURCE_NAMESPACE,
    GoldenPatientSeedError,
    GoldenPatientSeeder,
    build_golden_patient_bundle,
    golden_input_resource_keys,
)
from apps.clinical.health_screening.models import (
    AIAnalysisJob,
    Encounter,
    HealthScreening,
    Observation,
    Problem,
    QuestionnaireResponse,
)
from apps.clinical.patients.models import Patient
from apps.integration.fhir_integration.models import FHIRResource, FHIRResourceMapping
from apps.integration.fhir_integration.resource_identity import identity
from services.disease_risk_engine.repository import DiseaseRiskInputRepository


def _patient_counts(patient):
    return {
        "screenings": HealthScreening.objects.filter(patient=patient).count(),
        "encounters": Encounter.objects.filter(patient=patient).count(),
        "observations": Observation.objects.filter(patient=patient).count(),
        "questionnaire_responses": QuestionnaireResponse.objects.filter(patient=patient).count(),
    }


def test_golden_patient_bundle_is_valid_fhir_r4():
    parsed = FHIRBundle(build_golden_patient_bundle(), strict=True)
    assert parsed.type == "collection"
    assert len(parsed.entry) == len(golden_input_resource_keys())


@pytest.mark.django_db
def test_golden_patient_seed_fails_closed_when_reserved_mrn_is_duplicated():
    for suffix in ("one", "two"):
        Patient.objects.create(
            first_name="Golden",
            last_name=suffix,
            date_of_birth="1980-01-01",
            medical_record_number=GOLDEN_PATIENT_MRN,
            metadata_json={"conformance_fixture": GOLDEN_FIXTURE_KEY},
        )

    with pytest.raises(GoldenPatientSeedError, match="multiple patients"):
        GoldenPatientSeeder().seed()


@pytest.mark.django_db
def test_golden_patient_seed_does_not_take_over_fixed_fhir_ids():
    owner = Patient.objects.create(
        first_name="Hospital",
        last_name="Owner",
        date_of_birth="1970-01-01",
        medical_record_number="REAL-OWNER-001",
    )
    local_observation = Observation.objects.create(
        patient=owner,
        observation_type="bmi",
        code="39156-5",
        value_quantity=24,
        value_unit="kg/m2",
    )
    persisted = FHIRResource.objects.create(
        resource_type="Observation",
        resource_id="golden-risk-obs-bmi",
        origin_namespace=GOLDEN_SOURCE_NAMESPACE,
        resource_data={
            "resourceType": "Observation",
            "id": "golden-risk-obs-bmi",
            "subject": {"reference": str(owner.id)},
        },
    )
    FHIRResourceMapping.objects.create(
        patient=owner,
        fhir_resource_ref=persisted,
        local_table=Observation._meta.db_table,
        local_id=local_observation.id,
        fhir_resource_type="Observation",
        fhir_resource_id="golden-risk-obs-bmi",
        fhir_json=persisted.resource_data,
        sync_status="synced",
        metadata_json={"source_namespace": GOLDEN_SOURCE_NAMESPACE},
    )

    with pytest.raises(GoldenPatientSeedError, match="owned by another patient"):
        GoldenPatientSeeder().seed()

    persisted.refresh_from_db()
    assert persisted.resource_data["subject"]["reference"] == str(owner.id)
    assert not Patient.objects.filter(medical_record_number=GOLDEN_PATIENT_MRN).exists()


@pytest.mark.django_db
def test_golden_patient_is_idempotent_isolated_and_verifies_the_whole_risk_pipeline():
    unrelated = Patient.objects.create(
        first_name="Real",
        last_name="Patient",
        date_of_birth="1980-01-01",
        sex="female",
        medical_record_number="KEEP-UNRELATED-001",
        metadata_json={"owner": "hospital"},
    )

    first = GoldenPatientSeeder().seed()
    golden = Patient.objects.get(id=first.patient_id)
    first_counts = _patient_counts(golden)
    first_input_fhir_count = sum(
        FHIRResource.objects.filter(resource_type=resource_type, resource_id=resource_id).count()
        for resource_type, resource_id in golden_input_resource_keys()
    )

    second = GoldenPatientSeeder().seed()
    golden.refresh_from_db()
    unrelated.refresh_from_db()

    assert second.patient_id == first.patient_id
    assert Patient.objects.filter(medical_record_number=GOLDEN_PATIENT_MRN).count() == 1
    assert _patient_counts(golden) == first_counts
    assert first_counts["screenings"] == 1
    assert first_counts["encounters"] == 1
    assert first_counts["observations"] > 20
    assert first_counts["questionnaire_responses"] == 1
    assert first_input_fhir_count == len(golden_input_resource_keys())
    assert unrelated.medical_record_number == "KEEP-UNRELATED-001"
    assert unrelated.metadata_json == {"owner": "hospital"}
    assert Patient.objects.filter(id=unrelated.id).exists()
    assert golden.metadata_json["conformance_fixture"] == GOLDEN_FIXTURE_KEY
    assert golden.metadata_json["synthetic"] is True
    assert golden.metadata_json["clinical_use_prohibited"] is True

    input_models = {
        "Patient": Patient,
        "Encounter": Encounter,
        "Observation": Observation,
        "Condition": Problem,
        "QuestionnaireResponse": QuestionnaireResponse,
    }
    input_mapping_ids = set()
    for resource_type, resource_id in golden_input_resource_keys():
        mapping = FHIRResourceMapping.objects.get(
            fhir_resource_type=resource_type,
            fhir_resource_id=resource_id,
        )
        model = input_models[resource_type]
        local_object = model.objects.get(pk=mapping.local_id)
        input_mapping_ids.add(mapping.id)
        assert mapping.patient_id == golden.id
        assert mapping.local_table == model._meta.db_table
        assert mapping.fhir_resource_ref.resource_type == resource_type
        assert mapping.fhir_resource_ref.resource_id == resource_id
        assert mapping.fhir_resource_ref.origin_namespace == GOLDEN_SOURCE_NAMESPACE
        assert mapping.fhir_json == mapping.fhir_resource_ref.resource_data
        assert mapping.metadata_json["source_namespace"] == GOLDEN_SOURCE_NAMESPACE
        assert mapping.sync_status == "synced"
        assert mapping.last_synced_at is not None
        if resource_type == "Patient":
            assert local_object.id == golden.id
        else:
            assert local_object.patient_id == golden.id
    assert len(input_mapping_ids) == len(golden_input_resource_keys())

    output = StringIO()
    call_command("seed_golden_patient", verify=True, stdout=output)
    assert "Golden patient verification PASS" in output.getvalue()

    snapshot = DiseaseRiskInputRepository().build_snapshot(golden)
    assert snapshot.data["bmi"] == 28.4
    assert snapshot.data["systolic_bp"] == 138.0
    assert snapshot.data["diastolic_bp"] == 86.0
    assert snapshot.data["waist_hip_ratio"] == pytest.approx(0.941)
    assert snapshot.data["is_smoker"] is False
    assert snapshot.sources["bmi"]["fhir_reference"] == "Observation/golden-risk-obs-bmi"
    assert snapshot.sources["family_history_diabetes"]["table"] == "questionnaire_responses"

    job = AIAnalysisJob.objects.get(patient=golden, job_type="disease_risk_assessment")
    results = list(job.results.all())
    assert len(results) == len(EXPECTED_RISK_ALGORITHMS)
    assert {result.result_type for result in results} == EXPECTED_RISK_ALGORITHMS
    assert all(not result.result_json["missing_data"] for result in results)
    executable_results = [
        result
        for result in results
        if result.result_type in EXPECTED_EXECUTABLE_RISK_ALGORITHMS
    ]
    gated_results = [
        result
        for result in results
        if result.result_type in EXPECTED_GATED_RISK_ALGORITHMS
    ]
    assert all(
        (
            result.result_json["applicability"] == "applicable"
            and result.result_json["risk_score"] is not None
        )
        or (
            result.result_json["applicability"] == "not_applicable"
            and result.result_json["risk_score"] is None
        )
        for result in executable_results
    )
    assert all(result.result_json["risk_score"] is None for result in gated_results)
    assert all(
        result.result_json["applicability"] == "clinical_review_required"
        for result in gated_results
    )
    result_by_type = {result.result_type: result.result_json for result in results}
    for algorithm_id, expected in GOLDEN_EXPECTED_RISK_VECTORS.items():
        for key, value in expected.items():
            actual = result_by_type[algorithm_id][key]
            if key == "risk_score" and value is not None:
                assert math.isclose(float(actual), float(value), rel_tol=0, abs_tol=1e-6)
            else:
                assert actual == value

    mappings = list(
        FHIRResourceMapping.objects.filter(
            patient=golden,
            local_table="ai_analysis_results",
            local_id__in=[result.id for result in results],
            fhir_resource_type__in=("RiskAssessment", "Observation"),
        ).select_related("fhir_resource_ref")
    )
    assert len(mappings) == len(EXPECTED_RISK_ALGORITHMS)
    for mapping in mappings:
        model = FHIRObservation if mapping.fhir_resource_type == "Observation" else FHIRRiskAssessment
        model(mapping.fhir_resource_ref.resource_data, strict=True)
        assert mapping.fhir_resource_ref.resource_data["subject"]["reference"] == (
            f"Patient/{identity.patient_id(golden)}"
        )
        provenance_id = mapping.metadata_json["provenance_resource_id"]
        provenance = FHIRResource.objects.get(resource_type="Provenance", resource_id=provenance_id)
        FHIRProvenance(provenance.resource_data, strict=True)
        assert "patient" not in provenance.resource_data
        assert {item["reference"] for item in provenance.resource_data["target"]} == {
            f"{mapping.fhir_resource_type}/{mapping.fhir_resource_id}"
        }
