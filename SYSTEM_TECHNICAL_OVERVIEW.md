# Allcare 365 System Technical Overview

Last updated: 2026-06-09

## 0. Certification Status

The ONC Certification (g)(10) Standardized API Report has passed for:

- US Core 7.0.0 / USCDI v4 Single Patient API.
- SMART App Launch 2.2.0.
- Bulk Data 2.0.0 / Group export.
- Visual Inspection and Attestation requirements.

The passed state is archived in `docs/onc_g10_final_pass_archive.md`. Before changing certification-facing code, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\verify_onc_certification_baseline.ps1
```

The next product phase is tracked in `docs/post_onc_ehr_emr_product_plan.md`.

## 1. Purpose and System Vision

Allcare 365 is intended to become a modern health information management platform that can support ONC Health IT Certification, expose clinical data through FHIR R4 APIs, and manage USCDI-aligned patient and health screening data. The long-term target is a commercial-grade system with:

- A React frontend on port `3000`.
- A Django backend on port `8000`.
- PostgreSQL as the primary operational database.
- FHIR R4 and US Core compliant clinical exchange APIs.
- SMART on FHIR security using OAuth2/OIDC.
- Role-based user access.
- Single-record and bulk health screening data entry.
- Disease risk analysis from persisted clinical data.
- Device, hospital equipment, and wearable data ingestion.
- Auditability and provenance for certification and clinical traceability.

The current codebase is already moving toward a FHIR-native architecture. The most important architectural decision is:

```text
Relational clinical models are the source of truth.
FHIR resources are deterministic projections from source data.
```

This means the system should avoid hand-maintained certification JSON as primary data. Clinical records should be captured once in stable domain models, then projected into FHIR resources through a validated projection layer.

## 2. Current Technology Stack

Backend:

- Python / Django.
- Django REST Framework.
- django-oauth-toolkit for OAuth2 and SMART on FHIR flows.
- djangorestframework-simplejwt for the application login flow.
- PostgreSQL configured as the default database.
- Celery and Redis configured for asynchronous work, but not yet a central execution path.
- `fhir.resources` and `fhirclient` for FHIR-related implementation.
- pandas/openpyxl/xlsxwriter for tabular ingestion.
- scikit-learn/scipy/numpy for future risk analysis expansion.

Frontend:

- React.
- React Router.
- Material UI.
- `fhirclient` package for SMART/FHIR client-side integration.
- Local storage based session state and token handling.

Testing and certification support:

- Django checks.
- pytest-style tests under `tests/`.
- US Core projection contract tests.
- Inferno/g10-oriented artifacts under `docs/`.
- Preflight utility: `inferno_preflight_validator.py`.

## 3. Repository Layout

Current top-level structure:

```text
openmer_python/
  apps/
    clinical/
      patients/
      health_screening/
    core/
      authentication/
    integration/
      fhir_integration/
  docs/
  frontend/
  medical_system/
  services/
    disease_risk_engine/
  static/
  templates/
  tests/
  anon/
  manage.py
  requirements.txt
  start_system.bat
