import json
import os
import sys

import pytest


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medical_system.settings")

import django


django.setup()

from services.disease_risk_engine.algorithm_registry import (
    CLINICAL_SYSTEM_DEFINITIONS,
    CLINICAL_VARIABLES,
    CatalogInvariantError,
    CatalogSchemaValidationError,
    ClinicalSourceKind,
    ClinicalSystem,
    VariableDataType,
    RUNTIME_ALGORITHMS,
    load_review_catalog,
    public_algorithm_catalog,
    registry_with_review_candidates,
    runtime_registry,
)
from services.disease_risk_engine.formula_catalog import (
    DiseaseRiskResult,
    FORMULA_CALCULATION_STEPS,
    calculate_ausdrisk_diabetes,
    calculate_chinese_diabetes,
    calculate_fhs_diabetes,
    calculate_metabolic_syndrome,
    calculate_prevent_risks,
)
from services.disease_risk_engine.runtime_calculators import (
    calculate_catalog_risks,
    calculate_runtime_risks,
)
from services.disease_risk_engine.service import DiseaseRiskAssessmentService


_REVIEW_CATEGORY_RUNTIME_IDS = {
    "anthropometry": "bmi",
    "metabolic": "tyg_index",
    "diabetes": "framingham_diabetes",
    "fatty_liver": "fatty_liver_index",
    "liver_fibrosis": "fib4",
    "cardiovascular": "framingham_cvd_10_lipids",
    "cardiovascular_diabetes": "christianson_t2dm_chd_score",
    "hypertension": "framingham_hypertension",
    "dementia": "dementia_risk_score_thin_60_79",
    "lung_cancer": "mayo_pulmonary_nodule",
    "mental_health": "gad7",
}


def _review_record(algorithm_id, category, implementation_status):
    return {
        "id": algorithm_id,
        "name": f"Review fixture for {algorithm_id}",
        "category": category,
        "target": "test outcome",
        "time_horizon": None,
        "population": "synthetic test population",
        "implementation_status": implementation_status,
        "formula": (
            "test-only extracted formula"
            if implementation_status == "candidate_after_clinical_validation"
            else None
        ),
        "output": "test result",
        "inputs": [{
            "name": "age",
            "type": "number",
            "unit": "years",
            "encoding": None,
            "constraints": ">=0",
        }],
        "source_locations": ["synthetic-test-source"],
        "literature": [],
        "issues": [],
        "fhir_output": "RiskAssessment",
    }


@pytest.fixture
def review_catalog_files(tmp_path):
    source = {
        "schema_version": "test-1.0.0",
        "algorithms": [
            *[
                _review_record(algorithm_id, category, "candidate_after_clinical_validation")
                for category, algorithm_id in _REVIEW_CATEGORY_RUNTIME_IDS.items()
            ],
            _review_record(
                "blocked_source_conflict_test",
                "cardiovascular",
                "blocked_source_conflict",
            ),
        ],
    }
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["schema_version", "algorithms"],
        "properties": {
            "schema_version": {"type": "string"},
            "algorithms": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "id",
                        "name",
                        "category",
                        "implementation_status",
                        "formula",
                        "output",
                        "inputs",
                        "source_locations",
                        "fhir_output",
                    ],
                    "properties": {
                        "id": {"type": "string", "pattern": "^[a-z0-9_]+$"},
                        "name": {"type": "string"},
                        "category": {"type": "string"},
                        "implementation_status": {
                            "enum": [
                                "candidate_after_clinical_validation",
                                "blocked_source_conflict",
                                "reference_only",
                            ]
                        },
                        "formula": {"type": ["string", "null"]},
                        "output": {"type": "string"},
                        "inputs": {"type": "array"},
                        "source_locations": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                        },
                        "fhir_output": {"enum": ["RiskAssessment", "Observation"]},
                    },
                },
            },
        },
    }
    catalog_path = tmp_path / "algorithms.json"
    schema_path = tmp_path / "algorithm.schema.json"
    catalog_path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
    schema_path.write_text(json.dumps(schema, ensure_ascii=False), encoding="utf-8")
    return source, catalog_path, schema_path


