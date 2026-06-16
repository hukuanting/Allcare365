# Product Development Log

## 2026-06-09 - Phase 1 EHR shell

- Problem: Post-ONC system needed a clean product UI foundation instead of fragmented/corrupted frontend files.
- Changed: `frontend/src/App.js`, `frontend/src/App.css`, `frontend/src/index.css`.
- Changed: `frontend/src/config/api.js`, `frontend/src/utils/auth.js`, `frontend/src/hooks/useAuth.js`, `frontend/src/components/ProtectedRoute.js`.
- Changed: `frontend/src/components/Navigation.js`, `frontend/src/components/Dashboard.js`, `frontend/src/components/PatientManagement.js`, `frontend/src/components/PatientChart.js`, `frontend/src/components/Login.js`, `frontend/src/components/Register.js`.
- Changed: `medical_system/urls.py` now exposes product APIs at `/api/patients/` and `/api/health-screening/`.
- Result: Added authenticated EHR shell, clinical worklist, patient registry, patient chart route, and clean auth screens.
- Verified: `npm run build`, `manage.py check`, `verify_onc_certification_baseline.ps1`.

## 2026-06-09 - Health intake and bulk import boundary

- Problem: `localhost:3000` rendered blank due React/ReactDOM version mismatch.
- Changed: `frontend/package.json`, `frontend/package-lock.json`, `frontend/src/App.smoke.test.js`.
- Problem: Manual intake and bulk import used old fields/endpoints that did not match the USCDI/FHIR projectable models.
- Changed: `apps/clinical/health_screening/ingestion_service.py`, `serializers.py`, `views.py`, `urls.py`.
- Changed: `frontend/src/components/HealthDataInput.js`, `BulkHealthDataImport.js`, `RiskAnalysis.js`, `frontend/src/config/api.js`.
- Result: Manual, CSV/Excel, and FHIR JSON intake now share one ingestion service and feed risk analysis.
- Verified: `manage.py check`, frontend smoke test, `npm run build`, endpoint smoke test, `verify_onc_certification_baseline.ps1`.

## 2026-06-10 - AllCare365 frontend product direction

- Problem: Frontend needed concise Chinese text and a brighter medical AI SaaS style.
- Changed: `frontend/src/App.js`, `App.css`, `index.css`, navigation, landing, auth, dashboard, patient, intake, bulk, risk pages.
- Added: `frontend/src/components/LandingPage.js`, `HistoryRecords.js`, `ConnectionHub.js`.
- Result: Added responsive landing page, dashboard, intake flow, AI review, history, and connection hub.
- Verified: frontend smoke test, `npm run build`.

## 2026-06-10 - Product database cleanup and risk schema

- Problem: Old product tokens and derived risk FHIR rows could confuse post-ONC database design.
- Added: `cleanup_product_database` command and `docs/allcare365_database_definition.md`.
- Changed: Added `RiskAssessmentRun`, `RiskAssessmentResult`, `RiskRecommendation` tables.
- Changed: Risk engine now persists relational risk history and still writes FHIR `RiskAssessment` projection.
- Verified: cleanup dry-run/execute manifests, risk smoke test, `manage.py check`, ONC baseline.

## 2026-06-10 - Database schema v1

- Problem: Product needed a clear MVP schema separate from ONC-only FHIR fixtures.
- Added: `users`, `practitioners`, `patient_practitioner_links`, `encounters`, `observations`, questionnaires, import, AI, care task, consent, FHIR mapping, audit tables.
- Changed: Extended `patients` and `care_plans` with source metadata, AI linkage, and JSONB fields.
- Added: `seed_product_schema_v1` command and `docs/allcare365_schema_v1.md`.
- Verified: migrations applied, seed data created, `manage.py check`, migration dry-run.

## 2026-06-10 - CORE.xlsx disease risk direction

- Problem: Product risk feature should follow `CORE.xlsx`, not generic AI wording or legacy risk modules.
- Added: `docs/core_xlsx_disease_risk_architecture.md`.
- Changed: Main frontend labels from AI wording to disease risk assessment wording.
- Changed: Product table comments and seed audit action now use disease risk terminology.
- Verified: `manage.py check`, migration dry-run, frontend build, ONC baseline.

## 2026-06-10 - CORE.xlsx disease risk engine cleanup

- Problem: Legacy `services/risk_engine` duplicated formulas and kept data flow tied to old screening tables.
- Added: `services/disease_risk_engine/` with repository, CORE calculators, persistence, FHIR mapping, and audit logging.
- Changed: Health screening risk APIs now call `DiseaseRiskAssessmentService`; added `/api/health-screening/disease-risk/`.
- Changed: Manual/FHIR/bulk ingestion now writes `encounters`, `observations`, `questionnaire_responses`, and import row tracking.
- Changed: Added UACR manual input support and LOINC `9318-7` mapping.
- Removed: legacy `services/risk_engine/` and old `verify_risk_engine.py`.
- Added: `verify_disease_risk_engine.py`.

## 2026-06-10 - CORE.xlsx A1/HQ manual input and risk models

- Problem: Single input needed to match CORE.xlsx `A1 KEY IN` and `HQ`, not the old generic health form.
- Changed: Manual input now sends `a1_key_in`, `hq`, vitals, labs, assessments, and problems into normalized product tables.
- Changed: Batch row mapping now projects CORE fields into the same ingestion payload.
- Added: MetS, NAFLD, FHSFLD, AusDM, and GVR CAIDE v1 calculators.
- Verified: risk engine smoke, frontend build, ONC full local baseline.

## 2026-06-10 - Disease risk missing-data UX

- Problem: Risk results exposed internal keys and partial scores when source data was missing.
- Changed: Risk engine now marks incomplete formulas as `資料不足` and returns Chinese missing-field labels.
- Changed: Risk page now shows block cards with severity colors, missing data chips, and recommendations.
- Found: Prevent CVD, ASCVD, and HF 10-year risks only remain in old migrations/templates/archive, not in the new engine.
- Verified: full-data smoke, missing-data smoke, frontend build, migration dry-run, ONC baseline.

## 2026-06-11 - Latest available risk input selection

- Problem: Risk input must combine multiple visits instead of using only the newest incomplete exam.
- Changed: `DiseaseRiskInputRepository` now selects latest valid value per field across observations, HQ responses, and legacy fallback rows.
- Changed: Source metadata records table, id, effective date, and `latest_available_per_field` policy.
- Added: A/B/C exam smoke test covering old urine, newer blood, newest body measurements.
- Verified: risk engine smoke, migration dry-run, ONC baseline.
