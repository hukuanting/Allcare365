---
name: fhir-us-core-mapper
description: Maps clinical data to HL7 FHIR R4 resources compliant with US Core 7.0.0 and USCDI v6. Use when mapping database fields, CSVs, or internal models to FHIR resources for ONC certification.
---

# FHIR US Core Mapper

This skill provides specialized expertise for generating and validating FHIR resources that comply with the HL7 US Core Implementation Guide (v7.0.0) and USCDI v6 standards for the Allcare 365 EHR system.

## Core Workflows

### 1. Resource Mapping
When mapping clinical data to FHIR, refer to [us-core-v7-mapping.md](references/us-core-v7-mapping.md) for detailed field-to-field instructions.

**Strategy:**
1. Identify the target US Core Profile (e.g., Patient, Observation, Condition).
2. Extract required data from local models (`apps.clinical.*`).
3. Construct the FHIR JSON structure ensuring "Must Support" elements are included.
4. Add mandatory extensions (e.g., Race, Ethnicity, assertedDate).

### 2. Compliance Validation
After generating a resource snippet, use the [must-support-checklist.md](references/must-support-checklist.md) to perform a self-audit before submitting code or responding to the user.

## Code Patterns

### Python (fhir.resources)
Use the following pattern when implementing conversion logic in `apps/integration/fhir_integration/services.py`:

```python
from fhir.resources.condition import Condition

def create_us_core_condition(data):
    condition_data = {
        "resourceType": "Condition",
        "meta": {"profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition-problems-health-concerns"]},
        "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
        "category": [{"coding": [{"system": "http://hl7.org/fhir/us/core/CodeSystem/condition-category", "code": "problem-list-item"}]}],
        "code": {"coding": [{"system": "http://snomed.info/sct", "code": data['snomed_code'], "display": data['display']}]},
        "subject": {"reference": f"Patient/{data['patient_id']}"},
        "onsetDateTime": data['onset_date'],
        "recordedDate": data['recorded_date'],
        "extension": [
            {"url": "http://hl7.org/fhir/StructureDefinition/condition-assertedDate", "valueDateTime": data['recorded_date']}
        ]
    }
    return Condition(**condition_data)
```

## Reference Links
- [HL7 US Core IG v7.0.0](https://build.fhir.org/ig/HL7/US-Core/)
- [USCDI v6 Standards](https://www.healthit.gov/isa/united-states-core-data-interoperability-uscdi)