def test_review_catalog_validates_and_only_instantiates_reviewable_candidates(review_catalog_files):
    source, catalog_path, schema_path = review_catalog_files
    reviewable_ids = {
        record["id"]
        for record in source["algorithms"]
        if record["implementation_status"] == "candidate_after_clinical_validation"
    }
    blocked_ids = {
        record["id"]
        for record in source["algorithms"]
        if record["implementation_status"] == "blocked_source_conflict"
    }

    snapshot = load_review_catalog(catalog_path, schema_path)

    assert set(snapshot.candidate_ids) == reviewable_ids
    assert blocked_ids
    assert blocked_ids.isdisjoint(snapshot.candidate_ids)
    assert snapshot.omitted_record_count == len(source["algorithms"]) - len(reviewable_ids)
    assert all(candidate.governance_status == "clinical_review_required" for candidate in snapshot.candidates)
    assert all(candidate.runtime_enabled is False for candidate in snapshot.candidates)
    assert all(not hasattr(candidate, "formula") for candidate in snapshot.candidates)
    assert all("formula" not in candidate.to_public_dict() for candidate in snapshot.candidates)
    serialized_public_catalog = json.dumps(snapshot.to_public_list(), ensure_ascii=False)
    assert all(blocked_id not in serialized_public_catalog for blocked_id in blocked_ids)


def test_public_catalog_contains_all_non_conflicted_models_without_formulas(review_catalog_files):
    source, _, _ = review_catalog_files
    payload = public_algorithm_catalog()
    algorithms = [
        algorithm
        for system in payload["systems"]
        for algorithm in system["algorithms"]
    ]
    ids = {algorithm["algorithm_id"] for algorithm in algorithms}
    blocked_ids = {
        record["id"]
        for record in source["algorithms"]
        if record["implementation_status"] == "blocked_source_conflict"
    }

    assert payload["counts"] == {
        "total_models": 42,
        "runtime_catalog_models": 42,
        "executable_models": 42,
        "clinical_review_required_models": 0,
        "review_candidate_models": 0,
    }
    assert len(algorithms) == len(ids) == 42
    assert blocked_ids.isdisjoint(ids)
    assert {item["catalog_kind"] for item in algorithms} == {"runtime"}
    assert all(algorithm["display_name_zh"] for algorithm in algorithms)
    assert all(algorithm["display_name_en"] for algorithm in algorithms)
    serialized = json.dumps(payload, ensure_ascii=False)
    assert '"formula"' not in serialized
    assert all(blocked_id not in serialized for blocked_id in blocked_ids)


def test_public_catalog_does_not_depend_on_the_offline_review_catalog(monkeypatch):
    def unavailable_review_catalog(*args, **kwargs):
        raise CatalogSchemaValidationError("offline review catalog unavailable")

    public_algorithm_catalog.cache_clear()
    monkeypatch.setattr(
        "services.disease_risk_engine.algorithm_registry.registry_with_review_candidates",
        unavailable_review_catalog,
    )

    payload = public_algorithm_catalog()

    assert payload["counts"]["runtime_catalog_models"] == len(RUNTIME_ALGORITHMS)
    assert payload["counts"]["executable_models"] == len(RUNTIME_ALGORITHMS)
    assert payload["counts"]["review_candidate_models"] == 0
    public_algorithm_catalog.cache_clear()


def test_schema_validation_rejects_a_catalog_missing_required_metadata(tmp_path, review_catalog_files):
    source, _, schema_path = review_catalog_files
    del source["schema_version"]
    invalid_catalog = tmp_path / "algorithms.json"
    invalid_catalog.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(CatalogSchemaValidationError, match="schema_version"):
        load_review_catalog(invalid_catalog, schema_path)


