# Projection Contract Table

Status: `FINAL DRAFT FOR APPROVAL`  
Format: `Relational Field -> FHIR Element -> Terminology Source -> Reference Dependency`

## A. Core Chain Contract

| Relational field(s) | FHIR element(s) | Terminology source | Reference dependency |
|---|---|---|---|
| `Patient.id` | `Patient.id` | N/A | N/A |
| `Patient.medical_record_number` | `Patient.identifier.value` (`system` fixed) | projector constant | N/A |
| `Patient.first_name,last_name,middle_name,name_suffix,previous_name` | `Patient.name[*]` incl. old-name slice | N/A | N/A |
| `Patient.date_of_birth` | `Patient.birthDate` | N/A | N/A |
| `Patient.date_of_death` | `Patient.deceasedDateTime` | N/A | N/A |
| `Patient.sex` | `Patient.gender` | TerminologyService gender mapping | N/A |
| `Patient.current_address_* , previous_address` | `Patient.address[*]` incl. old-address slice | N/A | N/A |
| `Patient.phone_number,email_address` | `Patient.telecom[*]` | N/A | N/A |
| `Patient.preferred_language` | `Patient.communication.language` | BCP-47 mapping | N/A |
| `HealthScreening.id` | `Encounter.id` | N/A | `Encounter.subject -> Patient` |
| `HealthScreening.encounter_identifier` | `Encounter.identifier.value` | N/A | N/A |
| `HealthScreening.encounter_type` | `Encounter.class`, `Encounter.type` | TerminologyService class/type mapping | N/A |
| `HealthScreening.encounter_time` | `Encounter.period.start/end` | N/A | N/A |
| `HealthScreening.encounter_disposition` | `Encounter.hospitalization.dischargeDisposition` | TerminologyService | N/A |
| projector singleton | `Encounter.participant.individual` | N/A | `-> Practitioner/example-practitioner` |
| projector singleton | `Encounter.location.location` | N/A | `-> Location/bulk-location-1` |
| projector singleton | `Encounter.serviceProvider` | N/A | `-> Organization/bulk-organization-1` |
| `Problem.id` | `Condition.id` | N/A | `Condition.subject -> Patient` |
| `Problem.problem_name` | `Condition.code` | TerminologyService SNOMED mapping/fallback | N/A |
| `Problem.status,date_of_resolution` | `Condition.clinicalStatus` | TerminologyService condition status mapping | N/A |
| `Problem.date_of_onset` | `Condition.onsetDateTime` + assertedDate extension | N/A | N/A |
| `Problem.date_of_diagnosis` | `Condition.recordedDate` | N/A | N/A |
| `Problem.date_of_resolution` (+ fallback rule) | `Condition.abatementDateTime` | N/A | N/A |
| `Problem + projector rule` | `Condition.category` slices | TerminologyService/category constants | N/A |
| `HealthScreening.id` (by patient join) | `Condition.encounter` | N/A | `-> Encounter/enc-*` |
| `LaboratoryResults.id` | `Observation.id` (lab) | N/A | `Observation.subject -> Patient` |
| `LaboratoryResults.test_name` | `Observation.code` | TerminologyService LOINC mapping | N/A |
| `LaboratoryResults.value_result,result_unit` | `Observation.value[x]` | TerminologyService UCUM mapping | N/A |
| `LaboratoryResults.result_interpretation` (or fallback) | `Observation.interpretation` | TerminologyService | N/A |
| `LaboratoryResults.result_reference_range` | `Observation.referenceRange` | N/A | N/A |
| `HealthScreening.id` (lab FK) | `Observation.encounter` | N/A | `-> Encounter/enc-*` |
| `LaboratoryResults.id` | `Observation.specimen` | N/A | `-> Specimen/spm-*` |
| `LaboratoryResults.id` | `Specimen.id` | N/A | `Specimen.subject -> Patient` |
| `LaboratoryResults.specimen_type` | `Specimen.type` | TerminologyService SNOMED mapping | N/A |
| `HealthScreening.screening_date` | `Specimen.collection.collectedDateTime` | N/A | N/A |
| `LaboratoryResults.id` | `DiagnosticReport.id` (lab) | N/A | `DiagnosticReport.subject -> Patient` |
| `LaboratoryResults.test_name` | `DiagnosticReport.code` (lab) | TerminologyService LOINC mapping | N/A |
| projector constant + profile routing | `DiagnosticReport.category` | TerminologyService/constants | N/A |
| `HealthScreening.id` | `DiagnosticReport.encounter` | N/A | `-> Encounter/enc-*` |
| `LaboratoryResults.id` | `DiagnosticReport.result` | N/A | `-> Observation/obs-*-lab` |
| projector singleton | `DiagnosticReport.performer` | N/A | `-> Practitioner/example-practitioner` |
| projector singleton | `DiagnosticReport.media.link` | N/A | `-> Media/media-example-1` |
| `PatientDocument.id` | `DiagnosticReport.id` (note) | N/A | `DiagnosticReport.subject -> Patient` |
| `PatientDocument.note_type` | `DiagnosticReport.code` (note) | TerminologyService LOINC mapping | N/A |
| `PatientDocument.content` | `DiagnosticReport.presentedForm.data` | base64 encoder | N/A |
| `PatientDocument.id` | `DocumentReference.id` | N/A | `DocumentReference.subject -> Patient` |
| `PatientDocument.note_type` | `DocumentReference.type` | TerminologyService LOINC mapping | N/A |
| `PatientDocument.document_date` | `DocumentReference.date`, `context.period` | N/A | N/A |
| `PatientDocument.content` | `DocumentReference.content.attachment.data` | base64 encoder | N/A |
| projector singleton | `DocumentReference.author` | N/A | `-> Practitioner/example-practitioner` |
| `HealthScreening.id` (by patient join) | `DocumentReference.context.encounter` | N/A | `-> Encounter/enc-*` |

