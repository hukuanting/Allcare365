"""Persisted golden-patient conformance data and whole-pipeline verification.

This module is deliberately opt-in.  It is called by a management command and
tests only; application request paths must never use it as missing-data
fallback.  The synthetic record is persisted through the production FHIR
ingestion and disease-risk services so the same database and mapping contracts
used by hospital data are exercised.
"""

from dataclasses import dataclass
import math
from datetime import date
from typing import Any, Dict, List, Optional, Set, Tuple

from django.db import transaction
from django.utils import timezone
from fhirclient.models.bundle import Bundle as FHIRBundle
from fhirclient.models.observation import Observation as FHIRObservation
from fhirclient.models.provenance import Provenance as FHIRProvenance
from fhirclient.models.riskassessment import RiskAssessment as FHIRRiskAssessment

from apps.clinical.health_screening.ingestion_service import HealthScreeningIngestionService
from apps.clinical.health_screening.models import (
    Encounter,
    HealthScreening,
    Observation,
    Problem,
    QuestionnaireResponse,
)
from apps.clinical.patients.clinical_scope import (
    GOLDEN_DEMO_FIXTURE_KEY,
    GOLDEN_DEMO_MRN,
    GOLDEN_DEMO_SOURCE_SYSTEM,
)
from apps.clinical.patients.models import Patient
from apps.integration.fhir_integration.models import FHIRResource, FHIRResourceMapping
from apps.integration.fhir_integration.resource_identity import identity
from services.disease_risk_engine.algorithm_registry import (
    CLINICAL_VARIABLES,
    ClinicalSourceKind,
    runtime_registry,
)
from services.disease_risk_engine.repository import DiseaseRiskInputRepository
from services.disease_risk_engine.service import (
    RISK_OUTPUT_ORIGIN_NAMESPACE,
    DiseaseRiskAssessmentService,
)


GOLDEN_FIXTURE_KEY = GOLDEN_DEMO_FIXTURE_KEY
GOLDEN_FIXTURE_VERSION = "2026.07.2"
GOLDEN_SOURCE_NAMESPACE = "allcare365:golden-risk:v1"
GOLDEN_PATIENT_MRN = GOLDEN_DEMO_MRN
GOLDEN_PATIENT_FHIR_ID = "golden-risk-patient-v1"
GOLDEN_ENCOUNTER_FHIR_ID = "golden-risk-encounter-v1"
GOLDEN_QUESTIONNAIRE_RESPONSE_FHIR_ID = "golden-risk-questionnaire-v1"
GOLDEN_CONDITION_FHIR_ID = "golden-risk-condition-hypertension-v1"
GOLDEN_PATIENT_FULL_URL = "urn:uuid:1d57a8de-4e6d-46fe-9660-a67b869d1111"
GOLDEN_ENCOUNTER_FULL_URL = "urn:uuid:2d57a8de-4e6d-46fe-9660-a67b869d2222"
GOLDEN_EFFECTIVE_AT = "2026-07-15T09:30:00+08:00"
GOLDEN_EVALUATION_AS_OF = date(2026, 7, 15)

_RUNTIME_REGISTRY = runtime_registry()
EXPECTED_RISK_ALGORITHMS = frozenset(
    metadata.algorithm_id for metadata in _RUNTIME_REGISTRY.runtime_algorithms
)
EXPECTED_EXECUTABLE_RISK_ALGORITHMS = frozenset(
    metadata.algorithm_id
    for metadata in _RUNTIME_REGISTRY.runtime_algorithms
    if metadata.runtime_enabled
)
EXPECTED_GATED_RISK_ALGORITHMS = EXPECTED_RISK_ALGORITHMS.difference(
    EXPECTED_EXECUTABLE_RISK_ALGORITHMS
)
GOLDEN_EXPECTED_RISK_VECTORS = {
    "framingham_diabetes": {"risk_score": None, "applicability": "not_applicable"},
    "chinese_diabetes": {"risk_score": 48},
    "metabolic_syndrome": {"risk_score": 4, "risk_category": "metabolic_syndrome"},
    "bmi": {"risk_score": 28.373702},
    "tyg_index": {"risk_score": 9.09493},
    "homa_ir": {"risk_score": 3.733333},
    "quicki": {"risk_score": 0.31451},
    "hepatic_steatosis_index": {"risk_score": 39.242105},
    "nafld_liver_fat_score": {"risk_score": 1.959524},
    "fatty_liver_index": {"risk_score": 73.765799},
    "fib4": {"risk_score": 1.732406},
    "apri": {"risk_score": 0.431818},
    "rpr": {"risk_score": 0.06},
    "nafld_fibrosis_score": {"risk_score": -0.206686},
    "incident_hepatic_steatosis_model_2": {"risk_score": 0.45001},
    "nafld_cv_risk_score": {"risk_score": -2.4574},
    "cambridge_diabetes_risk": {"risk_score": 0.844618},
    "framingham_cvd_10_lipids": {"risk_score": 0.473648},
    "framingham_cvd_10_bmi": {"risk_score": 0.501516},
    "framingham_hypertension": {"risk_score": 0.585886},
    "dementia_risk_score_thin_60_79": {"risk_score": 0.015339},
    "nomas_global_vascular_risk": {"risk_score": 0.05156},
    "mayo_pulmonary_nodule": {"risk_score": 0.191236},
    "christianson_t2dm_chd_score": {"risk_score": 31.0},
    "gad7": {"risk_score": 4.0},
    "ausdrisk_diabetes": {"risk_score": None, "applicability": "not_applicable"},
    "aha_prevent_cvd_10y": {"risk_score": 0.21592},
    "aha_prevent_ascvd_10y": {"risk_score": 0.138975},
    "aha_prevent_hf_10y": {"risk_score": 0.111181},
    "reynolds_risk_score_women_10y": {"risk_score": None, "applicability": "not_applicable"},
    "reynolds_risk_score_men_10y": {"risk_score": 0.230866},
    "pooled_cohort_ascvd_10y": {"risk_score": 0.326627},
    "cardiometabolic_index": {"risk_score": 2.117647},
    "lipid_accumulation_product": {"risk_score": 57.74835},
    "ggt_platelet_ratio": {"risk_score": 0.5},
    "ipag_copd_questionnaire": {"risk_score": 24.0},
    "mci_to_ad_3y": {"risk_score": 6.0},
    "anu_adri": {"risk_score": -10.0},
    "brock_pancan_pulmonary_nodule": {"risk_score": 0.089709},
    "va_pulmonary_nodule": {"risk_score": 0.079842},
    "caide_dementia_20y": {"risk_score": 5.0},
    "bdsi_dementia_6y": {"risk_score": 3.0},
}
RUNTIME_REQUIRED_SNAPSHOT_FIELDS = frozenset(
    field
    for metadata in _RUNTIME_REGISTRY.runtime_algorithms
    for field in metadata.required_inputs
)

