"""
US Core STU7 capability extraction from repository-backed artifacts.
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List


FHIR_INTEGRATION_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = FHIR_INTEGRATION_DIR.parents[2]
USCORE_ARTIFACT_DIR = PROJECT_ROOT / "docs" / "uscore_stu7_artifacts"


PROFILE_TO_KEY: Dict[str, str] = {
    "allergy_intolerance": "us-core-allergyintolerance",
    "care_plan": "us-core-careplan",
    "care_team": "us-core-careteam",
    "patient": "us-core-patient",
    "condition_problems_health_concerns": "us-core-condition-problems-health-concerns",
    "condition_encounter_diagnosis": "us-core-condition-encounter-diagnosis",
    "coverage": "us-core-coverage",
    "device": "us-core-implantable-device",
    "diagnostic_report_lab": "us-core-diagnosticreport-lab",
    "diagnostic_report_note": "us-core-diagnosticreport-note",
    "document_reference": "us-core-documentreference",
    "encounter": "us-core-encounter",
    "goal": "us-core-goal",
    "head_circumference": "us-core-head-circumference",
    "head_circumference_percentile": "us-core-head-circumference-percentile",
    "medication_request": "us-core-medicationrequest",
    "medication_dispense": "us-core-medicationdispense",
    "observation_lab": "us-core-observation-lab",
    "observation_clinical_result": "us-core-observation-clinical-result",
    "observation_occupation": "us-core-observation-occupation",
    "observation_pregnancyintent": "us-core-observation-pregnancyintent",
    "observation_pregnancystatus": "us-core-observation-pregnancystatus",
    "observation_screening_assessment": "us-core-observation-screening-assessment",
    "organization": "us-core-organization",
    "pediatric_bmi_for_age": "us-core-pediatric-bmi-for-age",
    "pediatric_weight_for_height": "us-core-pediatric-weight-for-height",
    "practitioner": "us-core-practitioner",
    "procedure": "us-core-procedure",
    "provenance": "us-core-provenance",
    "related_person": "us-core-relatedperson",
    "service_request": "us-core-servicerequest",
    "simple_observation": "us-core-vital-signs",
    "smokingstatus": "us-core-smokingstatus",
    "specimen": "us-core-specimen",
    "treatment_intervention_preference": "us-core-treatment-intervention-preference",
    "care_experience_preference": "us-core-care-experience-preference",
    "blood_pressure": "us-core-blood-pressure",
    "average_blood_pressure": "us-core-average-blood-pressure",
    "body_height": "us-core-body-height",
    "body_weight": "us-core-body-weight",
    "body_temperature": "us-core-body-temperature",
    "heart_rate": "us-core-heart-rate",
    "location": "us-core-location",
    "respiratory_rate": "us-core-respiratory-rate",
    "pulse_oximetry": "us-core-pulse-oximetry",
    "bmi": "us-core-bmi",
    "immunization": "us-core-immunization",
}


@dataclass(frozen=True)
class ExtractedCapability:
    resource_types: List[str]
    required_profiles: Dict[str, List[str]]
    required_searches: Dict[str, List[str]]
    must_support_elements: Dict[str, List[str]]
    must_support_references: Dict[str, List[dict]]


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _normalize_search_combo(combo: str) -> str:
    return "+".join([part for part in combo.split("+") if part])


@lru_cache(maxsize=1)
def extract_us_core_capability() -> ExtractedCapability:
    must_support_rows = _load_json(USCORE_ARTIFACT_DIR / "must_support_catalog.json")
    search_rows = _load_json(USCORE_ARTIFACT_DIR / "search_catalog.json")
    reference_rows = _load_json(USCORE_ARTIFACT_DIR / "reference_edges_agg.json")

    required_profiles: Dict[str, set[str]] = defaultdict(set)
    required_searches: Dict[str, set[str]] = defaultdict(set)
    must_support_elements: Dict[str, set[str]] = defaultdict(set)
    must_support_references: Dict[str, list[dict]] = defaultdict(list)
    resource_types: set[str] = set()

    for row in must_support_rows:
        resource = row["resource"]
        resource_types.add(resource)
        profile_key = PROFILE_TO_KEY.get(row["profile_dir"])
        if profile_key:
            required_profiles[resource].add(profile_key)
        raw_elements = row.get("must_support_elements", "")
        for element in [item.strip() for item in raw_elements.split(",") if item.strip()]:
            must_support_elements[resource].add(element)

    for row in search_rows:
        resource = row["resource"]
        resource_types.add(resource)
        combo = _normalize_search_combo(row["search_combo"])
        if combo:
            required_searches[resource].add(combo)

    for row in reference_rows:
        resource = row["source"]
        resource_types.add(resource)
        must_support_references[resource].append(
            {
                "target": row["target"],
                "paths": [path.strip() for path in str(row["paths"]).split(";") if path.strip()],
            }
        )

    return ExtractedCapability(
        resource_types=sorted(resource_types),
        required_profiles={k: sorted(v) for k, v in required_profiles.items()},
        required_searches={k: sorted(v) for k, v in required_searches.items()},
        must_support_elements={k: sorted(v) for k, v in must_support_elements.items()},
        must_support_references={k: v for k, v in must_support_references.items()},
    )