def test_clinical_system_codes_and_order_are_stable():
    assert [definition.code.value for definition in CLINICAL_SYSTEM_DEFINITIONS] == [
        "cardiovascular",
        "metabolic_endocrine",
        "hepatic",
        "renal",
        "neurocognitive",
        "respiratory",
        "mental_health",
        "other",
    ]
    assert [definition.sort_order for definition in CLINICAL_SYSTEM_DEFINITIONS] == [10, 20, 30, 40, 50, 60, 70, 999]


def test_review_source_categories_have_explicit_stable_classifications(review_catalog_files):
    expected = {
        "anthropometry": ClinicalSystem.METABOLIC_ENDOCRINE,
        "metabolic": ClinicalSystem.METABOLIC_ENDOCRINE,
        "diabetes": ClinicalSystem.METABOLIC_ENDOCRINE,
        "fatty_liver": ClinicalSystem.HEPATIC,
        "liver_fibrosis": ClinicalSystem.HEPATIC,
        "cardiovascular": ClinicalSystem.CARDIOVASCULAR,
        "cardiovascular_diabetes": ClinicalSystem.CARDIOVASCULAR,
        "hypertension": ClinicalSystem.CARDIOVASCULAR,
        "dementia": ClinicalSystem.NEUROCOGNITIVE,
        "lung_cancer": ClinicalSystem.RESPIRATORY,
        "mental_health": ClinicalSystem.MENTAL_HEALTH,
    }

    _, catalog_path, schema_path = review_catalog_files
    candidates = load_review_catalog(catalog_path, schema_path).candidates

    assert {candidate.source_category for candidate in candidates} == set(expected)
    assert all(candidate.clinical_system is expected[candidate.source_category] for candidate in candidates)


def test_formal_runtime_catalog_has_stable_system_and_governance_metadata():
    expected = {
        "framingham_diabetes": ClinicalSystem.METABOLIC_ENDOCRINE,
        "chinese_diabetes": ClinicalSystem.METABOLIC_ENDOCRINE,
        "metabolic_syndrome": ClinicalSystem.METABOLIC_ENDOCRINE,
        "hepatic_steatosis_index": ClinicalSystem.HEPATIC,
        "fib4": ClinicalSystem.HEPATIC,
        "framingham_cvd_10_lipids": ClinicalSystem.CARDIOVASCULAR,
        "dementia_risk_score_thin_60_79": ClinicalSystem.NEUROCOGNITIVE,
        "mayo_pulmonary_nodule": ClinicalSystem.RESPIRATORY,
        "gad7": ClinicalSystem.MENTAL_HEALTH,
        "ausdrisk_diabetes": ClinicalSystem.METABOLIC_ENDOCRINE,
        "caide_dementia_20y": ClinicalSystem.NEUROCOGNITIVE,
        "cardiometabolic_index": ClinicalSystem.METABOLIC_ENDOCRINE,
        "ggt_platelet_ratio": ClinicalSystem.HEPATIC,
        "ipag_copd_questionnaire": ClinicalSystem.RESPIRATORY,
        "brock_pancan_pulmonary_nodule": ClinicalSystem.RESPIRATORY,
        "aha_prevent_cvd_10y": ClinicalSystem.CARDIOVASCULAR,
        "aha_prevent_ascvd_10y": ClinicalSystem.CARDIOVASCULAR,
        "aha_prevent_hf_10y": ClinicalSystem.CARDIOVASCULAR,
    }

    assert len(RUNTIME_ALGORITHMS) == 42
    actual = {item.algorithm_id: item.clinical_system for item in RUNTIME_ALGORITHMS}
    assert all(actual[algorithm_id] is system for algorithm_id, system in expected.items())
    assert all(item.runtime_enabled for item in RUNTIME_ALGORITHMS)
    assert all(item.governance_status == "runtime_approved" for item in RUNTIME_ALGORITHMS)


