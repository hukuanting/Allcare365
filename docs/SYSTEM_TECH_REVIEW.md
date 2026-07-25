# System Technical Review and Handoff Map

Last reviewed: 2026-07-25. This is a code-location guide for the current active product, not a claim of ONC certification.

## System purpose

Allcare 365 is a Django + React clinical-data demonstration platform. Its active product surface is patient management, health screening and risk calculation, FHIR R4 exchange, and SMART on FHIR authorization. The intended database is PostgreSQL.

## Active modules

| Module | Responsibility | Primary code location |
| --- | --- | --- |
| Django runtime | settings, route composition, WSGI/ASGI, health endpoint | `medical_system/` |
| Authentication | local auth APIs/pages, user/role models, OAuth customizations | `apps/core/authentication/` |
| Patients | patient domain model, clinical detail REST endpoints and access control | `apps/clinical/patients/` |
| Screening | screenings, imports, cohorts, reports, data quality, risk workflow | `apps/clinical/health_screening/` |
| FHIR integration | FHIR REST API, search, resource projectors, SMART config, bulk export | `apps/integration/fhir_integration/` |
| Risk engine | algorithms, units, calculators, persistence boundary | `services/disease_risk_engine/` |
| React UI | login, dashboard, patient chart, data input, bulk import, risk screens | `frontend/src/` |
| Verification | Django/pytest contracts and React unit tests | `tests/`, app `tests.py`, `frontend/src/**/*.test.js` |
| Certification evidence | verification notes and generated artifacts | `docs/`, `ONC_CERTIFICATION_LOG.md` |

Only the Django apps listed in `medical_system/settings.py:INSTALLED_APPS` are operational. The active app set is `authentication`, `patients`, `health_screening`, and `fhir_integration` plus framework dependencies.

## Runtime and request boundaries

```text
Browser → React (`frontend/src`)
        → /api/auth              → authentication
        → /api/patients          → patients
        → /api/health-screening  → health_screening → disease_risk_engine
        → /fhir/R4               → fhir_integration → FHIRResource / projectors
        → /o/*                   → OAuth2 + SMART support
```

`medical_system/urls.py` owns the public route table. `medical_system/settings.py` remains the local-development configuration. `medical_system/settings_production.py` is the strict production profile used by the Render blueprint.

## Important data flows

1. **App login:** React calls `apps/core/authentication/api_urls.py`; the token is used by `frontend/src/config/api.js` for later API requests.
2. **Patient data:** `apps/clinical/patients/views.py` and serializers persist source clinical records. FHIR projectors must be treated as derived exchange representations, not the source of truth.
3. **Screening/risk:** `apps/clinical/health_screening/views.py` coordinates input validation and the `services/disease_risk_engine/` service. The resulting risk data is projected as FHIR `RiskAssessment` with provenance.
4. **FHIR/SMART:** `apps/integration/fhir_integration/views.py` is the largest integration boundary. It handles content negotiation, authorization, resource search/read, and bulk export. Related mappings belong in `projectors/`, not in the viewset.

## Cleanup completed in this handoff

- Removed 39 unreferenced server-rendered templates for retired appointment, billing, document, encounter, form, laboratory, pharmacy, and therapy-group modules.
- Preserved active patient, authentication, OAuth, FHIR/SMART, and health-screening templates.
- Removed neither migrations nor source-risk evidence. Migrations are historical database contracts and must not be deleted from a deployed system.
- Corrected two frontend cloud-deployment blockers: refresh-token calls and SMART launch configuration now use `REACT_APP_API_URL` instead of a hard-coded localhost backend.

The repository already contained substantial uncommitted deletions under `archive/` before this review. They are intentionally left untouched so the owner can decide whether to publish that historical removal in the next commit.

## Known risks and next-engineer priorities

| Priority | Finding | Recommended action |
| --- | --- | --- |
| Critical before real use | Free hosting is not appropriate for PHI, service-level commitments, backups, or regulated operation. | Use synthetic demo data only; select a compliant paid hosting/data agreement before any clinical use. |
| High | `medical_system/settings.py` deliberately defaults to development values. | Deploy only with `medical_system.settings_production`; set every required environment variable. |
| High | `fhir_integration/views.py` has several responsibilities. | Extract renderer, permission, search, resource-read, and bulk-export services behind focused tests. |
| High | Some legacy server-rendered pages coexist with React. | Choose React or Django templates per feature; remove/repair only after route-level regression tests. |
| Medium | Redis/Celery are configured but the free demo blueprint does not run a durable worker. | Keep demo requests synchronous or provision worker + durable Redis before enabling async jobs. |
| Medium | Documentation contains certification preparation records. | State “certification-ready work” precisely; do not claim certification without official evidence. |
| Medium | Root `templates/health_screening/` has legacy files while the active API is React-first. | Add integration tests before pruning this remaining set. |

## Handoff operating procedure

1. Read this file, `SYSTEM_TECHNICAL_OVERVIEW.md`, and the latest `ONC_CERTIFICATION_LOG.md`.
2. Copy `.env.example`; use local PostgreSQL; run migrations and test checks.
3. Make schema changes through Django migrations only. Do not alter existing migration files.
4. For a new FHIR resource, add the mapping/projection first, then views/routes, then contract tests.
5. For a new risk algorithm, register it in `services/disease_risk_engine/algorithm_registry.py`, validate units/formula inputs, and retain source/provenance metadata.
6. Keep real clinical data out of local fixtures, Git history, screenshots, CI logs, and free hosting.

## Verification commands

```bash
python manage.py check
pytest
cd frontend && CI=true npm test -- --watchAll=false && npm run build
```

When validating production settings, use only a throwaway test database and environment variables. `python manage.py check --deploy` should be part of the release gate.
