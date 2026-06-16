from __future__ import annotations

from statistics import mean
from typing import Any, Dict, Optional

from django.utils.dateparse import parse_date

from .cohort_service import BOOLEAN_FEATURES, CANONICAL_NUMERIC_FEATURES, CohortFilters, CohortSummaryService
from .models import HealthScreening


NUMERIC_MATCH_FEATURES = {
    "age": {"weight": 0.16, "scale": 10.0, "label": "Age"},
    "sbp": {"weight": 0.13, "scale": 20.0, "label": "Systolic blood pressure"},
    "dbp": {"weight": 0.07, "scale": 12.0, "label": "Diastolic blood pressure"},
    "bmi": {"weight": 0.11, "scale": 5.0, "label": "Body mass index"},
    "waist": {"weight": 0.06, "scale": 12.0, "label": "Waist circumference"},
    "fpg": {"weight": 0.08, "scale": 25.0, "label": "Fasting glucose"},
    "hba1c": {"weight": 0.15, "scale": 1.5, "label": "Hemoglobin A1c"},
    "tg": {"weight": 0.05, "scale": 60.0, "label": "Triglycerides"},
    "hdl": {"weight": 0.05, "scale": 15.0, "label": "HDL cholesterol"},
    "ldl": {"weight": 0.09, "scale": 35.0, "label": "LDL cholesterol"},
    "creatinine": {"weight": 0.05, "scale": 0.4, "label": "Creatinine"},
}

TREND_MATCH_FEATURES = {
    "sbp": {"weight": 0.07, "scale": 15.0, "label": "Systolic blood pressure delta"},
    "dbp": {"weight": 0.03, "scale": 10.0, "label": "Diastolic blood pressure delta"},
    "bmi": {"weight": 0.04, "scale": 2.0, "label": "Body mass index delta"},
    "fpg": {"weight": 0.04, "scale": 20.0, "label": "Fasting glucose delta"},
    "hba1c": {"weight": 0.08, "scale": 0.8, "label": "Hemoglobin A1c delta"},
    "ldl": {"weight": 0.05, "scale": 25.0, "label": "LDL cholesterol delta"},
}

CATEGORICAL_MATCH_FEATURES = {
    "sex": {"weight": 0.10, "label": "Sex"},
}

BOOLEAN_MATCH_FEATURES = {
    "diabetes": {"weight": 0.04, "label": "Diabetes history"},
    "smoker": {"weight": 0.03, "label": "Current smoker"},
    "hypertension_treated": {"weight": 0.02, "label": "Hypertension treated"},
    "chd_history": {"weight": 0.03, "label": "CHD history"},
}


