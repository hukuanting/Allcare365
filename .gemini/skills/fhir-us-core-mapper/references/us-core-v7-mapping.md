# US Core v7 (USCDI v6) FHIR Mapping Guide

## 1. Condition Profile (Problems and Health Concerns)
Mapped to: `http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition-problems-health-concerns`

### Mandatory (SHALL) and Must Support (MS) Elements:
| Element | Cardinality | Requirement | Guidance |
| :--- | :--- | :--- | :--- |
| `clinicalStatus` | 0..1 | MS | Must use `http://terminology.hl7.org/CodeSystem/condition-clinical` |
| `verificationStatus` | 0..1 | MS | Must use `http://terminology.hl7.org/CodeSystem/condition-ver-status` |
| `category` | 1..* | SHALL | Must include `us-core` slice: `http://hl7.org/fhir/us/core/CodeSystem/condition-category` |
| `code` | 1..1 | SHALL | Must use SNOMED CT or ICD-10-CM |
| `subject` | 1..1 | SHALL | Reference to US Core Patient |
| `onsetDateTime` | 0..1 | MS | Date/Time when the condition started |
| `abatementDateTime` | 0..1 | MS | Required if the condition is resolved |
| `recordedDate` | 0..1 | MS | Date/Time when the record was first created |
| `extension:assertedDate`| 0..1 | MS | `http://hl7.org/fhir/StructureDefinition/condition-assertedDate` |

## 2. Patient Profile
Mapped to: `http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient`

### Must Support Elements:
- `identifier` (Medical Record Number)
- `name.family`, `name.given`
- `gender`, `birthDate`
- `address`, `telecom` (phone/email)
- `communication.language`
- **Race Extension**: `http://hl7.org/fhir/us/core/StructureDefinition/us-core-race`
- **Ethnicity Extension**: `http://hl7.org/fhir/us/core/StructureDefinition/us-core-ethnicity`
- **Birth Sex Extension**: `http://hl7.org/fhir/us/core/StructureDefinition/us-core-birthsex`

## 3. Observation Profile (Lab Results)
Mapped to: `http://hl7.org/fhir/us/core/StructureDefinition/us-core-observation-lab`

### Key Requirements:
- `status`: Must be `final`, `amended`, etc.
- `category`: Must include `laboratory` (http://terminology.hl7.org/CodeSystem/observation-category).
- `code`: Must use LOINC codes.
- `subject`: Reference to Patient.
- `effectiveDateTime`: Date/Time of result.
- `valueQuantity` or `valueCodeableConcept`.
