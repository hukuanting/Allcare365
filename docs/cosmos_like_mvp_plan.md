# Cosmos-Like MVP Plan

Status: active build plan  
Initial seed dataset: `H2U_cvd_input_update.csv`

## Product Direction

Allcare 365 should not copy Epic Cosmos directly. The practical MVP is a FHIR-native clinical data platform that can grow into a governed research and health-intelligence network.

The core product boundary is:

```text
Clinical source models
-> deterministic FHIR projection
-> de-identified research warehouse
-> cohort analytics and point-of-care intelligence
```

## Current Seed Data

`H2U_cvd_input_update.csv` is the first product-scale dataset for the database. It contains de-identified cardiovascular screening rows with demographics, vitals, labs, and questionnaire flags.

Import command:

```powershell
.\venv\Scripts\python.exe manage.py import_h2u_cvd --dry-run --limit 100
.\venv\Scripts\python.exe manage.py import_h2u_cvd --limit 1000
.\venv\Scripts\python.exe manage.py import_h2u_cvd
```

Import behavior:

- Patient MRN is derived as `H2U-{Source}-{ID}`.
- Encounter identifier is derived as `H2U-CVD-{Source}-{ID}-{CheckDate}`.
- Rows are recorded in `data_import_batches` and `data_import_rows`.
- Clinical facts are written to `patients`, `health_screening_healthscreening`, `encounters`, `observations`, and `questionnaire_responses`.
- Re-running the import skips existing encounter identifiers by default.
- `--allow-duplicates` exists only for controlled test cases.

## Maintenance Rules

- Do not create one-off import scripts for clinical datasets.
- Extend `HealthScreeningIngestionService` for CSV, Excel, FHIR import, hospital API, and device API ingestion.
- Store raw row payloads and normalized payloads in `DataImportRow` for traceability.
- Keep relational clinical models as source of truth.
- Keep FHIR resources as deterministic projections or derived/cache records.
- Keep archived modules under `archive/_archived_apps` out of active routing unless deliberately restored with tests.
- Do not expose new clinical APIs with `AllowAny`.

## MVP Sequence

### 1. Security and Routing Baseline

- Replace clinical `AllowAny` permissions with authenticated role-aware permissions.
- Introduce product roles: `admin`, `clinician`, `researcher`, `patient`, `device_client`, `system_service`.
- Ensure every PHI read, import, export, and risk run is auditable.
- Keep ONC g10 FHIR/SMART/Bulk behavior regression-guarded.

Current research endpoint role boundary:

- `ProductUser.role` is the preferred product authorization source.
- `admin`, `researcher`, `clinician`, `doctor`, `physician`, `nurse`, and `provider` can access aggregate research discovery endpoints.
- Legacy `UserProfile.role=professional` is accepted during migration.
- `patient` cannot access cohort, data-quality, or patients-like-this research endpoints.
- Superusers are treated as admins.
- Frontend navigation and `/research-cohorts` route use the same role set for UX-level access control.

Demo role accounts:

```text
admin          / admin123456
patient        / patient123456
researcher     / researcher123456
analyst        / analyst123456
clinician      / clinician123456
doctor         / doctor123456
physician      / physician123456
nurse          / nurse123456
provider       / provider123456
staff          / staff123456
device_client  / device_client123456
system_service / system_service123456
```

Seed command:

```powershell
.\venv\Scripts\python.exe manage.py seed_demo_role_accounts
```

### 2. Data Foundation

- Use H2U CVD as the first longitudinal screening dataset.
- Add dataset-level data quality reports: missingness, outliers, duplicate source identifiers, and code coverage.
- Normalize H2U vitals/labs/questionnaire fields into `Observation` and `QuestionnaireResponse`.
- Use deterministic FHIR projectors to expose the imported dataset through FHIR APIs.

### 3. Cohort Builder

- Build a researcher-facing cohort API over de-identified source data.
- Start with aggregate counts only.
- Support filters for age, sex, screening date, BP, BMI, glucose, HbA1c, lipids, smoking, diabetes history, and CVD history.
- Enforce minimum cell-count suppression before any result leaves the server.

Initial endpoint:

```text
GET /api/health-screening/cohorts/summary/
GET /api/health-screening/cohorts/summary/fhir/
GET /api/health-screening/cohorts/patients-like-this/
GET /api/health-screening/data-quality/summary/
```

Initial query parameters:

- `sex`
- `age_min`, `age_max`
- `date_from`, `date_to`
- `{feature}_min`, `{feature}_max` for `sbp`, `dbp`, `bmi`, `height`, `weight`, `waist`, `fpg`, `hba1c`, `tg`, `tc`, `hdl`, `ldl`, `creatinine`
- Boolean flags: `smoker`, `diabetes`, `hypertension_treated`, `diabetes_treated`, `chd_history`, `cvd_history`

