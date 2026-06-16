from __future__ import annotations

import hashlib
import json
from datetime import timezone
from typing import Any, Dict

from django.utils import timezone as django_timezone


ALLCARE_RESEARCH_SYSTEM = "https://allcare365.local/fhir/research"
MEASURE_POPULATION_SYSTEM = "http://terminology.hl7.org/CodeSystem/measure-population"
MEASURE_REPORT_PROFILE = "http://hl7.org/fhir/StructureDefinition/MeasureReport"


class CohortMeasureReportBuilder:
    """Build aggregate-only FHIR R4 MeasureReport resources for cohort discovery."""

    def build(self, cohort_summary: Dict[str, Any]) -> Dict[str, Any]:
        report_id = self._stable_report_id(cohort_summary)
        privacy = cohort_summary.get("privacy", {})
        filters = cohort_summary.get("filters", {})
        summary = cohort_summary.get("summary", {})
        cohort_count = cohort_summary.get("cohort_count")

        report = {
            "resourceType": "MeasureReport",
            "id": report_id,
            "meta": {
                "profile": [MEASURE_REPORT_PROFILE],
                "lastUpdated": django_timezone.now().astimezone(timezone.utc).isoformat(),
            },
            "status": "complete",
            "type": "summary",
            "measure": "https://allcare365.local/fhir/Measure/h2u-cvd-cohort-summary",
            "date": django_timezone.now().date().isoformat(),
            "reporter": {"display": "AllCare365 Research Cohort Service"},
            "extension": [
                {
                    "url": f"{ALLCARE_RESEARCH_SYSTEM}/StructureDefinition/line-level-data-returned",
                    "valueBoolean": bool(privacy.get("line_level_data_returned")),
                },
                {
                    "url": f"{ALLCARE_RESEARCH_SYSTEM}/StructureDefinition/minimum-cell-count",
                    "valueInteger": int(privacy.get("minimum_cell_count") or 0),
                },
                {
                    "url": f"{ALLCARE_RESEARCH_SYSTEM}/StructureDefinition/privacy-suppressed",
                    "valueBoolean": bool(privacy.get("suppressed")),
                },
                {
                    "url": f"{ALLCARE_RESEARCH_SYSTEM}/StructureDefinition/dataset",
                    "valueString": str(cohort_summary.get("dataset") or ""),
                },
            ],
            "group": [
                {
                    "id": "aggregate-cohort",
                    "code": {
                        "coding": [
                            {
                                "system": ALLCARE_RESEARCH_SYSTEM,
                                "code": "aggregate-cohort",
                                "display": "Aggregate cohort",
                            }
                        ],
                        "text": "Aggregate cohort",
                    },
                    "population": [self._initial_population(cohort_count, privacy)],
                    "extension": self._group_extensions(summary),
                }
            ],
        }

        period = self._period(filters)
        if period:
            report["period"] = period
        if filters:
            report["evaluatedResource"] = [
                {
                    "display": "Cohort filters",
                    "extension": [
                        {
                            "url": f"{ALLCARE_RESEARCH_SYSTEM}/StructureDefinition/filter-json",
                            "valueString": json.dumps(filters, sort_keys=True),
                        }
                    ],
                }
            ]
        return report

    def _initial_population(self, cohort_count: Any, privacy: Dict[str, Any]) -> Dict[str, Any]:
        population = {
            "code": {
                "coding": [
                    {
                        "system": MEASURE_POPULATION_SYSTEM,
                        "code": "initial-population",
                        "display": "Initial Population",
                    }
                ],
                "text": "Initial population",
            },
            "extension": [
                {
                    "url": f"{ALLCARE_RESEARCH_SYSTEM}/StructureDefinition/privacy-suppressed",
                    "valueBoolean": bool(privacy.get("suppressed")),
                }
            ],
        }
        if cohort_count is not None:
            population["count"] = int(cohort_count)
        return population

    def _group_extensions(self, summary: Dict[str, Any]) -> list[Dict[str, Any]]:
        extensions = []
        demographics = summary.get("demographics", {})
        age = demographics.get("age")
        if age:
            extensions.append(self._numeric_stats_extension("age", "Age", "a", age))

        for sex, count in (demographics.get("sex") or {}).items():
            if count is None:
                continue
            extensions.append({
                "url": f"{ALLCARE_RESEARCH_SYSTEM}/StructureDefinition/sex-count",
                "extension": [
                    {"url": "sex", "valueCode": str(sex)},
                    {"url": "count", "valueInteger": int(count)},
                ],
            })

        for key, stats in (summary.get("features") or {}).items():
            extensions.append(
                self._numeric_stats_extension(
                    key,
                    stats.get("label") or key,
                    stats.get("unit") or "",
                    stats,
                )
            )
        return extensions

    def _numeric_stats_extension(self, key: str, label: str, unit: str, stats: Dict[str, Any]) -> Dict[str, Any]:
        children = [
            {"url": "code", "valueCode": str(key)},
            {"url": "display", "valueString": str(label)},
            {"url": "unit", "valueString": str(unit)},
            {"url": "suppressed", "valueBoolean": bool(stats.get("suppressed"))},
        ]
        for name, fhir_type in {
            "count": "valueInteger",
            "mean": "valueDecimal",
            "min": "valueDecimal",
            "max": "valueDecimal",
        }.items():
            value = stats.get(name)
            if value is None:
                continue
            children.append({"url": name, fhir_type: value})

        return {
            "url": f"{ALLCARE_RESEARCH_SYSTEM}/StructureDefinition/numeric-feature-summary",
            "extension": children,
        }

    def _period(self, filters: Dict[str, Any]) -> Dict[str, str]:
        period = {}
        if filters.get("date_from"):
            period["start"] = filters["date_from"]
        if filters.get("date_to"):
            period["end"] = filters["date_to"]
        return period

    def _stable_report_id(self, cohort_summary: Dict[str, Any]) -> str:
        seed = {
            "dataset": cohort_summary.get("dataset"),
            "filters": cohort_summary.get("filters", {}),
            "privacy": cohort_summary.get("privacy", {}),
            "cohort_count": cohort_summary.get("cohort_count"),
        }
        digest = hashlib.sha256(json.dumps(seed, sort_keys=True).encode("utf-8")).hexdigest()[:24]
        return f"cohort-summary-{digest}"
