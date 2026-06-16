# US Core STU7 Single-Patient Projection Mapping

This document defines the relational-to-FHIR mapping used by projectors for Inferno Single Patient API tests.
Data remains relational in Django models; FHIR semantics are projected at response time only.

## Scope

- Target: US Core STU7 Single Patient Server tests (Inferno).
- Source models:
  - `apps.clinical.patients.models`
  - `apps.clinical.health_screening.models`
- FHIR generation layer:
  - `apps.integration.fhir_integration.projectors.*`
  - `apps.integration.fhir_integration.terminology.TerminologyService`

## Must Support Mapping by Profile

### `us-core-patient` -> `PatientProjector`
- Must Support:
  - `identifier`, `name`, `telecom`, `gender`, `birthDate`, `address`, `communication`, US Core race/ethnicity/birthsex extensions.
- Relational source:
  - `Patient.medical_record_number`, `first_name`, `last_name`, `middle_name`, `phone_number`, `email_address`, `sex`, `date_of_birth`, `current_address_line1/current_address_line2/city/state/postal_code/country`, `preferred_language`, `race`, `ethnicity`.
- Placeholder behavior:
  - Default telecom/address/language/gender-safe fallbacks when blank.

### `us-core-allergyintolerance` -> `AllergyIntoleranceProjector`
- Must Support:
  - `clinicalStatus`, `verificationStatus`, `patient`, `code`, `reaction.manifestation`.
- Relational source:
  - `PatientAllergy.substance`, `reaction`, `severity`, `patient`.
- Placeholder behavior:
  - Fallback manifestation text and severity normalization.

### `us-core-careplan` -> `CarePlanProjector`
- Must Support:
  - `status`, `intent`, `subject`, `category`, narrative.
- Relational source:
  - `CarePlan.status`, `care_plan`, `assessment_and_plan`, `patient`.
- Placeholder behavior:
  - Narrative fallback when fields are empty.

### `us-core-careteam` -> `CareTeamProjector`
- Must Support:
  - `status`, `subject`, `participant.role`, `participant.member`.
- Relational source:
  - `Patient.care_team` via `CareTeamMember.name/role`.
- Placeholder behavior:
  - Default participant when no active team members exist.

### `us-core-condition-problems-health-concerns` and `us-core-condition-encounter-diagnosis` -> `ConditionProjector`
- Must Support:
  - `clinicalStatus`, `verificationStatus`, `category`, `code`, `subject`, `onsetDateTime`, `recordedDate`.
  - Encounter diagnosis linkage: `encounter`.
- Relational source:
  - `Problem.problem_name/status/date_of_onset/date_of_diagnosis/date_of_resolution/patient`.
  - `HealthScreening` used to populate `Condition.encounter`.
- Placeholder behavior:
  - Date fallbacks from `created_at` when diagnosis/onset missing.

### `us-core-coverage` -> `CoverageProjector`
- Must Support:
  - `status`, `type`, `subscriberId`, `beneficiary`, `relationship`, `payor`, `class`, `period`.
- Relational source:
  - `InsuranceData.coverage_status/coverage_type/subscriber_identifier/member_identifier/relationship_to_subscriber/group_identifier/payer_identifier/patient`.
- Placeholder behavior:
  - `period.start` from `created_at` fallback.

### `us-core-implantable-device` -> `DeviceProjector`
- Must Support:
  - `status`, `type`, `udiCarrier`, `patient`.
- Relational source:
  - `MedicalDevice.device_name/status/udi/patient`.
- Placeholder behavior:
  - Safe UDI fallback when absent.

### `us-core-diagnosticreport-lab` -> `DiagnosticReportProjector`
- Must Support:
  - `status`, `category`, `code`, `subject`, `effectiveDateTime`, `issued`, `performer`, `result`.
- Relational source:
  - `LaboratoryResults.test_name/health_screening/screening_date`.
- Required reference:
  - `DiagnosticReport.result -> Observation/{id}` from matching projected lab Observation.

### `us-core-documentreference` -> `DocumentReferenceProjector`
- Must Support:
  - `status`, `type`, `category`, `subject`, `date`, `author`, `content.attachment`.
- Relational source:
  - `PatientDocument.note_type/content/document_date/patient`.
- Placeholder behavior:
  - Default note type mapping and text payload encoding fallback.

### `us-core-encounter` -> `EncounterProjector`
- Must Support:
  - `status`, `class`, `type`, `subject`, `period`, `participant`, `location`, `serviceProvider`.
- Relational source:
  - `HealthScreening.encounter_type/encounter_time/encounter_location/encounter_disposition/patient`.

### `us-core-goal` -> `GoalProjector`
- Must Support:
  - `lifecycleStatus`, `description`, `subject`.