GOLDEN_REQUIRED_SNAPSHOT_FIELDS = RUNTIME_REQUIRED_SNAPSHOT_FIELDS.union(
    {
        "age",
        "sex",
        "body_height",
        "body_weight",
        "bmi",
        "waist_circumference",
        "hip_circumference",
        "waist_hip_ratio",
        "alcohol_drinks_per_week",
        "heart_rate",
        "resting_heart_rate",
        "systolic_bp",
        "diastolic_bp",
        "fasting_glucose",
        "total_cholesterol",
        "hdl_cholesterol",
        "triglycerides",
        "creatinine",
        "egfr",
        "alt_gpt",
        "ast_got",
        "ast_uln",
        "ggt",
        "ggt_uln",
        "ggt_uln",
        "platelet_count",
        "albumin",
        "insulin",
        "rdw",
        "mean_platelet_volume",
        "hba1c",
        "hs_crp",
        "hs_crp",
        "microalbumin_excretion_rate",
        "pulmonary_nodule_diameter",
        "urine_albumin_creatinine_ratio",
        "apoe_e4",
        "family_history_diabetes",
        "anti_hypertensive_drugs",
        "using_lipid_lowering_drugs",
        "has_diabetes",
        "prediabetes",
        "has_hypertension",
        "vegetables_daily",
        "physical_activity_active",
        "is_smoker",
        "former_smoker",
        "chd_history",
        "cvd_history",
        "pvd_history",
        "prescribed_steroids",
        "family_history_diabetes_both",
        "parental_hypertension_count",
        "deprivation_quintile",
        "depression_or_antidepressant",
        "aspirin_use",
        "stroke_tia_history",
        "atrial_fibrillation",
        "race_black",
        "ethnicity_hispanic",
        "moderate_heavy_activity",
        "ever_smoker",
        "extrathoracic_cancer_over_5y",
        "nodule_spiculation",
        "nodule_upper_lobe",
        "diabetes_duration_years",
        *(f"gad7_q{index}" for index in range(1, 8)),
    }
)

DIRECT_FHIR_OBSERVATION_FIELDS = frozenset(
    {
        "body_height",
        "body_weight",
        "bmi",
        "waist_circumference",
        "hip_circumference",
        "alcohol_drinks_per_week",
        "heart_rate",
        "systolic_bp",
        "diastolic_bp",
        "fasting_glucose",
        "total_cholesterol",
        "hdl_cholesterol",
        "triglycerides",
        "creatinine",
        "egfr",
        "alt_gpt",
        "ast_got",
        "ast_uln",
        "ggt",
        "platelet_count",
        "albumin",
        "insulin",
        "urine_albumin_creatinine_ratio",
        "apoe_e4",
        "is_smoker",
        "rdw",
        "mean_platelet_volume",
        "hba1c",
        "microalbumin_excretion_rate",
        "pulmonary_nodule_diameter",
    }
)

QUESTIONNAIRE_SOURCE_FIELDS = frozenset(
    field
    for field in GOLDEN_REQUIRED_SNAPSHOT_FIELDS
    if field in CLINICAL_VARIABLES
    and ClinicalSourceKind.QUESTIONNAIRE_RESPONSE in CLINICAL_VARIABLES[field].source_kinds
    and field not in {"is_smoker", "has_hypertension"}
)

CONDITION_SOURCE_FIELDS = frozenset({"has_hypertension"})


class GoldenPatientError(RuntimeError):
    """Base error for golden-patient seed and verification failures."""


class GoldenPatientSeedError(GoldenPatientError):
    """Raised when the isolated synthetic record cannot be safely seeded."""


class GoldenPatientVerificationError(GoldenPatientError):
    """Raised when any conformance-gate invariant fails."""


@dataclass(frozen=True)
class GoldenPatientSeedResult:
    patient_id: str
    medical_record_number: str
    observation_count: int
    questionnaire_response_count: int
    input_fhir_resource_count: int


@dataclass(frozen=True)
class GoldenPatientVerificationResult:
    patient_id: str
    risk_run_id: str
    algorithm_count: int
    risk_assessment_count: int
    result_observation_count: int
    provenance_count: int
    basis_reference_count: int


def _category(code: str, display: str) -> List[Dict[str, Any]]:
    return [
        {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                    "code": code,
                    "display": display,
                }
            ]
        }
    ]


def _quantity_observation(
    resource_id: str,
    code: str,
    display: str,
    value: float,
    unit: str,
    unit_code: str,
    category_code: str = "laboratory",
    category_display: str = "Laboratory",
) -> Dict[str, Any]:
    return {
        "resourceType": "Observation",
        "id": resource_id,
        "meta": {
            "tag": [
                {
                    "system": "https://allcare365.local/fhir/CodeSystem/conformance-data",
                    "code": "golden-patient",
                }
            ]
        },
        "status": "final",
        "category": _category(category_code, category_display),
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": code,
                    "display": display,
                }
            ],
            "text": display,
        },
        "subject": {"reference": GOLDEN_PATIENT_FULL_URL},
        "encounter": {"reference": GOLDEN_ENCOUNTER_FULL_URL},
        "effectiveDateTime": GOLDEN_EFFECTIVE_AT,
        "valueQuantity": {
            "value": value,
            "unit": unit,
            "system": "http://unitsofmeasure.org",
            "code": unit_code,
        },
    }