## B. Additional Non-Optional Contracts (Minimum ONC-pass)

| Relational field(s) | FHIR element(s) | Terminology source | Reference dependency |
|---|---|---|---|
| `InsuranceData.coverage_status` | `Coverage.status` | TerminologyService coverage status map | N/A |
| `InsuranceData.member_identifier` | `Coverage.identifier:memberid.value` | N/A | N/A |
| `InsuranceData.subscriber_identifier` | `Coverage.subscriberId` | N/A | N/A |
| `InsuranceData.relationship_to_subscriber` | `Coverage.relationship` | TerminologyService | N/A |
| `InsuranceData.group_identifier` | `Coverage.class:group.value` | N/A | N/A |
| projector value | `Coverage.class:plan.value/name` | N/A | N/A |
| projector singleton | `Coverage.payor` | N/A | `-> Organization/bulk-organization-1` |
| `MedicalDevice.device_name` | `Device.type` | TerminologyService SNOMED mapping | N/A |
| `MedicalDevice.udi` | `Device.udiCarrier.deviceIdentifier` | N/A | N/A |
| `MedicalDevice.status` | `Device.status` | TerminologyService | N/A |
| `MedicalDevice.patient_id` | `Device.patient` | N/A | `-> Patient/{id}` |
| `Immunization.vaccine_name` | `Immunization.vaccineCode` | TerminologyService CVX mapping | N/A |
| `Immunization.administration_date` | `Immunization.occurrenceDateTime` | N/A | N/A |
| projector rule | `Immunization.statusReason` | TerminologyService | N/A |
| `HealthScreening.id` (by patient join) | `Immunization.encounter` | N/A | `-> Encounter/enc-*` |
| projector singleton | `Immunization.location` | N/A | `-> Location/bulk-location-1` |
| `PatientMedication.dispense_status` | `MedicationRequest.status` / `MedicationDispense.status` | TerminologyService status map | N/A |
| projector rule | `MedicationRequest.intent` | contract constant | N/A |
| `PatientMedication.medication` | `MedicationRequest.medicationReference` | TerminologyService RxNorm/fallback | `-> Medication/med-*` |
| `HealthScreening.id` (by patient join) | `MedicationRequest.encounter` | N/A | `-> Encounter/enc-*` |
| projector singleton | `MedicationRequest.requester` | N/A | `-> Practitioner/example-practitioner` |
| `PatientMedication.start_date` | `MedicationRequest.authoredOn` | N/A | N/A |
| `PatientMedication.medication_instructions` | `MedicationRequest.dosageInstruction.text` | N/A | N/A |
| `PatientMedication.id` | `MedicationDispense.authorizingPrescription` | N/A | `-> MedicationRequest/mreq-*` |
| `HealthScreening.id` (by patient join) | `MedicationDispense.context` | N/A | `-> Encounter/enc-*` |
| projector singleton | `MedicationDispense.performer.actor` | N/A | `-> Organization/bulk-organization-1` |
| `PatientMedication.end_date` | `MedicationDispense.whenHandedOver` | N/A | N/A |
| `Procedure.procedure_name` | `Procedure.code` | TerminologyService SNOMED mapping | N/A |
| `Procedure.performance_time` | `Procedure.performedDateTime` | N/A | N/A |
| `HealthScreening.id` (by patient join) | `Procedure.encounter` | N/A | `-> Encounter/enc-*` |
| `MedicalOrder.order_type` | `ServiceRequest.category` | TerminologyService | N/A |
| `MedicalOrder.order_detail` | `ServiceRequest.code.text` | N/A | N/A |
| `MedicalOrder.order_date` | `ServiceRequest.authoredOn` | N/A | N/A |
| projector singleton | `ServiceRequest.requester` | N/A | `-> Practitioner/example-practitioner` |
| `HealthScreening.id` (by patient join) | `ServiceRequest.encounter` | N/A | `-> Encounter/enc-*` |

