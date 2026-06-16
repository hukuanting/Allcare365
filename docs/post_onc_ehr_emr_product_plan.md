# Post-ONC EHR/EMR Product Plan

Status: Active planning baseline after ONC g10 pass.

The next phase is to turn the certified interoperability backend into a complete EHR/EMR product while preserving the passed ONC API behavior.

## Current Phase 1 Baseline

Implemented on 2026-06-09:

- Clean React EHR shell with authenticated routing.
- Clinical worklist dashboard.
- Patient registry backed by `/api/patients/`.
- Patient chart route at `/patients/:patientId`.
- Product API client and local session/auth helpers.
- Product API route includes for patients and health screening.

Verification baseline:

- `npm run build`
- `python manage.py check`
- `verify_onc_certification_baseline.ps1`

## Product Goal

Allcare 365 should become a commercial-grade EHR/EMR and health intelligence system with:

- A polished frontend on port `3000`.
- A Django backend on port `8000`.
- Certified FHIR R4 / US Core API behavior preserved.
- Patient chart, health screening, bulk intake, and manual entry workflows.
- Risk prediction, longitudinal tracking, alerts, and report generation.
- Device and wearable ingestion using FHIR-compatible data flows.
- Auditability, role-based access, and operational administration.

## Architectural Boundary

Keep three layers separate:

```text
Product UI and workflows
-> Product APIs and clinical services
-> Certified FHIR/SMART/Bulk interoperability layer
-> Relational clinical source data
```

The certified FHIR API is not the place for product-specific shortcuts. Product APIs may aggregate and simplify workflows, but the underlying clinical data must remain mappable to FHIR R4 and USCDI.

## Phase 0 - Certification Freeze

Purpose: make the passed state hard to break.

Deliverables:

- Keep `docs/onc_g10_final_pass_archive.md` current.
- Run `verify_onc_certification_baseline.ps1` before certification-facing changes.
- Keep every certification fix summarized in `ONC_CERTIFICATION_LOG.md`.
- Treat FHIR projectors, SMART auth, Bulk export, and CapabilityStatement as locked contracts.

## Phase 1 - Frontend Foundation

Purpose: create the usable EHR/EMR shell.

Deliverables:

- React app on port `3000`.
- Login/logout/session handling.
- Role-aware navigation: admin, clinician, researcher, patient.
- Patient search and patient chart layout.
- FHIR-aware API client with token handling.
- Shared design system for tables, forms, side panels, charts, and clinical status indicators.

Primary screens:

- Patient registry.
- Patient chart summary.
- Encounters and timeline.
- Vitals/labs/problems/medications/documents.
- Bulk upload dashboard.
- Risk analytics dashboard.
- Admin and audit views.

## Phase 2 - Clinical Workflows

Purpose: move from API compliance to useful clinical operations.

Deliverables:

- Single patient manual entry for USCDI-aligned data.
- Bulk health screening upload with validation preview.
- Patient summary assembled from FHIR-backed source data.
- Clinical note/document management.
- Encounter-centric data entry.
- Medication, allergy, condition, procedure, and observation workflows.

Rules:

- Store source data in domain models.
- Project to FHIR using existing projectors.
- Do not create untraceable derived clinical facts.

## Phase 3 - Disease Risk Assessment

Purpose: build the health intelligence layer.

Deliverables:

- Disease risk service boundary under `services/disease_risk_engine/`.
- CORE.xlsx-compatible disease risk models from vitals, labs, demographics, questionnaires, smoking status, and conditions.
- Longitudinal trend computation.
- Explainable risk report with input evidence.
- Derived output stored as `RiskAssessment` and/or `Observation`.
- `Provenance` for algorithm version, source resources, and calculation time.

Implementation rule:

```text
FHIR/USCDI source data -> CORE input vector -> disease risk model -> FHIR-traceable derived result
```

## Phase 4 - Realtime and Device Integration

Purpose: ingest device, wearable, and hospital equipment data without breaking standards.

Deliverables:

- Device client registration model.
- FHIR Observation ingestion endpoint or adapter pipeline.
- Device identity mapped to FHIR `Device`.
- Measurement normalization to LOINC/UCUM.
- Queue-based ingestion for bursty device data.
- Alert rules for abnormal trends.

## Phase 5 - Production Hardening

Purpose: prepare for real deployments.

Deliverables:

- Split settings into local/test/staging/production.
- Remove certification-only defaults from production settings.
- Production secret management.
- AuditEvent-style logging for PHI access and exports.
- Backup and restore process.
- Monitoring and alerting.
- Security review for CORS, CSRF, OAuth clients, refresh token policy, and private keys.
- Database migration review and seed-data separation.

## Near-Term Work Order

1. Freeze and commit the ONC pass baseline.
2. Create the React app shell and routing.
3. Implement authenticated patient registry and patient chart read views.
4. Implement manual health screening entry.
5. Implement bulk upload validation and ingestion.
6. Add first risk analytics service and UI dashboard.
7. Add regression tests that prove product changes do not alter ONC API behavior.