def _blood_pressure_observation() -> Dict[str, Any]:
    return {
        "resourceType": "Observation",
        "id": "golden-risk-obs-blood-pressure",
        "meta": {
            "tag": [
                {
                    "system": "https://allcare365.local/fhir/CodeSystem/conformance-data",
                    "code": "golden-patient",
                }
            ]
        },
        "status": "final",
        "category": _category("vital-signs", "Vital Signs"),
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "85354-9",
                    "display": "Blood pressure panel with all children optional",
                }
            ]
        },
        "subject": {"reference": GOLDEN_PATIENT_FULL_URL},
        "encounter": {"reference": GOLDEN_ENCOUNTER_FULL_URL},
        "effectiveDateTime": GOLDEN_EFFECTIVE_AT,
        "component": [
            {
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "8480-6",
                            "display": "Systolic blood pressure",
                        }
                    ]
                },
                "valueQuantity": {
                    "value": 138,
                    "unit": "mmHg",
                    "system": "http://unitsofmeasure.org",
                    "code": "mm[Hg]",
                },
            },
            {
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "8462-4",
                            "display": "Diastolic blood pressure",
                        }
                    ]
                },
                "valueQuantity": {
                    "value": 86,
                    "unit": "mmHg",
                    "system": "http://unitsofmeasure.org",
                    "code": "mm[Hg]",
                },
            },
        ],
    }


def _smoking_status_observation() -> Dict[str, Any]:
    return {
        "resourceType": "Observation",
        "id": "golden-risk-obs-smoking-status",
        "meta": {
            "tag": [
                {
                    "system": "https://allcare365.local/fhir/CodeSystem/conformance-data",
                    "code": "golden-patient",
                }
            ]
        },
        "status": "final",
        "category": _category("social-history", "Social History"),
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "72166-2",
                    "display": "Tobacco smoking status",
                }
            ]
        },
        "subject": {"reference": GOLDEN_PATIENT_FULL_URL},
        "encounter": {"reference": GOLDEN_ENCOUNTER_FULL_URL},
        "effectiveDateTime": GOLDEN_EFFECTIVE_AT,
        "valueCodeableConcept": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "266919005",
                    "display": "Never smoked tobacco",
                }
            ],
            "text": "Never smoker",
        },
    }


def _questionnaire_response() -> Dict[str, Any]:
    answers = {
        "family_history_diabetes": True,
        "anti_hypertensive_drugs": True,
        "using_lipid_lowering_drugs": False,
        "statin_use": False,
        "has_diabetes": True,
        "prediabetes": False,
        "metabolic_syndrome": True,
        "has_hypertension": True,
        "vegetables_daily": True,
        "physical_activity_active": True,
        "moderate_alcohol": True,
        "heavy_alcohol": False,
        "is_smoker": False,
        "former_smoker": False,
        "chd_history": False,
        "cvd_history": False,
        "pvd_history": False,
        "prescribed_steroids": False,
        "family_history_diabetes_both": False,
        "parental_hypertension_count": 1,
        "deprivation_quintile": 3,
        "depression_or_antidepressant": False,
        "aspirin_use": True,
        "stroke_tia_history": False,
        "atrial_fibrillation": False,
        "race_black": False,
        "ethnicity_hispanic": False,
        "moderate_heavy_activity": True,
        "ever_smoker": False,
        "extrathoracic_cancer_over_5y": False,
        "nodule_spiculation": True,
        "nodule_upper_lobe": True,
        "education_high_school_or_below": True,
        "ever_high_blood_glucose": True,
        "ausdrisk_indigenous_or_pacific": False,
        "ausdrisk_high_risk_birth_region": False,
        "ausdrisk_lower_waist_threshold_group": True,
        "ascvd_history": False,
        "heart_failure_history": False,
        "parental_mi_before_60": True,
        "family_history_lung_cancer": True,
        "has_emphysema": False,
        "weather_affected_cough": True,
        "sputum_without_cold": True,
        "morning_sputum": True,
        "wheeze_sometimes_or_often": True,
        "allergy_history": False,
        "has_amnestic_mci": True,
        "stubborn_or_resistive": False,
        "upset_when_separated_from_caregiver": False,
        "difficulty_shopping_alone": True,
        "forgets_appointments": True,
        "depressive_symptoms": False,
        "needs_help_money_or_medications": False,
        "high_cholesterol": True,
        "traumatic_brain_injury": False,
        "pesticide_exposure": False,
        "periodical_daily_cough": True,
        "diabetes_duration_years": 8,
        "education_years": 12,
        "pack_years": 18,
        "cigarettes_per_day": 10,
        "years_since_quitting": 0,
        "indoor_smoke_exposure_hours": 1,
        "fish_servings_per_week": 3,
        "mean_words_recalled": 5.5,
        "orientation_correct": 7,
        "clock_drawing_score": 4,
        "nodule_count": 2,
        "pce_race": "white",
        "smoking_status": "former",
        "alcohol_category": "light_moderate",
        "social_engagement_level": "medium_high",
        "physical_activity_level": "medium",
        "cognitive_activity_level": "high",
        "nodule_type": "solid",
        "gad7_q1": 1,
        "gad7_q2": 0,
        "gad7_q3": 1,
        "gad7_q4": 1,
        "gad7_q5": 0,
        "gad7_q6": 1,
        "gad7_q7": 0,
    }
    return {
        "resourceType": "QuestionnaireResponse",
        "id": GOLDEN_QUESTIONNAIRE_RESPONSE_FHIR_ID,
        "meta": {
            "tag": [
                {
                    "system": "https://allcare365.local/fhir/CodeSystem/conformance-data",
                    "code": "golden-patient",
                }
            ]
        },
        "questionnaire": "Questionnaire/allcare365-risk-intake-v1",
        "status": "completed",
        "subject": {"reference": GOLDEN_PATIENT_FULL_URL},
        "encounter": {"reference": GOLDEN_ENCOUNTER_FULL_URL},
        "authored": GOLDEN_EFFECTIVE_AT,
        "item": [
            {
                "linkId": link_id,
                "text": link_id.replace("_", " "),
                "answer": [
                    {"valueBoolean": value}
                    if isinstance(value, bool)
                    else {"valueInteger": value}
                    if isinstance(value, int)
                    else {"valueDecimal": value}
                    if isinstance(value, float)
                    else {"valueString": value}
                ],
            }
            for link_id, value in answers.items()
        ],
    }