```

### 3.1 `medical_system/`

Django project configuration.

Main responsibilities:

- Django settings.
- Root URL routing.
- ASGI/WSGI entrypoints.
- Health check endpoint.
- Celery configuration.

Important files:

- `settings.py`: installed apps, database, DRF, CORS, OAuth2/OIDC, SMART scopes, security flags.
- `urls.py`: root router for admin, FHIR, SMART configuration, OAuth2, auth, and health check.
- `health_check.py`: operational health check.
- `celery.py`: Celery application bootstrap.

Current issue:

- `settings.py` contains several environment-sensitive values and test-oriented settings in the same file. It should be split into `base`, `local`, `test`, and `production` settings before production or certification use.
- `CORS_ALLOW_ALL_ORIGINS=True`, default `SECRET_KEY`, embedded OIDC RSA private key, DEBUG-friendly behavior, and Inferno exceptions must be isolated from production.

### 3.2 `apps/core/authentication/`

Application authentication and SMART authorization support.

Main responsibilities:

- User registration/login/logout/profile APIs.
- User profile and role storage.
- JWT login for the React application.
- OAuth authorization and token customizations for SMART on FHIR.
- SMART launch and token response context support.

Important files:

- `models.py`: `UserProfile`, `LoginHistory`.
- `serializers.py`: user, registration, and login serializers.
- `views.py`: standard login APIs plus custom OAuth2 authorization and token views.
- `smart_utils.py`: SMART context helper.
- `middleware.py`: OAuth scope cleanup.
- `api_urls.py`: `/api/auth/...` routes.
- `web_urls.py`: server-rendered auth pages.

Current state:

- Roles are currently minimal: `professional` and `patient`.
- React uses JWT endpoints for app login.
- FHIR endpoints use OAuth2 token validation and SMART scopes.

Target state:

- Normalize roles into a commercial-grade role model: `admin`, `clinician`, `researcher`, `patient`, `device_client`, and `system_service`.
- Keep JWT app login and SMART OAuth2 responsibilities clearly separated.
- Add permission policies per role and per resource.
- Add audit events for login, token issuance, PHI access, export, and failed access attempts.

### 3.3 `apps/clinical/patients/`

Clinical patient domain.

Main responsibilities:

- Patient demographics.
- Care team.
- Organization.
- Allergy/intolerance source data.
- Care plan source data.
- Medication source data.
- Orders.
- Insurance data.
- Advance directives.
- Family health history.
- Medical devices.
- Clinical notes.

Important models:

- `Patient`
- `CareTeamMember`
- `Organization`
- `PatientAllergy`
- `CarePlan`
- `PatientMedication`
- `MedicalOrder`
- `InsuranceData`
- `AdvanceDirective`
- `FamilyHealthHistory`
- `MedicalDevice`
- `PatientDocument`

Current state:

- Models are relational and are intended to align with USCDI concepts.
- ViewSets exist for CRUD operations.
- Several ViewSets use `AllowAny`.
- Patient routes are implemented in `apps/clinical/patients/urls.py`.

Current issue:

- Root routing does not currently include `apps.clinical.patients.urls` under `/api/patients/`, although the frontend expects `/api/patients/`.
- Some naming mixes clinical/FHIR/business terms, for example `PatientDocument` storing clinical notes and `MedicalOrder` covering several FHIR-like concepts.
- Some country/default values are Taiwan-oriented while US Core/ONC projection requires US-oriented code systems and address semantics for certification datasets.

Target state:

- Treat this app as the patient source-data domain.
- Keep FHIR projection logic out of this app.
- Require authentication and role-based permissions.
- Add stable service APIs for patient search, duplicate detection, and patient summary.

### 3.4 `apps/clinical/health_screening/`

Health screening, vitals, labs, problems, procedures, immunizations, health status assessments, clinical tests, and imaging source data.

Important models:

- `HealthScreening`
- `VitalSigns`
- `LaboratoryResults`
- `Problem`
- `Procedure`
- `Immunization`
- `HealthStatusAssessment`
- `ClinicalTestResult`
- `DiagnosticImagingResult`

Current state:

- Models cover many USCDI categories.
- Basic ViewSets exist.
- Risk analysis is exposed as an action on `HealthScreeningViewSet`.
- Bulk import services exist in `bulk_import_service.py` and `enhanced_bulk_import_service.py`.

Current issue:

- Root routing does not currently include this app under `/api/health-screening/`, while the frontend expects it.
- ViewSets use `AllowAny`.
- Some labels/comments contain encoding corruption, reducing maintainability.
- The frontend expects endpoints such as `/api/health-screening/parse-file/`, `/api/health-screening/fhir-import/`, and `/api/health-screening/risk-analysis/`, but the active Django routing does not clearly expose those exact endpoints.

Target state:

- Treat this app as the source-data domain for screening encounters and measurements.
- Make ingestion produce relational source data first, then FHIR projection.
- Move risk-analysis orchestration to an explicit API boundary, for example `/api/risk/patients/{id}/`.
- Preserve source measurements and write derived results separately as FHIR `RiskAssessment` or `Observation` with provenance.

### 3.5 `apps/integration/fhir_integration/`

FHIR, US Core, USCDI, SMART, and certification integration layer.

Main responsibilities:

- FHIR R4 endpoint routing.
- SMART on FHIR discovery and OAuth/OIDC support.
- FHIR resource rendering.
- SMART scope enforcement.
- CapabilityStatement generation.
- US Core projection contracts.
- Deterministic ORM-to-FHIR resource projection.
- FHIR search parsing.
- Include and revinclude handling.
- Bulk Data simulation/export support.
- USCDI compliance dashboard support.

Important files and folders:

- `views.py`: FHIR REST controllers, SMART validator, bulk export endpoints.
- `urls.py`: FHIR resource routes such as `/fhir/Patient`, `/fhir/Observation`, `/fhir/metadata`.
- `projectors/`: one projector per FHIR resource type.
- `projectors/base.py`: projection pipeline contract.
- `projectors/registry.py`: resource type to projector registry.
- `projection_contracts.py`: US Core STU7 projection constraints.
- `capability_statement.py`: generated CapabilityStatement.
- `fhir_search/`: search parsing and translation.
- `bundle_builder.py`: FHIR Bundle construction.
- `reference_builder.py`: FHIR reference generation.
- `reference_resolution.py`: contract/reference validation.
- `resource_identity.py`: stable IDs and canonical patient identity.
- `terminology.py`: terminology/coding mapping.
- `smart_config.py`: SMART discovery response.
- `g10_testkit.py`: ONC g10 certification contract artifacts.

Current state:

- This is the strongest architectural area of the codebase.
- The project has moved from ad hoc FHIR JSON toward a deterministic projector pattern.
- Projectors are registered by resource type, and FHIR views delegate list/read operations to the registry.
- CapabilityStatement generation is contract-driven.

Current issue:

- `FHIRResource` JSON persistence still exists beside the projection pattern. It should be treated as legacy/cache/derived data unless a clear persistence policy is defined.
- `views.py` still contains several responsibilities: rendering, permissions, SMART validation, search orchestration, FHIR read/list, patient-specific fallbacks, and bulk export.
- Test and certification accommodations are mixed into runtime code.
- `FHIRPatientViewSet` and `FHIRResourceViewSet` overlap in responsibilities.

Target state:

- Keep `projectors/` as the canonical FHIR mapping mechanism.
- Split `views.py` into smaller modules:
  - `api_views.py` for FHIR resource controllers.
  - `permissions.py` for SMART scope enforcement.
  - `oauth_validators.py` for SMART/OIDC validators.
  - `bulk_export_views.py` for Bulk Data.
  - `renderers.py` for FHIR renderers.
  - `launch_views.py` for SMART launch simulation.
- Make all certification test shortcuts explicit and environment gated.

### 3.6 `services/disease_risk_engine/`

Hospital-approved deterministic disease risk assessment engine.

Main responsibilities:

- Retrieve patient demographics, observations, and questionnaire responses.
- Build CORE.xlsx-style input vectors from `A1 KEY IN` and `HQ` equivalents using latest-available field selection across multiple visits.
- Execute the single formula source at `formula_catalog.py` through a registry-locked runtime plan.
- Save disease risk jobs/results, FHIR `Observation` or `RiskAssessment` mappings, provenance, and audit logs.

Current algorithms and outputs:

- 30 hospital-approved algorithms across cardiovascular, metabolic/endocrine, hepatic, neurocognitive, respiratory, and mental-health groups.
- `algorithm_registry.py` owns metadata, canonical required inputs, versions, governance, and FHIR output type.
- `formula_catalog.py` is the only executable formula source and binds every approved algorithm exactly once.
- `runtime_calculators.py` validates the formula plan against the registry before execution.
- Output persisted in `ai_analysis_jobs` / `ai_analysis_results` as disease-risk records until the table rename is migrated.
- Index/survey outputs map to FHIR `Observation`; predicted-event outputs map to `RiskAssessment`; provenance retains method version and source references.

Current issue:

- The remaining table names still contain `ai_analysis_*`; these are now used as disease-risk job/result tables and should be renamed in a planned migration.
- Formula changes require published/hospital verification vectors plus the Golden Patient DB-to-FHIR regression suite.
- AHA PREVENT CVD, ASCVD, and HF 10-year base equations are active members of the 30-model runtime catalog.

Target state:

- Disease risk engine should remain a domain service with a clear input/output contract.
- Inputs should be traceable to source clinical records or FHIR references.
- Source selection should stay field-level: urine, blood, body measurements, and questionnaire fields may come from different encounters when that is the freshest valid data for each field.
- Outputs should include:
  - Algorithm name.
  - Algorithm version.
  - Input data references.
  - Calculation timestamp.
  - Missing data list.
  - Clinically meaningful interpretation.
  - Provenance.
- Store source-independent derived results as relational risk records and expose them as FHIR `RiskAssessment`.

### 3.7 `frontend/`

React application for users.

Main responsibilities:

- Login/register.
- Role-based theme switching.
- Protected routes.
- Dashboard.
- Patient management.
- Single health data input.
- Bulk health data import.
- Risk analysis.
- SMART launch entrypoint.

Important files:

- `src/App.js`: root router and theme selection.
- `src/components/Navigation.js`: navigation shell.
- `src/components/Login.js`, `Register.js`, `ProtectedRoute.js`.
- `src/components/PatientManagement.js`.
- `src/components/HealthDataInput.js`.
- `src/components/BulkHealthDataImport.js`.
- `src/components/RiskAnalysis.js`.
- `src/components/Launch.js`: SMART launch entrypoint.
- `src/config/api.js`: endpoint constants and fetch wrapper.
- `src/utils/auth.js`: token storage and validation.
- `src/utils/sessionManager.js`: session activity tracking.

Current state:

- `src/config/api.js` is the single endpoint registry and authenticated fetch client.
- Active routes only expose backend modules that remain in the product boundary.
- SMART launch remains separate from normal application login.

Target state:

- Create one API client module with typed endpoint groups.
- Align frontend route names with backend route names.
- Remove or hide modules whose backend is archived.
- Add a feature flag or module registry so the UI only exposes implemented capabilities.
- Treat SMART launch separately from normal application login.

### 3.8 `docs/`

Architecture, certification, US Core, and ONC g10 documentation.

Important current documents:

- `ARCHITECTURE.md`: short architecture overview, but currently too shallow and contains encoding artifacts.
- `certification_risks.md`: certification risk notes.
- `compliance_api.md`: USCDI compliance API notes.
- `uscore_stu7_*`: detailed US Core STU7 projection documentation.
- `g10_certification_artifacts/`: generated certification contract artifacts.

Target state:

- Keep this file as the onboarding map.
- Keep US Core projection docs as detailed implementation references.
- Add decision records for major architecture choices.

## 4. Runtime Architecture

### 4.1 Backend Runtime

Expected local services:

```text
React frontend:  http://localhost:3000
Django backend:  http://localhost:8000
PostgreSQL:      localhost:5432
Redis:           localhost:6379
```

`start_system.bat` starts only the local application services:

1. Django migration and backend server on `0.0.0.0:8000`.
2. React frontend through `npm start`.

The optional Cloudflare quick-tunnel script is not part of normal application
startup. Run it separately only when an ONC/Inferno public endpoint is needed:

```powershell
.\start_system.bat
.\start_cloudflare_quick_tunnel.ps1
```

When used, the optional tunnel script prints:

- `PUBLIC_BASE_URL`
- FHIR Base URL, for example `https://<quick-id>.trycloudflare.com/fhir/R4`
- FHIR metadata URL
- OIDC issuer, for example `https://<quick-id>.trycloudflare.com/o/`