class PatientsLikeThisService:
    """Deterministic aggregate-only patient similarity for research discovery."""

    model_name = "patients-like-this-deterministic"
    model_version = "v2"

    def __init__(self):
        self.cohorts = CohortSummaryService()

    def find(self, params: Dict[str, Any], *, minimum_cell_count: int = 10) -> Dict[str, Any]:
        dataset = str(params.get("dataset") or "h2u_cvd_csv")
        requested_limit = self._bounded_int(params.get("limit"), default=50, minimum=minimum_cell_count, maximum=200)
        filters = CohortFilters(
            dataset=dataset,
            date_from=parse_date(str(params.get("date_from"))) if params.get("date_from") else None,
            date_to=parse_date(str(params.get("date_to"))) if params.get("date_to") else None,
            numeric={},
            boolean={},
        )
        base_qs = self.cohorts._base_screenings(filters).select_related("patient").order_by("screening_date", "id")
        screening_ids = [str(value) for value in base_qs.values_list("id", flat=True)]
        feature_values = self.cohorts._feature_values(screening_ids)
        questionnaire_values = self.cohorts._questionnaire_values(screening_ids)
        trend_values = self._trend_values(base_qs, feature_values)

        reference_result = self._reference_profile(params, base_qs, feature_values, questionnaire_values, trend_values)
        if reference_result.get("error"):
            return reference_result

        reference_profile = reference_result["profile"]
        reference_screening_id = reference_result.get("screening_id")
        ranked_rows = []
        for screening in base_qs:
            screening_id = str(screening.id)
            if reference_screening_id and screening_id == reference_screening_id:
                continue

            row = self._row_from_screening(screening, feature_values, questionnaire_values, trend_values)
            similarity = self._similarity(reference_profile, row)
            if similarity is None:
                continue
            row["similarity"] = similarity
            ranked_rows.append(row)

        ranked_rows.sort(
            key=lambda row: (
                -row["similarity"]["score"],
                row["screening"].screening_date.isoformat() if row["screening"].screening_date else "",
                str(row["screening"].id),
            )
        )
        matched_rows = ranked_rows[:requested_limit]
        count = len(matched_rows)
        suppressed = 0 < count < minimum_cell_count

        response = {
            "dataset": dataset,
            "privacy": {
                "minimum_cell_count": minimum_cell_count,
                "suppressed": suppressed,
                "line_level_data_returned": False,
            },
            "reference_source": reference_result["source"],
            "reference_profile": self._serialize_profile(reference_profile),
            "match_request": {
                "limit": requested_limit,
                "date_from": filters.date_from.isoformat() if filters.date_from else None,
                "date_to": filters.date_to.isoformat() if filters.date_to else None,
            },
            "matching_model": self._model_metadata(),
            "matched_count": None if suppressed else count,
        }
        if suppressed:
            response["average_similarity"] = None
            response["summary"] = {}
            return response

        response["average_similarity"] = (
            round(mean([row["similarity"]["score"] for row in matched_rows]), 4) if matched_rows else None
        )
        response["summary"] = {
            "demographics": self.cohorts._demographics(matched_rows, minimum_cell_count),
            "features": self.cohorts._feature_summary(matched_rows, minimum_cell_count),
            "flags": self.cohorts._flag_summary(matched_rows, minimum_cell_count),
            "trends": self._trend_summary(matched_rows, minimum_cell_count),
        }
        return response

    def _reference_profile(
        self,
        params: Dict[str, Any],
        base_qs,
        feature_values: Dict[str, Dict[str, float]],
        questionnaire_values: Dict[str, Dict[str, bool]],
        trend_values: Dict[str, Dict[str, float]],
    ) -> Dict[str, Any]:
        screening_id = str(params.get("screening_id") or "").strip()
        if screening_id:
            screening = next((item for item in base_qs if str(item.id) == screening_id), None)
            if not screening:
                return {"error": "screening_id was not found in the requested dataset"}
            return {
                "source": "screening",
                "screening_id": screening_id,
                "profile": self._row_from_screening(screening, feature_values, questionnaire_values, trend_values),
            }

        profile = {
            "age": self.cohorts._to_int(params.get("age")),
            "sex": str(params.get("sex") or "").upper(),
            "values": {},
            "booleans": {},
            "trends": {},
        }
        for key in CANONICAL_NUMERIC_FEATURES:
            value = self.cohorts._to_float(params.get(key))
            if value is not None:
                profile["values"][key] = value
        for key in BOOLEAN_FEATURES:
            value = self.cohorts._parse_bool(params.get(key))
            if value is not None:
                profile["booleans"][key] = value
        for key in TREND_MATCH_FEATURES:
            value = self.cohorts._to_float(params.get(f"{key}_delta"))
            if value is None:
                value = self.cohorts._to_float(params.get(f"{key}_trend"))
            if value is not None:
                profile["trends"][key] = value

        if not self._has_matchable_input(profile):
            return {"error": "Provide screening_id, or at least one matchable feature such as age, sbp, hba1c, sbp_delta, or diabetes"}
        return {"source": "manual_profile", "profile": profile}

    def _row_from_screening(
        self,
        screening: HealthScreening,
        feature_values: Dict[str, Dict[str, float]],
        questionnaire_values: Dict[str, Dict[str, bool]],
        trend_values: Dict[str, Dict[str, float]],
    ) -> Dict[str, Any]:
        screening_id = str(screening.id)
        return {
            "screening": screening,
            "age": self.cohorts._age_at(screening.patient.date_of_birth, screening.screening_date),
            "sex": (screening.patient.sex or "").upper(),
            "values": feature_values.get(screening_id, {}),
            "booleans": questionnaire_values.get(screening_id, {}),
            "trends": trend_values.get(screening_id, {}),
        }

    def _similarity(self, reference: Dict[str, Any], candidate: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        weighted_distance = 0.0
        total_weight = 0.0
        matched_features = []

        for key, spec in NUMERIC_MATCH_FEATURES.items():
            ref_value = reference.get("age") if key == "age" else reference.get("values", {}).get(key)
            candidate_value = candidate.get("age") if key == "age" else candidate.get("values", {}).get(key)
            if ref_value is None or candidate_value is None:
                continue
            distance = min(abs(float(ref_value) - float(candidate_value)) / spec["scale"], 2.0) / 2.0
            weighted_distance += spec["weight"] * distance
            total_weight += spec["weight"]
            matched_features.append(key)

        ref_sex = reference.get("sex")
        candidate_sex = candidate.get("sex")
        if ref_sex and candidate_sex:
            weight = CATEGORICAL_MATCH_FEATURES["sex"]["weight"]
            weighted_distance += 0.0 if ref_sex == candidate_sex else weight
            total_weight += weight
            matched_features.append("sex")

        for key, spec in BOOLEAN_MATCH_FEATURES.items():
            ref_value = reference.get("booleans", {}).get(key)
            candidate_value = candidate.get("booleans", {}).get(key)
            if ref_value is None or candidate_value is None:
                continue
            weighted_distance += 0.0 if ref_value is candidate_value else spec["weight"]
            total_weight += spec["weight"]
            matched_features.append(key)

        for key, spec in TREND_MATCH_FEATURES.items():
            ref_value = reference.get("trends", {}).get(key)
            candidate_value = candidate.get("trends", {}).get(key)
            if ref_value is None or candidate_value is None:
                continue
            distance = min(abs(float(ref_value) - float(candidate_value)) / spec["scale"], 2.0) / 2.0
            weighted_distance += spec["weight"] * distance
            total_weight += spec["weight"]
            matched_features.append(f"{key}_delta")

        if total_weight <= 0:
            return None
        normalized_distance = weighted_distance / total_weight
        return {
            "score": round(max(0.0, 1.0 - normalized_distance), 4),
            "matched_feature_count": len(matched_features),
        }

    def _serialize_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "age": profile.get("age"),
            "sex": profile.get("sex") or "",
            "features": {
                key: profile.get("values", {}).get(key)
                for key in NUMERIC_MATCH_FEATURES
                if key != "age" and key in profile.get("values", {})
            },
            "flags": {
                key: profile.get("booleans", {}).get(key)
                for key in BOOLEAN_MATCH_FEATURES
                if key in profile.get("booleans", {})
            },
            "trends": {
                f"{key}_delta": profile.get("trends", {}).get(key)
                for key in TREND_MATCH_FEATURES
                if key in profile.get("trends", {})
            },
        }

    def _model_metadata(self) -> Dict[str, Any]:
        return {
            "name": self.model_name,
            "version": self.model_version,
            "numeric_features": NUMERIC_MATCH_FEATURES,
            "trend_features": TREND_MATCH_FEATURES,
            "categorical_features": CATEGORICAL_MATCH_FEATURES,
            "boolean_features": BOOLEAN_MATCH_FEATURES,
        }

    def _has_matchable_input(self, profile: Dict[str, Any]) -> bool:
        numeric_count = int(profile.get("age") is not None) + len(profile.get("values", {}))
        return numeric_count > 0 or bool(profile.get("booleans")) or bool(profile.get("trends"))

    def _trend_values(self, screenings, feature_values: Dict[str, Dict[str, float]]) -> Dict[str, Dict[str, float]]:
        values: Dict[str, Dict[str, float]] = {}
        previous_by_patient: Dict[str, Dict[str, float]] = {}
        ordered = sorted(
            list(screenings),
            key=lambda screening: (
                str(screening.patient_id),
                screening.screening_date.isoformat() if screening.screening_date else "",
                str(screening.id),
            ),
        )
        for screening in ordered:
            screening_id = str(screening.id)
            patient_id = str(screening.patient_id)
            current = feature_values.get(screening_id, {})
            previous = previous_by_patient.get(patient_id, {})
            target = {}
            for key in TREND_MATCH_FEATURES:
                if key in current and key in previous:
                    target[key] = round(float(current[key]) - float(previous[key]), 4)
            if target:
                values[screening_id] = target
            if current:
                previous_by_patient[patient_id] = current
        return values

    def _trend_summary(self, rows: list[Dict[str, Any]], minimum_cell_count: int) -> Dict[str, Any]:
        summary = {}
        for key, spec in TREND_MATCH_FEATURES.items():
            vals = [row["trends"][key] for row in rows if key in row.get("trends", {})]
            summary[f"{key}_delta"] = {
                "label": spec["label"],
                "unit": CANONICAL_NUMERIC_FEATURES.get(key, {}).get("unit", ""),
                **self.cohorts._numeric_stats(vals, minimum_cell_count),
            }
        return summary

    def _bounded_int(self, value: Any, *, default: int, minimum: int, maximum: int) -> int:
        parsed = self.cohorts._to_int(value)
        if parsed is None:
            return default
        return max(minimum, min(maximum, parsed))