def build_golden_patient_bundle() -> Dict[str, Any]:
    """Build the versioned synthetic FHIR R4 collection used by the gate."""

    patient = {
        "resourceType": "Patient",
        "id": GOLDEN_PATIENT_FHIR_ID,
        "meta": {
            "tag": [
                {
                    "system": "https://allcare365.local/fhir/CodeSystem/conformance-data",
                    "code": "golden-patient",
                    "display": "Synthetic golden conformance patient - not clinical data",
                },
                {
                    "system": "https://allcare365.local/fhir/CodeSystem/fixture-version",
                    "code": GOLDEN_FIXTURE_VERSION,
                },
            ]
        },
        "identifier": [
            {
                "use": "usual",
                "system": "https://allcare365.local/identifier/golden-conformance-mrn",
                "value": GOLDEN_PATIENT_MRN,
            }
        ],
        "active": True,
        "name": [{"use": "official", "family": "Conformance", "given": ["Golden"]}],
        "gender": "male",
        "birthDate": "1961-02-14",
        "communication": [
            {
                "language": {
                    "coding": [
                        {
                            "system": "urn:ietf:bcp:47",
                            "code": "zh-TW",
                            "display": "Chinese (Taiwan)",
                        }
                    ]
                },
                "preferred": True,
            }
        ],
    }
    encounter = {
        "resourceType": "Encounter",
        "id": GOLDEN_ENCOUNTER_FHIR_ID,
        "meta": {
            "tag": [
                {
                    "system": "https://allcare365.local/fhir/CodeSystem/conformance-data",
                    "code": "golden-patient",
                }
            ]
        },
        "identifier": [
            {
                "system": "https://allcare365.local/identifier/encounter",
                "value": "GOLDEN-ENC-2026-001",
            }
        ],
        "status": "finished",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "AMB",
            "display": "ambulatory",
        },
        "type": [
            {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "185349003",
                        "display": "Encounter for check up",
                    }
                ]
            }
        ],
        "subject": {"reference": GOLDEN_PATIENT_FULL_URL},
        "period": {
            "start": "2026-07-15T09:00:00+08:00",
            "end": "2026-07-15T10:00:00+08:00",
        },
        "reasonCode": [{"text": "Golden-patient whole-stack conformance check"}],
    }

    observations = [
        _quantity_observation(
            "golden-risk-obs-height",
            "8302-2",
            "Body height",
            170,
            "cm",
            "cm",
            "vital-signs",
            "Vital Signs",
        ),
        _quantity_observation(
            "golden-risk-obs-weight",
            "29463-7",
            "Body weight",
            82,
            "kg",
            "kg",
            "vital-signs",
            "Vital Signs",
        ),
        _quantity_observation(
            "golden-risk-obs-bmi",
            "39156-5",
            "Body mass index",
            28.4,
            "kg/m2",
            "kg/m2",
            "vital-signs",
            "Vital Signs",
        ),
        _quantity_observation(
            "golden-risk-obs-waist",
            "8280-0",
            "Waist circumference",
            96,
            "cm",
            "cm",
            "vital-signs",
            "Vital Signs",
        ),
        _quantity_observation(
            "golden-risk-obs-hip",
            "56074-8",
            "Hip circumference",
            102,
            "cm",
            "cm",
            "vital-signs",
            "Vital Signs",
        ),
        _quantity_observation(
            "golden-risk-obs-alcohol-weekly",
            "74013-4",
            "Alcoholic drinks per week",
            4,
            "drinks/week",
            "1/wk",
            "social-history",
            "Social History",
        ),
        _quantity_observation(
            "golden-risk-obs-heart-rate",
            "8867-4",
            "Heart rate",
            72,
            "beats/minute",
            "/min",
            "vital-signs",
            "Vital Signs",
        ),
        _blood_pressure_observation(),
        _quantity_observation("golden-risk-obs-glucose", "1558-6", "Fasting glucose", 108, "mg/dL", "mg/dL"),
        _quantity_observation("golden-risk-obs-total-cholesterol", "2093-3", "Total cholesterol", 210, "mg/dL", "mg/dL"),
        _quantity_observation("golden-risk-obs-hdl", "2085-9", "HDL cholesterol", 44, "mg/dL", "mg/dL"),
        _quantity_observation("golden-risk-obs-triglycerides", "2571-8", "Triglycerides", 165, "mg/dL", "mg/dL"),
        _quantity_observation("golden-risk-obs-creatinine", "2160-0", "Creatinine", 1.1, "mg/dL", "mg/dL"),
        _quantity_observation(
            "golden-risk-obs-egfr",
            "33914-3",
            "Glomerular filtration rate/1.73 sq M predicted",
            83,
            "mL/min/1.73m2",
            "mL/min/{1.73_m2}",
        ),
        _quantity_observation("golden-risk-obs-alt", "1742-6", "Alanine aminotransferase", 42, "U/L", "U/L"),
        _quantity_observation("golden-risk-obs-ast", "1920-8", "Aspartate aminotransferase", 38, "U/L", "U/L"),
        _quantity_observation("golden-risk-obs-ast-uln", "1916-6", "AST upper limit of normal", 40, "U/L", "U/L"),
        _quantity_observation("golden-risk-obs-ggt", "2324-2", "Gamma glutamyl transferase", 55, "U/L", "U/L"),
        _quantity_observation("golden-risk-obs-ggt-uln", "allcare365-ggt-uln", "GGT upper limit of normal", 50, "U/L", "U/L"),
        _quantity_observation("golden-risk-obs-platelets", "777-3", "Platelet count", 220, "10*3/uL", "10*3/uL"),
        _quantity_observation("golden-risk-obs-albumin", "1751-7", "Albumin", 4.2, "g/dL", "g/dL"),
        _quantity_observation("golden-risk-obs-insulin", "20448-7", "Insulin", 14, "uIU/mL", "[uIU]/mL"),
        _quantity_observation("golden-risk-obs-rdw", "788-0", "Red cell distribution width", 13.2, "%", "%"),
        _quantity_observation("golden-risk-obs-mpv", "32623-1", "Mean platelet volume", 10.2, "fL", "fL"),
        _quantity_observation("golden-risk-obs-hba1c", "4548-4", "Hemoglobin A1c", 7.2, "%", "%"),
        _quantity_observation("golden-risk-obs-hs-crp", "30522-7", "High sensitivity C-reactive protein", 2.2, "mg/L", "mg/L"),
        _quantity_observation("golden-risk-obs-microalbumin-rate", "14956-7", "Urine albumin excretion rate", 20, "ug/min", "ug/min"),
        _quantity_observation("golden-risk-obs-nodule-diameter", "allcare365-nodule-diameter", "Pulmonary nodule diameter", 8, "mm", "mm", "imaging", "Imaging"),
        _quantity_observation(
            "golden-risk-obs-uacr",
            "9318-7",
            "Albumin/Creatinine ratio in urine",
            18,
            "mg/g",
            "mg/g",
        ),
        _quantity_observation("golden-risk-obs-apoe-e4", "79713-2", "APOE e4 allele count", 1, "allele", "{allele}"),
        _smoking_status_observation(),
    ]

    condition = {
        "resourceType": "Condition",
        "id": GOLDEN_CONDITION_FHIR_ID,
        "meta": {
            "tag": [
                {
                    "system": "https://allcare365.local/fhir/CodeSystem/conformance-data",
                    "code": "golden-patient",
                }
            ]
        },
        "clinicalStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": "active",
                }
            ]
        },
        "verificationStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                    "code": "confirmed",
                }
            ]
        },
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                        "code": "problem-list-item",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "38341003",
                    "display": "Essential hypertension",
                }
            ],
            "text": "Essential hypertension",
        },
        "subject": {"reference": GOLDEN_PATIENT_FULL_URL},
        "encounter": {"reference": GOLDEN_ENCOUNTER_FULL_URL},
        "onsetDateTime": "2020-06-01T00:00:00+08:00",
        "recordedDate": GOLDEN_EFFECTIVE_AT,
    }

    resources = [patient, encounter, *observations, condition, _questionnaire_response()]
    return {
        "resourceType": "Bundle",
        "id": "golden-risk-conformance-bundle-v1",
        "meta": {
            "tag": [
                {
                    "system": "https://allcare365.local/fhir/CodeSystem/conformance-data",
                    "code": "golden-patient",
                }
            ]
        },
        "type": "collection",
        "timestamp": "2026-07-15T10:00:00+08:00",
        "entry": [
            {
                "fullUrl": (
                    GOLDEN_PATIENT_FULL_URL
                    if resource["resourceType"] == "Patient"
                    else GOLDEN_ENCOUNTER_FULL_URL
                    if resource["resourceType"] == "Encounter"
                    else f"https://allcare365.local/fhir/{resource['resourceType']}/{resource['id']}"
                ),
                "resource": resource,
            }
            for resource in resources
        ],
    }