Quick tunnel URLs can change each time `cloudflared` is restarted. The
application itself does not require Cloudflare; configure `PUBLIC_BASE_URL`,
`ALLOWED_HOSTS`, and `CSRF_TRUSTED_ORIGINS` explicitly when using any public
reverse proxy.

### 4.2 Backend Request Paths

Current active root routes:

```text
/admin/
/fhir/
/.well-known/smart-configuration
/metadata
/o/authorize/
/o/token/
/o/
/
/api/health-check/
/api/auth/
/auth/
```

Important observation:

The active root router includes FHIR and auth, but does not currently include:

```text
/api/patients/
/api/health-screening/
```

Those route modules exist under `apps/clinical/.../urls.py`, and the React frontend expects them. This mismatch is a high-priority integration issue.

## 5. Core Data Flow

### 5.1 Normal Application Login

```text
React Login
  -> POST /api/auth/login/
  -> LoginAPIView authenticates Django User
  -> SimpleJWT refresh/access tokens returned
  -> React stores tokens in localStorage
  -> ProtectedRoute checks token
  -> API calls include Authorization: Bearer <access_token>
```

Current role flow:

```text
Django User
  -> UserProfile.role
  -> Login response user.role
  -> React theme and navigation behavior
```

### 5.2 SMART on FHIR Authorization

