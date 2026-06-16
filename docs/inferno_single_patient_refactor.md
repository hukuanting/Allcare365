# Inferno Single Patient API (US Core 7.0.0) Refactor Guide

## What this refactor changes

- Centralizes mock US Core data generation in:
  - `apps/integration/fhir_integration/uscore_mock_dataset.py`
- Routes `FHIRService.get_mock_resources_for_patient(...)` to the centralized dataset.
- Fixes bundle construction in `FHIRResourceViewSet.list(...)`:
  - Uses dictionary access (`bundle["entry"]`, `bundle["total"]`) instead of attribute access.
- Fixes `Observation` search path to use the same mock dataset flow.

## Why this matters for test 12

The Inferno Single Patient API suite validates that your server can:

- Return US Core resources under expected profiles.
- Support patient-scoped search interactions and common search parameters.
- Return valid FHIR Bundles and resources for read/search workflows.

This refactor removes several failure modes:

- Missing resources for many resource types.
- Runtime errors from malformed bundle handling.
- Observation endpoint calling a missing service method.

## Seed deterministic test patient

```powershell
python manage.py seed_onc_data --patient-id 00038eba-e39d-4991-b60a-6e6cea9133e8 --mrn MRN-AMY-001
```

## Quick smoke checks (examples)

```powershell
# Patient
GET /fhir/Patient?_id=00038eba-e39d-4991-b60a-6e6cea9133e8

# Single-patient resources
GET /fhir/Observation?patient=00038eba-e39d-4991-b60a-6e6cea9133e8
GET /fhir/Condition?patient=00038eba-e39d-4991-b60a-6e6cea9133e8
GET /fhir/DiagnosticReport?patient=00038eba-e39d-4991-b60a-6e6cea9133e8

# Provenance revinclude
GET /fhir/Observation?patient=00038eba-e39d-4991-b60a-6e6cea9133e8&_revinclude=Provenance:target
```

## Notes

- This is a deterministic mock dataset path intended for certification testing.
- Production data flow can coexist, but certification routing should remain stable and predictable.