def test_runtime_contracts_require_every_risk_affecting_boolean_used_by_calculators():
    required = {item.algorithm_id: set(item.required_inputs) for item in RUNTIME_ALGORITHMS}

    assert {"family_history_diabetes", "anti_hypertensive_drugs"} <= required["framingham_diabetes"]
    assert {
        "has_diabetes",
        "prediabetes",
        "anti_hypertensive_drugs",
        "has_hypertension",
    } <= required["metabolic_syndrome"]
    assert "using_lipid_lowering_drugs" not in required["metabolic_syndrome"]
    assert {"has_diabetes", "metabolic_syndrome"} <= required["nafld_liver_fat_score"]
    assert {"has_diabetes", "prediabetes"} <= required["nafld_fibrosis_score"]
    assert "anti_hypertensive_drugs" in required["ausdrisk_diabetes"]
    for algorithm_id in ("aha_prevent_cvd_10y", "aha_prevent_ascvd_10y", "aha_prevent_hf_10y"):
        assert {"statin_use", "chd_history", "cvd_history", "pvd_history", "ascvd_history", "heart_failure_history"} <= required[algorithm_id]
        assert "using_lipid_lowering_drugs" not in required[algorithm_id]


def test_runtime_required_inputs_match_calculator_missing_data_contracts():
    single_result_calculators = {
        "framingham_diabetes": calculate_fhs_diabetes,
        "chinese_diabetes": calculate_chinese_diabetes,
        "metabolic_syndrome": calculate_metabolic_syndrome,
        "ausdrisk_diabetes": calculate_ausdrisk_diabetes,
    }
    metadata_by_id = {item.algorithm_id: item for item in RUNTIME_ALGORITHMS}

    for algorithm_id, calculator in single_result_calculators.items():
        result = calculator({})
        assert tuple(result.missing_data) == metadata_by_id[algorithm_id].required_inputs
        payload = result.to_api_payload()
        assert payload["clinical_system"] == metadata_by_id[algorithm_id].clinical_system.value
        assert payload["fhir_output"] == metadata_by_id[algorithm_id].output_resource.value
        assert payload["governance_status"] == "runtime_approved"

    bound_algorithm_ids = tuple(
        algorithm_id
        for step in FORMULA_CALCULATION_STEPS
        for algorithm_id in step.algorithm_ids
    )
    assert bound_algorithm_ids == tuple(item.algorithm_id for item in RUNTIME_ALGORITHMS)

    prevent_results = calculate_prevent_risks({})
    for result in prevent_results:
        assert tuple(result.missing_data) == metadata_by_id[result.algorithm_key].required_inputs
        payload = result.to_api_payload()
        assert payload["clinical_system"] == metadata_by_id[result.algorithm_key].clinical_system.value
        assert payload["fhir_output"] == metadata_by_id[result.algorithm_key].output_resource.value
        assert payload["governance_status"] == "runtime_approved"

    referenced_inputs = {key for metadata in RUNTIME_ALGORITHMS for key in metadata.required_inputs}
    assert referenced_inputs <= set(CLINICAL_VARIABLES)


def test_runtime_execution_plan_produces_every_enabled_algorithm_exactly_once():
    results = calculate_runtime_risks({})

    assert [result.algorithm_key for result in results] == [
        metadata.algorithm_id for metadata in RUNTIME_ALGORITHMS if metadata.runtime_enabled
    ]


def test_catalog_response_contains_only_formally_executable_algorithms():
    results = calculate_catalog_risks({})

    assert [result.algorithm_key for result in results] == [
        metadata.algorithm_id for metadata in RUNTIME_ALGORITHMS
    ]
    gated = [result for result in results if result.applicability == "clinical_review_required"]
    assert gated == []
    assert all(result.missing_data for result in results)