```text
SMART client or Inferno
  -> GET/POST /o/authorize/
  -> CustomAuthorizationView normalizes SMART scopes
  -> User grants scopes
  -> /o/token/ exchanges authorization code
  -> CustomTokenView injects SMART context
  -> FHIR endpoints enforce FHIRScopePermission
```

SMART discovery:

```text
GET /.well-known/smart-configuration
GET /fhir/.well-known/smart-configuration
```

FHIR metadata:

```text
GET /metadata
GET /fhir/metadata
```

### 5.3 Clinical Source Data Entry

Intended flow:

```text
React single health data form
  -> REST API for patient/screening source data
  -> Django clinical models
  -> PostgreSQL
  -> FHIR projectors expose data through /fhir/*
```

Current gap:

The clinical REST endpoints exist in app URL modules but are not mounted in the root URL config, so the intended frontend calls are not reliably reachable.

### 5.4 Bulk Health Data Import

Current intended flow:

```text
CSV upload
  -> BulkDataProcessor or health_screening bulk import service
  -> USCDIv6Mapper
  -> FHIRResource / USCDIDataElement records
```

Recommended target flow:

```text
CSV/XLSX upload
  -> ingestion validator
  -> normalized staging table
  -> relational clinical source models
  -> transaction log and validation report
  -> deterministic FHIR projection
```

