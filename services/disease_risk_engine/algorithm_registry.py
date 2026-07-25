"""Canonical metadata boundary for disease-risk algorithms.

This module deliberately separates three trust levels:

* ``RUNTIME_ALGORITHMS`` is the product catalog.  Entries are executable only
  after an explicit clinical-governance promotion.
* ``load_review_catalog`` validates the extracted ``example`` catalog and
  returns non-executable review candidates only.

An extracted formula is never imported, evaluated, or attached to runtime
metadata here. Records with a source conflict (and all other non-candidate
statuses) are discarded before a :class:`ReviewCandidateMetadata` object is
created. Promotion into ``RUNTIME_ALGORITHMS`` therefore requires a future,
explicit code and clinical-governance change.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Optional

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REVIEW_CATALOG_PATH = PROJECT_ROOT / "example" / "algorithms.json"
DEFAULT_REVIEW_SCHEMA_PATH = PROJECT_ROOT / "example" / "algorithm.schema.json"

RUNTIME_CATALOG_VERSION = "3.0.0"
REVIEWABLE_STATUS = "candidate_after_clinical_validation"
RUNTIME_APPROVED_STATUS = "runtime_approved"
CLINICAL_REVIEW_REQUIRED_STATUS = "clinical_review_required"


class CatalogError(ValueError):
    """Base error for invalid risk-algorithm metadata."""


class CatalogSchemaValidationError(CatalogError):
    """The extracted catalog or its JSON Schema is invalid."""


class CatalogInvariantError(CatalogError):
    """The catalog violates a clinical registry invariant."""


def _validate_algorithm_id(algorithm_id: str) -> None:
    if not re.fullmatch(r"[a-z0-9_]+", algorithm_id):
        raise CatalogInvariantError(f"Invalid algorithm id: {algorithm_id!r}")


class ClinicalSystem(str, Enum):
    """Stable codes shared by backend grouping and the risk-analysis UI."""

    CARDIOVASCULAR = "cardiovascular"
    METABOLIC_ENDOCRINE = "metabolic_endocrine"
    HEPATIC = "hepatic"
    RENAL = "renal"
    NEUROCOGNITIVE = "neurocognitive"
    RESPIRATORY = "respiratory"
    MENTAL_HEALTH = "mental_health"
    OTHER = "other"


class FHIRResultType(str, Enum):
    RISK_ASSESSMENT = "RiskAssessment"
    OBSERVATION = "Observation"


class VariableDataType(str, Enum):
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ENUM = "enum"


class ClinicalSourceKind(str, Enum):
    PATIENT = "Patient"
    OBSERVATION = "Observation"
    QUESTIONNAIRE_RESPONSE = "QuestionnaireResponse"
    CONDITION = "Condition"
    DERIVED = "Derived"


@dataclass(frozen=True, slots=True)
class ClinicalSystemDefinition:
    code: ClinicalSystem
    display_zh_tw: str
    display_en: str
    sort_order: int

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "display_zh_tw": self.display_zh_tw,
            "display_en": self.display_en,
            "sort_order": self.sort_order,
        }


CLINICAL_SYSTEM_DEFINITIONS = (
    ClinicalSystemDefinition(ClinicalSystem.CARDIOVASCULAR, "心血管", "Cardiovascular", 10),
    ClinicalSystemDefinition(ClinicalSystem.METABOLIC_ENDOCRINE, "代謝與內分泌", "Metabolic and endocrine", 20),
    ClinicalSystemDefinition(ClinicalSystem.HEPATIC, "肝臟", "Hepatic", 30),
    ClinicalSystemDefinition(ClinicalSystem.RENAL, "腎臟", "Renal", 40),
    ClinicalSystemDefinition(ClinicalSystem.NEUROCOGNITIVE, "神經與認知", "Neurocognitive", 50),
    ClinicalSystemDefinition(ClinicalSystem.RESPIRATORY, "呼吸系統", "Respiratory", 60),
    ClinicalSystemDefinition(ClinicalSystem.MENTAL_HEALTH, "心理健康", "Mental health", 70),
    ClinicalSystemDefinition(ClinicalSystem.OTHER, "其他", "Other", 999),
)

_SYSTEM_DEFINITION_BY_CODE = MappingProxyType(
    {definition.code: definition for definition in CLINICAL_SYSTEM_DEFINITIONS}
)


@dataclass(frozen=True, slots=True)
class ClinicalVariableContract:
    """Canonical input name and its normalized clinical-data contract.

    ``unit`` uses a UCUM code when a scalar has units. ``loinc_codes`` are
    accepted source aliases, not a claim that every source must be a LOINC
    Observation. The source kinds describe the current repository boundary.
    """

    key: str
    data_type: VariableDataType
    unit: Optional[str]
    source_kinds: tuple[ClinicalSourceKind, ...]
    loinc_codes: tuple[str, ...] = ()
    source_aliases: tuple[str, ...] = ()
    allowed_values: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_]*", self.key):
            raise CatalogInvariantError(f"Invalid canonical variable key: {self.key!r}")
        if not self.source_kinds:
            raise CatalogInvariantError(f"Variable {self.key!r} has no clinical source kind")
        if len(set(self.source_kinds)) != len(self.source_kinds):
            raise CatalogInvariantError(f"Variable {self.key!r} repeats a source kind")
        if len(set(self.loinc_codes)) != len(self.loinc_codes):
            raise CatalogInvariantError(f"Variable {self.key!r} repeats a LOINC alias")
        if len(set(self.source_aliases)) != len(self.source_aliases):
            raise CatalogInvariantError(f"Variable {self.key!r} repeats a source alias")
        if self.key in self.source_aliases:
            raise CatalogInvariantError(f"Variable {self.key!r} lists its canonical key as an alias")
        if self.data_type in {VariableDataType.BOOLEAN, VariableDataType.ENUM} and self.unit is not None:
            raise CatalogInvariantError(f"Categorical variable {self.key!r} cannot have a scalar unit")
        if self.data_type is VariableDataType.ENUM and not self.allowed_values:
            raise CatalogInvariantError(f"Enum variable {self.key!r} must declare allowed values")
        if self.data_type is not VariableDataType.ENUM and self.allowed_values:
            raise CatalogInvariantError(f"Non-enum variable {self.key!r} cannot declare allowed values")
        for code in self.loinc_codes:
            if not re.fullmatch(r"\d{1,5}-\d", code):
                raise CatalogInvariantError(f"Invalid LOINC alias {code!r} on {self.key!r}")

    def normalize(self, value: Any) -> Any:
        """Return a valid canonical scalar or ``None`` without converting units.

        The mapped clinical snapshot must contain real booleans, declared enum
        values, and finite non-negative numeric quantities. Invalid values stay
        unknown; they are never converted to zero or ``False``.
        """

        if value is None or value == "":
            return None
        if self.data_type is VariableDataType.BOOLEAN:
            return value if isinstance(value, bool) else None
        if self.data_type is VariableDataType.ENUM:
            if not isinstance(value, str):
                return None
            normalized = value.strip().casefold()
            return next(
                (allowed for allowed in self.allowed_values if allowed.casefold() == normalized),
                None,
            )
        if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
            return None
        try:
            numeric = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if not math.isfinite(numeric) or numeric < 0:
            return None
        if self.data_type is VariableDataType.INTEGER:
            return int(numeric) if numeric.is_integer() else None
        return numeric

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "data_type": self.data_type.value,
            "unit": self.unit,
            "source_kinds": [kind.value for kind in self.source_kinds],
            "loinc_codes": list(self.loinc_codes),
            "source_aliases": list(self.source_aliases),
            "allowed_values": list(self.allowed_values),
        }


def _variable(
    key: str,
    data_type: VariableDataType,
    unit: Optional[str],
    *source_kinds: ClinicalSourceKind,
    loinc_codes: tuple[str, ...] = (),
    source_aliases: tuple[str, ...] = (),
    allowed_values: tuple[str, ...] = (),
) -> ClinicalVariableContract:
    return ClinicalVariableContract(
        key=key,
        data_type=data_type,
        unit=unit,
        source_kinds=source_kinds,
        loinc_codes=loinc_codes,
        source_aliases=source_aliases,
        allowed_values=allowed_values,
    )


_VARIABLE_CONTRACTS = (
    _variable(
        "body_height",
        VariableDataType.NUMBER,
        "cm",
        ClinicalSourceKind.OBSERVATION,
        loinc_codes=("8302-2",),
        source_aliases=("height_cm",),
    ),
    _variable(
        "body_weight",
        VariableDataType.NUMBER,
        "kg",
        ClinicalSourceKind.OBSERVATION,
        loinc_codes=("29463-7",),
        source_aliases=("weight_kg",),
    ),
    _variable("age", VariableDataType.INTEGER, "a", ClinicalSourceKind.PATIENT, source_aliases=("age_years",)),
    _variable(
        "sex",
        VariableDataType.ENUM,
        None,
        ClinicalSourceKind.PATIENT,
        source_aliases=("gender",),
        allowed_values=("M", "F"),
    ),
    _variable(
        "bmi",
        VariableDataType.NUMBER,
        "kg/m2",
        ClinicalSourceKind.OBSERVATION,
        ClinicalSourceKind.DERIVED,
        loinc_codes=("39156-5",),
        source_aliases=("body_mass_index",),
    ),
    _variable(
        "fasting_glucose",
        VariableDataType.NUMBER,
        "mg/dL",
        ClinicalSourceKind.OBSERVATION,
        # 1558-6 explicitly represents glucose after fasting.  Generic glucose
        # observations (2339-0/2345-7) must not silently satisfy a fasting
        # equation without separate fasting provenance.
        loinc_codes=("1558-6",),
        source_aliases=("glucose", "fpg"),
    ),
    _variable(
        "hdl_cholesterol",
        VariableDataType.NUMBER,
        "mg/dL",
        ClinicalSourceKind.OBSERVATION,
        loinc_codes=("2085-9",),
        source_aliases=("hdl",),
    ),
    _variable(
        "total_cholesterol",
        VariableDataType.NUMBER,
        "mg/dL",
        ClinicalSourceKind.OBSERVATION,
        loinc_codes=("2093-3",),
        source_aliases=("tc",),
    ),
    _variable(
        "triglycerides",
        VariableDataType.NUMBER,
        "mg/dL",
        ClinicalSourceKind.OBSERVATION,
        loinc_codes=("2571-8",),
        source_aliases=("tg",),
    ),
    _variable(
        "systolic_bp",
        VariableDataType.NUMBER,
        "mm[Hg]",
        ClinicalSourceKind.OBSERVATION,
        loinc_codes=("8480-6",),
        source_aliases=("systolic_blood_pressure",),
    ),
    _variable(
        "diastolic_bp",
        VariableDataType.NUMBER,
        "mm[Hg]",
        ClinicalSourceKind.OBSERVATION,
        loinc_codes=("8462-4",),
        source_aliases=("diastolic_blood_pressure",),
    ),
    _variable(
        "resting_heart_rate",
        VariableDataType.NUMBER,
        "/min",
        ClinicalSourceKind.OBSERVATION,
        loinc_codes=("8867-4",),
        source_aliases=("heart_rate",),
    ),
    _variable(
        "waist_circumference",
        VariableDataType.NUMBER,
        "cm",
        ClinicalSourceKind.OBSERVATION,
        loinc_codes=("8280-0",),
        source_aliases=("waist",),
    ),
    _variable(
        "waist_hip_ratio",
        VariableDataType.NUMBER,
        "{ratio}",
        ClinicalSourceKind.DERIVED,
        source_aliases=("whr",),
    ),
    _variable(
        "alcohol_drinks_per_week",
        VariableDataType.NUMBER,
        "{drink}/wk",
        ClinicalSourceKind.OBSERVATION,
        loinc_codes=("74013-4",),
        source_aliases=("drinks_per_week",),
    ),
    _variable(
        "ast_got",
        VariableDataType.NUMBER,
        "U/L",
        ClinicalSourceKind.OBSERVATION,
        loinc_codes=("1920-8",),
        source_aliases=("ast", "got"),
    ),
    _variable(
        "alt_gpt",
        VariableDataType.NUMBER,
        "U/L",
        ClinicalSourceKind.OBSERVATION,
        loinc_codes=("1742-6",),
        source_aliases=("alt", "gpt"),
    ),
    _variable(
        "ast_uln",
        VariableDataType.NUMBER,
        "U/L",
        ClinicalSourceKind.OBSERVATION,
        loinc_codes=("1916-6",),
        source_aliases=("ast_upper_limit",),
    ),
    _variable(
        "platelet_count",
        VariableDataType.NUMBER,
        "10*9/L",
        ClinicalSourceKind.OBSERVATION,
        loinc_codes=("777-3",),
        source_aliases=("platelet",),
    ),
    _variable(
        "albumin",
        VariableDataType.NUMBER,
        "g/dL",
        ClinicalSourceKind.OBSERVATION,
        loinc_codes=("1751-7",),
    ),
    _variable(
        "ggt",
        VariableDataType.NUMBER,
        "U/L",
        ClinicalSourceKind.OBSERVATION,
        loinc_codes=("2324-2",),
    ),
    _variable(
        "insulin",
        VariableDataType.NUMBER,
        "u[IU]/mL",
        ClinicalSourceKind.OBSERVATION,
        loinc_codes=("20448-7",),
    ),
    _variable(
        "rdw",
        VariableDataType.NUMBER,
        "%",
        ClinicalSourceKind.OBSERVATION,
        loinc_codes=("788-0",),
        source_aliases=("rdw_percent",),
    ),
    _variable(
        "mean_platelet_volume",
        VariableDataType.NUMBER,
        "fL",
        ClinicalSourceKind.OBSERVATION,
        loinc_codes=("32623-1",),
        source_aliases=("mpv", "mpv_fl"),
    ),
    _variable(
        "hba1c",
        VariableDataType.NUMBER,
        "%",
        ClinicalSourceKind.OBSERVATION,
        loinc_codes=("4548-4",),
        source_aliases=("glycated_hemoglobin",),
    ),
    _variable(
        "hs_crp",
        VariableDataType.NUMBER,
        "mg/L",
        ClinicalSourceKind.OBSERVATION,
        loinc_codes=("30522-7",),
        source_aliases=("high_sensitivity_crp",),
    ),
    _variable(
        "ggt_uln",
        VariableDataType.NUMBER,
        "U/L",
        ClinicalSourceKind.OBSERVATION,
        source_aliases=("ggt_upper_limit",),
    ),
    _variable(
        "microalbumin_excretion_rate",
        VariableDataType.NUMBER,
        "ug/min",
        ClinicalSourceKind.OBSERVATION,
        source_aliases=("microalbumin_ug_min",),
    ),
    _variable(
        "pulmonary_nodule_diameter",
        VariableDataType.NUMBER,
        "mm",
        ClinicalSourceKind.OBSERVATION,
        source_aliases=("nodule_diameter_mm",),
    ),
    _variable(
        "egfr",
        VariableDataType.NUMBER,
        "mL/min/{1.73_m2}",
        ClinicalSourceKind.OBSERVATION,
        ClinicalSourceKind.DERIVED,
        loinc_codes=("33914-3", "48642-3", "62238-1", "98979-8"),
        source_aliases=("estimated_glomerular_filtration_rate",),
    ),
    _variable(
        "apoe_e4",
        VariableDataType.INTEGER,
        "{allele}",
        ClinicalSourceKind.OBSERVATION,
        loinc_codes=("79713-2",),
    ),
    _variable(
        "family_history_diabetes",
        VariableDataType.BOOLEAN,
        None,
        ClinicalSourceKind.QUESTIONNAIRE_RESPONSE,
    ),
    _variable(
        "anti_hypertensive_drugs",
        VariableDataType.BOOLEAN,
        None,
        ClinicalSourceKind.QUESTIONNAIRE_RESPONSE,
        source_aliases=("on_bp_treatment",),
    ),
    _variable(
        "using_lipid_lowering_drugs",
        VariableDataType.BOOLEAN,
        None,
        ClinicalSourceKind.QUESTIONNAIRE_RESPONSE,
        source_aliases=("lipid_lowering_treatment",),
    ),
    _variable(
        "statin_use",
        VariableDataType.BOOLEAN,
        None,
        ClinicalSourceKind.QUESTIONNAIRE_RESPONSE,
        source_aliases=("statin",),
    ),
    _variable(
        "has_diabetes",
        VariableDataType.BOOLEAN,
        None,
        ClinicalSourceKind.QUESTIONNAIRE_RESPONSE,
        ClinicalSourceKind.CONDITION,
        source_aliases=("dm_treated",),
    ),
    _variable(
        "prediabetes",
        VariableDataType.BOOLEAN,
        None,
        ClinicalSourceKind.QUESTIONNAIRE_RESPONSE,
        ClinicalSourceKind.CONDITION,
    ),
    _variable(
        "has_hypertension",
        VariableDataType.BOOLEAN,
        None,
        ClinicalSourceKind.QUESTIONNAIRE_RESPONSE,
        ClinicalSourceKind.CONDITION,
    ),
    _variable(
        "vegetables_daily",
        VariableDataType.BOOLEAN,
        None,
        ClinicalSourceKind.QUESTIONNAIRE_RESPONSE,
    ),
    _variable(
        "is_smoker",
        VariableDataType.BOOLEAN,
        None,
        ClinicalSourceKind.OBSERVATION,
        ClinicalSourceKind.QUESTIONNAIRE_RESPONSE,
        loinc_codes=("72166-2",),
        source_aliases=("current_smoker", "smoking_status"),
    ),
    _variable(
        "physical_activity_active",
        VariableDataType.BOOLEAN,
        None,
        ClinicalSourceKind.QUESTIONNAIRE_RESPONSE,
        source_aliases=("exercise_active",),
    ),
    _variable(
        "metabolic_syndrome",
        VariableDataType.BOOLEAN,
        None,
        ClinicalSourceKind.QUESTIONNAIRE_RESPONSE,
        ClinicalSourceKind.DERIVED,
    ),
    _variable(
        "chd_history",
        VariableDataType.BOOLEAN,
        None,
        ClinicalSourceKind.QUESTIONNAIRE_RESPONSE,
        ClinicalSourceKind.CONDITION,
    ),
    _variable(
        "cvd_history",
        VariableDataType.BOOLEAN,
        None,
        ClinicalSourceKind.QUESTIONNAIRE_RESPONSE,
        ClinicalSourceKind.CONDITION,
    ),
    _variable(
        "pvd_history",
        VariableDataType.BOOLEAN,
        None,
        ClinicalSourceKind.QUESTIONNAIRE_RESPONSE,
        ClinicalSourceKind.CONDITION,
    ),
    _variable("former_smoker", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("moderate_alcohol", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("heavy_alcohol", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("prescribed_steroids", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("family_history_diabetes_both", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("parental_hypertension_count", VariableDataType.INTEGER, "{count}", ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("deprivation_quintile", VariableDataType.INTEGER, "{score}", ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("depression_or_antidepressant", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE, ClinicalSourceKind.CONDITION),
    _variable("aspirin_use", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("stroke_tia_history", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE, ClinicalSourceKind.CONDITION),
    _variable("atrial_fibrillation", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE, ClinicalSourceKind.CONDITION),
    _variable("race_black", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("ethnicity_hispanic", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("moderate_heavy_activity", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("ever_smoker", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("extrathoracic_cancer_over_5y", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE, ClinicalSourceKind.CONDITION),
    _variable("nodule_spiculation", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("nodule_upper_lobe", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("diabetes_duration_years", VariableDataType.NUMBER, "a", ClinicalSourceKind.QUESTIONNAIRE_RESPONSE, ClinicalSourceKind.OBSERVATION),
    _variable("education_high_school_or_below", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("ever_high_blood_glucose", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("ausdrisk_indigenous_or_pacific", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("ausdrisk_high_risk_birth_region", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("ausdrisk_lower_waist_threshold_group", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("ascvd_history", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE, ClinicalSourceKind.CONDITION),
    _variable("heart_failure_history", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE, ClinicalSourceKind.CONDITION),
    _variable("parental_mi_before_60", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("family_history_lung_cancer", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("has_emphysema", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE, ClinicalSourceKind.CONDITION),
    _variable("weather_affected_cough", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("sputum_without_cold", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("morning_sputum", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("wheeze_sometimes_or_often", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("allergy_history", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("has_amnestic_mci", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE, ClinicalSourceKind.CONDITION),
    _variable("stubborn_or_resistive", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("upset_when_separated_from_caregiver", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("difficulty_shopping_alone", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("forgets_appointments", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("depressive_symptoms", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE, ClinicalSourceKind.CONDITION),
    _variable("needs_help_money_or_medications", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("high_cholesterol", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE, ClinicalSourceKind.CONDITION),
    _variable("traumatic_brain_injury", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE, ClinicalSourceKind.CONDITION),
    _variable("pesticide_exposure", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("periodical_daily_cough", VariableDataType.BOOLEAN, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("education_years", VariableDataType.NUMBER, "a", ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("pack_years", VariableDataType.NUMBER, "{pack-year}", ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("cigarettes_per_day", VariableDataType.NUMBER, "{cigarette}/d", ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("years_since_quitting", VariableDataType.NUMBER, "a", ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("indoor_smoke_exposure_hours", VariableDataType.NUMBER, "h/d", ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("fish_servings_per_week", VariableDataType.NUMBER, "{serving}/wk", ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("mean_words_recalled", VariableDataType.NUMBER, "{score}", ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("orientation_correct", VariableDataType.INTEGER, "{score}", ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("clock_drawing_score", VariableDataType.INTEGER, "{score}", ClinicalSourceKind.QUESTIONNAIRE_RESPONSE),
    _variable("nodule_count", VariableDataType.INTEGER, "{count}", ClinicalSourceKind.QUESTIONNAIRE_RESPONSE, ClinicalSourceKind.OBSERVATION),
    _variable("pce_race", VariableDataType.ENUM, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE, allowed_values=("black", "white")),
    _variable("smoking_status", VariableDataType.ENUM, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE, allowed_values=("never", "former", "current")),
    _variable("alcohol_category", VariableDataType.ENUM, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE, allowed_values=("none", "light_moderate", "heavy")),
    _variable("social_engagement_level", VariableDataType.ENUM, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE, allowed_values=("high", "medium_high", "medium_low", "low")),
    _variable("physical_activity_level", VariableDataType.ENUM, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE, allowed_values=("low", "medium", "high")),
    _variable("cognitive_activity_level", VariableDataType.ENUM, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE, allowed_values=("low", "medium", "high")),
    _variable("nodule_type", VariableDataType.ENUM, None, ClinicalSourceKind.QUESTIONNAIRE_RESPONSE, ClinicalSourceKind.OBSERVATION, allowed_values=("solid", "part_solid", "nonsolid")),
    _variable("evaluation_year", VariableDataType.INTEGER, "a", ClinicalSourceKind.DERIVED),
    *(
        _variable(
            f"gad7_q{index}",
            VariableDataType.INTEGER,
            "{score}",
            ClinicalSourceKind.QUESTIONNAIRE_RESPONSE,
        )
        for index in range(1, 8)
    ),
)

CLINICAL_VARIABLES: Mapping[str, ClinicalVariableContract] = MappingProxyType(
    {contract.key: contract for contract in _VARIABLE_CONTRACTS}
)

if len(CLINICAL_VARIABLES) != len(_VARIABLE_CONTRACTS):
    raise CatalogInvariantError("Duplicate canonical clinical variable key")


ALGORITHM_DISPLAY_NAMES_ZH: Mapping[str, str] = MappingProxyType(
    {
        "framingham_diabetes": "Framingham 糖尿病風險",
        "chinese_diabetes": "中國糖尿病風險評分",
        "metabolic_syndrome": "代謝症候群",
        "bmi": "身體質量指數",
        "tyg_index": "三酸甘油脂－葡萄糖指數",
        "homa_ir": "胰島素阻抗恆定模式評估",
        "quicki": "胰島素敏感性定量檢查指數",
        "hepatic_steatosis_index": "肝脂肪變性指數",
        "nafld_liver_fat_score": "非酒精性脂肪肝肝脂肪評分",
        "fatty_liver_index": "脂肪肝指數",
        "fib4": "肝纖維化四因子指數",
        "apri": "AST／血小板比值指數",
        "rpr": "紅血球分布寬度／血小板比值",
        "nafld_fibrosis_score": "非酒精性脂肪肝纖維化評分",
        "incident_hepatic_steatosis_model_2": "新發肝脂肪變性風險模型 2",
        "nafld_cv_risk_score": "非酒精性脂肪肝心血管風險評分",
        "cambridge_diabetes_risk": "Cambridge 糖尿病風險評分",
        "framingham_cvd_10_lipids": "Framingham 十年心血管風險（血脂版）",
        "framingham_cvd_10_bmi": "Framingham 十年心血管風險（BMI 版）",
        "framingham_hypertension": "Framingham 近期高血壓風險",
        "dementia_risk_score_thin_60_79": "THIN 失智風險評分（60–79 歲）",
        "nomas_global_vascular_risk": "NOMAS 全域血管風險評分",
        "mayo_pulmonary_nodule": "Mayo 孤立性肺結節惡性風險模型",
        "christianson_t2dm_chd_score": "Christianson 第二型糖尿病冠心病風險評分",
        "gad7": "廣泛性焦慮症七題量表",
        "ausdrisk_diabetes": "澳洲第二型糖尿病風險評估",
        "aha_prevent_cvd_10y": "AHA PREVENT 十年心血管疾病風險",
        "aha_prevent_ascvd_10y": "AHA PREVENT 十年動脈粥樣硬化性心血管疾病風險",
        "aha_prevent_hf_10y": "AHA PREVENT 十年心衰竭風險",
        "reynolds_risk_score_women_10y": "Reynolds 女性十年心血管風險",
        "reynolds_risk_score_men_10y": "Reynolds 男性十年心血管風險",
        "pooled_cohort_ascvd_10y": "ACC／AHA 合併世代方程式十年 ASCVD 風險",
        "cardiometabolic_index": "心臟代謝指數",
        "lipid_accumulation_product": "脂質蓄積指數",
        "ggt_platelet_ratio": "GGT／血小板比值",
        "ipag_copd_questionnaire": "IPAG 慢性阻塞性肺病診斷問卷",
        "mci_to_ad_3y": "遺忘型輕度認知障礙轉阿茲海默症三年風險評分",
        "anu_adri": "澳洲國立大學阿茲海默症風險指數",
        "brock_pancan_pulmonary_nodule": "Brock／PanCan 肺結節惡性風險模型",
        "va_pulmonary_nodule": "美國退伍軍人肺結節惡性風險模型",
        "caide_dementia_20y": "CAIDE 二十年失智風險評分",
        "bdsi_dementia_6y": "簡式失智篩檢指標",
    }
)


def algorithm_display_name_zh(algorithm_id: str, fallback: str = "") -> str:
    return ALGORITHM_DISPLAY_NAMES_ZH.get(algorithm_id, fallback or algorithm_id)


@dataclass(frozen=True, slots=True)
class RuntimeAlgorithmMetadata:
    algorithm_id: str
    display_name: str
    outcome_key: str
    clinical_system: ClinicalSystem
    output_resource: FHIRResultType
    required_inputs: tuple[str, ...]
    model_version: str
    source_label: str
    time_horizon: Optional[str] = None
    method_uri: Optional[str] = None
    score_represents_probability: bool = False
    governance_status: str = RUNTIME_APPROVED_STATUS
    runtime_enabled: bool = True
    clinical_review_reason: Optional[str] = None

    def __post_init__(self) -> None:
        _validate_algorithm_id(self.algorithm_id)
        if len(set(self.required_inputs)) != len(self.required_inputs):
            raise CatalogInvariantError(f"Algorithm {self.algorithm_id!r} repeats a required input")
        unknown = set(self.required_inputs).difference(CLINICAL_VARIABLES)
        if unknown:
            raise CatalogInvariantError(
                f"Algorithm {self.algorithm_id!r} references unknown canonical inputs: {sorted(unknown)}"
            )
        allowed_statuses = {
            RUNTIME_APPROVED_STATUS,
            CLINICAL_REVIEW_REQUIRED_STATUS,
        }
        if self.governance_status not in allowed_statuses:
            raise CatalogInvariantError(
                f"Algorithm {self.algorithm_id!r} has unsupported governance status "
                f"{self.governance_status!r}"
            )
        if self.runtime_enabled and self.governance_status != RUNTIME_APPROVED_STATUS:
            raise CatalogInvariantError(
                f"Algorithm {self.algorithm_id!r} cannot execute before governance approval"
            )
        if not self.runtime_enabled and not self.clinical_review_reason:
            raise CatalogInvariantError(
                f"Disabled catalog algorithm {self.algorithm_id!r} must explain its governance gate"
            )

    @property
    def input_contracts(self) -> tuple[ClinicalVariableContract, ...]:
        return tuple(CLINICAL_VARIABLES[key] for key in self.required_inputs)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "catalog_kind": "runtime",
            "algorithm_id": self.algorithm_id,
            "display_name": self.display_name,
            "display_name_en": self.display_name,
            "display_name_zh": algorithm_display_name_zh(self.algorithm_id, self.display_name),
            "outcome_key": self.outcome_key,
            "clinical_system": self.clinical_system.value,
            "fhir_output": self.output_resource.value,
            "governance_status": self.governance_status,
            "runtime_enabled": self.runtime_enabled,
            "model_version": self.model_version,
            "source_label": self.source_label,
            "time_horizon": self.time_horizon,
            "method_uri": self.method_uri,
            "score_represents_probability": self.score_represents_probability,
            "clinical_review_reason": self.clinical_review_reason,
            "required_input_keys": list(self.required_inputs),
        }


@dataclass(frozen=True, slots=True)
class RequiredInputValidation:
    """Validated canonical required inputs for one runtime algorithm."""

    algorithm_id: str
    values: Mapping[str, Any]
    missing_fields: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return not self.missing_fields


CORE_MODEL_VERSION = "allcare-risk-catalog-2026-07-21"
PREVENT_MODEL_VERSION = "AHA-PREVENT-base-2023-10y"
PREVENT_METHOD_URI = "https://doi.org/10.1161/CIRCULATIONAHA.123.067626"


def _runtime(
    algorithm_id: str,
    display_name: str,
    outcome_key: str,
    clinical_system: ClinicalSystem,
    required_inputs: tuple[str, ...],
    *,
    model_version: str = CORE_MODEL_VERSION,
    source_label: str = "CORE.xlsx",
    time_horizon: Optional[str] = None,
    method_uri: Optional[str] = None,
    score_represents_probability: bool = False,
    governance_status: str = RUNTIME_APPROVED_STATUS,
    runtime_enabled: bool = True,
    clinical_review_reason: Optional[str] = None,
    output_resource: FHIRResultType = FHIRResultType.RISK_ASSESSMENT,
) -> RuntimeAlgorithmMetadata:
    return RuntimeAlgorithmMetadata(
        algorithm_id=algorithm_id,
        display_name=display_name,
        outcome_key=outcome_key,
        clinical_system=clinical_system,
        output_resource=output_resource,
        required_inputs=required_inputs,
        model_version=model_version,
        source_label=source_label,
        time_horizon=time_horizon,
        method_uri=method_uri,
        score_represents_probability=score_represents_probability,
        governance_status=governance_status,
        runtime_enabled=runtime_enabled,
        clinical_review_reason=clinical_review_reason,
    )


_PREVENT_REQUIRED_INPUTS = (
    "age",
    "sex",
    "systolic_bp",
    "total_cholesterol",
    "hdl_cholesterol",
    "bmi",
    "egfr",
    "has_diabetes",
    "is_smoker",
    "anti_hypertensive_drugs",
    "statin_use",
    "chd_history",
    "cvd_history",
    "pvd_history",
    "ascvd_history",
    "stroke_tia_history",
    "heart_failure_history",
)

RUNTIME_ALGORITHMS = (
    _runtime(
        "framingham_diabetes",
        "Framingham Diabetes Risk",
        "diabetes_risk",
        ClinicalSystem.METABOLIC_ENDOCRINE,
        (
            "age",
            "sex",
            "fasting_glucose",
            "bmi",
            "hdl_cholesterol",
            "triglycerides",
            "systolic_bp",
            "diastolic_bp",
            "family_history_diabetes",
            "anti_hypertensive_drugs",
        ),
    ),
    _runtime(
        "chinese_diabetes",
        "Chinese Diabetes Risk",
        "diabetes_risk",
        ClinicalSystem.METABOLIC_ENDOCRINE,
        (
            "age",
            "sex",
            "bmi",
            "family_history_diabetes",
            "systolic_bp",
            "diastolic_bp",
            "anti_hypertensive_drugs",
            "resting_heart_rate",
            "fasting_glucose",
            "triglycerides",
            "using_lipid_lowering_drugs",
            "education_high_school_or_below",
        ),
    ),
    _runtime(
        "metabolic_syndrome",
        "Metabolic Syndrome",
        "ncep_mets",
        ClinicalSystem.METABOLIC_ENDOCRINE,
        (
            "sex",
            "waist_circumference",
            "fasting_glucose",
            "systolic_bp",
            "diastolic_bp",
            "hdl_cholesterol",
            "triglycerides",
            "has_diabetes",
            "prediabetes",
            "anti_hypertensive_drugs",
            "has_hypertension",
        ),
    ),
    _runtime("bmi", "Body Mass Index", "body_mass_index", ClinicalSystem.METABOLIC_ENDOCRINE,
             ("body_weight", "body_height"), output_resource=FHIRResultType.OBSERVATION,
             model_version="WHO-BMI-formula-2026-07", source_label="Hospital-approved catalog; WHO anthropometry"),
    _runtime("tyg_index", "Triglyceride-Glucose Index (TyG)", "insulin_resistance_index", ClinicalSystem.METABOLIC_ENDOCRINE,
             ("triglycerides", "fasting_glucose"), output_resource=FHIRResultType.OBSERVATION,
             model_version="TyG-ln-2026-07", source_label="Hospital-approved catalog"),
    _runtime("homa_ir", "HOMA-IR", "insulin_resistance_index", ClinicalSystem.METABOLIC_ENDOCRINE,
             ("insulin", "fasting_glucose"), output_resource=FHIRResultType.OBSERVATION,
             model_version="HOMA1-IR-mgdl-2026-07", source_label="Matthews et al. 1985",
             method_uri="https://doi.org/10.1007/BF00280883"),
    _runtime("quicki", "QUICKI", "insulin_sensitivity_index", ClinicalSystem.METABOLIC_ENDOCRINE,
             ("insulin", "fasting_glucose"), output_resource=FHIRResultType.OBSERVATION,
             model_version="QUICKI-log10-2026-07", source_label="Katz et al. 2000",
             method_uri="https://doi.org/10.1210/jcem.85.7.6661"),
    _runtime("hepatic_steatosis_index", "Hepatic Steatosis Index (HSI)", "hepatic_steatosis_screening", ClinicalSystem.HEPATIC,
             ("alt_gpt", "ast_got", "bmi", "has_diabetes", "sex"), output_resource=FHIRResultType.OBSERVATION,
             model_version="HSI-Lee-2010", source_label="Lee et al. 2010", method_uri="https://doi.org/10.1016/j.dld.2009.08.002"),
    _runtime("nafld_liver_fat_score", "NAFLD Liver Fat Score (LFS)", "hepatic_steatosis_screening", ClinicalSystem.HEPATIC,
             ("metabolic_syndrome", "has_diabetes", "insulin", "ast_got", "alt_gpt"), output_resource=FHIRResultType.OBSERVATION,
             model_version="NAFLD-LFS-Kotronen-2009", source_label="Kotronen et al. 2009", method_uri="https://pubmed.ncbi.nlm.nih.gov/19524579/"),
    _runtime("fatty_liver_index", "Fatty Liver Index (FLI)", "hepatic_steatosis_screening", ClinicalSystem.HEPATIC,
             ("triglycerides", "bmi", "ggt", "waist_circumference"), output_resource=FHIRResultType.OBSERVATION,
             model_version="FLI-Bedogni-2006-corrected", source_label="Bedogni et al. 2006", method_uri="https://pubmed.ncbi.nlm.nih.gov/17081293/"),
    _runtime("fib4", "Fibrosis-4 Index (FIB-4)", "liver_fibrosis_screening", ClinicalSystem.HEPATIC,
             ("age", "ast_got", "alt_gpt", "platelet_count"), output_resource=FHIRResultType.OBSERVATION,
             model_version="FIB4-WHO-2024", source_label="WHO hepatitis B guidance", method_uri="https://www.who.int/publications/i/item/9789240090903"),
    _runtime("apri", "AST to Platelet Ratio Index (APRI)", "liver_fibrosis_screening", ClinicalSystem.HEPATIC,
             ("ast_got", "ast_uln", "platelet_count"), output_resource=FHIRResultType.OBSERVATION,
             model_version="APRI-WHO-2024", source_label="WHO hepatitis B guidance", method_uri="https://www.who.int/publications/i/item/9789240090903"),
    _runtime("rpr", "RDW-to-Platelet Ratio (RPR)", "liver_fibrosis_screening", ClinicalSystem.HEPATIC,
             ("rdw", "platelet_count"), output_resource=FHIRResultType.OBSERVATION,
             model_version="RPR-Chen-2013", source_label="Chen et al. 2013", method_uri="https://doi.org/10.1371/journal.pone.0068780"),
    _runtime("nafld_fibrosis_score", "NAFLD Fibrosis Score (NFS)", "liver_fibrosis_screening", ClinicalSystem.HEPATIC,
             ("age", "bmi", "prediabetes", "has_diabetes", "ast_got", "alt_gpt", "platelet_count", "albumin"),
             output_resource=FHIRResultType.OBSERVATION, model_version="NFS-Angulo-2007", source_label="Angulo et al. 2007",
             method_uri="https://doi.org/10.1002/hep.21496"),
    _runtime("incident_hepatic_steatosis_model_2", "Incident Hepatic Steatosis Risk Model 2", "incident_hepatic_steatosis", ClinicalSystem.HEPATIC,
             ("sex", "age", "bmi", "alcohol_drinks_per_week", "triglycerides"), model_version="hospital-model-2-2026-07",
             source_label="Hospital-approved Model 2", score_represents_probability=True),
    _runtime("nafld_cv_risk_score", "NAFLD Cardiovascular Risk Score", "nafld_cardiovascular_risk", ClinicalSystem.CARDIOVASCULAR,
             ("age", "mean_platelet_volume", "has_diabetes"), model_version="Abeles-NAFLD-CV-2019", source_label="Abeles et al. 2019",
             method_uri="https://pubmed.ncbi.nlm.nih.gov/30836450/"),
    _runtime("cambridge_diabetes_risk", "Cambridge Diabetes Risk Score", "diabetes_risk", ClinicalSystem.METABOLIC_ENDOCRINE,
             ("sex", "anti_hypertensive_drugs", "prescribed_steroids", "age", "bmi", "family_history_diabetes", "family_history_diabetes_both", "is_smoker", "former_smoker"),
             model_version="Cambridge-Griffin-2000", source_label="Griffin et al. 2000", method_uri="https://doi.org/10.1002/1520-7560(200005/06)16:3%3C164::AID-DMRR103%3E3.0.CO;2-R", score_represents_probability=True),
    _runtime("framingham_cvd_10_lipids", "Framingham General CVD 10-Year Risk (Lipids)", "total_cvd_10_year_risk", ClinicalSystem.CARDIOVASCULAR,
             ("sex", "age", "systolic_bp", "anti_hypertensive_drugs", "total_cholesterol", "hdl_cholesterol", "is_smoker", "has_diabetes"),
             model_version="Framingham-General-CVD-2008-lipids", source_label="D'Agostino et al. 2008", time_horizon="10 years", method_uri="https://doi.org/10.1161/CIRCULATIONAHA.107.699579", score_represents_probability=True),
    _runtime("framingham_cvd_10_bmi", "Framingham General CVD 10-Year Risk (BMI)", "total_cvd_10_year_risk", ClinicalSystem.CARDIOVASCULAR,
             ("sex", "age", "systolic_bp", "anti_hypertensive_drugs", "bmi", "is_smoker", "has_diabetes"),
             model_version="Framingham-General-CVD-2008-bmi", source_label="D'Agostino et al. 2008", time_horizon="10 years", method_uri="https://doi.org/10.1161/CIRCULATIONAHA.107.699579", score_represents_probability=True),
    _runtime("framingham_hypertension", "Framingham Near-Term Hypertension Risk", "incident_hypertension", ClinicalSystem.CARDIOVASCULAR,
             ("age", "sex", "bmi", "systolic_bp", "diastolic_bp", "is_smoker", "parental_hypertension_count"),
             model_version="Framingham-HTN-Parikh-2008-4y", source_label="Parikh et al. 2008", time_horizon="4 years", method_uri="https://doi.org/10.7326/0003-4819-148-2-200801150-00005", score_represents_probability=True),
    _runtime("dementia_risk_score_thin_60_79", "Dementia Risk Score (THIN age 60-79)", "dementia_5_year_risk", ClinicalSystem.NEUROCOGNITIVE,
             ("age", "bmi", "sex", "has_hypertension", "evaluation_year", "deprivation_quintile", "is_smoker", "former_smoker", "heavy_alcohol", "depression_or_antidepressant", "aspirin_use", "stroke_tia_history", "atrial_fibrillation", "has_diabetes"),
             model_version="THIN-DRS-Walters-2016", source_label="Walters et al. 2016", time_horizon="5 years", method_uri="https://doi.org/10.1186/s12916-016-0549-y", score_represents_probability=True),
    _runtime("nomas_global_vascular_risk", "NOMAS Global Vascular Risk Score", "global_vascular_10_year_risk", ClinicalSystem.CARDIOVASCULAR,
             ("age", "sex", "race_black", "ethnicity_hispanic", "waist_circumference", "moderate_alcohol", "is_smoker", "former_smoker", "moderate_heavy_activity", "systolic_bp", "diastolic_bp", "anti_hypertensive_drugs", "pvd_history", "fasting_glucose", "total_cholesterol", "hdl_cholesterol"),
             model_version="NOMAS-GVRS-Sacco-2009", source_label="Sacco et al. 2009", time_horizon="10 years", method_uri="https://doi.org/10.1016/j.jacc.2009.07.047", score_represents_probability=True),
    _runtime("mayo_pulmonary_nodule", "Mayo Solitary Pulmonary Nodule Malignancy Model", "pulmonary_nodule_malignancy", ClinicalSystem.RESPIRATORY,
             ("age", "ever_smoker", "extrathoracic_cancer_over_5y", "pulmonary_nodule_diameter", "nodule_spiculation", "nodule_upper_lobe"),
             model_version="Mayo-SPN-Swensen", source_label="Swensen/Mayo model", method_uri="https://pmc.ncbi.nlm.nih.gov/articles/PMC2882437/", score_represents_probability=True),
    _runtime("christianson_t2dm_chd_score", "Christianson Type 2 Diabetes CHD Risk Score", "coronary_heart_disease_risk", ClinicalSystem.CARDIOVASCULAR,
             ("age", "sex", "has_diabetes", "diabetes_duration_years", "is_smoker", "hba1c", "systolic_bp", "total_cholesterol", "hdl_cholesterol", "microalbumin_excretion_rate"),
             model_version="Christianson-T2DM-CHD-hospital-table-2026-07", source_label="Hospital-approved point table"),
    _runtime("gad7", "Generalized Anxiety Disorder 7-item Scale (GAD-7)", "anxiety_symptom_severity", ClinicalSystem.MENTAL_HEALTH,
             tuple(f"gad7_q{index}" for index in range(1, 8)), output_resource=FHIRResultType.OBSERVATION,
             model_version="GAD7-Spitzer-2006", source_label="Spitzer et al. 2006", method_uri="https://doi.org/10.1001/archinte.166.10.1092"),
    _runtime(
        "ausdrisk_diabetes",
        "Australian Type 2 Diabetes Risk",
        "diabetes_risk",
        ClinicalSystem.METABOLIC_ENDOCRINE,
        (
            "age",
            "sex",
            "waist_circumference",
            "family_history_diabetes",
            "ever_high_blood_glucose",
            "ausdrisk_indigenous_or_pacific",
            "ausdrisk_high_risk_birth_region",
            "ausdrisk_lower_waist_threshold_group",
            "vegetables_daily",
            "is_smoker",
            "physical_activity_active",
            "anti_hypertensive_drugs",
            "has_diabetes",
        ),
    ),
    _runtime(
        "aha_prevent_cvd_10y",
        "AHA PREVENT-CVD Base Equation (10-year)",
        "total_cvd_10_year_risk",
        ClinicalSystem.CARDIOVASCULAR,
        _PREVENT_REQUIRED_INPUTS,
        model_version=PREVENT_MODEL_VERSION,
        source_label="AHA PREVENT base equations",
        time_horizon="10 years",
        method_uri=PREVENT_METHOD_URI,
        score_represents_probability=True,
    ),
    _runtime(
        "aha_prevent_ascvd_10y",
        "AHA PREVENT-ASCVD Base Equation (10-year)",
        "ascvd_10_year_risk",
        ClinicalSystem.CARDIOVASCULAR,
        _PREVENT_REQUIRED_INPUTS,
        model_version=PREVENT_MODEL_VERSION,
        source_label="AHA PREVENT base equations",
        time_horizon="10 years",
        method_uri=PREVENT_METHOD_URI,
        score_represents_probability=True,
    ),
    _runtime(
        "aha_prevent_hf_10y",
        "AHA PREVENT-HF Base Equation (10-year)",
        "heart_failure_10_year_risk",
        ClinicalSystem.CARDIOVASCULAR,
        _PREVENT_REQUIRED_INPUTS,
        model_version=PREVENT_MODEL_VERSION,
        source_label="AHA PREVENT base equations",
        time_horizon="10 years",
        method_uri=PREVENT_METHOD_URI,
        score_represents_probability=True,
    ),
    _runtime(
        "reynolds_risk_score_women_10y", "Reynolds Risk Score for Women",
        "major_cardiovascular_event_10_year_risk", ClinicalSystem.CARDIOVASCULAR,
        ("age", "sex", "systolic_bp", "hs_crp", "total_cholesterol", "hdl_cholesterol", "hba1c", "has_diabetes", "is_smoker", "parental_mi_before_60"),
        model_version="Reynolds-Women-Ridker-2007", source_label="Ridker et al. 2007",
        time_horizon="10 years", method_uri="https://doi.org/10.1001/jama.297.6.611",
        score_represents_probability=True,
    ),
    _runtime(
        "reynolds_risk_score_men_10y", "Reynolds Risk Score for Men",
        "major_cardiovascular_event_10_year_risk", ClinicalSystem.CARDIOVASCULAR,
        ("age", "sex", "systolic_bp", "hs_crp", "total_cholesterol", "hdl_cholesterol", "is_smoker", "parental_mi_before_60"),
        model_version="Reynolds-Men-Ridker-2008", source_label="Ridker et al. 2008",
        time_horizon="10 years", method_uri="https://doi.org/10.1161/CIRCULATIONAHA.108.814251",
        score_represents_probability=True,
    ),
    _runtime(
        "pooled_cohort_ascvd_10y", "2013 ACC/AHA Pooled Cohort Equation",
        "first_hard_ascvd_10_year_risk", ClinicalSystem.CARDIOVASCULAR,
        ("age", "sex", "pce_race", "total_cholesterol", "hdl_cholesterol", "systolic_bp", "anti_hypertensive_drugs", "is_smoker", "has_diabetes"),
        model_version="ACC-AHA-PCE-2013", source_label="2013 ACC/AHA Guideline",
        time_horizon="10 years", method_uri="https://doi.org/10.1016/j.jacc.2013.11.005",
        score_represents_probability=True,
    ),
    _runtime(
        "cardiometabolic_index", "Cardiometabolic Index (CMI)",
        "cardiometabolic_index", ClinicalSystem.METABOLIC_ENDOCRINE,
        ("triglycerides", "hdl_cholesterol", "waist_circumference", "body_height"),
        output_resource=FHIRResultType.OBSERVATION, model_version="CMI-Wakabayashi-2015",
        source_label="Wakabayashi and Daimon 2015", method_uri="https://doi.org/10.1016/j.cca.2014.08.042",
    ),
    _runtime(
        "lipid_accumulation_product", "Lipid Accumulation Product (LAP)",
        "lipid_accumulation_index", ClinicalSystem.METABOLIC_ENDOCRINE,
        ("sex", "waist_circumference", "triglycerides"),
        output_resource=FHIRResultType.OBSERVATION, model_version="LAP-Kahn-2005",
        source_label="Kahn 2005", method_uri="https://doi.org/10.1186/1471-2261-5-26",
    ),
    _runtime(
        "ggt_platelet_ratio", "GGT-to-Platelet Ratio (GPR)",
        "liver_fibrosis_screening", ClinicalSystem.HEPATIC,
        ("ggt", "ggt_uln", "platelet_count"), output_resource=FHIRResultType.OBSERVATION,
        model_version="GPR-Lemoine-2016", source_label="Lemoine et al. 2016",
        method_uri="https://doi.org/10.1136/gutjnl-2015-309260",
    ),
    _runtime(
        "ipag_copd_questionnaire", "IPAG COPD Diagnostic Questionnaire",
        "copd_screening_score", ClinicalSystem.RESPIRATORY,
        ("age", "pack_years", "bmi", "weather_affected_cough", "sputum_without_cold", "morning_sputum", "wheeze_sometimes_or_often", "allergy_history"),
        output_resource=FHIRResultType.OBSERVATION, model_version="IPAG-CDQ-Price-2005",
        source_label="Price et al. 2005", method_uri="https://pmc.ncbi.nlm.nih.gov/articles/PMC1513460/",
    ),
    _runtime(
        "mci_to_ad_3y", "Amnestic MCI to Probable Alzheimer Disease Score",
        "mci_to_alzheimer_3_year_score", ClinicalSystem.NEUROCOGNITIVE,
        ("has_amnestic_mci", "sex", "stubborn_or_resistive", "upset_when_separated_from_caregiver", "difficulty_shopping_alone", "forgets_appointments", "mean_words_recalled", "orientation_correct", "clock_drawing_score"),
        output_resource=FHIRResultType.OBSERVATION, model_version="MCI-AD-Barnes-2014",
        source_label="Barnes et al. 2014", time_horizon="3 years", method_uri="https://pubmed.ncbi.nlm.nih.gov/25486250/",
    ),
    _runtime(
        "anu_adri", "Australian National University Alzheimer Disease Risk Index",
        "alzheimer_disease_risk_index", ClinicalSystem.NEUROCOGNITIVE,
        ("age", "sex", "education_years", "bmi", "has_diabetes", "depressive_symptoms", "high_cholesterol", "traumatic_brain_injury", "smoking_status", "alcohol_category", "social_engagement_level", "physical_activity_level", "cognitive_activity_level", "fish_servings_per_week", "pesticide_exposure"),
        output_resource=FHIRResultType.OBSERVATION, model_version="ANU-ADRI-Anstey-2013",
        source_label="Anstey et al. 2013", method_uri="https://pmc.ncbi.nlm.nih.gov/articles/PMC3696462/",
    ),
    _runtime(
        "brock_pancan_pulmonary_nodule", "Brock/PanCan Pulmonary Nodule Model",
        "pulmonary_nodule_malignancy", ClinicalSystem.RESPIRATORY,
        ("age", "sex", "family_history_lung_cancer", "has_emphysema", "pulmonary_nodule_diameter", "nodule_type", "nodule_upper_lobe", "nodule_count", "nodule_spiculation"),
        model_version="Brock-PanCan-full-spiculation", source_label="McWilliams et al. 2013",
        method_uri="https://pmc.ncbi.nlm.nih.gov/articles/PMC3951177/", score_represents_probability=True,
    ),
    _runtime(
        "va_pulmonary_nodule", "Veterans Affairs Pulmonary Nodule Model",
        "pulmonary_nodule_malignancy", ClinicalSystem.RESPIRATORY,
        ("age", "ever_smoker", "pulmonary_nodule_diameter", "years_since_quitting"),
        model_version="VA-SPN-Gould-2007", source_label="Gould et al. VA model",
        method_uri="https://pmc.ncbi.nlm.nih.gov/articles/PMC2882437/", score_represents_probability=True,
    ),
    _runtime(
        "caide_dementia_20y", "CAIDE Dementia Risk Score",
        "dementia_20_year_risk_score", ClinicalSystem.NEUROCOGNITIVE,
        ("age", "sex", "education_years", "systolic_bp", "bmi", "total_cholesterol", "physical_activity_active"),
        output_resource=FHIRResultType.OBSERVATION, model_version="CAIDE-Kivipelto-2006-clinical",
        source_label="Kivipelto et al. 2006", time_horizon="20 years", method_uri="https://doi.org/10.1016/S1474-4422(06)70537-3",
    ),
    _runtime(
        "bdsi_dementia_6y", "Brief Dementia Screening Indicator",
        "dementia_6_year_screening_score", ClinicalSystem.NEUROCOGNITIVE,
        ("age", "education_years", "bmi", "has_diabetes", "stroke_tia_history", "needs_help_money_or_medications", "depressive_symptoms"),
        output_resource=FHIRResultType.OBSERVATION, model_version="BDSI-Barnes-2014",
        source_label="Barnes et al. 2014", time_horizon="6 years", method_uri="https://doi.org/10.1016/j.jalz.2013.11.006",
    ),
)


@dataclass(frozen=True, slots=True)
class ReviewInputDeclaration:
    """An extracted input awaiting deliberate canonical-field onboarding."""

    source_name: str
    declared_type: VariableDataType
    declared_unit: Optional[str]
    encoding: Optional[str]
    constraints: Optional[str]

    @property
    def onboarding_status(self) -> str:
        return "unmapped_pending_clinical_onboarding"

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "declared_type": self.declared_type.value,
            "declared_unit": self.declared_unit,
            "encoding": self.encoding,
            "constraints": self.constraints,
            "onboarding_status": self.onboarding_status,
        }


@dataclass(frozen=True, slots=True)
class ReviewCandidateMetadata:
    """Validated discovery metadata with no executable formula or enable flag."""

    algorithm_id: str
    display_name: str
    source_category: str
    clinical_system: ClinicalSystem
    output_resource: FHIRResultType
    declared_output: str
    target: Optional[str]
    time_horizon: Optional[str]
    population: Optional[str]
    declared_inputs: tuple[ReviewInputDeclaration, ...]
    source_locations: tuple[str, ...]
    literature: tuple[str, ...]
    issues: tuple[str, ...]
    catalog_schema_version: str

    def __post_init__(self) -> None:
        _validate_algorithm_id(self.algorithm_id)
        input_names = [item.source_name for item in self.declared_inputs]
        if len(input_names) != len(set(input_names)):
            raise CatalogInvariantError(f"Review candidate {self.algorithm_id!r} repeats an input name")
        if not self.source_locations:
            raise CatalogInvariantError(f"Review candidate {self.algorithm_id!r} has no source location")

    @property
    def governance_status(self) -> str:
        return "clinical_review_required"

    @property
    def runtime_enabled(self) -> bool:
        return False

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "catalog_kind": "review_candidate",
            "algorithm_id": self.algorithm_id,
            "display_name": self.display_name,
            "clinical_system": self.clinical_system.value,
            "source_category": self.source_category,
            "fhir_output": self.output_resource.value,
            "governance_status": self.governance_status,
            "runtime_enabled": self.runtime_enabled,
            "declared_output": self.declared_output,
            "target": self.target,
            "time_horizon": self.time_horizon,
            "population": self.population,
            "declared_inputs": [item.to_public_dict() for item in self.declared_inputs],
            "source_locations": list(self.source_locations),
            "literature": list(self.literature),
            "issues": list(self.issues),
            "catalog_schema_version": self.catalog_schema_version,
        }


@dataclass(frozen=True, slots=True)
class ReviewCatalogSnapshot:
    schema_version: str
    candidates: tuple[ReviewCandidateMetadata, ...]
    omitted_record_count: int
    source_path: Path

    @property
    def candidate_ids(self) -> tuple[str, ...]:
        return tuple(candidate.algorithm_id for candidate in self.candidates)

    def find(self, algorithm_id: str) -> Optional[ReviewCandidateMetadata]:
        return next((candidate for candidate in self.candidates if candidate.algorithm_id == algorithm_id), None)

    def to_public_list(self) -> list[dict[str, Any]]:
        return [candidate.to_public_dict() for candidate in self.candidates]


_SOURCE_CATEGORY_TO_SYSTEM: Mapping[str, ClinicalSystem] = MappingProxyType(
    {
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
)


def load_review_catalog(
    catalog_path: Path | str = DEFAULT_REVIEW_CATALOG_PATH,
    schema_path: Path | str = DEFAULT_REVIEW_SCHEMA_PATH,
) -> ReviewCatalogSnapshot:
    """Validate and load clinically reviewable, non-executable candidates.

    The complete source document is schema-validated first. Only records with
    ``candidate_after_clinical_validation`` are then transformed. Blocked and
    reference-only records are not instantiated and cannot leak through the
    returned object.
    """

    resolved_catalog_path = Path(catalog_path).resolve()
    resolved_schema_path = Path(schema_path).resolve()
    payload = _read_json_object(resolved_catalog_path, "algorithm catalog")
    schema = _read_json_object(resolved_schema_path, "algorithm catalog schema")
    _validate_against_schema(payload, schema)
    _validate_raw_catalog_invariants(payload)

    schema_version = payload["schema_version"]
    candidates = tuple(
        _candidate_from_record(record, schema_version)
        for record in payload["algorithms"]
        if record["implementation_status"] == REVIEWABLE_STATUS
    )
    omitted_record_count = len(payload["algorithms"]) - len(candidates)
    return ReviewCatalogSnapshot(
        schema_version=schema_version,
        candidates=candidates,
        omitted_record_count=omitted_record_count,
        source_path=resolved_catalog_path,
    )


@dataclass(frozen=True, slots=True)
class RiskAlgorithmRegistry:
    runtime_algorithms: tuple[RuntimeAlgorithmMetadata, ...] = RUNTIME_ALGORITHMS
    review_candidates: tuple[ReviewCandidateMetadata, ...] = ()

    def __post_init__(self) -> None:
        runtime_ids = [metadata.algorithm_id for metadata in self.runtime_algorithms]
        review_ids = [metadata.algorithm_id for metadata in self.review_candidates]
        if len(runtime_ids) != len(set(runtime_ids)):
            raise CatalogInvariantError("Duplicate runtime algorithm id")
        if len(review_ids) != len(set(review_ids)):
            raise CatalogInvariantError("Duplicate review-candidate algorithm id")
        overlap = set(runtime_ids).intersection(review_ids)
        if overlap:
            raise CatalogInvariantError(
                "A review candidate cannot shadow a runtime-approved algorithm: " + ", ".join(sorted(overlap))
            )
        missing_localizations = set(runtime_ids).difference(ALGORITHM_DISPLAY_NAMES_ZH)
        if missing_localizations:
            raise CatalogInvariantError(
                "Runtime algorithms are missing Traditional Chinese display names: "
                + ", ".join(sorted(missing_localizations))
            )

    def get_runtime(self, algorithm_id: str) -> Optional[RuntimeAlgorithmMetadata]:
        return next((item for item in self.runtime_algorithms if item.algorithm_id == algorithm_id), None)

    def validate_required_inputs(
        self,
        algorithm_id: str,
        data: Mapping[str, Any],
    ) -> RequiredInputValidation:
        """Validate required values using the registry's canonical contracts."""

        metadata = self.get_runtime(algorithm_id)
        if metadata is None:
            raise CatalogInvariantError(f"Unknown runtime algorithm: {algorithm_id!r}")
        values: dict[str, Any] = {}
        missing = []
        for field in metadata.required_inputs:
            normalized = CLINICAL_VARIABLES[field].normalize(data.get(field))
            values[field] = normalized
            if normalized is None:
                missing.append(field)
        return RequiredInputValidation(
            algorithm_id=algorithm_id,
            values=MappingProxyType(values),
            missing_fields=tuple(missing),
        )

    def get_review_candidate(self, algorithm_id: str) -> Optional[ReviewCandidateMetadata]:
        return next((item for item in self.review_candidates if item.algorithm_id == algorithm_id), None)

    def grouped(self, *, include_review_candidates: bool = False) -> dict[ClinicalSystem, tuple[Any, ...]]:
        algorithms: Iterable[RuntimeAlgorithmMetadata | ReviewCandidateMetadata] = self.runtime_algorithms
        if include_review_candidates:
            algorithms = (*self.runtime_algorithms, *self.review_candidates)
        grouped: dict[ClinicalSystem, list[Any]] = {system: [] for system in ClinicalSystem}
        for algorithm in algorithms:
            grouped[algorithm.clinical_system].append(algorithm)
        return {
            system: tuple(sorted(items, key=lambda item: (item.display_name.casefold(), item.algorithm_id)))
            for system, items in grouped.items()
        }

    def to_frontend_payload(
        self,
        *,
        include_review_candidates: bool = False,
        include_empty_systems: bool = False,
    ) -> dict[str, Any]:
        groups = self.grouped(include_review_candidates=include_review_candidates)
        visible_algorithms: tuple[RuntimeAlgorithmMetadata | ReviewCandidateMetadata, ...] = (
            self.runtime_algorithms
        )
        if include_review_candidates:
            visible_algorithms = (*self.runtime_algorithms, *self.review_candidates)
        systems = []
        for definition in CLINICAL_SYSTEM_DEFINITIONS:
            algorithms = groups[definition.code]
            if not algorithms and not include_empty_systems:
                continue
            system_payload = definition.to_public_dict()
            system_payload["algorithms"] = [algorithm.to_public_dict() for algorithm in algorithms]
            systems.append(system_payload)
        return {
            "catalog_version": RUNTIME_CATALOG_VERSION,
            "counts": {
                "total_models": len(visible_algorithms),
                "runtime_catalog_models": len(self.runtime_algorithms),
                "executable_models": sum(
                    1 for algorithm in self.runtime_algorithms if algorithm.runtime_enabled
                ),
                "clinical_review_required_models": sum(
                    1
                    for algorithm in visible_algorithms
                    if algorithm.governance_status == CLINICAL_REVIEW_REQUIRED_STATUS
                ),
                "review_candidate_models": (
                    len(self.review_candidates) if include_review_candidates else 0
                ),
            },
            "systems": systems,
        }


