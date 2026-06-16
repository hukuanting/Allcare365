from dataclasses import dataclass
from datetime import date, datetime, time, timezone as dt_timezone
from typing import Any, Dict, Iterable, Optional

from apps.clinical.health_screening.models import (
    HealthScreening,
    LaboratoryResults,
    Observation,
    Problem,
    QuestionnaireResponse,
)
from apps.clinical.patients.models import Patient


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
        "fasting_glucose": {
            "types": {"fasting_glucose", "glucose", "fpg"},
            "codes": {"1558-6", "2339-0", "2345-7"},
            "text": {"glucose", "fpg"},
        },
        "total_cholesterol": {"types": {"total_cholesterol", "tc"}, "codes": {"2093-3"}, "text": {"total cholesterol"}},
        "hdl_cholesterol": {"types": {"hdl_cholesterol", "hdl"}, "codes": {"2085-9"}, "text": {"hdl"}},
        "triglycerides": {"types": {"triglycerides", "tg"}, "codes": {"2571-8"}, "text": {"triglyceride", "tg"}},
        "creatinine": {"types": {"creatinine", "serum_creatinine"}, "codes": {"2160-0"}, "text": {"creatinine"}},
        "alt_gpt": {"types": {"alt_gpt", "alt"}, "codes": {"1742-6"}, "text": {"alanine", "alt"}},
        "ast_got": {"types": {"ast_got", "ast"}, "codes": {"1920-8"}, "text": {"aspartate", "ast"}},
        "ast_uln": {"types": {"ast_uln"}, "codes": {"1916-6"}, "text": {"ast upper"}},
        "ggt": {"types": {"ggt"}, "codes": {"2324-2"}, "text": {"gamma glutamyl", "ggt"}},
        "platelet_count": {"types": {"platelet_count", "platelet"}, "codes": {"777-3"}, "text": {"platelet"}},
        "albumin": {"types": {"albumin"}, "codes": {"1751-7"}, "text": {"albumin"}},
        "insulin": {"types": {"insulin"}, "codes": {"20448-7"}, "text": {"insulin"}},
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
        "has_diabetes": [["dm", "treated"], ["dm_treated"], ["t2dm"], ["diabetes", "treated"], ["has", "diabetes"]],
        "prediabetes": [["predm"], ["pre", "diabetes"], ["prediabetes"]],
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
    }

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
        return (
            Patient.objects.filter(id=patient_id).first()
            or Patient.objects.filter(medical_record_number=str(patient_id)).first()
        )

    def build_snapshot(self, patient: Patient) -> ClinicalSnapshot:
        data: Dict[str, Any] = {
            "age": patient.age,
            "sex": patient.sex,
            "gender": patient.sex,
        }
        sources: Dict[str, Any] = {"patient_id": str(patient.id)}

        self._add_product_observations(patient, data, sources)
        self._add_questionnaire_flags(patient, data, sources)
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
                value = self._observation_value(observation)
                if value is None:
                    continue
                candidates.append(
                    ClinicalDataCandidate(
                        field=field,
                        value=value,
                        effective_at=observation.effective_at or observation.created_at,
                        source={
                            "table": "observations",
                            "id": str(observation.id),
                            "code": observation.code,
                            "display": observation.display,
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
                "effective_at": self._iso_datetime(effective_at),
            }
            systolic = self._component_value(bp_observation.component_json, {"8480-6", "systolic", "sbp"})
            diastolic = self._component_value(bp_observation.component_json, {"8462-4", "diastolic", "dbp"})
            if systolic is not None:
                systolic_candidates.append(
                    ClinicalDataCandidate("systolic_bp", systolic, effective_at, source, source_priority=30)
                )
            if diastolic is not None:
                diastolic_candidates.append(
                    ClinicalDataCandidate("diastolic_bp", diastolic, effective_at, source, source_priority=30)
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
                            "effective_at": self._iso_datetime(effective_at),
                        },
                        source_priority=20,
                    )
                )
            self._apply_latest_candidate(data, sources, field, candidates)

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

        for field, model_attr in self.LEGACY_VITAL_FIELDS.items():
            candidates = []
            for screening in screenings:
                vitals = self._legacy_vitals(screening)
                if not vitals:
                    continue
                value = self._float(getattr(vitals, model_attr, None))
                if value is None:
                    continue
                effective_at = screening.encounter_time or screening.screening_date or screening.created_at
                candidates.append(
                    ClinicalDataCandidate(
                        field=field,
                        value=value,
                        effective_at=effective_at,
                        source={
                            "table": "health_screening_vitalsigns",
                            "id": str(vitals.id),
                            "screening_id": str(screening.id),
                            "effective_at": self._iso_datetime(effective_at),
                        },
                        source_priority=10,
                    )
                )
            self._apply_latest_candidate(data, sources, field, candidates)

        for field, aliases in self.LEGACY_LAB_ALIASES.items():
            candidates = []
            for screening in screenings:
                for lab in screening.lab_results.filter(is_active=True):
                    name = (lab.test_name or "").lower()
                    if not any(alias in name for alias in aliases):
                        continue
                    value = self._float(lab.value_result)
                    if value is None:
                        continue
                    effective_at = screening.encounter_time or screening.screening_date or lab.created_at
                    candidates.append(
                        ClinicalDataCandidate(
                            field=field,
                            value=value,
                            effective_at=effective_at,
                            source={
                                "table": "health_screening_laboratoryresults",
                                "id": str(lab.id),
                                "screening_id": str(screening.id),
                                "test_name": lab.test_name,
                                "effective_at": self._iso_datetime(effective_at),
                            },
                            source_priority=10,
                        )
                    )
            self._apply_latest_candidate(data, sources, field, candidates)

        problems = " ".join(
            Problem.objects.filter(patient=patient, is_active=True).values_list("problem_name", flat=True)
        ).lower()
        if "diabetes" in problems:
            data.setdefault("has_diabetes", True)
        if "hypertension" in problems:
            data.setdefault("has_hypertension", True)
            data.setdefault("anti_hypertensive_drugs", True)

    def _observation_matches(self, observation: Observation, field: str) -> bool:
        alias = self.OBSERVATION_ALIASES[field]
        observation_type = (observation.observation_type or "").lower()
        code = observation.code or ""
        display = (observation.display or "").lower()
        if observation_type in alias["types"] or code in alias["codes"]:
            return True
        return any(token in display for token in alias["text"])

    def _observation_value(self, observation: Observation) -> Optional[float]:
        if observation.value_quantity is not None:
            return float(observation.value_quantity)
        if isinstance(observation.value_json, dict):
            for key in ("value", "result", "numeric_value"):
                parsed = self._float(observation.value_json.get(key))
                if parsed is not None:
                    return parsed
        return self._float(observation.value_string)

    def _component_value(self, components: Any, accepted_codes: set[str]) -> Optional[float]:
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
                return self._float(component.get("value") or component.get("valueQuantity", {}).get("value"))
        return None

    def _find_bool(self, payload: Dict[str, Any], token_groups: list[list[str]]) -> Optional[bool]:
        for key, value in self._flatten_payload(payload).items():
            lowered_key = str(key).lower()
            if any(all(token in lowered_key for token in tokens) for tokens in token_groups):
                return self._bool(value)
        return None

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

    def _bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value in (None, ""):
            return False
        return str(value).strip().lower() in {"1", "true", "yes", "y", "positive", "treated", "current"}
