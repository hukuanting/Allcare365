"""
US Core STU7 projection contracts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .meta_builder import MetaBuilder
from .uscore_capability import extract_us_core_capability


TERMINOLOGY_BINDING_RULES: Dict[str, Dict[str, List[str]]] = {
    "Patient": {
        "communication.language.coding": ["urn:ietf:bcp:47"],
    },
    "Condition": {
        "clinicalStatus.coding": ["http://terminology.hl7.org/CodeSystem/condition-clinical"],
        "verificationStatus.coding": ["http://terminology.hl7.org/CodeSystem/condition-ver-status"],
        "category.coding": [
            "http://terminology.hl7.org/CodeSystem/condition-category",
            "http://hl7.org/fhir/us/core/CodeSystem/condition-category",
            "http://hl7.org/fhir/us/core/CodeSystem/us-core-category",
        ],
        "code.coding": ["http://snomed.info/sct"],
    },
    "Coverage": {
        "type.coding": ["http://terminology.hl7.org/CodeSystem/v3-ActCode"],
        "relationship.coding": ["http://terminology.hl7.org/CodeSystem/subscriber-relationship"],
    },
    "DiagnosticReport": {
        "category.coding": ["http://loinc.org", "http://terminology.hl7.org/CodeSystem/v2-0074"],
        "code.coding": ["http://loinc.org"],
    },
    "Observation": {
        "category.coding": ["http://terminology.hl7.org/CodeSystem/observation-category"],
        "code.coding": ["http://loinc.org"],
    },
    "MedicationRequest": {
        "category.coding": [
            "http://terminology.hl7.org/CodeSystem/medicationrequest-category",
            "http://hl7.org/fhir/us/core/CodeSystem/us-core-medicationrequest-category",
        ],
    },
    "Encounter": {
        "class": ["http://terminology.hl7.org/CodeSystem/v3-ActCode"],
        "participant.type.coding": ["http://terminology.hl7.org/CodeSystem/v3-ParticipationType"],
        "hospitalization.dischargeDisposition.coding": ["http://terminology.hl7.org/CodeSystem/discharge-disposition"],
    },
    "DocumentReference": {
        "type.coding": ["http://loinc.org"],
        "category.coding": ["http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category"],
    },
}

SEARCH_PARAM_PRIORITY = (
    "patient",
    "subject",
    "category",
    "code",
    "status",
    "date",
    "authored",
    "identifier",
    "_id",
)

MANDATORY_TOP_LEVEL_ELEMENTS: Dict[str, List[str]] = {
    "Patient": ["active", "identifier", "name", "gender", "birthDate", "address", "communication", "extension"],
    "Condition": ["clinicalStatus", "verificationStatus", "category", "code", "subject", "onsetDateTime", "recordedDate", "encounter"],
    "Coverage": ["identifier", "status", "type", "subscriberId", "beneficiary", "relationship", "period", "payor", "class"],
    "DiagnosticReport": ["status", "category", "code", "subject", "encounter", "effectiveDateTime", "issued", "performer", "result"],
    "Observation": ["status", "category", "code", "subject", "encounter", "effectiveDateTime"],
    "MedicationRequest": ["status", "intent", "category", "reportedBoolean", "medicationReference", "subject", "encounter", "authoredOn", "requester", "dosageInstruction", "dispenseRequest"],
    "Encounter": ["identifier", "status", "class", "type", "subject", "participant", "period", "reasonReference", "location", "serviceProvider", "hospitalization"],
    "DocumentReference": ["identifier", "status", "type", "category", "subject", "date", "author", "content", "context"],
    "RiskAssessment": ["status", "subject", "prediction"],
}

MANDATORY_REFERENCE_TARGETS: Dict[str, List[str]] = {
    "Condition": ["Encounter", "Patient"],
    "Coverage": ["Organization", "Patient"],
    "DiagnosticReport": ["Encounter", "Observation", "Patient", "Practitioner"],
    "Observation": ["Encounter", "Patient", "Specimen"],
    "MedicationRequest": ["Encounter", "Patient", "Practitioner"],
    "Encounter": ["Condition", "Location", "Organization", "Patient", "Practitioner"],
    "DocumentReference": ["Encounter", "Patient", "Practitioner"],
    "RiskAssessment": ["Patient"],
}


@dataclass(frozen=True)
class ProjectionContract:
    resource_type: str
    required_profiles: List[str]
    required_searches: List[str]
    must_support_elements: List[str]
    must_support_references: List[dict]
    terminology_bindings: Dict[str, List[str]] = field(default_factory=dict)
    enforced_elements: List[str] = field(default_factory=list)
    enforced_references: List[dict] = field(default_factory=list)

    @property
    def supported_profile_urls(self) -> List[str]:
        urls = []
        for key in self.required_profiles:
            try:
                urls.append(MetaBuilder.profile_url(key))
            except ValueError:
                continue
        return urls

    @property
    def deterministic_search_params(self) -> List[str]:
        seen = set()
        ordered: List[str] = []
        for combo in self.required_searches:
            for part in combo.split("+"):
                if part in SEARCH_PARAM_PRIORITY and part not in seen:
                    seen.add(part)
                    ordered.append(part)
        return ordered

    @property
    def top_level_must_support_elements(self) -> List[str]:
        if self.enforced_elements:
            return list(self.enforced_elements)
        top = set()
        for element in self.must_support_elements:
            clean = element.split(":")[0].split("[")[0]
            top.add(clean.split(".")[0])
        return sorted(top)


def build_projection_contracts(selected_resources: Optional[List[str]] = None) -> Dict[str, ProjectionContract]:
    extracted = extract_us_core_capability()
    resource_types = selected_resources or list(extracted.resource_types)
    contracts: Dict[str, ProjectionContract] = {}

    for resource_type in resource_types:
        enforced_targets = set(MANDATORY_REFERENCE_TARGETS.get(resource_type, []))
        contracts[resource_type] = ProjectionContract(
            resource_type=resource_type,
            required_profiles=extracted.required_profiles.get(resource_type, []),
            required_searches=extracted.required_searches.get(resource_type, []),
            must_support_elements=extracted.must_support_elements.get(resource_type, []),
            must_support_references=extracted.must_support_references.get(resource_type, []),
            terminology_bindings=TERMINOLOGY_BINDING_RULES.get(resource_type, {}),
            enforced_elements=MANDATORY_TOP_LEVEL_ELEMENTS.get(resource_type, []),
            enforced_references=[
                edge
                for edge in extracted.must_support_references.get(resource_type, [])
                if edge["target"] in enforced_targets
            ],
        )

    # RiskAssessment is a core FHIR R4 resource used for our derived disease
    # risk outputs, but it is outside the US Core STU7 resource list from
    # which the other contracts are extracted.
    if selected_resources is None or "RiskAssessment" in resource_types:
        contracts["RiskAssessment"] = ProjectionContract(
            resource_type="RiskAssessment",
            required_profiles=[],
            required_searches=["_id", "patient", "subject"],
            must_support_elements=["status", "subject", "prediction"],
            must_support_references=[
                {"paths": ["subject"], "target": "Patient"},
            ],
            enforced_elements=MANDATORY_TOP_LEVEL_ELEMENTS["RiskAssessment"],
            enforced_references=[
                {"paths": ["subject"], "target": "Patient"},
            ],
        )
    return contracts


_CONTRACT_CACHE = build_projection_contracts()


def get_projection_contract(resource_type: str) -> Optional[ProjectionContract]:
    return _CONTRACT_CACHE.get(resource_type)


def all_projection_contracts() -> Dict[str, ProjectionContract]:
    return dict(_CONTRACT_CACHE)
