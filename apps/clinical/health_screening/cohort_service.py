from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from statistics import mean
from typing import Any, Dict, Iterable, Optional

from django.db.models import QuerySet
from django.utils.dateparse import parse_date

from .models import HealthScreening, Observation, QuestionnaireResponse


CANONICAL_NUMERIC_FEATURES = {
    "sbp": {"label": "Systolic blood pressure", "unit": "mmHg", "observation_type": "blood_pressure", "component_code": "8480-6"},
    "dbp": {"label": "Diastolic blood pressure", "unit": "mmHg", "observation_type": "blood_pressure", "component_code": "8462-4"},
    "bmi": {"label": "Body mass index", "unit": "kg/m2", "observation_type": "body_mass_index"},
    "height": {"label": "Body height", "unit": "cm", "observation_type": "body_height"},
    "weight": {"label": "Body weight", "unit": "kg", "observation_type": "body_weight"},
    "waist": {"label": "Waist circumference", "unit": "cm", "observation_type": "waist_circumference"},
    "fpg": {"label": "Fasting glucose", "unit": "mg/dL", "observation_type": "fasting_glucose"},
    "hba1c": {"label": "Hemoglobin A1c", "unit": "%", "observation_type": "hba1c"},
    "tg": {"label": "Triglycerides", "unit": "mg/dL", "observation_type": "triglycerides"},
    "tc": {"label": "Total cholesterol", "unit": "mg/dL", "observation_type": "total_cholesterol"},
    "hdl": {"label": "HDL cholesterol", "unit": "mg/dL", "observation_type": "hdl_cholesterol"},
    "ldl": {"label": "LDL cholesterol", "unit": "mg/dL", "observation_type": "ldl_cholesterol"},
    "creatinine": {"label": "Creatinine", "unit": "mg/dL", "observation_type": "creatinine"},
}

BOOLEAN_FEATURES = {
    "smoker": ("lifestyle", "smoking_status", "current"),
    "diabetes": ("lifestyle", "has_diabetes", True),
    "hypertension_treated": ("hq", "hypertension_treated", True),
    "diabetes_treated": ("hq", "dm_treated", True),
    "chd_history": ("hq", "chd_history", True),
    "cvd_history": ("hq", "cvd_history", True),
}


@dataclass(frozen=True)
class CohortFilters:
    dataset: str = "h2u_cvd_csv"
    sex: str = ""
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    numeric: Dict[str, tuple[Optional[float], Optional[float]]] = None
    boolean: Dict[str, bool] = None