Privacy behavior:

- The endpoint returns aggregate summaries only.
- It never returns patient IDs, screening IDs, or row-level records.
- Cohorts smaller than the configured minimum cell count are suppressed.
- Query execution is recorded in `audit_logs` with filters and privacy metadata.

Data quality endpoint:

- Returns dataset record counts, screening date range, latest import batch, duplicate encounter identifier count, canonical feature coverage, questionnaire coverage, and readiness label.
- Query execution is recorded in `audit_logs`.
- Frontend Cohort Workbench displays the summary before cohort results so researchers can judge dataset fitness before filtering.

FHIR aggregate projection:

- `GET /api/health-screening/cohorts/summary/fhir/` returns a FHIR R4 `MeasureReport`.
- The report represents aggregate cohort discovery only.
- It does not include `Group.member`, `Patient` references, screening IDs, or row-level data.
- Cohort count is represented as an `initial-population` count when not suppressed.
- Exploratory numeric stats such as mean/min/max are represented as AllCare365 research extensions.

### 4. Patients Like This

Initial implementation is active.

- Similarity runs over de-identified H2U feature vectors.
- The matching model is deterministic normalized feature distance, not a black-box model.
- Reference input can be a manual profile with age, sex, vitals, labs, and questionnaire flags.
- Version `v2` adds optional trend-aware matching from repeated screenings for the same patient.
- Trend inputs use deltas such as `sbp_delta`, `hba1c_delta`, and `ldl_delta`; negative values represent improvement for those markers.
- Server-side release rules are the same as cohort summary: aggregate-only response, no matched patient IDs, no screening IDs, and minimum cell-count suppression.
- Query execution is recorded in `audit_logs` with privacy and matching model metadata.

Initial endpoint:

```text
GET /api/health-screening/cohorts/patients-like-this/
```

Initial query parameters:

- `age`, `sex`, `limit`
- Clinical features: `sbp`, `dbp`, `bmi`, `waist`, `fpg`, `hba1c`, `tg`, `hdl`, `ldl`, `creatinine`
- Trend features: `sbp_delta`, `dbp_delta`, `bmi_delta`, `fpg_delta`, `hba1c_delta`, `ldl_delta`
- Boolean flags: `smoker`, `diabetes`, `hypertension_treated`, `chd_history`

Frontend:

- `/research-cohorts` now includes a Patients Like This panel.
- The UI displays matched count, average similarity, aggregate demographics, and aggregate clinical feature means only.
- The UI supports trend delta inputs and displays aggregate trend means when longitudinal data is available.
- Suppressed matches show no cohort summary.

### 5. Best Care Choices

- Start with cardiometabolic outcomes where H2U has enough source data.
- Compare risk strata and longitudinal marker movement when repeated screenings exist.
- Require provenance for every derived recommendation.

### 6. Research Governance

- Add `ResearchProject`, `DataUseAgreement`, `AccessRequest`, and query audit models.
- Restrict line-level data to a secure in-app workspace.
- Export aggregate results by default; require approval for de-identified extracts.

### 7. Research Warehouse

- Add a research schema after the source-data ingestion path is stable.
- Prefer OMOP CDM for observational research compatibility.
- Keep FHIR as the exchange/API standard and OMOP as the analytics/research standard.

## Near-Term Implementation Backlog

1. Add ResearchProject/DataUseAgreement models before any line-level de-identified workspace.
2. Add report linkage to ResearchProject once governance models exist.

## Aggregate Export Governance

Initial implementation is active.

Governed report endpoints:

```text
GET  /api/health-screening/research-reports/
POST /api/health-screening/research-reports/
GET  /api/health-screening/research-reports/{id}/
POST /api/health-screening/research-reports/{id}/approve/
POST /api/health-screening/research-reports/{id}/reject/
GET  /api/health-screening/research-reports/{id}/artifact/
```

Supported aggregate report types:

- `cohort_summary`
- `cohort_measure_report`
- `patients_like_this`

Governance behavior:

- Report requests save an immutable aggregate snapshot in `research_aggregate_reports`.
- Artifacts are locked while status is `requested`.
- Approval/rejection requires admin or clinical role access.
- Pure researcher role can request/list reports but cannot self-approve.
- Approved artifacts can be retrieved from the artifact endpoint.
- Artifacts remain aggregate-only and retain the same minimum cell-count suppression rules.
- Every request, approval, rejection, and artifact view writes an `audit_logs` event.

Frontend:

- `/research-reports` provides a pending report review queue.
- Research roles can request aggregate reports and view approval status.
- Admin/clinical approval roles can approve or reject requested reports.
- Approved artifacts can be previewed from the queue.
