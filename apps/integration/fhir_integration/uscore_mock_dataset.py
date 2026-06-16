"""
Centralized US Core 7.0.0 mock resources for Single Patient API testing.
"""

from __future__ import annotations

import copy
from datetime import date, datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from apps.clinical.patients.models import Patient


US_CORE_PROFILE_BASE = "http://hl7.org/fhir/us/core/StructureDefinition"
US_CORE_VERSION = "7.0.0"

SHARED_RESOURCE_TYPES = {
    "Organization",
    "Location",
    "Practitioner",
    "PractitionerRole",
    "Medication",
}

SUPPORTED_RESOURCE_TYPES = SHARED_RESOURCE_TYPES | {
    "Patient",
    "AllergyIntolerance",
    "CarePlan",
    "CareTeam",
    "Condition",
    "Coverage",
    "Device",
    "DiagnosticReport",
    "DocumentReference",
    "Encounter",
    "Goal",
    "Immunization",
    "MedicationRequest",
    "MedicationDispense",
    "Observation",
    "Procedure",
    "RelatedPerson",
    "ServiceRequest",
    "Specimen",
    "Provenance",
}


def _now_iso() -> str:
    # Keep mock timestamps deterministic across requests so Inferno date-based
    # follow-up searches compare the same value.
    return "2026-02-26T08:47:36.236701+00:00"


def _profile(name: str) -> List[str]:
    return [f"{US_CORE_PROFILE_BASE}/{name}|{US_CORE_VERSION}"]


def _pid_prefix(patient_id: str) -> str:
    return patient_id[:8]


def _rid(short_code: str, patient_id: str, index: int = 0) -> str:
    return f"m-{short_code}-{_pid_prefix(patient_id)}-{index}"


def _gender(patient: Patient) -> str:
    value = (patient.sex or "").strip().lower()
    if value in {"m", "male"}:
        return "male"
    if value in {"f", "female"}:
        return "female"
    return "unknown"


def _csv_tokens(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    return [part.strip() for part in str(raw).split(",") if part.strip()]


def _normalize_id_token(token: str) -> str:
    value = str(token).strip()
    if "/_history/" in value:
        value = value.split("/_history/", 1)[0]
    if "/" in value:
        value = value.split("/")[-1]
    return value


def _coding_matches(raw: Optional[str], codings: Iterable[Dict[str, Any]]) -> bool:
    tokens = _csv_tokens(raw)
    if not tokens:
        return True
    for token in tokens:
        for coding in codings:
            code = coding.get("code")
            system = coding.get("system")
            if "|" in token:
                target_system, target_code = token.split("|", 1)
                if target_system == system and target_code == code:
                    return True
            elif token == code:
                return True
    return False


def _date_prefix(raw: str) -> Tuple[str, str]:
    if len(raw) >= 2 and raw[:2].isalpha():
        return raw[:2], raw[2:]
    return "eq", raw


def _to_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except ValueError:
            return None


def _date_match(candidate: Optional[str], query: Optional[str]) -> bool:
    if not query:
        return True
    op, target_raw = _date_prefix(str(query))
    target = _to_date(target_raw)
    value = _to_date(candidate)
    if not target or not value:
        return False
    if op == "eq":
        return value == target
    if op == "ge":
        return value >= target
    if op == "gt":
        return value > target
    if op == "le":
        return value <= target
    if op == "lt":
        return value < target
    return value == target


def _get_codings(resource: Dict[str, Any], field_name: str) -> List[Dict[str, Any]]:
    value = resource.get(field_name)
    if isinstance(value, dict):
        return value.get("coding", [])
    if isinstance(value, list):
        codings: List[Dict[str, Any]] = []
        for item in value:
            if isinstance(item, dict):
                codings.extend(item.get("coding", []))
        return codings
    return []


def _build_shared(patient: Patient, now: str) -> Dict[str, List[Dict[str, Any]]]:
    patient_id = str(patient.id)
    return {
        "Organization": [
            {
                "resourceType": "Organization",
                "id": "bulk-organization-1",
                "meta": {"profile": _profile("us-core-organization"), "lastUpdated": now},
                "active": True,
                "identifier": [{"system": "http://hl7.org/fhir/sid/us-npi", "value": "1068613102"}],
                "name": "Allcare 365 Medical Group",
                "telecom": [{"system": "phone", "value": "555-555-5555"}],
                "address": [{"line": ["123 Health Way"], "city": "Ann Arbor", "state": "MI", "postalCode": "48105", "country": "US"}],
            }
        ],
        "Location": [
            {
                "resourceType": "Location",
                "id": "bulk-location-1",
                "meta": {"profile": _profile("us-core-location"), "lastUpdated": now},
                "status": "active",
                "name": "Allcare 365 Main Clinic",
                "address": {"line": ["123 Clinic Street"], "city": "Ann Arbor", "state": "MI", "postalCode": "48105", "country": "US"},
                "managingOrganization": {"reference": "Organization/bulk-organization-1"},
            }
        ],
        "Practitioner": [
            {
                "resourceType": "Practitioner",
                "id": "example-practitioner",
                "meta": {"profile": _profile("us-core-practitioner"), "lastUpdated": now},
                "identifier": [{"system": "http://hl7.org/fhir/sid/us-npi", "value": "1091370068"}],
                "active": True,
                "name": [{"family": "Careful", "given": ["Adam"], "prefix": ["Dr."]}],
                "telecom": [{"system": "phone", "value": "555-555-5501", "use": "work"}],
                "address": [{"line": ["123 Health Way"], "city": "Ann Arbor", "state": "MI", "postalCode": "48105", "country": "US"}],
            }
        ],
        "PractitionerRole": [
            {
                "resourceType": "PractitionerRole",
                "id": "example-practitioner-role",
                "meta": {"profile": _profile("us-core-practitionerrole"), "lastUpdated": now},
                "active": True,
                "practitioner": {"reference": "Practitioner/example-practitioner"},
                "organization": {"reference": "Organization/bulk-organization-1"},
                "code": [{"coding": [{"system": "http://snomed.info/sct", "code": "158965000", "display": "Medical practitioner"}]}],
                "specialty": [{"coding": [{"system": "http://nucc.org/provider-taxonomy", "code": "207Q00000X", "display": "Family Medicine"}]}],
                "location": [{"reference": "Location/bulk-location-1"}],
                "telecom": [{"system": "phone", "value": "555-555-5501", "use": "work"}],
            }
        ],
        "Medication": [
            {
                "resourceType": "Medication",
                "id": _rid("med", patient_id),
                "meta": {"profile": _profile("us-core-medication"), "lastUpdated": now},
                "code": {"coding": [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "198440", "display": "Aspirin"}]},
                "status": "active",
            }
        ],
    }


