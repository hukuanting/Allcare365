# Golden Patient Specification (US Core STU7, Inferno Single Patient)

Status: `CONTRACT DRAFT FOR APPROVAL`  
Purpose: define the single canonical patient graph that satisfies non-optional Inferno STU7 checks.

## 1. Required Resource Instances

Minimum instance inventory for one Golden Patient (`Patient/{id}`):

1. `Patient`: 1
2. `Encounter`: 2 (at least one for active context, one for resolved/diagnosis context)
3. `Condition`: 3
   - 1 active problem/health concern
   - 1 resolved encounter diagnosis
   - 1 screening-assessment category condition
4. `Observation`:
   - Lab: 3 (to cover `valueQuantity`, `valueCodeableConcept`, `valueString`)
   - Vital signs: 1 per required profile in lock scope
5. `DiagnosticReport`: 2
   - 1 lab report
   - 1 note/report exchange
6. `DocumentReference`: 1 (clinical note)
7. `Specimen`: 1
8. `Coverage`: 1
9. `Device`: 1
10. `Immunization`: 1
11. `MedicationRequest`: 1
12. `MedicationDispense`: 1
13. `Procedure`: 1
14. `ServiceRequest`: 1
15. `Goal`: 1
16. `CarePlan`: 1
17. `CareTeam`: 1
18. `AllergyIntolerance`: 1
19. `RelatedPerson`: 1
20. `Provenance`: projected per target resource

Reference-anchor singleton resources (projector-owned):

- `Practitioner/example-practitioner`
- `Organization/bulk-organization-1`
- `Location/bulk-location-1`
- `Media/media-example-1`

## 2. Must Support Elements Always Projected (Lock Scope)

This section declares non-optional ALWAYS-projected Must Support elements for core lock sequence.

### Patient

- `identifier.system`, `identifier.value`
- `name.use`, `name.family`, `name.given`, `name.suffix`, `name.period.end`
- `telecom.system`, `telecom.value`, `telecom.use`
- `gender`, `birthDate`, `deceasedDateTime`
- `address.use`, `address.line`, `address.city`, `address.state`, `address.postalCode`, `address.period.end`
- `communication.language`

### Encounter

- `identifier.system`, `identifier.value`
- `status`, `class`, `type`, `subject`, `period`
- `participant.type`, `participant.period`, `participant.individual`
- `reasonReference`
- `location.location`, `serviceProvider`

### Condition (Problems/Health Concerns + Encounter Diagnosis)

- `clinicalStatus`, `verificationStatus`, `category`, `code`, `subject`
- `onsetDateTime`, `recordedDate`, `abatementDateTime`
- `encounter`
- extension `condition-assertedDate`

### Observation (Lab lock scope)

- `status`, `category`, `code`, `subject`, `encounter`, `effectiveDateTime`
- one of `valueQuantity` / `valueCodeableConcept` / `valueString`
- `interpretation`
- `specimen`
- `referenceRange`

### DiagnosticReport (Lab + Note lock scope)

- `status`, `category`, `code`, `subject`, `encounter`, `effectiveDateTime`, `issued`
- `performer`
- `result`
- `media.link`
- `presentedForm` (note profile)

### DocumentReference

- `identifier`
- `status`, `type`, `category`, `subject`, `date`
- `author`
- `content.attachment.contentType`, `content.attachment.data`, `content.format`
- `context.encounter`, `context.period`

## 3. Relational Source vs Synthesized Semantics

### Relationally sourced (examples)

- `Patient.first_name/last_name/date_of_birth/sex`
- `HealthScreening.encounter_*`
- `Problem.problem_name/date_of_onset/date_of_diagnosis/date_of_resolution/status`
- `LaboratoryResults.test_name/value_result/result_unit/result_reference_range/specimen_*`
- `PatientDocument.note_type/content/document_date`
- `InsuranceData.*`
- `PatientMedication.*`

### Synthesized at projection time (examples)

- Required fallback slices (`Patient.name.use=old`, `Patient.address.use=old`)
- Placeholder dates where Must Support requires presence and relational is null
- FHIR `meta.profile` / `meta.lastUpdated`
- Terminology codings (LOINC/SNOMED/RxNorm/UCUM) via TerminologyService
- Static reference anchors (Practitioner/Organization/Location/Media)

## 4. Required Reference Integrity for Golden Patient

All must resolve via REST read:

1. `Condition.encounter -> Encounter`
2. `Encounter.participant.individual -> Practitioner`
3. `Encounter.reasonReference -> Condition`
4. `Encounter.location.location -> Location`
5. `Encounter.serviceProvider -> Organization`
6. `Observation.specimen -> Specimen`
7. `DiagnosticReport.result -> Observation`
8. `DiagnosticReport.performer -> Practitioner` (and optional Organization)
9. `DiagnosticReport.media.link -> Media`
10. `DocumentReference.author -> Practitioner`
11. `DocumentReference.context.encounter -> Encounter`
12. `Coverage.payor -> Organization`
13. `MedicationRequest.requester -> Practitioner`
14. `MedicationDispense.context -> Encounter`
15. `MedicationDispense.authorizingPrescription -> MedicationRequest`

