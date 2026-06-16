# ONC g10 Single Patient API Pass Archive (US Core 7.0.0)

Status: Passed in Inferno 12 Single Patient API (US Core 7.0.0), reported on 2026-05-29.

This archive is a maintenance lock for the Allcare 365 FHIR R4 backend. It records the certification-facing shape that must not regress while future backend, frontend, risk analysis, or device integration work continues.

This is not an official ONC certificate. It is the engineering evidence point that the current server behavior satisfied Inferno g10 Single Patient API test group 12 for US Core 7.0.0.

## Scope

- Test suite: ONC Certification g10 Single Patient API.
- US Core version: 7.0.0 / STU7.
- FHIR version: R4 / 4.0.1.
- Golden patient: `Justin Hu`.
- Golden patient id: `00000000-0000-4000-a000-000000000001`.
- FHIR base path: `/fhir/R4`.
- Public tunnel: ephemeral Cloudflare quick tunnel; do not hard-code a specific `trycloudflare.com` host in certification logic.

## Source Of Truth

The certification API is projected from relational clinical data. Do not replace the projector layer with hand-authored FHIR JSON fixtures as the primary source of truth.

Canonical flow:

```text
Relational DB
-> US Core semantic mapping
-> Golden patient seed
-> Projector contracts
-> Deterministic FHIR projection
-> SMART/OAuth protected FHIR R4 API
-> Inferno validation
```

Canonical seed commands:

```powershell
.\venv\Scripts\python.exe manage.py seed_onc_patient
.\venv\Scripts\python.exe manage.py seed_onc_data
```

`seed_onc_data` is a compatibility wrapper and must not diverge from `seed_onc_patient`.

## Regression Guard

Run this before changing any certification-facing backend code:

```powershell
.\verify_onc_single_patient_api.ps1
```

Optional live API preflight when a tunnel and fresh bearer token are available:

```powershell
.\verify_onc_single_patient_api.ps1 `
  -BaseUrl "https://<current-cloudflare-host>/fhir/R4" `
  -Token "<fresh-inferno-token>"
```

The local guard currently runs:

- Django system check.
- US Core projection contract unit tests.
- Optional live FHIR preflight through `inferno_preflight_validator.py`.

Inferno remains the external source of certification truth. The guard is a fast local regression gate, not a replacement for the Inferno suite.

## Files Under Certification Lock

Changes to these files can break the passed state and require at least the local guard plus the affected Inferno group:

- `apps/integration/fhir_integration/views.py`
- `apps/integration/fhir_integration/fhir_context.py`
- `apps/integration/fhir_integration/fhir_search/`
- `apps/integration/fhir_integration/projectors/`
- `apps/integration/fhir_integration/terminology.py`
- `apps/integration/fhir_integration/resource_identity.py`
- `apps/integration/fhir_integration/reference_builder.py`
- `apps/integration/fhir_integration/reference_resolution.py`
- `apps/integration/fhir_integration/meta_builder.py`
- `apps/integration/fhir_integration/capability_statement.py`
- `apps/integration/fhir_integration/uscore_capability.py`
- `apps/integration/fhir_integration/projection_contracts.py`
- `apps/integration/fhir_integration/g10_testkit.py`
- `medical_system/settings.py`
- `medical_system/urls.py`
- OAuth/SMART launch code under `apps/core/authentication/`.

## Critical Contracts To Preserve

- All US Core resources must use FHIR R4 JSON and `application/fhir+json`.
- Patient-scoped search must support both `patient=<id>` and `patient=Patient/<id>`.
- Required GET and POST `_search` interactions must return consistent counts.
- `_revinclude=Provenance:target` must return readable US Core Provenance resources.
- FHIR ids must stay within the 64 character R4 id limit.
- Must Support references must resolve to conformant target resources.
- DocumentReference attachment URLs must use valid lowercase UUID URNs.
- Observation profiles must expose the required value slices across returned resources.
- Smoking Status must include both `valueCodeableConcept` and `valueQuantity` evidence.
- Pediatric BMI for Age must expose `valueQuantity` with UCUM `%`.
- Pulse Oximetry must include PulseOx coding and oxygen flow/concentration components.
- Blood Pressure and Average Blood Pressure must keep required systolic/diastolic slices and data absent variants.
- Missing data evidence must include the DataAbsentReason extension.
- Provenance ids must remain compact and deterministic.

## Change Policy

Before merging or continuing major development:

1. Run `.\verify_onc_single_patient_api.ps1`.
2. If any file under certification lock changed, rerun the affected Inferno profile group.
3. If FHIR search, auth, CapabilityStatement, projectors, terminology, or references changed, rerun all group 12 Single Patient API tests.
4. Append a concise entry to `ONC_CERTIFICATION_LOG.md`.
5. Keep certification-specific behavior explicit and documented; do not hide it inside unrelated application logic.

## Evidence Artifacts

- Human archive: `docs/onc_single_patient_api_us_core_7_pass_archive.md`.
- Machine manifest: `docs/g10_certification_artifacts/single_patient_api_pass_manifest.json`.
- Executable local guard: `verify_onc_single_patient_api.ps1`.
- Repair history: `ONC_CERTIFICATION_LOG.md`.
- Generated contract: `docs/g10_certification_artifacts/g10_single_patient_contract.json`.