def runtime_registry() -> RiskAlgorithmRegistry:
    """Return the registry used for execution and normal frontend display."""

    return RiskAlgorithmRegistry()


def registry_with_review_candidates(
    catalog_path: Path | str = DEFAULT_REVIEW_CATALOG_PATH,
    schema_path: Path | str = DEFAULT_REVIEW_SCHEMA_PATH,
) -> RiskAlgorithmRegistry:
    """Return runtime metadata plus explicitly requested review-only records."""

    review_catalog = load_review_catalog(catalog_path, schema_path)
    runtime_ids = {metadata.algorithm_id for metadata in RUNTIME_ALGORITHMS}
    # The extraction catalog remains immutable audit input after promotion.
    # Promoted records are represented only by their governed runtime metadata,
    # never duplicated as stale review cards.
    pending = tuple(
        candidate
        for candidate in review_catalog.candidates
        if candidate.algorithm_id not in runtime_ids
    )
    return RiskAlgorithmRegistry(review_candidates=pending)


@lru_cache(maxsize=1)
def public_algorithm_catalog() -> dict[str, Any]:
    """Return the complete non-conflicted catalog for authenticated product UI.

    Review candidates remain metadata-only: no extracted formula is exposed or
    executed. ``blocked_source_conflict`` records were discarded by the loader
    before this payload is built.
    """

    return registry_with_review_candidates().to_frontend_payload(
        include_review_candidates=True,
        include_empty_systems=True,
    )