def golden_input_resource_keys(bundle: Dict[str, Any] = None) -> Set[Tuple[str, str]]:
    current_bundle = bundle or build_golden_patient_bundle()
    return {
        (entry["resource"]["resourceType"], entry["resource"]["id"])
        for entry in current_bundle["entry"]
    }


class GoldenPatientSeeder:
    """Idempotently replace only the reserved synthetic patient's inputs."""

    def __init__(self, ingestion_service: HealthScreeningIngestionService = None):
        self.ingestion_service = ingestion_service or HealthScreeningIngestionService()

    @transaction.atomic
    def seed(self) -> GoldenPatientSeedResult:
        bundle = build_golden_patient_bundle()
        self._validate_bundle(bundle)

        existing_matches = list(
            Patient.objects.filter(medical_record_number=GOLDEN_PATIENT_MRN)[:2]
        )
        if len(existing_matches) > 1:
            raise GoldenPatientSeedError(
                f"Reserved MRN {GOLDEN_PATIENT_MRN} resolves to multiple patients; refusing to select one."
            )
        existing = existing_matches[0] if existing_matches else None
        if existing:
            marker = (existing.metadata_json or {}).get("conformance_fixture")
            if marker != GOLDEN_FIXTURE_KEY:
                raise GoldenPatientSeedError(
                    f"Reserved MRN {GOLDEN_PATIENT_MRN} belongs to an unmarked patient; refusing to overwrite it."
                )
        self._assert_fixture_fhir_identity_available(existing, bundle)
        if existing:
            self._reset_fixture_patient_inputs(existing)

        import_summary = self.ingestion_service.import_fhir(
            bundle,
            source_namespace=GOLDEN_SOURCE_NAMESPACE,
        )
        if import_summary.get("error_count"):
            details = "; ".join(import_summary.get("errors") or [])
            raise GoldenPatientSeedError(f"FHIR ingestion failed: {details}")

        patient_matches = list(
            Patient.objects.filter(medical_record_number=GOLDEN_PATIENT_MRN)[:2]
        )
        if len(patient_matches) != 1:
            raise GoldenPatientSeedError(
                "FHIR ingestion did not resolve the reserved golden MRN to exactly one patient."
            )
        patient = patient_matches[0]

        metadata = dict(patient.metadata_json or {})
        metadata.update(
            {
                "conformance_fixture": GOLDEN_FIXTURE_KEY,
                "conformance_fixture_version": GOLDEN_FIXTURE_VERSION,
                "synthetic": True,
                "clinical_use_prohibited": True,
                "fhir_patient_id": GOLDEN_PATIENT_FHIR_ID,
            }
        )
        patient.source_system = GOLDEN_DEMO_SOURCE_SYSTEM
        patient.source_record_id = GOLDEN_PATIENT_FHIR_ID
        patient.last_imported_at = timezone.now()
        patient.metadata_json = metadata
        patient.save(
            update_fields=[
                "source_system",
                "source_record_id",
                "last_imported_at",
                "metadata_json",
                "updated_at",
            ]
        )

        expected_keys = golden_input_resource_keys(bundle)
        persisted_resource_count = sum(
            FHIRResource.objects.filter(resource_type=resource_type, resource_id=resource_id).exists()
            for resource_type, resource_id in expected_keys
        )
        if persisted_resource_count != len(expected_keys):
            raise GoldenPatientSeedError(
                f"Only {persisted_resource_count}/{len(expected_keys)} input FHIR resources were persisted."
            )

        return GoldenPatientSeedResult(
            patient_id=str(patient.id),
            medical_record_number=patient.medical_record_number,
            observation_count=Observation.objects.filter(patient=patient).count(),
            questionnaire_response_count=QuestionnaireResponse.objects.filter(patient=patient).count(),
            input_fhir_resource_count=persisted_resource_count,
        )

    def _validate_bundle(self, bundle: Dict[str, Any]) -> None:
        try:
            FHIRBundle(bundle, strict=True)
        except Exception as exc:
            raise GoldenPatientSeedError(f"Golden-patient FHIR R4 Bundle is invalid: {exc}") from exc

    def _assert_fixture_fhir_identity_available(
        self,
        existing: Optional[Patient],
        bundle: Dict[str, Any],
    ) -> None:
        identity_matches = list(
            Patient.objects.filter(metadata_json__fhir_patient_id=GOLDEN_PATIENT_FHIR_ID)[:2]
        )
        if len(identity_matches) > 1 or (
            identity_matches
            and (existing is None or identity_matches[0].id != existing.id)
        ):
            raise GoldenPatientSeedError(
                f"FHIR Patient/{GOLDEN_PATIENT_FHIR_ID} is already owned by another patient."
            )

        for resource_type, resource_id in golden_input_resource_keys(bundle):
            mappings = list(
                FHIRResourceMapping.objects.filter(
                    fhir_resource_type=resource_type,
                    fhir_resource_id=resource_id,
                )[:2]
            )
            if len(mappings) > 1:
                raise GoldenPatientSeedError(
                    f"FHIR {resource_type}/{resource_id} has multiple owners."
                )
            persisted = FHIRResource.objects.filter(
                resource_type=resource_type,
                resource_id=resource_id,
            ).first()
            if persisted is None:
                if mappings:
                    raise GoldenPatientSeedError(
                        f"FHIR {resource_type}/{resource_id} has a mapping without a resource."
                    )
                continue
            if persisted.origin_namespace != GOLDEN_SOURCE_NAMESPACE:
                raise GoldenPatientSeedError(
                    f"FHIR {resource_type}/{resource_id} belongs to source namespace "
                    f"{persisted.origin_namespace}, not {GOLDEN_SOURCE_NAMESPACE}."
                )
            if len(mappings) != 1:
                raise GoldenPatientSeedError(
                    f"FHIR {resource_type}/{resource_id} exists without exactly one ownership mapping."
                )
            if existing is None or mappings[0].patient_id != existing.id:
                raise GoldenPatientSeedError(
                    f"FHIR {resource_type}/{resource_id} is already owned by another patient."
                )

    def _reset_fixture_patient_inputs(self, patient: Patient) -> None:
        # This patient is reserved for conformance only.  Resetting all of its
        # source inputs makes create-only ingestion deterministic while never
        # touching another patient's records or application runtime behavior.
        Observation.objects.filter(patient=patient).delete()
        QuestionnaireResponse.objects.filter(patient=patient).delete()
        Encounter.objects.filter(patient=patient).delete()
        HealthScreening.objects.filter(patient=patient).delete()
        Problem.objects.filter(patient=patient).delete()


