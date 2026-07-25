from dataclasses import dataclass
from datetime import date, datetime, time, timezone as dt_timezone
from typing import Any, Dict, Iterable, Optional
from uuid import UUID

from django.utils import timezone

from apps.clinical.health_screening.models import (
    HealthScreening,
    LaboratoryResults,
    Observation,
    Problem,
    QuestionnaireResponse,
)
from apps.clinical.patients.models import Patient
from apps.integration.fhir_integration.models import FHIRResourceMapping

from .algorithm_registry import CLINICAL_VARIABLES
from .clinical_math import CKD_EPI_2021_URI, CKD_EPI_2021_VERSION, calculate_egfr_2021
from .clinical_units import (
    NormalizedClinicalQuantity,
    assume_legacy_canonical_quantity,
    canonical_unit_for,
    normalize_observation_quantity,
)


@dataclass
class ClinicalSnapshot:
    data: Dict[str, Any]
    sources: Dict[str, Any]


@dataclass
class ClinicalDataCandidate:
    field: str
    value: Any
    effective_at: Any
    source: Dict[str, Any]
    source_priority: int


class DiseaseRiskInputRepository:
    """Builds CORE.xlsx style input vectors from the product clinical schema."""

    OBSERVATION_ALIASES = {
        "body_height": {"types": {"body_height", "height"}, "codes": {"8302-2"}, "text": {"height"}},
        "body_weight": {"types": {"body_weight", "weight"}, "codes": {"29463-7"}, "text": {"weight"}},
        "bmi": {"types": {"bmi", "body_mass_index"}, "codes": {"39156-5"}, "text": {"bmi", "body mass index"}},
        "waist_circumference": {"types": {"waist_circumference", "waist"}, "codes": {"8280-0"}, "text": {"waist"}},
        "hip_circumference": {"types": {"hip_circumference", "hip"}, "codes": {"56074-8"}, "text": {"hip"}},
        "alcohol_drinks_per_week": {"types": {"alcohol_drinks_per_week", "drinks_per_week"}, "codes": {"74013-4"}, "text": {"alcoholic drinks"}},
        "heart_rate": {"types": {"heart_rate", "resting_heart_rate"}, "codes": {"8867-4"}, "text": {"heart rate", "pulse"}},
        "systolic_bp": {"types": {"systolic_bp", "systolic_blood_pressure"}, "codes": {"8480-6"}, "text": {"systolic"}},
        "diastolic_bp": {"types": {"diastolic_bp", "diastolic_blood_pressure"}, "codes": {"8462-4"}, "text": {"diastolic"}},
        "fasting_glucose": {
            "types": {"fasting_glucose", "glucose", "fpg"},
            "codes": {"1558-6"},
            "text": {"glucose", "fpg"},
        },
        "total_cholesterol": {"types": {"total_cholesterol", "tc"}, "codes": {"2093-3"}, "text": {"total cholesterol"}},
        "hdl_cholesterol": {"types": {"hdl_cholesterol", "hdl"}, "codes": {"2085-9"}, "text": {"hdl"}},
        "triglycerides": {"types": {"triglycerides", "tg"}, "codes": {"2571-8"}, "text": {"triglyceride", "tg"}},
        "creatinine": {"types": {"creatinine", "serum_creatinine"}, "codes": {"2160-0"}, "text": {"creatinine"}},
        "egfr": {
            "types": {"egfr", "estimated_glomerular_filtration_rate"},
            "codes": {"33914-3", "48642-3", "62238-1", "98979-8"},
            "text": {"egfr", "glomerular filtration rate"},
        },
        "alt_gpt": {"types": {"alt_gpt", "alt"}, "codes": {"1742-6"}, "text": {"alanine", "alt"}},
        "ast_got": {"types": {"ast_got", "ast"}, "codes": {"1920-8"}, "text": {"aspartate", "ast"}},
        "ast_uln": {"types": {"ast_uln"}, "codes": {"1916-6"}, "text": {"ast upper"}},
        "ggt": {"types": {"ggt"}, "codes": {"2324-2"}, "text": {"gamma glutamyl", "ggt"}},
        "ggt_uln": {"types": {"ggt_uln", "ggt_upper_limit"}, "codes": {"allcare365-ggt-uln"}, "text": {"ggt upper"}},
        "platelet_count": {"types": {"platelet_count", "platelet"}, "codes": {"777-3"}, "text": {"platelet"}},
        "albumin": {"types": {"albumin"}, "codes": {"1751-7"}, "text": {"albumin"}},
        "insulin": {"types": {"insulin"}, "codes": {"20448-7"}, "text": {"insulin"}},
        "rdw": {"types": {"rdw"}, "codes": {"788-0"}, "text": {"red cell distribution width", "rdw"}},
        "mean_platelet_volume": {"types": {"mean_platelet_volume", "mpv"}, "codes": {"32623-1"}, "text": {"mean platelet volume", "mpv"}},
        "hba1c": {"types": {"hba1c", "glycated_hemoglobin"}, "codes": {"4548-4"}, "text": {"hba1c", "hemoglobin a1c"}},
        "hs_crp": {"types": {"hs_crp", "high_sensitivity_crp"}, "codes": {"30522-7"}, "text": {"high sensitivity crp", "hs-crp"}},
        "microalbumin_excretion_rate": {"types": {"microalbumin_excretion_rate"}, "codes": {"14956-7"}, "text": {"albumin excretion rate"}},
        "pulmonary_nodule_diameter": {"types": {"pulmonary_nodule_diameter"}, "codes": {"allcare365-nodule-diameter"}, "text": {"pulmonary nodule diameter"}},
        "urine_albumin_creatinine_ratio": {"types": {"urine_albumin_creatinine_ratio", "uacr"}, "codes": {"9318-7"}, "text": {"albumin/creatinine"}},
        "apoe_e4": {"types": {"apoe_e4"}, "codes": {"79713-2"}, "text": {"apoe"}},
    }

    QUESTIONNAIRE_BOOL_FIELDS = {
        "family_history_diabetes": [["family", "diabetes"]],
        "anti_hypertensive_drugs": [
            ["anti", "hyper"],
            ["bp", "treat"],
            ["hypertension", "treated"],
            ["hypertension_treated"],
        ],
        "using_lipid_lowering_drugs": [
            ["lipid", "drug"],
            ["statin"],
            ["lipid", "lowering"],
            ["dys", "rx"],
            ["lipid_lowering_treated"],
        ],
        "statin_use": [["statin"]],
        "has_diabetes": [["dm", "treated"], ["dm_treated"], ["t2dm"], ["diabetes", "treated"], ["has", "diabetes"]],
        "prediabetes": [["predm"], ["pre", "diabetes"], ["prediabetes"]],
        "metabolic_syndrome": [["metabolic", "syndrome"], ["metabolic_syndrome"]],
        "has_hypertension": [["has", "hypertension"], ["hypertension"], ["htn"]],
        "vegetables_daily": [["vegetable"], ["vege"], ["vegetables_daily"]],
        "physical_activity_active": [["exercise"], ["physical", "activity"], ["physical_activity_active"]],
        "moderate_alcohol": [["moderate", "drink"], ["moderate_alcohol"]],
        "heavy_alcohol": [["heavy", "drink"], ["heavy_alcohol"]],
        "is_smoker": [["current", "smok"], ["is_smoker"], ["smoking_status"]],
        "former_smoker": [["former", "smok"]],
        "chd_history": [["chd"]],
        "cvd_history": [["cvd"]],
        "pvd_history": [["pvd"]],
        "prescribed_steroids": [["prescribed", "steroids"]],
        "family_history_diabetes_both": [["family", "diabetes", "both"]],
        "depression_or_antidepressant": [["depression"], ["antidepressant"]],
        "aspirin_use": [["aspirin"]],
        "stroke_tia_history": [["stroke"], ["tia"]],
        "atrial_fibrillation": [["atrial", "fibrillation"]],
        "race_black": [["race", "black"]],
        "ethnicity_hispanic": [["ethnicity", "hispanic"]],
        "moderate_heavy_activity": [["moderate", "heavy", "activity"]],
        "ever_smoker": [["ever", "smoker"]],
        "extrathoracic_cancer_over_5y": [["extrathoracic", "cancer", "over", "5y"]],
        "nodule_spiculation": [["nodule", "spiculation"]],
        "nodule_upper_lobe": [["nodule", "upper", "lobe"]],
        "education_high_school_or_below": [["education", "high", "school", "or", "below"]],
        "ever_high_blood_glucose": [["ever", "high", "blood", "glucose"]],
        "ausdrisk_indigenous_or_pacific": [["ausdrisk", "indigenous", "or", "pacific"]],
        "ausdrisk_high_risk_birth_region": [["ausdrisk", "high", "risk", "birth", "region"]],
        "ausdrisk_lower_waist_threshold_group": [["ausdrisk", "lower", "waist", "threshold", "group"]],
        "ascvd_history": [["ascvd", "history"]],
        "heart_failure_history": [["heart", "failure", "history"]],
        "parental_mi_before_60": [["parental", "mi", "before", "60"]],
        "family_history_lung_cancer": [["family", "history", "lung", "cancer"]],
        "has_emphysema": [["has", "emphysema"]],
        "weather_affected_cough": [["weather", "affected", "cough"]],
        "sputum_without_cold": [["sputum", "without", "cold"]],
        "morning_sputum": [["morning", "sputum"]],
        "wheeze_sometimes_or_often": [["wheeze", "sometimes", "or", "often"]],
        "allergy_history": [["allergy", "history"]],
        "has_amnestic_mci": [["has", "amnestic", "mci"]],
        "stubborn_or_resistive": [["stubborn", "or", "resistive"]],
        "upset_when_separated_from_caregiver": [["upset", "when", "separated", "from", "caregiver"]],
        "difficulty_shopping_alone": [["difficulty", "shopping", "alone"]],
        "forgets_appointments": [["forgets", "appointments"]],
        "depressive_symptoms": [["depressive", "symptoms"]],
        "needs_help_money_or_medications": [["needs", "help", "money", "or", "medications"]],
        "high_cholesterol": [["high", "cholesterol"]],
        "traumatic_brain_injury": [["traumatic", "brain", "injury"]],
        "pesticide_exposure": [["pesticide", "exposure"]],
        "periodical_daily_cough": [["periodical", "daily", "cough"]],
    }

    QUESTIONNAIRE_SCALAR_FIELDS = (
        "parental_hypertension_count",
        "deprivation_quintile",
        "diabetes_duration_years",
        "education_years",
        "pack_years",
        "cigarettes_per_day",
        "years_since_quitting",
        "indoor_smoke_exposure_hours",
        "fish_servings_per_week",
        "mean_words_recalled",
        "orientation_correct",
        "clock_drawing_score",
        "nodule_count",
        "pce_race",
        "smoking_status",
        "alcohol_category",
        "social_engagement_level",
        "physical_activity_level",
        "cognitive_activity_level",
        "nodule_type",
        *(f"gad7_q{index}" for index in range(1, 8)),
    )

    LEGACY_VITAL_FIELDS = {
        "systolic_bp": "systolic_blood_pressure",
        "diastolic_bp": "diastolic_blood_pressure",
        "heart_rate": "heart_rate",
        "resting_heart_rate": "heart_rate",
        "body_height": "body_height",
        "body_weight": "body_weight",
    }

    LEGACY_LAB_ALIASES = {
        "fasting_glucose": {"glucose", "fpg", "fasting glucose"},
        "total_cholesterol": {"total cholesterol", "tc"},
        "hdl_cholesterol": {"hdl cholesterol", "hdl"},
        "triglycerides": {"triglyceride", "triglycerides", "tg"},
        "creatinine": {"creatinine", "serum creatinine"},
        "egfr": {"egfr", "glomerular filtration rate"},
        "alt_gpt": {"alt", "gpt", "alanine"},
        "ast_got": {"ast", "got", "aspartate"},
        "ast_uln": {"ast uln", "ast upper"},
        "ggt": {"ggt", "gamma glutamyl"},
        "platelet_count": {"platelet", "platelets"},
        "albumin": {"albumin"},
        "insulin": {"insulin"},
        "urine_albumin_creatinine_ratio": {"uacr", "albumin/creatinine", "albumin creatinine ratio"},
    }

    def get_patient(self, patient_id: str) -> Optional[Patient]:
        identifier = str(patient_id or "").strip()
        if not identifier:
            return None

        try:
            parsed_id = UUID(identifier)
        except (TypeError, ValueError, AttributeError):
            parsed_id = None
        if parsed_id is not None:
            patient = Patient.objects.filter(id=parsed_id).first()
            if patient is not None:
                return patient

        mrn_matches = list(
            Patient.objects.filter(medical_record_number=identifier).order_by("id")[:2]
        )
        return mrn_matches[0] if len(mrn_matches) == 1 else None

    def build_snapshot(
        self,
        patient: Patient,
        *,
        evaluation_as_of: Optional[date] = None,
    ) -> ClinicalSnapshot:
        as_of = evaluation_as_of or timezone.localdate()
        sex = self._canonical_sex(patient.sex)
        data: Dict[str, Any] = {
            "age": self._age_on(patient.date_of_birth, as_of),
            "sex": sex,
            "gender": sex,
            "evaluation_year": as_of.year,
        }
        patient_reference = self._mapped_fhir_reference(patient._meta.db_table, patient.id, "Patient")
        patient_source = {
            "table": patient._meta.db_table,
            "id": str(patient.id),
            "fhir_reference": patient_reference,
        }
        sources: Dict[str, Any] = {
            "patient_id": str(patient.id),
            "age": {
                **patient_source,
                "field": "date_of_birth",
                "evaluation_as_of": as_of.isoformat(),
            },
            "sex": {**patient_source, "field": "sex"},
            "evaluation_year": {
                "derived_from": "evaluation_as_of",
                "evaluation_as_of": as_of.isoformat(),
                "fhir_reference": patient_reference,
            },
        }

        self._add_product_observations(patient, data, sources)
        self._add_coded_observation_flags(patient, data, sources)
        self._add_questionnaire_flags(patient, data, sources)
        self._add_questionnaire_scalars(patient, data, sources)
        self._add_problem_flags(patient, data, sources)
        self._add_legacy_screening_fallback(patient, data, sources)

        if data.get("bmi") is None and data.get("body_height") and data.get("body_weight"):
            height_m = float(data["body_height"]) / 100
            if height_m > 0:
                data["bmi"] = round(float(data["body_weight"]) / (height_m**2), 2)
                sources["bmi"] = {
                    "derived_from": ["body_height", "body_weight"],
                    "source_fields": {
                        "body_height": sources.get("body_height"),
                        "body_weight": sources.get("body_weight"),
                    },
                    "selection_policy": "latest_available_per_field",
                    "normalized_unit": canonical_unit_for("bmi"),
                    "unit_handling": "derived_from_canonical_inputs",
                }
        if data.get("egfr") is None and data.get("creatinine") not in (None, ""):
            egfr = calculate_egfr_2021(data["creatinine"], data.get("age"), data.get("sex"))
            if egfr is not None:
                data["egfr"] = egfr
                sources["egfr"] = {
                    "derived_from": ["creatinine", "age", "sex"],
                    "formula": CKD_EPI_2021_VERSION,
                    "formula_uri": CKD_EPI_2021_URI,
                    "source_fields": {
                        "creatinine": sources.get("creatinine"),
                        "age": {"table": "patients", "id": str(patient.id), "field": "date_of_birth"},
                        "sex": {"table": "patients", "id": str(patient.id), "field": "sex"},
                    },
                    "selection_policy": "derive_only_when_reported_egfr_is_unavailable",
                    "normalized_unit": canonical_unit_for("egfr"),
                    "unit_handling": "derived_from_canonical_inputs",
                }
        if data.get("resting_heart_rate") is None and data.get("heart_rate") is not None:
            data["resting_heart_rate"] = data["heart_rate"]
            sources["resting_heart_rate"] = sources.get("heart_rate", {})
        if (
            data.get("waist_hip_ratio") is None
            and data.get("waist_circumference") is not None
            and data.get("hip_circumference") not in (None, 0)
        ):
            data["waist_hip_ratio"] = round(float(data["waist_circumference"]) / float(data["hip_circumference"]), 3)
            sources["waist_hip_ratio"] = {
                "derived_from": ["waist_circumference", "hip_circumference"],
                "source_fields": {
                    "waist_circumference": sources.get("waist_circumference"),
                    "hip_circumference": sources.get("hip_circumference"),
                },
                "selection_policy": "latest_available_per_field",
            }

        return ClinicalSnapshot(data=data, sources=sources)

    @staticmethod
    def _age_on(date_of_birth: Optional[date], as_of: date) -> Optional[int]:
        if date_of_birth is None or date_of_birth > as_of:
            return None
        return as_of.year - date_of_birth.year - (
            (as_of.month, as_of.day) < (date_of_birth.month, date_of_birth.day)
        )

    @staticmethod
    def _canonical_sex(value: Any) -> Optional[str]:
        normalized = str(value or "").strip().upper()
        if normalized in {"M", "MALE"}:
            return "M"
        if normalized in {"F", "FEMALE"}:
            return "F"
        return None

    def _add_product_observations(self, patient: Patient, data: Dict[str, Any], sources: Dict[str, Any]) -> None:
        observations = list(
            Observation.objects.filter(patient=patient, is_active=True)
            .order_by("-effective_at", "-created_at")
            .select_related("encounter")
        )
        for field in self.OBSERVATION_ALIASES:
            candidates = []
            for observation in observations:
                if not self._observation_matches(observation, field):
                    continue
                quantity = self._observation_quantity(observation, field)
                if quantity is None:
                    continue
                candidates.append(
                    ClinicalDataCandidate(
                        field=field,
                        value=quantity.value,
                        effective_at=observation.effective_at or observation.created_at,
                        source={
                            "table": "observations",
                            "id": str(observation.id),
                            "code": observation.code,
                            "display": observation.display,
                            "original_unit": quantity.original_unit,
                            "source_unit_display": self._observation_unit_display(observation),
                            "source_unit_code": self._observation_unit_code(observation),
                            "normalized_unit": quantity.normalized_unit,
                            "unit_conversion": quantity.conversion,
                            "unit_handling": "explicit_observation_unit",
                            "fhir_reference": self._fhir_reference(observation),
                            "effective_at": self._iso_datetime(observation.effective_at or observation.created_at),
                        },
                        source_priority=30,
                    )
                )
            self._apply_latest_candidate(data, sources, field, candidates)

        systolic_candidates = []
        diastolic_candidates = []
        for bp_observation in (
            observation
            for observation in observations
            if observation.observation_type == "blood_pressure" or observation.code == "85354-9"
        ):
            effective_at = bp_observation.effective_at or bp_observation.created_at
            source = {
                "table": "observations",
                "id": str(bp_observation.id),
                "code": bp_observation.code,
                "display": bp_observation.display,
                "fhir_reference": self._fhir_reference(bp_observation),
                "effective_at": self._iso_datetime(effective_at),
            }
            systolic = self._component_quantity(
                bp_observation.component_json,
                {"8480-6", "systolic", "sbp"},
                "systolic_bp",
            )
            diastolic = self._component_quantity(
                bp_observation.component_json,
                {"8462-4", "diastolic", "dbp"},
                "diastolic_bp",
            )
            if systolic is not None:
                systolic_candidates.append(
                    ClinicalDataCandidate(
                        "systolic_bp",
                        systolic.value,
                        effective_at,
                        {
                            **source,
                            "original_unit": systolic.original_unit,
                            "normalized_unit": systolic.normalized_unit,
                            "unit_conversion": systolic.conversion,
                            "unit_handling": "explicit_observation_component_unit",
                        },
                        source_priority=30,
                    )
                )
            if diastolic is not None:
                diastolic_candidates.append(
                    ClinicalDataCandidate(
                        "diastolic_bp",
                        diastolic.value,
                        effective_at,
                        {
                            **source,
                            "original_unit": diastolic.original_unit,
                            "normalized_unit": diastolic.normalized_unit,
                            "unit_conversion": diastolic.conversion,
                            "unit_handling": "explicit_observation_component_unit",
                        },
                        source_priority=30,
                    )
                )
        self._apply_latest_candidate(data, sources, "systolic_bp", systolic_candidates)
        self._apply_latest_candidate(data, sources, "diastolic_bp", diastolic_candidates)

    def _add_questionnaire_flags(self, patient: Patient, data: Dict[str, Any], sources: Dict[str, Any]) -> None:
        responses = list(
            QuestionnaireResponse.objects.filter(patient=patient, is_active=True)
            .order_by("-authored_at", "-created_at")
            .select_related("encounter")
        )
        if not responses:
            return
        for field, token_groups in self.QUESTIONNAIRE_BOOL_FIELDS.items():
            candidates = []
            for response in responses:
                payload = {}
                payload.update(response.response_json or {})
                payload.update(response.score_json or {})
                if response.source_type == "fhir_import":
                    value = self._find_exact_fhir_bool(payload, field)
                else:
                    value = self._find_bool(payload, token_groups)
                if value is None:
                    continue
                effective_at = response.authored_at or response.created_at
                candidates.append(
                    ClinicalDataCandidate(
                        field=field,
                        value=value,
                        effective_at=effective_at,
                        source={
                            "table": "questionnaire_responses",
                            "id": str(response.id),
                            "fhir_reference": self._questionnaire_fhir_reference(response),
                            "effective_at": self._iso_datetime(effective_at),
                        },
                        source_priority=20,
                    )
                )
            self._apply_latest_candidate(data, sources, field, candidates)

    def _add_questionnaire_scalars(self, patient: Patient, data: Dict[str, Any], sources: Dict[str, Any]) -> None:
        responses = list(
            QuestionnaireResponse.objects.filter(patient=patient, is_active=True)
            .order_by("-authored_at", "-created_at")
        )
        for field in self.QUESTIONNAIRE_SCALAR_FIELDS:
            contract = CLINICAL_VARIABLES[field]
            candidates = []
            for response in responses:
                payload = {**(response.response_json or {}), **(response.score_json or {})}
                accepted = {field.casefold(), *(alias.casefold() for alias in contract.source_aliases)}
                matches = [
                    contract.normalize(value)
                    for key, value in payload.items()
                    if str(key).strip().casefold() in accepted
                ]
                valid = [value for value in matches if value is not None]
                if not valid or not all(value == valid[0] for value in valid):
                    continue
                effective_at = response.authored_at or response.created_at
                candidates.append(
                    ClinicalDataCandidate(
                        field=field,
                        value=valid[0],
                        effective_at=effective_at,
                        source={
                            "table": "questionnaire_responses",
                            "id": str(response.id),
                            "fhir_reference": self._questionnaire_fhir_reference(response),
                            "effective_at": self._iso_datetime(effective_at),
                        },
                        source_priority=20,
                    )
                )
            self._apply_latest_candidate(data, sources, field, candidates)

    def _add_coded_observation_flags(self, patient: Patient, data: Dict[str, Any], sources: Dict[str, Any]) -> None:
        candidates = []
        observations = Observation.objects.filter(patient=patient, is_active=True, code="72166-2").order_by(
            "-effective_at", "-created_at"
        )
        for observation in observations:
            smoking = self._smoking_status_value(observation)
            if smoking is None:
                continue
            effective_at = observation.effective_at or observation.created_at
            candidates.append(
                ClinicalDataCandidate(
                    field="is_smoker",
                    value=smoking,
                    effective_at=effective_at,
                    source={
                        "table": "observations",
                        "id": str(observation.id),
                        "code": observation.code,
                        "display": observation.display,
                        "fhir_reference": self._fhir_reference(observation),
                        "effective_at": self._iso_datetime(effective_at),
                    },
                    source_priority=30,
                )
            )
        self._apply_latest_candidate(data, sources, "is_smoker", candidates)

    def _smoking_status_value(self, observation: Observation) -> Optional[bool]:
        raw_value = observation.value_json.get("raw_value") if isinstance(observation.value_json, dict) else None
        coding = []
        text = ""
        if isinstance(raw_value, dict):
            coding = raw_value.get("coding") or []
            text = str(raw_value.get("text") or "").lower()
        elif raw_value not in (None, ""):
            text = str(raw_value).lower()
        codes = {str(item.get("code") or "") for item in coding if isinstance(item, dict)}
        displays = " ".join(
            str(item.get("display") or "").lower() for item in coding if isinstance(item, dict)
        )
        current_codes = {
            "449868002",
            "428041000124106",
            "77176002",
            "428071000124103",
            "428061000124105",
        }
        non_current_codes = {"8517006", "266919005"}
        if codes.intersection(current_codes):
            return True
        if codes.intersection(non_current_codes):
            return False
        combined = f"{text} {displays}".strip()
        if any(token in combined for token in ("never smoker", "former smoker", "non-smoker", "nonsmoker")):
            return False
        if any(token in combined for token in ("current smoker", "every day smoker", "some day smoker")):
            return True
        return None

    def _add_problem_flags(self, patient: Patient, data: Dict[str, Any], sources: Dict[str, Any]) -> None:
        historical_problems = list(
            Problem.objects.filter(patient=patient, is_active=True)
            .exclude(status="entered-in-error")
            .order_by("-updated_at")
        )
        if not historical_problems:
            return
        active_problems = [
            problem
            for problem in historical_problems
            if str(problem.status or "").casefold() not in {"inactive", "resolved"}
        ]
        combined = " ".join(problem.problem_name or "" for problem in active_problems).lower()
        historical_combined = " ".join(
            problem.problem_name or "" for problem in historical_problems
        ).lower()
        diabetes_tokens = ("diabetes", "糖尿病")
        hypertension_tokens = ("hypertension", "高血壓")
        cvd_tokens = (
            "myocardial infarction",
            "coronary artery disease",
            "atherosclerotic cardiovascular",
            "heart failure",
            "stroke",
            "心肌梗塞",
            "冠狀動脈",
            "心衰竭",
            "心臟衰竭",
            "中風",
            "腦卒中",
        )
        chd_tokens = (
            "myocardial infarction",
            "coronary artery disease",
            "ischemic heart disease",
            "心肌梗塞",
            "冠狀動脈",
            "缺血性心臟病",
        )
        pvd_tokens = (
            "peripheral vascular disease",
            "peripheral artery disease",
            "peripheral arterial disease",
            "周邊血管疾病",
            "周邊動脈疾病",
        )
        mapping_by_problem_id = self._problem_fhir_mappings(historical_problems)
        historical_codes = {
            code
            for mapping in mapping_by_problem_id.values()
            for code in self._coding_values(mapping.fhir_json.get("code") or {})
        }
        chd_codes = {"22298006", "53741008", "41400", "I21", "I25"}
        stroke_codes = {"230690007", "I63", "I64"}
        heart_failure_codes = {"84114007", "I50"}
        pvd_codes = {"400047006", "399957001", "I70.2", "I73.9"}
        historical_references = [
            f"Condition/{mapping.fhir_resource_id}"
            for mapping in mapping_by_problem_id.values()
        ]
        source = {
            "table": "health_screening_problem",
            "ids": [str(problem.id) for problem in historical_problems],
            "fhir_references": historical_references,
            "selection_policy": "longitudinal_problem_history_excluding_entered_in_error",
        }
        if any(token in combined for token in diabetes_tokens):
            data["has_diabetes"] = True
            sources["has_diabetes"] = source
        if any(token in combined for token in hypertension_tokens):
            data["has_hypertension"] = True
            sources["has_hypertension"] = source
        if (
            any(token in historical_combined for token in cvd_tokens)
            or historical_codes.intersection(chd_codes | stroke_codes | heart_failure_codes | pvd_codes)
        ):
            data["cvd_history"] = True
            sources["cvd_history"] = source
        if any(token in historical_combined for token in chd_tokens) or historical_codes.intersection(chd_codes):
            data["chd_history"] = True
            sources["chd_history"] = source
        if any(token in historical_combined for token in pvd_tokens) or historical_codes.intersection(pvd_codes):
            data["pvd_history"] = True
            sources["pvd_history"] = source

    def _add_legacy_screening_fallback(self, patient: Patient, data: Dict[str, Any], sources: Dict[str, Any]) -> None:
        # Compatibility only: active ingestion now writes product observations.
        screenings = list(
            HealthScreening.objects.filter(patient=patient, is_active=True)
            .order_by("-screening_date", "-created_at")
            .prefetch_related("lab_results")
        )
        if not screenings:
            return
        sources.setdefault("legacy_health_screening_ids", [str(screening.id) for screening in screenings])
        product_backed_screening_ids = set(
            Observation.objects.filter(
                patient=patient,
                is_active=True,
                encounter__source_screening__in=screenings,
            ).values_list("encounter__source_screening_id", flat=True)
        )

        for field, model_attr in self.LEGACY_VITAL_FIELDS.items():
            candidates = []
            for screening in screenings:
                if screening.id in product_backed_screening_ids:
                    continue
                vitals = self._legacy_vitals(screening)
                if not vitals:
                    continue
                quantity = assume_legacy_canonical_quantity(
                    field,
                    self._float(getattr(vitals, model_attr, None)),
                )
                if quantity is None:
                    continue
                effective_at = screening.encounter_time or screening.screening_date or screening.created_at
                candidates.append(
                    ClinicalDataCandidate(
                        field=field,
                        value=quantity.value,
                        effective_at=effective_at,
                        source={
                            "table": "health_screening_vitalsigns",
                            "id": str(vitals.id),
                            "screening_id": str(screening.id),
                            "original_unit": quantity.original_unit,
                            "normalized_unit": quantity.normalized_unit,
                            "unit_conversion": quantity.conversion,
                            "unit_handling": "legacy_schema_contract",
                            "effective_at": self._iso_datetime(effective_at),
                        },
                        source_priority=10,
                    )
                )
            self._apply_latest_candidate(data, sources, field, candidates)

        for field, aliases in self.LEGACY_LAB_ALIASES.items():
            candidates = []
            for screening in screenings:
                if screening.id in product_backed_screening_ids:
                    continue
                for lab in screening.lab_results.filter(is_active=True):
                    name = (lab.test_name or "").lower()
                    if not any(alias in name for alias in aliases):
                        continue
                    value = self._float(lab.value_result)
                    # LaboratoryResults is a generic name/value/unit table, so a
                    # blank unit cannot inherit a field-specific canonical unit.
                    # Only typed legacy schema columns (VitalSigns above) may do so.
                    if not str(lab.result_unit or "").strip():
                        continue
                    quantity = normalize_observation_quantity(field, value, lab.result_unit)
                    unit_handling = "explicit_legacy_unit"
                    if quantity is None:
                        continue
                    effective_at = screening.encounter_time or screening.screening_date or lab.created_at
                    candidates.append(
                        ClinicalDataCandidate(
                            field=field,
                            value=quantity.value,
                            effective_at=effective_at,
                            source={
                                "table": "health_screening_laboratoryresults",
                                "id": str(lab.id),
                                "screening_id": str(screening.id),
                                "test_name": lab.test_name,
                                "original_unit": quantity.original_unit,
                                "normalized_unit": quantity.normalized_unit,
                                "unit_conversion": quantity.conversion,
                                "unit_handling": unit_handling,
                                "effective_at": self._iso_datetime(effective_at),
                            },
                            source_priority=10,
                        )
                    )
            self._apply_latest_candidate(data, sources, field, candidates)

    def _observation_matches(self, observation: Observation, field: str) -> bool:
        alias = self.OBSERVATION_ALIASES[field]
        observation_type = (observation.observation_type or "").lower()
        code = observation.code or ""
        display = (observation.display or "").lower()
        # Imported FHIR Observations are coded clinical records.  Only an exact
        # declared code may satisfy a risk input; display substrings and local
        # type labels are compatibility rules for non-FHIR product records.
        if observation.source_type == "fhir_import":
            return code in alias["codes"]
        if observation_type in alias["types"] or code in alias["codes"]:
            return True
        return any(token in display for token in alias["text"])

    def _observation_quantity(
        self,
        observation: Observation,
        field: str,
    ) -> Optional[NormalizedClinicalQuantity]:
        value = None
        if observation.value_quantity is not None:
            value = float(observation.value_quantity)
        elif isinstance(observation.value_json, dict):
            for key in ("value", "result", "numeric_value"):
                parsed = self._float(observation.value_json.get(key))
                if parsed is not None:
                    value = parsed
                    break
        if value is None:
            value = self._float(observation.value_string)
        return normalize_observation_quantity(
            field,
            value,
            self._declared_observation_unit(observation),
        )

    def _declared_observation_unit(self, observation: Observation) -> str:
        source_payload = observation.source_payload_json if isinstance(observation.source_payload_json, dict) else {}
        if observation.source_type == "fhir_import" and "valueQuantity" in source_payload:
            quantity = source_payload.get("valueQuantity")
            if not isinstance(quantity, dict):
                return ""
            return str(quantity.get("code") or quantity.get("unit") or "")
        return str(observation.value_unit or "")

    @staticmethod
    def _observation_unit_display(observation: Observation) -> str:
        source_payload = observation.source_payload_json if isinstance(observation.source_payload_json, dict) else {}
        quantity = source_payload.get("valueQuantity")
        if observation.source_type == "fhir_import" and isinstance(quantity, dict):
            return str(quantity.get("unit") or "")
        return str(observation.value_unit or "")

    @staticmethod
    def _observation_unit_code(observation: Observation) -> str:
        source_payload = observation.source_payload_json if isinstance(observation.source_payload_json, dict) else {}
        quantity = source_payload.get("valueQuantity")
        if observation.source_type == "fhir_import" and isinstance(quantity, dict):
            return str(quantity.get("code") or "")
        return ""

    def _fhir_reference(self, observation: Observation) -> Optional[str]:
        source_payload = observation.source_payload_json if isinstance(observation.source_payload_json, dict) else {}
        resource_id = source_payload.get("id")
        return f"Observation/{resource_id}" if resource_id else None

    def _component_quantity(
        self,
        components: Any,
        accepted_codes: set[str],
        field: str,
    ) -> Optional[NormalizedClinicalQuantity]:
        if not isinstance(components, list):
            return None
        for component in components:
            if not isinstance(component, dict):
                continue
            code = str(component.get("code") or "").lower()
            display = str(component.get("display") or "").lower()
            coding = component.get("code", {}).get("coding") if isinstance(component.get("code"), dict) else None
            coding_codes = {str(item.get("code", "")).lower() for item in coding or [] if isinstance(item, dict)}
            if code in accepted_codes or display in accepted_codes or coding_codes.intersection(accepted_codes):
                quantity = component.get("valueQuantity") if isinstance(component.get("valueQuantity"), dict) else {}
                value = component.get("value") if "value" in component else quantity.get("value")
                unit = component.get("unit") or quantity.get("code") or quantity.get("unit") or ""
                return normalize_observation_quantity(field, self._float(value), unit)
        return None

    def _find_bool(self, payload: Dict[str, Any], token_groups: list[list[str]]) -> Optional[bool]:
        for key, value in self._flatten_payload(payload).items():
            lowered_key = str(key).lower()
            if any(all(token in lowered_key for token in tokens) for tokens in token_groups):
                return self._bool(value)
        return None

    def _find_exact_fhir_bool(self, payload: Dict[str, Any], field: str) -> Optional[bool]:
        contract = CLINICAL_VARIABLES.get(field)
        accepted = {field.casefold()}
        if contract is not None:
            accepted.update(alias.casefold() for alias in contract.source_aliases)
        matches = [
            self._bool(value)
            for key, value in payload.items()
            if str(key).strip().casefold() in accepted
        ]
        valid = [value for value in matches if value is not None]
        if not valid:
            return None
        # Conflicting repeated linkIds are not silently resolved by order.
        return valid[0] if all(value == valid[0] for value in valid) else None

    def _questionnaire_fhir_reference(self, response: QuestionnaireResponse) -> Optional[str]:
        resource_id = (response.metadata_json or {}).get("fhir_resource_id")
        if not resource_id:
            return self._mapped_fhir_reference(
                response._meta.db_table,
                response.id,
                "QuestionnaireResponse",
            )
        return f"QuestionnaireResponse/{resource_id}"

    @staticmethod
    def _coding_values(codeable_concept: Dict[str, Any]) -> set[str]:
        values = set()
        for coding in codeable_concept.get("coding") or []:
            if not isinstance(coding, dict) or not coding.get("code"):
                continue
            code = str(coding["code"])
            values.add(code)
            values.add(code.upper())
            # Prefixes preserve clinically meaningful ICD families while
            # retaining the exact code in provenance.
            if code and code[0].isalpha():
                values.add(code[:3].upper())
        return values

    def _problem_fhir_mappings(self, problems: Iterable[Problem]) -> Dict[Any, FHIRResourceMapping]:
        problem_ids = [problem.id for problem in problems]
        mappings = FHIRResourceMapping.objects.filter(
            local_table=Problem._meta.db_table,
            local_id__in=problem_ids,
            fhir_resource_type="Condition",
        ).order_by("local_id", "created_at")
        by_id: Dict[Any, FHIRResourceMapping] = {}
        ambiguous = set()
        for mapping in mappings:
            if mapping.local_id in by_id:
                ambiguous.add(mapping.local_id)
            else:
                by_id[mapping.local_id] = mapping
        for local_id in ambiguous:
            by_id.pop(local_id, None)
        return by_id

    @staticmethod
    def _mapped_fhir_reference(
        local_table: str,
        local_id: Any,
        resource_type: str,
    ) -> Optional[str]:
        mappings = list(
            FHIRResourceMapping.objects.filter(
                local_table=local_table,
                local_id=local_id,
                fhir_resource_type=resource_type,
            ).order_by("created_at")[:2]
        )
        if len(mappings) != 1:
            return None
        return f"{resource_type}/{mappings[0].fhir_resource_id}"

    def _flatten_payload(self, payload: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        flattened = {}
        for key, value in payload.items():
            full_key = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(value, dict):
                flattened.update(self._flatten_payload(value, full_key))
            else:
                flattened[full_key] = value
        return flattened

    def _apply_latest_candidate(
        self,
        data: Dict[str, Any],
        sources: Dict[str, Any],
        field: str,
        candidates: Iterable[ClinicalDataCandidate],
    ) -> None:
        valid_candidates = [candidate for candidate in candidates if candidate.value not in (None, "")]
        if not valid_candidates:
            return
        selected = max(valid_candidates, key=self._candidate_sort_key)
        current_ts = self._source_timestamp(sources.get(field))
        selected_ts = self._timestamp(selected.effective_at)
        current_priority = self._source_priority(sources.get(field))
        if data.get(field) not in (None, ""):
            if current_ts > selected_ts:
                return
            if current_ts == selected_ts and current_priority > selected.source_priority:
                return
        data[field] = selected.value
        sources[field] = {
            **selected.source,
            "selection_policy": "latest_available_per_field",
            "source_priority": selected.source_priority,
        }

    def _candidate_sort_key(self, candidate: ClinicalDataCandidate) -> tuple[float, int]:
        return (self._timestamp(candidate.effective_at), candidate.source_priority)

    def _legacy_vitals(self, screening: HealthScreening) -> Any:
        try:
            return screening.vital_signs
        except Exception:
            return None

    def _timestamp(self, value: Any) -> float:
        if value in (None, ""):
            return float("-inf")
        if isinstance(value, datetime):
            current = value
        elif isinstance(value, date):
            current = datetime.combine(value, time.min)
        else:
            try:
                current = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            except ValueError:
                return float("-inf")
        if current.tzinfo is None:
            current = current.replace(tzinfo=dt_timezone.utc)
        return current.timestamp()

    def _source_timestamp(self, source: Any) -> float:
        if not isinstance(source, dict):
            return float("-inf")
        return self._timestamp(source.get("effective_at"))

    def _source_priority(self, source: Any) -> int:
        if not isinstance(source, dict):
            return -1
        return int(source.get("source_priority") or -1)

    def _iso_datetime(self, value: Any) -> Optional[str]:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return datetime.combine(value, time.min).isoformat()
        return str(value)

    def _float(self, value: Any) -> Optional[float]:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _bool(self, value: Any) -> Optional[bool]:
        if isinstance(value, bool):
            return value
        if value in (None, ""):
            return None
        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "y", "positive", "treated", "current"}:
            return True
        if normalized in {"0", "false", "no", "n", "negative", "untreated", "never", "former"}:
            return False
        return None