def _candidate_from_record(record: Mapping[str, Any], schema_version: str) -> ReviewCandidateMetadata:
    try:
        clinical_system = _SOURCE_CATEGORY_TO_SYSTEM[record["category"]]
    except KeyError as exc:
        raise CatalogInvariantError(
            f"Review candidate {record['id']!r} has unmapped source category {record['category']!r}"
        ) from exc

    try:
        output_resource = FHIRResultType(record["fhir_output"])
    except (KeyError, ValueError) as exc:
        raise CatalogInvariantError(
            f"Review candidate {record['id']!r} must declare a supported fhir_output"
        ) from exc

    declared_inputs = tuple(
        ReviewInputDeclaration(
            source_name=item["name"],
            declared_type=VariableDataType(item["type"]),
            declared_unit=item.get("unit"),
            encoding=item.get("encoding"),
            constraints=item.get("constraints"),
        )
        for item in record["inputs"]
    )
    return ReviewCandidateMetadata(
        algorithm_id=record["id"],
        display_name=record["name"],
        source_category=record["category"],
        clinical_system=clinical_system,
        output_resource=output_resource,
        declared_output=record.get("output") or "unspecified",
        target=record.get("target"),
        time_horizon=record.get("time_horizon"),
        population=record.get("population"),
        declared_inputs=declared_inputs,
        source_locations=tuple(record["source_locations"]),
        literature=tuple(record.get("literature") or ()),
        issues=tuple(record.get("issues") or ()),
        catalog_schema_version=schema_version,
    )