class GoldenPatientVerifier:
    """Run the persisted record through repository, risk, and FHIR outputs."""

    def __init__(
        self,
        repository: DiseaseRiskInputRepository = None,
        risk_service: DiseaseRiskAssessmentService = None,
    ):
        self.repository = repository or DiseaseRiskInputRepository()
        self.risk_service = risk_service or DiseaseRiskAssessmentService(repository=self.repository)

    @transaction.atomic
    def verify(self, patient_id: str) -> GoldenPatientVerificationResult:
        patient = self.repository.get_patient(patient_id)
        if patient is None:
            raise GoldenPatientVerificationError(f"Golden patient not found: {patient_id}")
        if (patient.metadata_json or {}).get("conformance_fixture") != GOLDEN_FIXTURE_KEY:
            raise GoldenPatientVerificationError("Patient is not marked as the golden conformance fixture.")

        self._verify_input_fhir_resources(patient)
        snapshot = self.repository.build_snapshot(
            patient,
            evaluation_as_of=GOLDEN_EVALUATION_AS_OF,
        )
        self._verify_snapshot(snapshot.data, snapshot.sources)

        response = self.risk_service.calculate_for_patient(
            str(patient.id),
            evaluation_as_of=GOLDEN_EVALUATION_AS_OF,
        )
        if response.get("error"):
            raise GoldenPatientVerificationError(str(response["error"]))
        results = response.get("disease_risk_results") or []
        execution_summary = response.get("execution_summary") or {}
        if (
            execution_summary.get("executable_models")
            != len(EXPECTED_EXECUTABLE_RISK_ALGORITHMS)
            or execution_summary.get("insufficient_data_models") != 0
            or execution_summary.get("resolved_models")
            != len(EXPECTED_EXECUTABLE_RISK_ALGORITHMS)
            or execution_summary.get("all_executable_models_resolved") is not True
            or (
                set(execution_summary.get("calculated_algorithm_ids") or ())
                | set(execution_summary.get("not_applicable_algorithm_ids") or ())
            )
            != EXPECTED_EXECUTABLE_RISK_ALGORITHMS
        ):
            raise GoldenPatientVerificationError(
                f"Golden patient did not calculate every executable model: {execution_summary}"
            )
        algorithms = {result.get("algorithm") for result in results}
        if len(results) != len(EXPECTED_RISK_ALGORITHMS) or algorithms != EXPECTED_RISK_ALGORITHMS:
            raise GoldenPatientVerificationError(
                f"Expected algorithms {sorted(EXPECTED_RISK_ALGORITHMS)}, received {sorted(algorithms)}."
            )

        invalid_results = [
            result.get("algorithm")
            for result in results
            if result.get("algorithm") in EXPECTED_EXECUTABLE_RISK_ALGORITHMS
            and (
                result.get("missing_data")
                or result.get("governance_status") != "runtime_approved"
                or (
                    result.get("applicability") == "applicable"
                    and result.get("risk_score") is None
                )
                or (
                    result.get("applicability") != "applicable"
                    and result.get("risk_score") is not None
                )
            )
        ]
        if invalid_results:
            raise GoldenPatientVerificationError(
                f"Algorithms did not produce complete resolved results: {sorted(invalid_results)}"
            )
        invalid_gates = [
            result.get("algorithm")
            for result in results
            if result.get("algorithm") in EXPECTED_GATED_RISK_ALGORITHMS
            and (
                result.get("risk_score") is not None
                or result.get("applicability") != "clinical_review_required"
                or result.get("governance_status") != "clinical_review_required"
                or (result.get("evidence") or {}).get("calculation_executed") is not False
            )
        ]
        if invalid_gates:
            raise GoldenPatientVerificationError(
                "Governance-gated algorithms were executed or misrepresented: "
                f"{sorted(invalid_gates)}"
            )
        result_by_algorithm = {result["algorithm"]: result for result in results}
        vector_mismatches = []
        for algorithm_id, expected in GOLDEN_EXPECTED_RISK_VECTORS.items():
            actual = result_by_algorithm[algorithm_id]
            mismatch = False
            for key, value in expected.items():
                actual_value = actual.get(key)
                if key == "risk_score" and value is not None:
                    mismatch = mismatch or not math.isclose(
                        float(actual_value), float(value), rel_tol=0, abs_tol=1e-6
                    )
                else:
                    mismatch = mismatch or actual_value != value
            if mismatch:
                vector_mismatches.append(
                    {
                        "algorithm": algorithm_id,
                        "expected": expected,
                        "actual": {key: actual.get(key) for key in expected},
                    }
                )
        if vector_mismatches:
            raise GoldenPatientVerificationError(
                f"Golden risk vectors changed: {vector_mismatches}"
            )

        result_ids = [result["id"] for result in results]
        mappings = list(
            FHIRResourceMapping.objects.filter(
                patient=patient,
                local_table="ai_analysis_results",
                local_id__in=result_ids,
                fhir_resource_type__in=("RiskAssessment", "Observation"),
            ).select_related("fhir_resource_ref")
        )
        if len(mappings) != len(EXPECTED_RISK_ALGORITHMS):
            raise GoldenPatientVerificationError(
                f"Expected {len(EXPECTED_RISK_ALGORITHMS)} FHIR result mappings, received {len(mappings)}."
            )

        provenance_count = 0
        basis_references: Set[str] = set()
        for mapping in mappings:
            risk_json = mapping.fhir_json or (
                mapping.fhir_resource_ref.resource_data if mapping.fhir_resource_ref else {}
            )
            if (
                mapping.fhir_resource_ref is None
                or mapping.fhir_resource_ref.origin_namespace != RISK_OUTPUT_ORIGIN_NAMESPACE
            ):
                raise GoldenPatientVerificationError(
                    f"{mapping.fhir_resource_type}/{mapping.fhir_resource_id} has the wrong origin namespace."
                )
            try:
                model_class = (
                    FHIRObservation
                    if mapping.fhir_resource_type == "Observation"
                    else FHIRRiskAssessment
                )
                model_class(risk_json, strict=True)
            except Exception as exc:
                raise GoldenPatientVerificationError(
                    f"Invalid {mapping.fhir_resource_type}/{mapping.fhir_resource_id}: {exc}"
                ) from exc
            expected_subject = f"Patient/{identity.patient_id(patient)}"
            if (risk_json.get("subject") or {}).get("reference") != expected_subject:
                raise GoldenPatientVerificationError(
                    f"{mapping.fhir_resource_type}/{mapping.fhir_resource_id} has the wrong subject."
                )
            algorithm_id = (mapping.metadata_json or {}).get("algorithm")
            expected_type = _RUNTIME_REGISTRY.get_runtime(algorithm_id).output_resource.value
            if mapping.fhir_resource_type != expected_type:
                raise GoldenPatientVerificationError(
                    f"{algorithm_id} mapped to {mapping.fhir_resource_type}, expected {expected_type}."
                )
            expected_status = "final"
            if risk_json.get("status") != expected_status:
                raise GoldenPatientVerificationError(
                    f"{mapping.fhir_resource_type}/{mapping.fhir_resource_id} has status "
                    f"{risk_json.get('status')!r}; expected {expected_status!r}."
                )

            current_basis = {
                item.get("reference")
                for item in (
                    risk_json.get("derivedFrom")
                    if mapping.fhir_resource_type == "Observation"
                    else risk_json.get("basis")
                ) or []
                if isinstance(item, dict) and item.get("reference")
            }
            metadata = _RUNTIME_REGISTRY.get_runtime(algorithm_id)
            expected_basis = set()
            if metadata is not None:
                for field in metadata.required_inputs:
                    field_references = self._source_references(snapshot.sources.get(field))
                    if not field_references:
                        raise GoldenPatientVerificationError(
                            f"{algorithm_id}.{field} has no traceable FHIR source reference."
                        )
                    expected_basis.update(field_references)
            if current_basis != expected_basis:
                raise GoldenPatientVerificationError(
                    f"{mapping.fhir_resource_type}/{mapping.fhir_resource_id} basis does not match its "
                    "declared input contract."
                )
            for reference in current_basis:
                self._verify_reference_is_persisted(reference)
            basis_references.update(current_basis)

            provenance_id = (mapping.metadata_json or {}).get("provenance_resource_id")
            provenance = FHIRResource.objects.filter(
                resource_type="Provenance",
                resource_id=provenance_id,
            ).first()
            if provenance is None:
                raise GoldenPatientVerificationError(
                    f"Missing Provenance for {mapping.fhir_resource_type}/{mapping.fhir_resource_id}."
                )
            if provenance.origin_namespace != RISK_OUTPUT_ORIGIN_NAMESPACE:
                raise GoldenPatientVerificationError(
                    f"Provenance/{provenance_id} has the wrong origin namespace."
                )
            try:
                FHIRProvenance(provenance.resource_data, strict=True)
            except Exception as exc:
                raise GoldenPatientVerificationError(
                    f"Invalid Provenance/{provenance_id}: {exc}"
                ) from exc
            targets = {
                item.get("reference")
                for item in provenance.resource_data.get("target") or []
                if isinstance(item, dict)
            }
            expected_target = f"{mapping.fhir_resource_type}/{mapping.fhir_resource_id}"
            if expected_target not in targets:
                raise GoldenPatientVerificationError(
                    f"Provenance/{provenance_id} does not target {expected_target}."
                )
            provenance_count += 1

        if not basis_references:
            raise GoldenPatientVerificationError("No FHIR result basis references were generated.")

        return GoldenPatientVerificationResult(
            patient_id=str(patient.id),
            risk_run_id=str(response["risk_run_id"]),
            algorithm_count=len(results),
            risk_assessment_count=sum(
                mapping.fhir_resource_type == "RiskAssessment" for mapping in mappings
            ),
            result_observation_count=sum(
                mapping.fhir_resource_type == "Observation" for mapping in mappings
            ),
            provenance_count=provenance_count,
            basis_reference_count=len(basis_references),
        )

    def _source_references(self, source: Any) -> Set[str]:
        references: Set[str] = set()
        if isinstance(source, dict):
            direct = source.get("fhir_reference")
            if direct:
                references.add(str(direct))
            references.update(
                str(item)
                for item in source.get("fhir_references") or []
                if item
            )
            for value in source.values():
                references.update(self._source_references(value))
        elif isinstance(source, list):
            for value in source:
                references.update(self._source_references(value))
        return references

    def _verify_input_fhir_resources(self, patient: Patient) -> None:
        expected_keys = golden_input_resource_keys()
        model_by_resource_type = {
            "Patient": Patient,
            "Encounter": Encounter,
            "Observation": Observation,
            "Condition": Problem,
            "QuestionnaireResponse": QuestionnaireResponse,
        }
        verified_mapping_ids = set()
        failures = []
        for resource_type, resource_id in sorted(expected_keys):
            resource = FHIRResource.objects.filter(
                resource_type=resource_type,
                resource_id=resource_id,
            ).first()
            if resource is None:
                failures.append(f"{resource_type}/{resource_id}: resource missing")
                continue
            if resource.origin_namespace != GOLDEN_SOURCE_NAMESPACE:
                failures.append(
                    f"{resource_type}/{resource_id}: wrong source namespace"
                )
            mappings = list(
                FHIRResourceMapping.objects.filter(
                    fhir_resource_type=resource_type,
                    fhir_resource_id=resource_id,
                ).select_related("fhir_resource_ref")[:2]
            )
            if len(mappings) != 1:
                failures.append(
                    f"{resource_type}/{resource_id}: expected one mapping, received {len(mappings)}"
                )
                continue
            mapping = mappings[0]
            expected_model = model_by_resource_type[resource_type]
            if mapping.patient_id != patient.id:
                failures.append(f"{resource_type}/{resource_id}: wrong patient")
            if mapping.local_table != expected_model._meta.db_table:
                failures.append(f"{resource_type}/{resource_id}: wrong local table")
                continue
            local_object = expected_model.objects.filter(pk=mapping.local_id).first()
            if local_object is None:
                failures.append(f"{resource_type}/{resource_id}: local row missing")
                continue
            if resource_type != "Patient" and local_object.patient_id != patient.id:
                failures.append(f"{resource_type}/{resource_id}: local row belongs to another patient")
            if resource_type == "Patient" and local_object.id != patient.id:
                failures.append(f"{resource_type}/{resource_id}: mapped patient row is incorrect")
            if mapping.fhir_resource_ref_id != resource.id:
                failures.append(f"{resource_type}/{resource_id}: wrong FHIRResource link")
            if mapping.fhir_json != resource.resource_data:
                failures.append(f"{resource_type}/{resource_id}: mapping JSON differs from source")
            if (mapping.metadata_json or {}).get("source_namespace") != GOLDEN_SOURCE_NAMESPACE:
                failures.append(f"{resource_type}/{resource_id}: mapping source namespace differs")
            if mapping.sync_status != "synced" or mapping.last_synced_at is None:
                failures.append(f"{resource_type}/{resource_id}: mapping is not synced")
            if resource_type == "Patient" and (
                (local_object.metadata_json or {}).get("fhir_patient_id") != resource_id
                or local_object.source_record_id != resource_id
            ):
                failures.append(f"{resource_type}/{resource_id}: patient source identity missing")
            if resource_type == "Encounter" and (
                (local_object.metadata_json or {}).get("fhir_encounter_id") != resource_id
            ):
                failures.append(f"{resource_type}/{resource_id}: encounter source identity missing")
            if resource_type == "Observation" and (
                (local_object.source_payload_json or {}).get("id") != resource_id
            ):
                failures.append(f"{resource_type}/{resource_id}: observation source identity missing")
            if resource_type == "QuestionnaireResponse" and (
                (local_object.metadata_json or {}).get("fhir_resource_id") != resource_id
            ):
                failures.append(f"{resource_type}/{resource_id}: response source identity missing")
            verified_mapping_ids.add(mapping.id)

        if len(verified_mapping_ids) != len(expected_keys):
            failures.append(
                f"mapping coverage {len(verified_mapping_ids)}/{len(expected_keys)}"
            )
        if failures:
            raise GoldenPatientVerificationError(
                f"Golden input FHIR mapping verification failed: {'; '.join(failures)}"
            )

    def _verify_snapshot(self, data: Dict[str, Any], sources: Dict[str, Any]) -> None:
        missing = sorted(
            field
            for field in GOLDEN_REQUIRED_SNAPSHOT_FIELDS
            if field not in data or data.get(field) in (None, "")
        )
        if missing:
            raise GoldenPatientVerificationError(
                f"Repository snapshot is missing required golden fields: {', '.join(missing)}"
            )

        for field in DIRECT_FHIR_OBSERVATION_FIELDS:
            source = sources.get(field) or {}
            if source.get("table") != "observations" or not source.get("fhir_reference"):
                raise GoldenPatientVerificationError(
                    f"Snapshot field {field} is not traceable to a persisted FHIR Observation."
                )
            self._verify_reference_is_persisted(source["fhir_reference"])

        for field in QUESTIONNAIRE_SOURCE_FIELDS:
            source = sources.get(field) or {}
            if source.get("table") != "questionnaire_responses" or not source.get("fhir_reference"):
                raise GoldenPatientVerificationError(
                    f"Snapshot field {field} is not mapped from QuestionnaireResponse."
                )
            self._verify_reference_is_persisted(source["fhir_reference"])

        for field in CONDITION_SOURCE_FIELDS:
            source = sources.get(field) or {}
            references = source.get("fhir_references") or []
            if source.get("table") != "health_screening_problem" or not references:
                raise GoldenPatientVerificationError(
                    f"Snapshot field {field} is not traceable to a persisted FHIR Condition."
                )
            for reference in references:
                self._verify_reference_is_persisted(reference)

        ratio_source = sources.get("waist_hip_ratio") or {}
        if ratio_source.get("derived_from") != ["waist_circumference", "hip_circumference"]:
            raise GoldenPatientVerificationError("waist_hip_ratio did not use the canonical derived mapping.")

    def _verify_reference_is_persisted(self, reference: str) -> None:
        parts = str(reference).split("/", 1)
        if len(parts) != 2 or not FHIRResource.objects.filter(
            resource_type=parts[0],
            resource_id=parts[1],
        ).exists():
            raise GoldenPatientVerificationError(f"FHIR reference does not resolve: {reference}")