class CohortSummaryService:
    """Aggregate-only cohort summaries for governed research discovery."""

    def summarize(self, params: Dict[str, Any], *, minimum_cell_count: int = 10) -> Dict[str, Any]:
        filters = self._parse_filters(params)
        base_qs = self._base_screenings(filters)
        screening_ids = list(base_qs.values_list("id", flat=True))
        feature_values = self._feature_values(screening_ids)
        questionnaire_values = self._questionnaire_values(screening_ids)

        selected_ids = []
        rows = []
        for screening in base_qs.select_related("patient").order_by("screening_date", "id"):
            values = feature_values.get(str(screening.id), {})
            booleans = questionnaire_values.get(str(screening.id), {})
            age = self._age_at(screening.patient.date_of_birth, screening.screening_date)
            if not self._matches_age(age, filters):
                continue
            if not self._matches_numeric(values, filters.numeric or {}):
                continue
            if not self._matches_boolean(booleans, filters.boolean or {}):
                continue
            selected_ids.append(str(screening.id))
            rows.append({"screening": screening, "age": age, "values": values, "booleans": booleans})

        count = len(rows)
        suppressed = 0 < count < minimum_cell_count
        response = {
            "dataset": filters.dataset,
            "privacy": {
                "minimum_cell_count": minimum_cell_count,
                "suppressed": suppressed,
                "line_level_data_returned": False,
            },
            "filters": self._serialize_filters(filters),
            "cohort_count": None if suppressed else count,
        }
        if suppressed:
            response["summary"] = {}
            return response

        response["summary"] = {
            "demographics": self._demographics(rows, minimum_cell_count),
            "features": self._feature_summary(rows, minimum_cell_count),
            "flags": self._flag_summary(rows, minimum_cell_count),
        }
        return response

    def _base_screenings(self, filters: CohortFilters) -> QuerySet:
        qs = HealthScreening.objects.filter(is_active=True)
        if filters.dataset:
            qs = qs.filter(product_encounters__source_type=filters.dataset).distinct()
        if filters.sex:
            qs = qs.filter(patient__sex__iexact=filters.sex)
        if filters.date_from:
            qs = qs.filter(screening_date__gte=filters.date_from)
        if filters.date_to:
            qs = qs.filter(screening_date__lte=filters.date_to)
        return qs

    def _feature_values(self, screening_ids: Iterable[str]) -> Dict[str, Dict[str, float]]:
        by_type = {spec["observation_type"]: key for key, spec in CANONICAL_NUMERIC_FEATURES.items()}
        values: Dict[str, Dict[str, float]] = {}
        qs = Observation.objects.filter(
            encounter__source_screening_id__in=screening_ids,
            observation_type__in=set(by_type.keys()),
        ).select_related("encounter")
        for obs in qs:
            screening_id = str(obs.encounter.source_screening_id)
            target = values.setdefault(screening_id, {})
            if obs.observation_type == "blood_pressure":
                for component in obs.component_json or []:
                    key = self._blood_pressure_feature_key(component.get("code"))
                    value = self._to_float(component.get("value"))
                    if key and value is not None:
                        target[key] = value
                continue
            feature_key = by_type.get(obs.observation_type)
            value = self._to_float(obs.value_quantity)
            if feature_key and value is not None:
                target[feature_key] = value
        return values

    def _questionnaire_values(self, screening_ids: Iterable[str]) -> Dict[str, Dict[str, bool]]:
        values: Dict[str, Dict[str, bool]] = {}
        qs = QuestionnaireResponse.objects.filter(
            encounter__source_screening_id__in=screening_ids,
            status="completed",
        ).select_related("encounter")
        for response in qs:
            screening_id = str(response.encounter.source_screening_id)
            target = values.setdefault(screening_id, {})
            data = response.response_json or {}
            for key, (section, field, expected) in BOOLEAN_FEATURES.items():
                actual = (data.get(section) or {}).get(field)
                target[key] = actual == expected if not isinstance(expected, bool) else bool(actual) is expected
        return values

    def _parse_filters(self, params: Dict[str, Any]) -> CohortFilters:
        numeric = {}
        for key in CANONICAL_NUMERIC_FEATURES:
            lower = self._to_float(params.get(f"{key}_min"))
            upper = self._to_float(params.get(f"{key}_max"))
            if lower is not None or upper is not None:
                numeric[key] = (lower, upper)

        boolean = {}
        for key in BOOLEAN_FEATURES:
            parsed = self._parse_bool(params.get(key))
            if parsed is not None:
                boolean[key] = parsed

        return CohortFilters(
            dataset=str(params.get("dataset") or "h2u_cvd_csv"),
            sex=str(params.get("sex") or "").upper(),
            age_min=self._to_int(params.get("age_min")),
            age_max=self._to_int(params.get("age_max")),
            date_from=parse_date(str(params.get("date_from"))) if params.get("date_from") else None,
            date_to=parse_date(str(params.get("date_to"))) if params.get("date_to") else None,
            numeric=numeric,
            boolean=boolean,
        )

    def _serialize_filters(self, filters: CohortFilters) -> Dict[str, Any]:
        return {
            "dataset": filters.dataset,
            "sex": filters.sex,
            "age_min": filters.age_min,
            "age_max": filters.age_max,
            "date_from": filters.date_from.isoformat() if filters.date_from else None,
            "date_to": filters.date_to.isoformat() if filters.date_to else None,
            "numeric": {
                key: {"min": bounds[0], "max": bounds[1]}
                for key, bounds in (filters.numeric or {}).items()
            },
            "boolean": filters.boolean or {},
        }

    def _matches_age(self, age: Optional[int], filters: CohortFilters) -> bool:
        if age is None:
            return filters.age_min is None and filters.age_max is None
        if filters.age_min is not None and age < filters.age_min:
            return False
        if filters.age_max is not None and age > filters.age_max:
            return False
        return True

    def _matches_numeric(self, values: Dict[str, float], filters: Dict[str, tuple[Optional[float], Optional[float]]]) -> bool:
        for key, (lower, upper) in filters.items():
            value = values.get(key)
            if value is None:
                return False
            if lower is not None and value < lower:
                return False
            if upper is not None and value > upper:
                return False
        return True

    def _matches_boolean(self, values: Dict[str, bool], filters: Dict[str, bool]) -> bool:
        for key, expected in filters.items():
            if values.get(key) is not expected:
                return False
        return True

    def _demographics(self, rows: list[Dict[str, Any]], minimum_cell_count: int) -> Dict[str, Any]:
        ages = [row["age"] for row in rows if row["age"] is not None]
        sex_counts: Dict[str, int] = {}
        for row in rows:
            sex = row["screening"].patient.sex or "U"
            sex_counts[sex] = sex_counts.get(sex, 0) + 1
        return {
            "age": self._numeric_stats(ages, minimum_cell_count),
            "sex": self._suppress_small_counts(sex_counts, minimum_cell_count),
        }

    def _feature_summary(self, rows: list[Dict[str, Any]], minimum_cell_count: int) -> Dict[str, Any]:
        summary = {}
        for key, spec in CANONICAL_NUMERIC_FEATURES.items():
            vals = [row["values"][key] for row in rows if key in row["values"]]
            summary[key] = {
                "label": spec["label"],
                "unit": spec["unit"],
                **self._numeric_stats(vals, minimum_cell_count),
            }
        return summary

    def _flag_summary(self, rows: list[Dict[str, Any]], minimum_cell_count: int) -> Dict[str, Any]:
        summary = {}
        for key in BOOLEAN_FEATURES:
            true_count = sum(1 for row in rows if row["booleans"].get(key) is True)
            false_count = sum(1 for row in rows if row["booleans"].get(key) is False)
            summary[key] = self._suppress_small_counts({"true": true_count, "false": false_count}, minimum_cell_count)
        return summary

    def _numeric_stats(self, values: list[Any], minimum_cell_count: int) -> Dict[str, Any]:
        numeric = [float(value) for value in values if value is not None]
        if len(numeric) < minimum_cell_count:
            return {"count": len(numeric), "suppressed": len(numeric) > 0, "mean": None, "min": None, "max": None}
        return {
            "count": len(numeric),
            "suppressed": False,
            "mean": round(mean(numeric), 4),
            "min": round(min(numeric), 4),
            "max": round(max(numeric), 4),
        }

    def _suppress_small_counts(self, counts: Dict[str, int], minimum_cell_count: int) -> Dict[str, Any]:
        return {
            key: (None if 0 < value < minimum_cell_count else value)
            for key, value in counts.items()
        }

    def _blood_pressure_feature_key(self, component_code: str) -> str:
        if component_code == "8480-6":
            return "sbp"
        if component_code == "8462-4":
            return "dbp"
        return ""

    def _age_at(self, birth_date: Optional[date], at_date: Optional[date]) -> Optional[int]:
        if not birth_date or not at_date:
            return None
        return at_date.year - birth_date.year - ((at_date.month, at_date.day) < (birth_date.month, birth_date.day))

    def _to_float(self, value: Any) -> Optional[float]:
        if value in (None, ""):
            return None
        if isinstance(value, Decimal):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _to_int(self, value: Any) -> Optional[int]:
        number = self._to_float(value)
        return int(number) if number is not None else None

    def _parse_bool(self, value: Any) -> Optional[bool]:
        if value in (None, ""):
            return None
        if isinstance(value, bool):
            return value
        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "y"}:
            return True
        if normalized in {"0", "false", "no", "n"}:
            return False
        return None