def test_fhir_probability_preserves_bounds_instead_of_fabricating_midpoints():
    service = DiseaseRiskAssessmentService()

    def result(risk_percentage):
        return DiseaseRiskResult(
            algorithm_key="framingham_diabetes",
            outcome_key="diabetes_risk",
            algorithm_name="Framingham Diabetes Risk",
            score=1,
            risk_percentage=risk_percentage,
            risk_level="low",
            risk_category="low",
            missing_data=[],
            evidence={},
            recommendation_text="",
        )

    assert service._probability_representation(result("<3%")) == (
        "probabilityRange",
        {
            "high": {
                "value": 0.03,
                "system": "http://unitsofmeasure.org",
                "code": "1",
            }
        },
    )
    assert service._probability_representation(result("8-12%")) == (
        "probabilityRange",
        {
            "low": {
                "value": 0.08,
                "system": "http://unitsofmeasure.org",
                "code": "1",
            },
            "high": {
                "value": 0.12,
                "system": "http://unitsofmeasure.org",
                "code": "1",
            },
        },
    )


def test_runtime_variable_contracts_define_sources_units_and_loinc_aliases():
    assert len(CLINICAL_VARIABLES) == 115
    assert all(contract.source_kinds for contract in CLINICAL_VARIABLES.values())
    observation_backed = [
        contract
        for contract in CLINICAL_VARIABLES.values()
        if ClinicalSourceKind.OBSERVATION in contract.source_kinds
    ]
    assert observation_backed
    assert all(
        contract.unit
        for contract in observation_backed
        if contract.data_type in {VariableDataType.NUMBER, VariableDataType.INTEGER}
    )
    assert CLINICAL_VARIABLES["systolic_bp"].unit == "mm[Hg]"
    assert CLINICAL_VARIABLES["egfr"].unit == "mL/min/{1.73_m2}"
    assert CLINICAL_VARIABLES["sex"].allowed_values == ("M", "F")


@pytest.mark.parametrize("invalid", ["not-a-number", float("nan"), float("inf"), -1, True])
def test_canonical_numeric_validation_preserves_invalid_values_as_missing(invalid):
    validation = runtime_registry().validate_required_inputs(
        "aha_prevent_cvd_10y",
        {"age": invalid},
    )

    assert validation.values["age"] is None
    assert "age" in validation.missing_fields


@pytest.mark.parametrize("invalid", [None, "", "unknown", "false", 0, 1])
def test_canonical_boolean_validation_never_defaults_invalid_values_to_false(invalid):
    validation = runtime_registry().validate_required_inputs(
        "aha_prevent_cvd_10y",
        {"has_diabetes": invalid},
    )

    assert validation.values["has_diabetes"] is None
    assert "has_diabetes" in validation.missing_fields


def test_frontend_grouping_defaults_to_runtime_and_requires_explicit_review_opt_in(review_catalog_files):
    _, catalog_path, schema_path = review_catalog_files
    registry = registry_with_review_candidates(catalog_path, schema_path)

    default_payload = registry.to_frontend_payload(include_empty_systems=True)
    default_algorithms = [
        algorithm
        for system in default_payload["systems"]
        for algorithm in system["algorithms"]
    ]
    assert len(default_payload["systems"]) == len(CLINICAL_SYSTEM_DEFINITIONS)
    assert {item["algorithm_id"] for item in default_algorithms} == {
        item.algorithm_id for item in RUNTIME_ALGORITHMS
    }
    assert all(item["runtime_enabled"] for item in default_algorithms)

    review_payload = registry.to_frontend_payload(include_review_candidates=True)
    review_algorithms = [
        algorithm
        for system in review_payload["systems"]
        for algorithm in system["algorithms"]
    ]
    review_only = [
        item
        for item in review_algorithms
        if item["algorithm_id"] in {candidate.algorithm_id for candidate in registry.review_candidates}
    ]
    assert len(review_only) == len(registry.review_candidates)
    assert review_only == []

    production_only = runtime_registry()
    assert production_only.review_candidates == ()