- Relational source:
  - `AdvanceDirective.patient_goals/sdoh_goals/patient`.
- Placeholder behavior:
  - Default description/target due date when data absent.

### `us-core-immunization` -> `ImmunizationProjector`
- Must Support:
  - `status`, `vaccineCode`, `patient`, `occurrenceDateTime`, `primarySource`.
- Relational source:
  - `Immunization.vaccine_name/administration_date/patient`.

### `us-core-medication` -> `MedicationProjector`
- Must Support:
  - `code`.
- Relational source:
  - `PatientMedication.medication`.

### `us-core-medicationrequest` -> `MedicationRequestProjector`
- Must Support:
  - `status`, `intent`, `medicationReference`, `subject`, `authoredOn`, `requester`, `dosageInstruction`.
- Relational source:
  - `PatientMedication.medication/dispense_status/start_date/medication_instructions/indication/patient`.
- Required include:
  - `MedicationRequest:medication`.

### `us-core-medicationdispense` -> `MedicationDispenseProjector`
- Must Support:
  - `status`, `medicationReference`, `subject`, `performer`, `authorizingPrescription`, `whenHandedOver`, `quantity`.
- Relational source:
  - `PatientMedication.dispense_status/end_date/medication_instructions/patient`.
- Status mapping:
  - internal `active/completed/stopped` -> FHIR `in-progress/completed/stopped`.

### `us-core-observation-lab`, `us-core-vital-signs`, `us-core-smokingstatus` (+ related observation profiles) -> `ObservationProjector`
- Must Support:
  - `status`, `category`, `code`, `subject`, `effectiveDateTime`, and value element (`valueQuantity`/`valueCodeableConcept`/`valueString`).
- Relational source:
  - `VitalSigns.*`, `LaboratoryResults.*`, `HealthStatusAssessment.smoking_status`.
- Required reference:
  - `Observation.subject -> Patient/{id}` on all projected observations.
- Placeholder behavior:
  - fallback coding and value conversion guards.

### `us-core-procedure` -> `ProcedureProjector`
- Must Support:
  - `status`, `code`, `subject`, `performed[x]`.
- Relational source:
  - `Procedure.procedure_name/performance_time/patient`.

### `us-core-servicerequest` -> `ServiceRequestProjector`
- Must Support:
  - `status`, `intent`, `category`, `code`, `subject`, `authoredOn`, `requester`.
- Relational source:
  - `MedicalOrder.order_type/order_detail/order_date/patient`.

### `us-core-specimen` -> `SpecimenProjector`
- Must Support:
  - `status`, `type`, `subject`, `collection.collectedDateTime`.
- Relational source:
  - `LaboratoryResults.specimen_type/health_screening/screening_date`.

### Supporting references for include/revinclude
- `us-core-practitioner`, `us-core-practitionerrole`, `us-core-organization`, `us-core-location`, `us-core-relatedperson`, `us-core-provenance`
- Implemented via corresponding projectors and `ReferenceBuilder`.

## Required Search Parameter Coverage (Single Patient)

Implemented in projectors/capability statement for Inferno-relevant interactions:
- Patient: `_id`, `name`, `family`, `given`, `birthdate`, `gender`, `identifier`
- AllergyIntolerance: `patient`, `clinical-status`, `_id`
- CarePlan: `patient`, `category`, `status`, `_id`
- CareTeam: `patient`, `status`, `_id`
- Condition: `patient`, `_id`, `category`, `clinical-status`, `code`, `onset-date`
- Coverage: `patient`, `_id`
- Device: `patient`, `_id`
- DiagnosticReport: `patient`, `category`, `code`, `date`, `_id`
- DocumentReference: `patient`, `category`, `type`, `date`, `_id`
- Encounter: `patient`, `_id`, `date`, `type`
- Goal: `patient`, `_id`, `lifecycle-status`
- Immunization: `patient`, `status`, `date`, `_id`
- Medication: `_id`, `patient`
- MedicationRequest: `patient`, `intent`, `status`, `_id`
- MedicationDispense: `patient`, `status`, `_id`
- Observation: `patient`, `category`, `code`, `date`, `_id`
- Procedure: `patient`, `date`, `code`, `_id`
- RelatedPerson: `patient`, `_id`
- ServiceRequest: `patient`, `_id`, `status`, `category`
- Specimen: `patient`, `_id`

## Key Referential Rules Enforced

- `Condition.encounter` is projected from relational `HealthScreening`.
- `DiagnosticReport.result` references projected `Observation` ids.
- `Observation.subject` always references `Patient/{id}`.

## Notes

- Terminology (LOINC/SNOMED/RxNorm/Ucum) is applied in projectors and terminology service, not persisted.
- When relational data is missing, projectors provide standards-safe placeholder values for Must Support population.
