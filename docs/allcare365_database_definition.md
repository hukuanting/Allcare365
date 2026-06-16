# AllCare365 Database Definition

Status: draft baseline after ONC g10 pass  
Last updated: 2026-06-10

Detailed implemented schema: `docs/allcare365_schema_v1.md`

## 1. Purpose

AllCare365 is now moving from certification readiness into product database design.

The database must support:

- EHR/EMR patient management.
- Manual health intake.
- Batch/bulk health data import.
- FHIR R4 and USCDI projection.
- Disease risk assessment and follow-up recommendations.
- Future device, wearable, hospital equipment, and external system integrations.

Certification-facing behavior must remain stable. Product database changes should extend the clinical source model and project to FHIR, not bypass the FHIR/USCDI boundary.

## 2. Protected ONC Boundary

Do not delete or remodel these records without a deliberate certification migration plan.

### Protected Patients

| Purpose | Patient ID | MRN |
| --- | --- | --- |
| ONC Single Patient API golden patient | `00000000-0000-4000-a000-000000000001` | `ONC-2026-001` |
| Bulk Data group patient | `10000000-0000-4000-a000-000000000001` | `BULK-001` |
| Bulk Data group patient | `10000000-0000-4000-a000-000000000002` | `BULK-002` |
| Bulk Data group patient | `10000000-0000-4000-a000-000000000003` | `BULK-003` |

### Protected OAuth Clients

| Client ID | Purpose |
| --- | --- |
| `inferno_ehr_client` | SMART EHR launch and certification tests |
| `inferno_client_id` | Inferno default SMART app |
| `inferno_public_client` | Public standalone launch |
| `inferno_asymmetric_client` | Private key JWT standalone launch |
| `inferno_bulk_client` | Backend Services Bulk Data |

### Protected Code Area

| Area | Rule |
| --- | --- |
| `apps/integration/fhir_integration/projectors/` | Certification FHIR projection logic. Avoid product-specific shortcuts. |
| `apps/integration/fhir_integration/management/commands/seed_onc_patient.py` | Golden patient seed. Do not use as product reset command. |
| `apps/integration/fhir_integration/management/commands/seed_bulk_group.py` | Bulk Data certification seed. |
| `verify_onc_certification_baseline.ps1` | Must pass after database changes. |

## 3. Cleanup Policy

Use this command for safe product cleanup:

```powershell
.\venv\Scripts\python.exe manage.py cleanup_product_database
.\venv\Scripts\python.exe manage.py cleanup_product_database --execute
```

Default mode is dry-run.

The command preserves:

- Protected ONC patients.
- Protected Inferno clients.
- FHIR projection code and seed code.

The command may clean:

- Expired/development OAuth `AccessToken`, `RefreshToken`, `Grant`.
- Non-protected product/dev patients and cascading product records.
- Product-derived `FHIRResource/RiskAssessment` rows.

Each run writes a manifest to:

```text
logs/database_cleanup/
```

## 4. Database Layers

AllCare365 should be designed in layers. The product code should write to relational source tables first. FHIR resources should be projections or exported representations.

| Layer | Responsibility | Current Main Tables | Target Direction |
| --- | --- | --- | --- |
| Identity and access | Users, roles, OAuth, SMART clients | `auth_user`, `authentication_userprofile`, `oauth2_provider_*` | Add organization membership and role permissions. |
| Patient master | Patient demographics and identity | `patients` | Keep as primary patient table; add external identifiers and source system fields. |
| Clinical source | Encounter, vitals, labs, problems, meds, notes | `health_screening_*`, patient child tables | Rename/normalize around FHIR concepts. |
| FHIR projection | US Core/FHIR resources and ONC tests | `fhir_integration_fhirresource`, projectors | Keep projection layer separate from product writes. |
| Ingestion | Manual, CSV, FHIR import jobs | currently service-only | Add import job, row result, source mapping tables. |
| Analytics | Risk models and recommendations | currently `FHIRResource/RiskAssessment` only | Add relational risk result and recommendation tables. |
| Integration | Devices, hospital systems, wearable feeds | `patients_medicaldevice` only | Add connection, data stream, device observation tables. |
| Audit and provenance | Trace who/what created data | `created_by`, `updated_by`, FHIR Provenance projection | Add event audit and source provenance records. |

## 5. Canonical Product Domains

### 5.1 Patient

Primary model: `patients.Patient`

Required product fields:

- Internal UUID.
- MRN.
- Name.
- Birth date.
- Sex.
- Contact.
- Address.
- Status.
- Source system metadata.

FHIR projection:

- `Patient`
- `RelatedPerson`
- demographic USCDI elements.

Next schema actions:

- Add `source_system`, `source_record_id`, `last_imported_at`.
- Add uniqueness strategy for MRN per organization.

### 5.2 Encounter

Current model: `health_screening.HealthScreening`

Target concept: Encounter or clinical intake event.

Required product fields:

- Patient.
- Encounter date/time.
- Encounter type.
- Location.
- Source import job.
- Provider or care team reference.

FHIR projection:

