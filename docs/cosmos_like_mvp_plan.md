# Cosmos-Like Product Roadmap

Status: active build plan  
Last reviewed: 2026-07-06
Reference: https://cosmos.epic.com/

## Product Direction

Allcare 365 should not copy Epic Cosmos directly. The practical target is a
FHIR-native clinical data and research intelligence platform that can grow from
a single product database into a governed, multi-organization learning health
network.

Epic describes Cosmos as a community dataset built with participating health
systems, used for research and point-of-care tools such as similar-patient
insights and treatment/outcome comparisons. For Allcare 365, the equivalent
direction is:

```text
Clinical source data
-> deterministic FHIR R4 projection
-> de-identified governed research layer
-> cohort analytics
-> similar-patient and best-care intelligence at the point of care
```

## Current Product Boundary

The active product should stay focused on the modules that support that path:

- Patient identity and demographics aligned to USCDI v6.
- Health screening, observations, questionnaires, encounters, and risk outputs.
- FHIR R4 API, SMART on FHIR OAuth2/OIDC, Bulk Data, and audit logging.
- Research cohort summaries, patients-like-this analytics, data quality reports,
  and governed aggregate report exports.
- Disease risk engine outputs recorded as derived clinical data with provenance.

Legacy EHR modules such as appointments, billing, pharmacy, laboratory, forms,
and the old patient portal were removed after an import and routing audit. If a
module returns, it must be rebuilt against current models, permissions, FHIR
mappings, and tests rather than copied from the archived implementation.

## Current Seed Data

`H2U_cvd_input_update.csv` is the first product-scale dataset. It contains
de-identified cardiovascular screening rows with demographics, vitals, labs,
and questionnaire flags.

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
- Clinical facts are written to patient, health screening, encounter,
  observation, and questionnaire response source tables.
- Re-running the import skips existing encounter identifiers by default.
- `--allow-duplicates` exists only for controlled test cases.

## Non-Negotiable Architecture Rules

- Keep clinical exchange FHIR R4-first; do not add proprietary APIs for USCDI
  data when a FHIR representation is expected.
- Use OAuth2/OIDC and SMART scopes for clinical access.
- Keep cohort and research endpoints aggregate-only unless governance models and
  extract approval workflows are in place.
- Record audit events for PHI reads, imports, exports, cohort queries, report
  approvals, and derived risk runs.
- Keep derived intelligence traceable through source references, algorithm
  version, input features, and provenance metadata.

## Roadmap

### Phase 1. Stabilize the Active Product Core

- Remove or quarantine active imports that reference archived apps.
- Align patient services, commands, and tests with the current USCDI/FHIR patient
  model fields.
- Keep ONC g10 FHIR/SMART/Bulk behavior regression-guarded.
- Make local/generated artifacts disposable: virtual environments, node modules,
  build output, logs, caches, and tunnel files should stay out of Git.

### Phase 2. Data Foundation

- Use H2U CVD as the first longitudinal screening dataset.
- Add dataset-level data quality reports: missingness, outliers, duplicate
  source identifiers, and terminology/code coverage.
- Normalize vitals, labs, questionnaire fields, encounters, and derived risk
  outputs into source tables.
- Expose the imported dataset through deterministic FHIR projectors.

### Phase 3. Cohort Builder

Initial endpoints:

```text
GET /api/health-screening/cohorts/summary/
GET /api/health-screening/cohorts/summary/fhir/
GET /api/health-screening/cohorts/patients-like-this/
GET /api/health-screening/data-quality/summary/
```

Required behavior:

- Return aggregate summaries only.
- Suppress results below the minimum cell count.
- Never return patient IDs, screening IDs, or row-level records.
- Audit every query with filters, privacy outcome, and returned count metadata.
- Provide a FHIR R4 `MeasureReport` projection for aggregate cohort discovery.

### Phase 4. Patients Like This

Current implementation uses deterministic normalized feature distance over
de-identified H2U feature vectors.

Next requirements:

- Keep responses aggregate-only.
- Support trend-aware matching for repeated screenings.
- Log matching model version and feature set.
- Make suppression behavior visible in the frontend without exposing row-level
  information.

### Phase 5. Best Care Choices

This should be introduced after cohort quality, governance, and provenance are
stable.

- Start with cardiometabolic outcomes where H2U has sufficient source data.
- Compare risk strata, longitudinal marker movement, and care plan/risk
  outcomes.
- Store outputs as derived data, preferably FHIR `RiskAssessment` and/or
  `Observation`, with provenance.
- Avoid black-box recommendations until clinical validation and governance are
  explicit.

### Phase 6. Research Governance

- Add `ResearchProject`, `DataUseAgreement`, `AccessRequest`, and query approval
  models before any line-level de-identified workspace.
- Restrict extracts to approved projects.
- Export aggregate artifacts by default.
- Keep approval, rejection, and artifact access in the audit trail.

### Phase 7. Research Warehouse

- Add a research schema after ingestion and projection are stable.
- Prefer OMOP CDM for observational research compatibility.
- Keep FHIR as the exchange/API standard and OMOP as the analytics/research
  standard.

## Cleanup Policy

Safe to remove locally:

- `.pytest_cache/`
- Python `__pycache__/`
- `venv/`
- `frontend/node_modules/`
- `frontend/build/`
- `build/`
- `logs/`
- `media/` generated during local testing
- Cloudflare tunnel URL and log files

Do not delete without a targeted migration plan:

- migrations
- ONC/FHIR certification artifacts
- seed data and clinical source files

## Near-Term Backlog

1. Add ResearchProject/DataUseAgreement models before any extract workspace.
2. Add report linkage to ResearchProject once governance models exist.
3. Restore removed product modules only from an approved current architecture and test plan.
4. Add a repeatable cleanup command or script for ignored local artifacts.