def build_static_reference_resources(now: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    timestamp = now or _now_iso()
    return {
        "Organization": [
            {
                "resourceType": "Organization",
                "id": "bulk-organization-1",
                "meta": {"profile": _profile("us-core-organization"), "lastUpdated": timestamp},
                "active": True,
                "identifier": [{"system": "http://hl7.org/fhir/sid/us-npi", "value": "1068613102"}],
                "name": "Allcare 365 Medical Group",
                "telecom": [{"system": "phone", "value": "555-555-5555"}],
                "address": [{"line": ["123 Health Way"], "city": "Ann Arbor", "state": "MI", "postalCode": "48105", "country": "US"}],
            }
        ],
        "Location": [
            {
                "resourceType": "Location",
                "id": "bulk-location-1",
                "meta": {"profile": _profile("us-core-location"), "lastUpdated": timestamp},
                "status": "active",
                "name": "Allcare 365 Main Clinic",
                "telecom": [{"system": "phone", "value": "555-555-5500"}],
                "address": {"line": ["123 Clinic Street"], "city": "Ann Arbor", "state": "MI", "postalCode": "48105", "country": "US"},
                "managingOrganization": {"reference": "Organization/bulk-organization-1"},
            }
        ],
        "Practitioner": [
            {
                "resourceType": "Practitioner",
                "id": "example-practitioner",
                "meta": {"profile": _profile("us-core-practitioner"), "lastUpdated": timestamp},
                "identifier": [{"system": "http://hl7.org/fhir/sid/us-npi", "value": "1091370068"}],
                "active": True,
                "name": [{"family": "Careful", "given": ["Adam"]}],
                "telecom": [{"system": "phone", "value": "555-555-5501", "use": "work"}],
                "address": [{"line": ["123 Health Way"], "city": "Ann Arbor", "state": "MI", "postalCode": "48105", "country": "US"}],
            }
        ],
        "PractitionerRole": [
            {
                "resourceType": "PractitionerRole",
                "id": "example-practitioner-role",
                "meta": {"profile": _profile("us-core-practitionerrole"), "lastUpdated": timestamp},
                "active": True,
                "practitioner": {"reference": "Practitioner/example-practitioner"},
                "organization": {"reference": "Organization/bulk-organization-1"},
                "code": [{"coding": [{"system": "http://snomed.info/sct", "code": "158965000", "display": "Medical practitioner"}]}],
                "specialty": [{"coding": [{"system": "http://nucc.org/provider-taxonomy", "code": "207Q00000X", "display": "Family Medicine"}]}],
                "location": [{"reference": "Location/bulk-location-1"}],
                "telecom": [{"system": "phone", "value": "555-555-5501", "use": "work"}],
            }
        ],
    }


def _build_patient_data(patient: Patient, now: str) -> Dict[str, List[Dict[str, Any]]]:
    patient_id = str(patient.id)
    p_ref = f"Patient/{patient_id}"
    gender = _gender(patient)
    med_id = _rid("med", patient_id)
    enc_id = _rid("enc", patient_id)
    serv_id = _rid("srv", patient_id)
    mreq_id = _rid("mrx", patient_id)
    spm_id = _rid("spm", patient_id)
    lab_obs_id = _rid("obs", patient_id)
    obs: List[Dict[str, Any]] = [
        {"resourceType": "Observation", "id": lab_obs_id, "meta": {"profile": _profile("us-core-observation-lab"), "lastUpdated": now}, "status": "final", "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory"}]}], "code": {"coding": [{"system": "http://loinc.org", "code": "2345-7"}]}, "subject": {"reference": p_ref}, "encounter": {"reference": f"Encounter/{enc_id}"}, "effectiveDateTime": now, "valueQuantity": {"value": 95, "unit": "mg/dL", "system": "http://unitsofmeasure.org", "code": "mg/dL"}, "specimen": {"reference": f"Specimen/{spm_id}"}},
        {"resourceType": "Observation", "id": _rid("obp", patient_id), "meta": {"profile": _profile("us-core-blood-pressure"), "lastUpdated": now}, "status": "final", "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs"}]}], "code": {"coding": [{"system": "http://loinc.org", "code": "85354-9"}]}, "subject": {"reference": p_ref}, "effectiveDateTime": now, "component": [{"code": {"coding": [{"system": "http://loinc.org", "code": "8480-6"}]}, "valueQuantity": {"value": 120, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}}, {"code": {"coding": [{"system": "http://loinc.org", "code": "8462-4"}]}, "valueQuantity": {"value": 80, "unit": "mmHg", "system": "http://unitsofmeasure.org", "code": "mm[Hg]"}}]},
        {"resourceType": "Observation", "id": _rid("obmi", patient_id), "meta": {"profile": _profile("us-core-bmi"), "lastUpdated": now}, "status": "final", "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs"}]}], "code": {"coding": [{"system": "http://loinc.org", "code": "39156-5"}]}, "subject": {"reference": p_ref}, "effectiveDateTime": now, "valueQuantity": {"value": 22.9, "unit": "kg/m2", "system": "http://unitsofmeasure.org", "code": "kg/m2"}},
        {"resourceType": "Observation", "id": _rid("obsm", patient_id), "meta": {"profile": _profile("us-core-smokingstatus"), "lastUpdated": now}, "status": "final", "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "social-history"}]}], "code": {"coding": [{"system": "http://loinc.org", "code": "72166-2"}]}, "subject": {"reference": p_ref}, "effectiveDateTime": now, "valueCodeableConcept": {"coding": [{"system": "http://snomed.info/sct", "code": "266919005"}]}},
        {"resourceType": "Observation", "id": _rid("obsa", patient_id), "meta": {"profile": _profile("us-core-observation-screening-assessment"), "lastUpdated": now}, "status": "final", "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "survey"}]}, {"coding": [{"system": "http://hl7.org/fhir/us/core/CodeSystem/us-core-category", "code": "sdoh"}]}], "code": {"coding": [{"system": "http://loinc.org", "code": "88122-7"}]}, "subject": {"reference": p_ref}, "effectiveDateTime": now, "valueCodeableConcept": {"coding": [{"system": "http://snomed.info/sct", "code": "445281000124101"}]}},
    ]

    patient_resources = {
        "Patient": [{
            "resourceType": "Patient",
            "id": patient_id,
            "meta": {"profile": _profile("us-core-patient"), "lastUpdated": now},
            "active": True,
            "identifier": [{"system": "http://hospital.smarthealthit.org", "value": patient.medical_record_number or f"MRN-{_pid_prefix(patient_id).upper()}"}],
            "name": [
                {
                    "use": "official",
                    "family": patient.last_name or "Smith",
                    "given": [patient.first_name or "Amy"],
                    "suffix": [patient.name_suffix or "Jr."],
                },
                {
                    "use": "old",
                    "family": patient.previous_name or "Smith",
                    "given": ["A."],
                    "period": {"end": "2019-01-01T00:00:00Z"},
                },
            ],
            "telecom": [{"system": "phone", "value": patient.phone_number or "555-555-0001", "use": "home"}],
            "gender": gender,
            "birthDate": patient.date_of_birth.isoformat() if patient.date_of_birth else "1990-05-15",
            "deceasedDateTime": "2024-01-01T12:00:00Z",
            "address": [
                {
                    "use": "home",
                    "line": [patient.current_address_line1 or "1234 Medical Parkway"],
                    "city": patient.city or "Ann Arbor",
                    "state": patient.state or "MI",
                    "postalCode": patient.postal_code or "48105",
                    "country": "US",
                },
                {
                    "use": "old",
                    "line": ["19 Old Lane"],
                    "city": "Ann Arbor",
                    "state": "MI",
                    "postalCode": "48103",
                    "country": "US",
                    "period": {"end": "2018-12-31T00:00:00Z"},
                },
            ],
            "communication": [{"language": {"coding": [{"system": "urn:ietf:bcp:47", "code": "en-US"}]}, "preferred": True}],
            "extension": [
                {
                    "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-race",
                    "extension": [
                        {"url": "ombCategory", "valueCoding": {"system": "urn:oid:2.16.840.1.113883.6.238", "code": "2106-3", "display": "White"}},
                        {"url": "text", "valueString": "White"},
                    ],
                },
                {
                    "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity",
                    "extension": [
                        {"url": "ombCategory", "valueCoding": {"system": "urn:oid:2.16.840.1.113883.6.238", "code": "2186-5", "display": "Not Hispanic or Latino"}},
                        {"url": "text", "valueString": "Not Hispanic or Latino"},
                    ],
                },
                {
                    "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-tribal-affiliation",
                    "extension": [
                        {
                            "url": "tribalAffiliation",
                            "valueCodeableConcept": {
                                "coding": [
                                    {
                                        "system": "http://terminology.hl7.org/CodeSystem/v3-TribalEntityUS",
                                        "code": "1.1",
                                        "display": "Apache",
                                    }
                                ]
                            },
                        },
                        {"url": "isEnrolled", "valueBoolean": True},
                    ],
                },
                {
                    "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-sex",
                    "valueCode": "M" if gender == "male" else ("F" if gender == "female" else "UNK"),
                },
            ],
        }],
        "AllergyIntolerance": [{
            "resourceType": "AllergyIntolerance",
            "id": _rid("alg", patient_id),
            "meta": {"profile": _profile("us-core-allergyintolerance"), "lastUpdated": now},
            "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical", "code": "active"}]},
            "verificationStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification", "code": "confirmed"}]},
            "category": ["medication"],
            "code": {"coding": [{"system": "http://snomed.info/sct", "code": "294954006", "display": "Penicillin allergy"}]},
            "patient": {"reference": p_ref},
            "reaction": [
                {
                    "manifestation": [
                        {"coding": [{"system": "http://snomed.info/sct", "code": "247472004", "display": "Hives"}]}
                    ],
                    "severity": "moderate",
                }
            ],
        }],
        "CarePlan": [
            {
                "resourceType": "CarePlan",
                "id": _rid("cpl", patient_id),
                "meta": {"profile": _profile("us-core-careplan"), "lastUpdated": now},
                "text": {
                    "status": "generated",
                    "div": '<div xmlns="http://www.w3.org/1999/xhtml">Care plan for chronic condition management.</div>',
                },
                "status": "active",
                "intent": "plan",
                "category": [{"coding": [{"system": "http://hl7.org/fhir/us/core/CodeSystem/careplan-category", "code": "assess-plan"}]}],
                "subject": {"reference": p_ref},
            }
        ],
        "CareTeam": [
            {
                "resourceType": "CareTeam",
                "id": _rid("ctm", patient_id),
                "meta": {"profile": _profile("us-core-careteam"), "lastUpdated": now},
                "status": "active",
                "subject": {"reference": p_ref},
                "participant": [
                    {
                        "role": [{"coding": [{"system": "http://snomed.info/sct", "code": "158965000", "display": "Medical practitioner"}]}],
                        "member": {"reference": "PractitionerRole/example-practitioner-role"},
                    },
                    {
                        "role": [{"coding": [{"system": "http://snomed.info/sct", "code": "133932002", "display": "Caregiver"}]}],
                        "member": {"reference": "Practitioner/example-practitioner"},
                    },
                    {
                        "role": [{"coding": [{"system": "http://snomed.info/sct", "code": "224535009", "display": "Parent"}]}],
                        "member": {"reference": f"RelatedPerson/{_rid('rel', patient_id)}"},
                    },
                ],
            }
        ],
        "Condition": [
            {
                "resourceType": "Condition",
                "id": _rid("con", patient_id),
                "meta": {"profile": _profile("us-core-condition-problems-health-concerns"), "lastUpdated": now},
                "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "resolved"}]},
                "verificationStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed"}]},
                "category": [
                    {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-category", "code": "problem-list-item"}]},
                    {"coding": [{"system": "http://hl7.org/fhir/us/core/CodeSystem/us-core-category", "code": "sdoh", "display": "SDOH"}]},
                ],
                "code": {"coding": [{"system": "http://snomed.info/sct", "code": "44054006"}]},
                "subject": {"reference": p_ref},
                "onsetDateTime": "2020-01-01T00:00:00Z",
                "abatementDateTime": "2024-01-01T00:00:00Z",
                "recordedDate": now,
                "extension": [{"url": "http://hl7.org/fhir/StructureDefinition/condition-assertedDate", "valueDateTime": "2020-01-01T10:00:00Z"}],
            },
            {
                "resourceType": "Condition",
                "id": _rid("cdx", patient_id),
                "meta": {"profile": _profile("us-core-condition-encounter-diagnosis"), "lastUpdated": now},
                "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "resolved"}]},
                "verificationStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed"}]},
                "category": [
                    {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-category", "code": "encounter-diagnosis"}]},
                    {"coding": [{"system": "http://hl7.org/fhir/us/core/CodeSystem/us-core-category", "code": "sdoh", "display": "SDOH"}]},
                ],
                "code": {"coding": [{"system": "http://snomed.info/sct", "code": "271737000"}]},
                "subject": {"reference": p_ref},
                "encounter": {"reference": f"Encounter/{enc_id}"},
                "onsetDateTime": "2021-05-10T00:00:00Z",
                "abatementDateTime": "2022-01-01T00:00:00Z",
                "recordedDate": now,
                "extension": [{"url": "http://hl7.org/fhir/StructureDefinition/condition-assertedDate", "valueDateTime": "2021-05-10T10:00:00Z"}],
            },
        ],
        "Coverage": [
            {
                "resourceType": "Coverage",
                "id": _rid("cov", patient_id),
                "meta": {"profile": _profile("us-core-coverage"), "lastUpdated": now},
                "status": "active",
                "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "HIP"}]},
                "subscriberId": "SUB12345",
                "identifier": [
                    {
                        "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0203", "code": "MB"}]},
                        "system": "http://hospital.org/coverage/memberid",
                        "value": "MEM12345",
                    }
                ],
                "beneficiary": {"reference": p_ref},
                "relationship": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/subscriber-relationship", "code": "self"}]},
                "period": {"start": "2024-01-01", "end": "2026-12-31"},
                "payor": [{"reference": "Organization/bulk-organization-1"}],
                "class": [
                    {
                        "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/coverage-class", "code": "group"}]},
                        "value": "GRP123",
                    },
                    {
                        "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/coverage-class", "code": "plan"}]},
                        "value": "PLN456",
                        "name": "Gold Plan",
                    },
                ],
            }
        ],
        "Device": [
            {
                "resourceType": "Device",
                "id": _rid("dev", patient_id),
                "meta": {"profile": _profile("us-core-implantable-device"), "lastUpdated": now},
                "status": "active",
                "type": {"coding": [{"system": "http://snomed.info/sct", "code": "34370006"}]},
                "patient": {"reference": p_ref},
                "manufacturer": "Medtronic",
                "udiCarrier": [{"deviceIdentifier": "00843169102317", "carrierHRF": "(01)00843169102317(17)230101(10)ABCD"}],
                "distinctIdentifier": "ABC12345",
                "manufactureDate": "2023-01-01T00:00:00Z",
                "expirationDate": "2030-01-01T00:00:00Z",
                "lotNumber": "LOT123",
                "serialNumber": "SN-987654",
            }
        ],
        "DiagnosticReport": [
            {
                "resourceType": "DiagnosticReport",
                "id": _rid("drp", patient_id),
                "meta": {"profile": _profile("us-core-diagnosticreport-lab"), "lastUpdated": now},
                "status": "final",
                "category": [
                    {
                        "coding": [
                            {"system": "http://terminology.hl7.org/CodeSystem/v2-0074", "code": "LAB"},
                            {"system": "http://loinc.org", "code": "LP29684-5"},
                            {"system": "http://loinc.org", "code": "LP29708-2"},
                        ]
                    }
                ],
                "code": {"coding": [{"system": "http://loinc.org", "code": "58410-2"}]},
                "subject": {"reference": p_ref},
                "effectiveDateTime": now,
                "issued": now,
                "encounter": {"reference": f"Encounter/{enc_id}"},
                "performer": [
                    {"reference": "Practitioner/example-practitioner"},
                    {"reference": "Organization/bulk-organization-1"},
                ],
                "result": [{"reference": f"Observation/{lab_obs_id}"}],
                "media": [{"link": {"reference": f"DocumentReference/{_rid('doc', patient_id)}"}}],
                "presentedForm": [{"contentType": "application/pdf", "data": "SGVsbG8="}],
            }
        ],
        "DocumentReference": [{
            "resourceType": "DocumentReference",
            "id": _rid("doc", patient_id),
            "meta": {"profile": _profile("us-core-documentreference"), "lastUpdated": now},
            "identifier": [{"system": "http://hospital.smarthealthit.org/document-reference", "value": f"DOC-{_pid_prefix(patient_id).upper()}-1"}],
            "status": "current",
            "docStatus": "final",
            "type": {"coding": [{"system": "http://loinc.org", "code": "34133-9"}]},
            "category": [{"coding": [{"system": "http://hl7.org/fhir/us/core/CodeSystem/us-core-documentreference-category", "code": "clinical-note"}]}],
            "subject": {"reference": p_ref},
            "date": now,
            "author": [{"reference": "Practitioner/example-practitioner"}],
            "content": [{
                "attachment": {"contentType": "text/plain", "data": "U2FtcGxlIGNsaW5pY2FsIG5vdGU="},
                "format": {"system": "http://ihe.net/fhir/ihe.formatcode.fhir/CodeSystem/formatcode", "code": "urn:ihe:iti:xds:2017:mimeTypeSufficient"},
            }],
            "context": {
                "encounter": [{"reference": f"Encounter/{enc_id}"}],
                "period": {"start": "2025-01-01T10:00:00Z", "end": "2025-01-01T11:00:00Z"},
            },
        }],
        "Encounter": [{
            "resourceType": "Encounter",
            "id": enc_id,
            "meta": {"profile": _profile("us-core-encounter"), "lastUpdated": now},
            "identifier": [{"system": "http://hospital.smarthealthit.org/encounter", "value": f"ENC-{_pid_prefix(patient_id).upper()}-1"}],
            "status": "finished",
            "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB"},
            "type": [{"coding": [{"system": "http://snomed.info/sct", "code": "185345009"}]}],
            "subject": {"reference": p_ref},
            "period": {"start": "2025-01-01T10:00:00Z", "end": "2025-01-01T11:00:00Z"},
            "participant": [{
                "type": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ParticipationType", "code": "ATND"}]}],
                "period": {"start": "2025-01-01T10:00:00Z", "end": "2025-01-01T11:00:00Z"},
                "individual": {"reference": "Practitioner/example-practitioner"},
            }],
            "reasonCode": [{"coding": [{"system": "http://snomed.info/sct", "code": "271737000", "display": "Anemia"}]}],
            "reasonReference": [
                {"reference": f"Condition/{_rid('cdx', patient_id)}"},
                {"reference": f"Condition/{_rid('con', patient_id)}"}
            ],
            "hospitalization": {
                "dischargeDisposition": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/discharge-disposition", "code": "home"}]}
            },
            "serviceProvider": {"reference": "Organization/bulk-organization-1"},
            "location": [{"location": {"reference": "Location/bulk-location-1"}}],
        }],
        "Goal": [{"resourceType": "Goal", "id": _rid("gol", patient_id), "meta": {"profile": _profile("us-core-goal"), "lastUpdated": now}, "lifecycleStatus": "active", "description": {"text": "Maintain HbA1c below 7%"}, "subject": {"reference": p_ref}, "target": [{"dueDate": "2026-12-31"}]}],
        "Immunization": [{
            "resourceType": "Immunization",
            "id": _rid("imm", patient_id),
            "meta": {"profile": _profile("us-core-immunization"), "lastUpdated": now},
            "status": "completed",
            "statusReason": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/immunization-status-reason", "code": "IMMUNE"}]},
            "vaccineCode": {"coding": [{"system": "http://hl7.org/fhir/sid/cvx", "code": "207"}]},
            "patient": {"reference": p_ref},
            "occurrenceDateTime": now,
            "primarySource": True,
            "encounter": {"reference": f"Encounter/{enc_id}"},
            "location": {"reference": "Location/bulk-location-1"},
        }],
        "MedicationRequest": [{
            "resourceType": "MedicationRequest", 
            "id": mreq_id, 
            "meta": {"profile": _profile("us-core-medicationrequest"), "lastUpdated": now}, 
            "status": "active", 
            "intent": "order", 
            "category": [
                {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/medicationrequest-category", "code": "outpatient"}]},
                {"coding": [{"system": "http://hl7.org/fhir/us/core/CodeSystem/us-core-medicationrequest-category", "code": "discharge"}]}
            ],
            "reportedBoolean": False,
            "medicationReference": {"reference": f"Medication/{med_id}"}, 
            "subject": {"reference": p_ref}, 
            "encounter": {"reference": f"Encounter/{enc_id}"}, 
            "reasonCode": [{"coding": [{"system": "http://snomed.info/sct", "code": "271737000", "display": "Anemia"}]}],
            "authoredOn": now, 
            "requester": {"reference": "Practitioner/example-practitioner"},
            "dosageInstruction": [{
                "text": "Take 1 tablet by mouth once daily",
                "timing": {"repeat": {"frequency": 1, "period": 1, "periodUnit": "d"}},
                "doseAndRate": [{"doseQuantity": {"value": 1, "unit": "tablet", "system": "http://unitsofmeasure.org", "code": "{tbl}"}}]
            }],
            "dispenseRequest": {
                "numberOfRepeatsAllowed": 3,
                "quantity": {"value": 30, "unit": "tab"}
            },
            "extension": [{
                "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-medication-adherence",
                "extension": [
                    {"url": "medicationAdherence", "valueCodeableConcept": {"coding": [{"system": "http://snomed.info/sct", "code": "183964008", "display": "Treatment compliant (finding)"}]}}
                ]
            }]
        }],
        "MedicationDispense": [{
            "resourceType": "MedicationDispense",
            "id": _rid("mds", patient_id),
            "meta": {"profile": _profile("us-core-medicationdispense"), "lastUpdated": now},
            "status": "completed",
            "medicationReference": {"reference": f"Medication/{med_id}"},
            "subject": {"reference": p_ref},
            "context": {"reference": f"Encounter/{enc_id}"},
            "performer": [
                {"actor": {"reference": "Practitioner/example-practitioner"}},
                {"actor": {"reference": "Organization/bulk-organization-1"}}
            ],
            "authorizingPrescription": [{"reference": f"MedicationRequest/{mreq_id}"}],
            "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "FFP"}]},
            "whenHandedOver": now,
            "quantity": {"value": 30, "unit": "tab"},
            "dosageInstruction": [{
                "text": "Take 1 tablet by mouth once daily",
                "timing": {"repeat": {"frequency": 1, "period": 1, "periodUnit": "d"}},
                "doseAndRate": [{"doseQuantity": {"value": 1, "unit": "tablet", "system": "http://unitsofmeasure.org", "code": "{tbl}"}}],
            }],
        }],
        "Observation": obs,
        "Procedure": [{"resourceType": "Procedure", "id": _rid("pro", patient_id), "meta": {"profile": _profile("us-core-procedure"), "lastUpdated": now}, "status": "completed", "code": {"coding": [{"system": "http://snomed.info/sct", "code": "430193006"}]}, "subject": {"reference": p_ref}, "encounter": {"reference": f"Encounter/{enc_id}"}, "performedDateTime": now, "basedOn": [{"reference": f"ServiceRequest/{serv_id}"}]}],
        "RelatedPerson": [{"resourceType": "RelatedPerson", "id": _rid("rel", patient_id), "meta": {"profile": _profile("us-core-relatedperson"), "lastUpdated": now}, "active": True, "patient": {"reference": p_ref}, "relationship": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-RoleCode", "code": "SPS"}]}], "name": [{"family": "Smith", "given": ["Jordan"]}], "telecom": [{"system": "phone", "value": "555-555-6677"}]}],
        "ServiceRequest": [{"resourceType": "ServiceRequest", "id": serv_id, "meta": {"profile": _profile("us-core-servicerequest"), "lastUpdated": now}, "status": "active", "intent": "order", "category": [{"coding": [{"system": "http://snomed.info/sct", "code": "386053000"}]}], "code": {"coding": [{"system": "http://snomed.info/sct", "code": "108252007"}]}, "subject": {"reference": p_ref}, "encounter": {"reference": f"Encounter/{enc_id}"}, "authoredOn": now, "requester": {"reference": "Practitioner/example-practitioner"}}],
        "Specimen": [{"resourceType": "Specimen", "id": spm_id, "meta": {"profile": _profile("us-core-specimen"), "lastUpdated": now}, "status": "available", "type": {"coding": [{"system": "http://snomed.info/sct", "code": "119297000"}]}, "subject": {"reference": p_ref}, "collection": {"collectedDateTime": now}}],
    }

    provenance_targets: List[Dict[str, Any]] = []
    for r_type, resources in patient_resources.items():
        if r_type == "Provenance":
            continue
        provenance_targets.extend(resources)
    patient_resources["Provenance"] = [build_provenance_for_resource(resource, now) for resource in provenance_targets]
    return patient_resources


def _apply_filters(resources: List[Dict[str, Any]], resource_type: str, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
    params = {k: (v[-1] if isinstance(v, list) and v else v) for k, v in (search_params or {}).items()}
    if params.get("_id"):
        ids = {_normalize_id_token(v) for v in _csv_tokens(params.get("_id"))}
        resources = [res for res in resources if res.get("id") in ids]
    if params.get("status"):
        statuses = {v.lower() for v in _csv_tokens(params.get("status"))}
        resources = [res for res in resources if str(res.get("status", "")).lower() in statuses]
    if params.get("category"):
        resources = [res for res in resources if _coding_matches(params.get("category"), _get_codings(res, "category"))]
    if params.get("code"):
        resources = [res for res in resources if _coding_matches(params.get("code"), _get_codings(res, "code"))]
    if resource_type == "Condition" and params.get("clinical-status"):
        resources = [res for res in resources if _coding_matches(params.get("clinical-status"), _get_codings(res, "clinicalStatus"))]
    if resource_type == "Goal" and params.get("lifecycle-status"):
        targets = {v.lower() for v in _csv_tokens(params.get("lifecycle-status"))}
        resources = [res for res in resources if str(res.get("lifecycleStatus", "")).lower() in targets]
    if resource_type == "Goal" and params.get("target-date"):
        resources = [res for res in resources if _date_match((res.get("target") or [{}])[0].get("dueDate"), params.get("target-date"))]
    if resource_type in {"Observation", "DiagnosticReport", "Procedure", "Immunization"} and params.get("date"):
        date_field = {"Observation": "effectiveDateTime", "DiagnosticReport": "effectiveDateTime", "Procedure": "performedDateTime", "Immunization": "occurrenceDateTime"}[resource_type]
        resources = [res for res in resources if _date_match(res.get(date_field), params.get("date"))]
    if resource_type == "Encounter" and params.get("date"):
        resources = [res for res in resources if _date_match((res.get("period") or {}).get("start"), params.get("date"))]
    if resource_type == "DocumentReference" and params.get("type"):
        resources = [res for res in resources if _coding_matches(params.get("type"), _get_codings(res, "type"))]
    if resource_type == "DocumentReference" and params.get("date"):
        resources = [res for res in resources if _date_match(res.get("date"), params.get("date"))]
    if resource_type == "MedicationRequest" and params.get("intent"):
        intents = {v.lower() for v in _csv_tokens(params.get("intent"))}
        resources = [res for res in resources if str(res.get("intent", "")).lower() in intents]
    if resource_type == "MedicationRequest" and params.get("authoredon"):
        resources = [res for res in resources if _date_match(res.get("authoredOn"), params.get("authoredon"))]
    if resource_type == "ServiceRequest":
        authored = params.get("authored") or params.get("authoredon")
        if authored:
            resources = [res for res in resources if _date_match(res.get("authoredOn"), authored)]
    if resource_type == "Provenance" and params.get("patient"):
        patient_ref = params.get("patient")
        if not str(patient_ref).startswith("Patient/"):
            patient_ref = f"Patient/{patient_ref}"
        resources = [
            res for res in resources
            if any(str(target.get("reference", "")).startswith(patient_ref) for target in res.get("target", []))
        ]
    if resource_type == "Provenance" and params.get("target"):
        target_token = str(params.get("target"))
        resources = [
            res for res in resources
            if any(str(target.get("reference", "")) == target_token for target in res.get("target", []))
        ]
    if resource_type == "Patient" and params.get("birthdate"):
        resources = [res for res in resources if _date_match(res.get("birthDate"), params.get("birthdate"))]
    if resource_type == "Patient" and params.get("gender"):
        resources = [res for res in resources if str(res.get("gender", "")).lower() == str(params.get("gender")).lower()]
    return resources


def build_resources_for_patient(
    patient: Optional[Patient],
    resource_type: str,
    search_params: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    if resource_type not in SUPPORTED_RESOURCE_TYPES:
        return []
    if patient is None:
        static_refs = build_static_reference_resources(_now_iso())
        return _apply_filters(copy.deepcopy(static_refs.get(resource_type, [])), resource_type, search_params or {})
    now = _now_iso()
    merged = _build_shared(patient, now)
    merged.update(_build_patient_data(patient, now))
    resources = copy.deepcopy(merged.get(resource_type, []))
    if resource_type not in SHARED_RESOURCE_TYPES:
        patient_ref = f"Patient/{patient.id}"
        filtered: List[Dict[str, Any]] = []
        for res in resources:
            ref = None
            for key in ("patient", "subject", "beneficiary"):
                item = res.get(key)
                if isinstance(item, dict) and item.get("reference"):
                    ref = item["reference"]
                    break
            if ref in {patient_ref, None}:
                filtered.append(res)
        resources = filtered
    return _apply_filters(resources, resource_type, search_params or {})


def build_provenance_for_resource(resource: Dict[str, Any], now: Optional[str] = None) -> Dict[str, Any]:
    timestamp = now or _now_iso()
    r_type = resource.get("resourceType", "Resource")
    r_id = resource.get("id", "unknown")
    return {
        "resourceType": "Provenance",
        "id": f"prov-{r_type.lower()}-{r_id}",
        "meta": {
            "profile": _profile("us-core-provenance"),
            "lastUpdated": timestamp,
        },
        "target": [{"reference": f"{r_type}/{r_id}"}],
        "recorded": timestamp,
        "agent": [
            {
                "type": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/provenance-participant-type",
                            "code": "author",
                        }
                    ]
                },
                "who": {"reference": "Practitioner/example-practitioner"},
            }
        ],
    }