- `Encounter`
- references from Observation, Condition, Procedure, DiagnosticReport.

Next schema actions:

- Keep current table for now to avoid certification regression.
- Introduce clearer API naming around "intake event" before any table rename.

### 5.3 Observation

Current models:

- `health_screening.VitalSigns`
- `health_screening.LaboratoryResults`
- `health_screening.HealthStatusAssessment`
- `health_screening.ClinicalTestResult`

Target concept:

- Observation source data grouped by encounter/intake.

FHIR projection:

- `Observation` vital signs.
- `Observation` laboratory.
- `Observation` social history.
- `Observation` survey/SDOH.
- `DiagnosticReport` for grouped lab/report outputs.

Next schema actions:

- Keep vitals and labs as explicit relational tables.
- Add optional normalized observation table only if device and wearable data require high-volume storage.
- Add source/provenance fields to each observation-producing table.

### 5.4 Condition and Problem

Current model: `health_screening.Problem`

Target concept:

- Condition/problem list, encounter diagnosis, health concerns.

FHIR projection:

- `Condition`

Next schema actions:

- Add category field: `problem-list-item`, `encounter-diagnosis`, `health-concern`.
- Add coding fields: code system, code, display.
- Preserve current `problem_name` for readable UI.

### 5.5 Procedure

Current model: `health_screening.Procedure`

FHIR projection:

- `Procedure`

Next schema actions:

- Add encounter reference.
- Add reason condition/reference.
- Add code system/code/display.

### 5.6 Medication

Current model: `patients.PatientMedication`

FHIR projection:

- `MedicationRequest`
- `MedicationDispense`
- `MedicationStatement`

Next schema actions:

- Separate prescribed medication from dispense history if real pharmacy workflow is needed.
- Add adherence and order metadata.

### 5.7 Document and Diagnostic Report

Current models:

- `patients.PatientDocument`
- `health_screening.DiagnosticImagingResult`
- `health_screening.LaboratoryResults`

FHIR projection:

- `DocumentReference`
- `DiagnosticReport`
- `Media`

Next schema actions:

- Add attachment metadata table for files/URLs.
- Add document type code and category.

### 5.8 Disease Risk Assessment

Current state:

- `services/disease_risk_engine`
- `CORE.xlsx` is the current source specification for `A1 KEY IN`, `HQ`, `FHS DM`, `CH DM`, `MetS`, `NAFLD`, `FHSFLD`, `AusDM`, and `GVR CAIDE`.
- Input is normalized into `encounters`, `observations`, and `questionnaire_responses`.
- Output is saved to `ai_analysis_jobs` / `ai_analysis_results` as disease-risk records until a table rename migration is scheduled.
- Output is mapped to FHIR `RiskAssessment` through `fhir_resource_mappings`.

Implemented source tables:

- `RiskAssessmentRun`
- `RiskAssessmentResult`
- `RiskRecommendation`

Required fields:

- Patient.
- Source encounter.
- Algorithm name and version.
- Inputs snapshot.
- Result value.
- Risk category.
- Recommendation text.
- Generated by.
- Generated at.

FHIR projection:

- `RiskAssessment`
- optional `Observation` for derived metrics.
- `Provenance`.

Next schema actions:

- Add richer recommendation taxonomy and clinician review state.
- Keep FHIRResource as projection/export cache, not primary source.

### 5.9 Device and Integration

Current model:

- `patients.MedicalDevice`

Target source tables:

- `IntegrationConnection`
- `Device`
- `DeviceDataStream`
- `DeviceObservation`

Required fields:

- Source type: hospital equipment, wearable, file import, external FHIR server.
- External ID.
- Connection status.
- Last sync time.
- Payload hash or deduplication key.

FHIR projection:

- `Device`
- `Observation`
- `Provenance`

## 6. Naming Rules

Use stable product names in code and API:

- Use `patient`, not `member` or `customer`.
- Use `encounter` or `intake`, not `screening_type` for all workflows.
- Use `observation` for clinical measurements.
- Use `problem` in UI and `Condition` in FHIR.
- Use `risk_assessment` for derived analytics.
- Use `integration` for external systems and devices.

Avoid:

- Ad hoc CSV-specific field names in models.
- FHIR-shaped JSON as the only source of truth.
- Product data writes directly into certification-only mock data.

## 7. Immediate Build Order

1. Freeze ONC baseline and keep cleanup command.
2. Add explicit risk analysis relational models.
3. Add import job and row result tables.
4. Add source/provenance fields to intake-generated tables.
5. Add condition/procedure coding fields.
6. Add integration connection/device stream tables.
7. Update frontend to consume these structured APIs.
8. Run `verify_onc_certification_baseline.ps1` after each migration group.

## 8. Verification Requirements

Before merging database changes:

```powershell
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\verify_onc_certification_baseline.ps1
```

Product API smoke tests should verify:

- Patient creation.
- Manual intake creation.
- Bulk import preview/import.
- Risk run creation.
- History record retrieval.
- FHIR endpoint still returns ONC-compatible data.