Reason:

For ONC/certification readiness, the system should be able to prove where each FHIR resource came from. Persisting mapped FHIR JSON directly as the primary record makes provenance, correction, and domain validation harder.

### 5.5 FHIR Search and Read

Current projection flow:

```text
GET /fhir/{ResourceType}
  -> FHIRResourceViewSet or specialized ViewSet
  -> SearchParser
  -> FHIRContext
  -> ProjectorRegistry.get(ResourceType)
  -> projector.query()
  -> projector.project_batch()
  -> ProjectionContractValidator
  -> IncludeResolver / Provenance revinclude
  -> FHIRBundleBuilder
  -> application/fhir+json Bundle
```

Read flow:

```text
GET /fhir/{ResourceType}/{id}
  -> ProjectorRegistry
  -> query by _id
  -> project
  -> return resource or OperationOutcome
```

### 5.6 Disease Risk Assessment

Current flow:

```text
DiseaseRiskAssessmentService.calculate_dynamic_risk(patient_id)
  -> Patient lookup by UUID or MRN
  -> observations + questionnaire_responses
  -> legacy HealthScreening fallback if needed
  -> CORE.xlsx-compatible calculators
  -> ai_analysis_jobs / ai_analysis_results
  -> FHIRResourceMapping RiskAssessment
  -> audit_logs
```

Recommended target flow:

```text
Disease Risk API
  -> DiseaseRiskAssessmentService
  -> data completeness check
  -> algorithm-specific calculator
  -> relational disease risk result
  -> FHIR RiskAssessment mapping
  -> Provenance/AuditEvent
  -> frontend dashboard
```

## 6. API Architecture

### 6.1 Active FHIR API

The FHIR router registers resource endpoints such as:

```text
/fhir/Patient
/fhir/Observation
/fhir/Condition
/fhir/Encounter
/fhir/DiagnosticReport
/fhir/DocumentReference
/fhir/CarePlan
/fhir/CareTeam
/fhir/Device
/fhir/MedicationRequest
/fhir/Provenance
/fhir/Group
/fhir/metadata
```

The root also includes the FHIR app at `/`, which exposes some FHIR endpoints without the `/fhir/` prefix. This exists for test compatibility but should be documented as compatibility behavior, not the preferred product API.

### 6.2 Application REST API

Currently active:

```text
/api/auth/register/
/api/auth/login/
/api/auth/logout/
/api/auth/profile/
/api/auth/token/
/api/auth/token/refresh/
/api/health-check/
```

Implemented but not root-mounted:

```text
apps/clinical/patients/urls.py
apps/clinical/health_screening/urls.py
```

Recommended target API groups:

```text
/api/auth/              Application login and profile
/api/users/             User and role administration
/api/patients/          Patient source-data CRUD
/api/screenings/        Health screening source-data CRUD
/api/ingestion/         CSV/XLSX/device ingestion jobs
/api/risk/              Risk calculation and reports
/api/audit/             Audit trail
/fhir/                  FHIR R4 API only
/o/                     OAuth2/OIDC endpoints
/.well-known/           SMART discovery
```

Do not expose USCDI clinical data through proprietary APIs as the long-term external integration contract. Proprietary APIs may exist for internal workflow, but certification-facing clinical exchange must remain FHIR/US Core.

## 7. Database Architecture