## C. Terminology Rule

All terminology assignments in this contract must be projection-time only:

- LOINC, SNOMED CT, RxNorm, CVX, UCUM
- implemented via TerminologyService
- never persisted in relational source tables

## D. Reusable US Core Template Contract

The projection layer must consume shared templates from `apps/integration/fhir_integration/uscore_templates.py`:

- Referential backbone singleton IDs:
  - `Practitioner/example-practitioner`
  - `PractitionerRole/example-practitioner-role`
  - `Organization/bulk-organization-1`
  - `Location/bulk-location-1`
  - `Media/media-example-1`
- Shared reference builders:
  - `encounter_ref_for_patient(patient_id, ref_builder, identity)` for all resources requiring `encounter`/`context`
  - `backbone_*_ref(...)` helpers for performer/author/serviceProvider/payor/location references
- Shared LOINC mappers:
  - `lab_test_name_to_loinc_key(test_name)`
  - `note_type_to_loinc(note_type)`

This contract guarantees Must Support references are linked to resolvable, reusable resources instead of projector-local hardcoded literals.

## E. Inferno Priority Code System Alignment

The following keys are the canonical projection-time code sources for Inferno-facing category/code searches:

- DiagnosticReport categories:
  - `category_dr_lab_loinc` -> `LOINC LP29684-5`
  - `category_dr_note_loinc` -> `LOINC LP29708-2`
- DocumentReference category:
  - `category_docref_clinical_note` -> `us-core-documentreference-category|clinical-note`
- Condition categories:
  - `category_problem_list`
  - `category_encounter_dx`
  - `category_health_concern`
  - `category_screening_sdoh`
  - `category_screening_functional_status`
- Observation lab/vitals/social categories:
  - `category_laboratory`
  - `category_vital_signs`
  - `category_social_history`
- Common support codings:
  - `obs_interpretation_normal`
  - `immunization_status_reason_immune`

Projectors must consume these terminology keys and must not introduce alternative system/code literals for the same semantics.
