"""
Executable certification contract layer derived from the ONC g10 test kit.

The US Core STU7 specification remains the normative source of truth.
This module records the g10 test kit as the executable validation source and
projects local artifacts into a machine-readable contract the server can use.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List

from .projection_contracts import all_projection_contracts
from .uscore_capability import extract_us_core_capability


G10_TEST_KIT_REPOSITORY = "https://github.com/onc-healthit/onc-certification-g10-test-kit"
G10_TEST_KIT_RELEASE = "v7.2.6"
G10_TEST_KIT_RELEASE_DATE = "2025-08-27"
G10_SINGLE_PATIENT_CANONICAL_ID = "00000000-0000-4000-a000-000000000001"
G10_SINGLE_PATIENT_NAME = "Justin Hu"


@dataclass(frozen=True)
class G10SourceManifest:
    repository: str
    release: str
    release_date: str
    fhir_version: str
    us_core_version: str
    smart_version_floor: str
    golden_patient_name: str
    golden_patient_id: str


def source_manifest() -> G10SourceManifest:
    return G10SourceManifest(
        repository=G10_TEST_KIT_REPOSITORY,
        release=G10_TEST_KIT_RELEASE,
        release_date=G10_TEST_KIT_RELEASE_DATE,
        fhir_version="4.0.1",
        us_core_version="7.0.0",
        smart_version_floor="2.0.0",
        golden_patient_name=G10_SINGLE_PATIENT_NAME,
        golden_patient_id=G10_SINGLE_PATIENT_CANONICAL_ID,
    )


def build_g10_single_patient_contract() -> dict:
    extracted = extract_us_core_capability()
    contracts = all_projection_contracts()

    resources: Dict[str, dict] = {}
    for resource_type, contract in sorted(contracts.items()):
        resources[resource_type] = {
            "required_profiles": contract.required_profiles,
            "required_searches": contract.required_searches,
            "must_support_elements": contract.must_support_elements,
            "must_support_references": contract.must_support_references,
            "enforced_elements": contract.enforced_elements,
            "enforced_references": contract.enforced_references,
            "supported_profile_urls": contract.supported_profile_urls,
            "deterministic_search_params": contract.deterministic_search_params,
        }

    return {
        "manifest": asdict(source_manifest()),
        "architecture_chain": [
            "RelationDB",
            "US Core semantic design",
            "Golden patient dataset",
            "Relational seed",
            "Projector contract",
            "Deterministic FHIR projection",
            "Inferno validation",
        ],
        "resource_types": extracted.resource_types,
        "resources": resources,
    }


def default_output_path() -> Path:
    return Path(__file__).resolve().parents[3] / "docs" / "g10_certification_artifacts" / "g10_single_patient_contract.json"