Current database strategy:

- PostgreSQL is configured as default.
- Clinical source data is represented by relational models.
- `FHIRResource.resource_data` stores JSON data.
- FHIR projection contracts and mock datasets support certification workflows.

Recommended database boundary:

```text
Source-of-truth tables:
  patients
  health_screening_*
  care_team_members
  patient_allergies
  patient_medications
  medical_orders
  insurance_data
  clinical_notes
  future risk source tables

Derived/cache tables:
  fhir_integration_fhirresource
  uscdi mapping tables
  generated certification artifacts

Operational tables:
  auth_user
  authentication_userprofile
  oauth2_provider_*
  audit events
  ingestion jobs
```

Recommended indexes:

- Patient MRN and identifiers.
- Patient name/date of birth search fields.
- Screening patient/date.
- Lab result test name/code/date.
- FHIR resource type/resource ID.
- JSONB indexes if `FHIRResource.resource_data` remains queryable.

## 8. Responsibility Boundaries

### 8.1 Clinical Apps

Own:

- Clinical source models.
- Domain validation.
- Internal CRUD serializers.
- Internal clinical workflow APIs.

Must not own:

- FHIR route behavior.
- SMART scope logic.
- Certification test-specific JSON.
- OAuth token behavior.

### 8.2 FHIR Integration

Own:

- FHIR REST behavior.
- CapabilityStatement.
- Search parameter support.
- US Core profile projection.
- SMART scope enforcement.
- FHIR Bundle and OperationOutcome formatting.
- Bulk Data export behavior.

Must not own:

- Core clinical business rules.
- User-facing form workflows.
- Source clinical record ownership.

### 8.3 Disease Risk Engine

Own:

- Risk algorithm execution.
- Data completeness checks.
- Clinical risk output contract.
- Algorithm metadata and versioning.

Must not own:

- UI rendering.
- FHIR endpoint routing.
- Patient CRUD.

### 8.4 Frontend

Own:

- User workflows.
- Form UX.
- Dashboard presentation.
- SMART launch client behavior.
- API client calls.

Must not own:

- Clinical calculations.
- FHIR profile compliance rules.
- Authorization decisions beyond route guarding and UX hints.

## 9. Naming and Structure Standards

Recommended naming rules:

- Django apps: lowercase snake_case domain names.
- Python modules: snake_case.
- Django models: singular PascalCase.
- DRF ViewSets: `{ModelName}ViewSet`.
- Services: `{Domain}Service`, `{Action}Processor`, or `{Resource}Projector`.
- React components: PascalCase.
- React utility modules: camelCase or kebab-free lowercase filenames, consistently applied.
- API route paths: plural nouns for collections, lowercase kebab-case where needed.
- FHIR route paths: exact FHIR resource names, PascalCase, for example `/fhir/Patient`.

Recommended folder pattern for active apps:

```text
apps/
  core/
    authentication/
    audit/
    common/
  clinical/
    patients/
    screenings/
    risk/
  integration/
    fhir_integration/
    device_ingestion/
    terminology/
```

Recommended frontend pattern:

```text
frontend/src/
  app/
  components/
  features/
    auth/
    patients/
    screenings/
    ingestion/
    risk/
    smart/
  api/
  hooks/
  routes/
  theme/
  utils/
```

## 10. Coupling, Redundancy, and Technical Debt

### High priority

1. Frontend/backend API mismatch.

   React expects `/api/patients/` and `/api/health-screening/`, but the root Django router does not mount those app routes.

2. Permission inconsistency.

   Clinical REST ViewSets use `AllowAny`, while DRF default permission is `IsAuthenticated` and FHIR uses OAuth scopes. This is unsafe for clinical data.

3. Environment and certification-test settings mixed with production settings.

   Examples include permissive CORS, default secrets, embedded OIDC key, debug/test launch behavior, and Inferno-specific behavior.

4. FHIR source-of-truth ambiguity.

   The system has both relational source models and `FHIRResource.resource_data`. The projectors imply relational source truth, but ingestion still creates `FHIRResource` records directly.

5. Encoding corruption in comments and verbose names.

   Many files contain unreadable text, which reduces new engineer productivity and increases risk during refactoring.

### Medium priority

1. Oversized FHIR views.

   `fhir_integration/views.py` handles many unrelated concerns and should be split.

2. Role model too small.

   `professional` and `patient` are not enough for a commercial clinical platform.

