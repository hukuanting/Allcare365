# ONC g10 Final Pass Archive

Status: Passed, reported by the tester on 2026-06-09.

Report scope: ONC Certification (g)(10) Standardized API Report - US Core 7.0.0 / USCDI v4, SMART App Launch 2.2.0, Bulk Data 2.0.0.

This archive is the engineering freeze point for the certified API behavior. It records what must stay stable while Allcare 365 moves into product development as an EHR/EMR platform with frontend workflows, clinical operations, risk analytics, and device integration.

## Passed Areas

- Single Patient API: US Core 7.0.0, FHIR R4, USCDI v4 mapped resources.
- Multi-Patient Authorization and API: Bulk Data Access STU2 / Bulk Data 2.0.0.
- SMART App Launch: SMART App Launch 2.2.0, public, symmetric confidential, asymmetric confidential, patient/user scopes, granular scopes, revocation, introspection, and token behavior.
- Visual Inspection and Attestation: registration support, authorization UI, offline access notice, refresh token duration, public service URLs, TLS attestation, JWKS cache behavior, Bulk `_since`, and granular Clinical Test Observation scope support.

## Certification Baseline

Primary FHIR base path:

```text
/fhir/R4
```

Public URL is tunnel or deployment dependent. Do not hard-code Cloudflare/ngrok hosts in code. Runtime public URLs must derive from the incoming request or a deliberate `PUBLIC_BASE_URL` deployment setting.

Core public endpoints:

```text
/.well-known/smart-configuration
/fhir/R4/.well-known/smart-configuration
/fhir/R4/metadata
/o/authorize/
/o/token/
/o/revoke/
/o/introspect/
/fhir/R4/jwks
/fhir/R4/Group/example-group/$export
/onc-certification/api-documentation/
```

## Local Regression Gates

Run the full baseline guard before changing certification-facing code:

```powershell
powershell -ExecutionPolicy Bypass -File .\verify_onc_certification_baseline.ps1
```

Targeted guards:

```powershell
powershell -ExecutionPolicy Bypass -File .\verify_onc_single_patient_api.ps1
powershell -ExecutionPolicy Bypass -File .\verify_onc_bulk_data_stu2.ps1
powershell -ExecutionPolicy Bypass -File .\verify_onc_visual_inspection.ps1
```

Use `-SeedBulk` on the full guard only when rebuilding the local Bulk Data certification dataset.

## Certification-Locked Areas

Changes to these areas require at least the relevant local guard and usually a rerun of the affected Inferno scenario:

- `apps/integration/fhir_integration/views.py`
- `apps/integration/fhir_integration/projectors/`
- `apps/integration/fhir_integration/fhir_search/`
- `apps/integration/fhir_integration/capability_statement.py`
- `apps/integration/fhir_integration/smart_config.py`
- `apps/integration/fhir_integration/fine_grained_scopes.py`
- `apps/integration/fhir_integration/resource_identity.py`
- `apps/integration/fhir_integration/reference_builder.py`
- `apps/integration/fhir_integration/reference_resolution.py`
- `apps/integration/fhir_integration/terminology.py`
- `apps/core/authentication/views.py`
- `apps/core/authentication/smart_utils.py`
- `medical_system/settings.py`
- `medical_system/urls.py`
- `templates/oauth2_provider/authorize.html`

## Product Development Rule

New EHR/EMR features should not bypass the certified FHIR contract.

- User-facing workflows may use product APIs under `/api/...` for ergonomics.
- Clinical exchange, third-party apps, device integrations, and certification-facing workflows must use FHIR R4 resources and SMART/Bulk security semantics.
- Derived analytics must be traceable. Risk outputs should be represented as `RiskAssessment` and/or `Observation`, with `Provenance` linking inputs, algorithm version, and authoring system.
- Any new clinical source model must have a documented USCDI/FHIR mapping before it is exposed to production workflows.

## Evidence Files

- `ONC_CERTIFICATION_LOG.md`
- `docs/onc_single_patient_api_us_core_7_pass_archive.md`
- `docs/onc_bulk_data_stu2_setup.md`
- `docs/onc_visual_inspection_attestation_setup.md`
- `docs/g10_certification_artifacts/`
- `tests/test_uscore_projection_contracts.py`
- `tests/test_bulk_data_stu2_contracts.py`
- `tests/test_smart_visual_inspection_contracts.py`