def _read_json_object(path: Path, description: str) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError as exc:
        raise CatalogSchemaValidationError(f"Missing {description}: {path}") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CatalogSchemaValidationError(f"Cannot read {description} {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise CatalogSchemaValidationError(f"{description.capitalize()} root must be a JSON object")
    return payload


def _validate_against_schema(payload: Mapping[str, Any], schema: Mapping[str, Any]) -> None:
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise CatalogSchemaValidationError(f"Invalid algorithm catalog schema: {exc.message}") from exc
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda item: list(item.absolute_path))
    if not errors:
        return
    details = []
    for error in errors[:20]:
        path = ".".join(str(part) for part in error.absolute_path) or "<root>"
        details.append(f"{path}: {error.message}")
    if len(errors) > 20:
        details.append(f"... and {len(errors) - 20} more schema errors")
    raise CatalogSchemaValidationError("Algorithm catalog schema validation failed: " + "; ".join(details))


def _validate_raw_catalog_invariants(payload: Mapping[str, Any]) -> None:
    schema_version = payload.get("schema_version")
    if not isinstance(schema_version, str) or not schema_version.strip():
        raise CatalogInvariantError("Catalog schema_version must be a non-empty string")
    records = payload.get("algorithms")
    if not isinstance(records, list):
        raise CatalogInvariantError("Catalog algorithms must be a list")
    ids = [record["id"] for record in records]
    duplicates = sorted({algorithm_id for algorithm_id in ids if ids.count(algorithm_id) > 1})
    if duplicates:
        raise CatalogInvariantError("Duplicate extracted algorithm ids: " + ", ".join(duplicates))
    for record in records:
        _validate_algorithm_id(record["id"])
        input_names = [item["name"] for item in record["inputs"]]
        if len(input_names) != len(set(input_names)):
            raise CatalogInvariantError(f"Algorithm {record['id']!r} repeats an extracted input name")
        if record["implementation_status"] == REVIEWABLE_STATUS:
            if not isinstance(record.get("formula"), str) or not record["formula"].strip():
                raise CatalogInvariantError(f"Review candidate {record['id']!r} has no extracted formula")
            if not isinstance(record.get("output"), str) or not record["output"].strip():
                raise CatalogInvariantError(f"Review candidate {record['id']!r} has no declared output")
            if not input_names:
                raise CatalogInvariantError(f"Review candidate {record['id']!r} has no declared inputs")
            if record.get("fhir_output") not in {item.value for item in FHIRResultType}:
                raise CatalogInvariantError(f"Review candidate {record['id']!r} has no supported FHIR output")


__all__ = [
    "CatalogError",
    "CatalogInvariantError",
    "CatalogSchemaValidationError",
    "ALGORITHM_DISPLAY_NAMES_ZH",
    "CORE_MODEL_VERSION",
    "ClinicalSourceKind",
    "ClinicalSystem",
    "ClinicalSystemDefinition",
    "ClinicalVariableContract",
    "CLINICAL_SYSTEM_DEFINITIONS",
    "CLINICAL_VARIABLES",
    "DEFAULT_REVIEW_CATALOG_PATH",
    "DEFAULT_REVIEW_SCHEMA_PATH",
    "FHIRResultType",
    "ReviewCandidateMetadata",
    "ReviewCatalogSnapshot",
    "ReviewInputDeclaration",
    "RequiredInputValidation",
    "RiskAlgorithmRegistry",
    "RUNTIME_ALGORITHMS",
    "RUNTIME_CATALOG_VERSION",
    "RuntimeAlgorithmMetadata",
    "VariableDataType",
    "algorithm_display_name_zh",
    "load_review_catalog",
    "public_algorithm_catalog",
    "registry_with_review_candidates",
    "runtime_registry",
]