3. Risk output persistence is incomplete.

   Risk results should include provenance, algorithm version, missing inputs, and source references.

### Lower priority

1. Existing docs need normalization and encoding cleanup.
2. `ARCHITECTURE.md` should be replaced or redirected to this overview.
3. Start scripts should be split into backend, frontend, worker, and tunnel scripts.
4. Static and template directories should be cleaned once active server-rendered pages are confirmed.

## 11. Recommended Refactoring Plan

### Phase 1: Stabilize routing and security

- Mount active clinical APIs in `medical_system/urls.py`.
- Replace `AllowAny` on clinical ViewSets with authenticated role-based permissions.
- Consolidate frontend API clients into one module.
- Make frontend endpoint constants match backend routes.
- Split settings into environment-specific files.
- Move private keys and secrets into environment variables.

### Phase 2: Clarify data ownership

- Declare relational clinical models as source of truth.
- Mark `FHIRResource` as derived/cache/legacy unless intentionally used for external imported FHIR.
- Refactor bulk import to write source clinical models first.
- Add ingestion job and validation result models.
- Add provenance and audit models.

### Phase 3: Modularize FHIR integration

- Split `fhir_integration/views.py`.
- Keep projectors as the central mapping layer.
- Make CapabilityStatement generation fully contract-driven.
- Add tests per projector.
- Gate Inferno-specific behavior with explicit settings.

### Phase 4: Risk engine hardening

- Add a risk assessment source model.
- Version all algorithms.
- Store input references and missing input lists.
- Expose risk results through both application API and FHIR `RiskAssessment`.
- Add regression tests for calculators and API outputs.

### Phase 5: Product module strategy

- Decide which archived modules return to the active product.
- Restore selected modules under active domain folders with tests.
- Remove or hide frontend screens for unavailable backend modules.
- Add module registry/feature flags.

### Phase 6: Certification readiness

- Run Inferno/ONC g10 test suites regularly.
- Maintain a golden patient dataset.
- Document SMART/OIDC configuration.
- Verify US Core searches and `_include`/`_revinclude` behavior.
- Produce certification evidence artifacts from repeatable commands.

## 12. Development and Verification Commands

Backend environment check:

```powershell
.\venv\Scripts\python.exe manage.py check
```

Start full local system:

```powershell
.\start_system.bat
```

Seed ONC/g10 golden patient data:

```powershell
.\venv\Scripts\python.exe manage.py seed_onc_patient
.\venv\Scripts\python.exe manage.py seed_onc_data
```

Export g10 contract:

```powershell
.\venv\Scripts\python.exe manage.py export_g10_certification_contract
```

Frontend:

```powershell
cd frontend
npm start
npm test
npm run build
```

## 13. Current Verification Notes

During this review:

- `python manage.py check` failed because the global Python environment did not have Django installed.
- `.\venv\Scripts\python.exe manage.py check` completed successfully with no Django system check issues.
- `manage.py show_urls` is unavailable because the corresponding Django extension command is not enabled in `INSTALLED_APPS`.

No application tests were run as part of this documentation pass.

## 14. New Engineer Onboarding Summary

Start here:

1. Read this file.
2. Read `apps/integration/fhir_integration/README.md`.
3. Read `docs/uscore_stu7_semantic_projection_architecture.md`.
4. Read `medical_system/settings.py` and `medical_system/urls.py`.
5. Read models in:
   - `apps/clinical/patients/models.py`
   - `apps/clinical/health_screening/models.py`
   - `apps/integration/fhir_integration/models.py`
6. Read FHIR projection flow:
   - `apps/integration/fhir_integration/views.py`
   - `apps/integration/fhir_integration/projectors/base.py`
   - `apps/integration/fhir_integration/projectors/registry.py`
   - `apps/integration/fhir_integration/projection_contracts.py`
7. Read frontend routing:
   - `frontend/src/App.js`
   - `frontend/src/config/api.js`
   - `frontend/src/utils/auth.js`

Mental model:

```text
React UI
  -> application REST APIs for workflow
  -> clinical relational source data
  -> deterministic FHIR projectors
  -> FHIR R4 / US Core API
  -> SMART OAuth2/OIDC security
```

Primary architectural risk:

The system is partway through a transition from a broad prototype with many modules into a certifiable FHIR-native platform. The next refactors should reduce ambiguity, not add new features on top of unstable boundaries.
