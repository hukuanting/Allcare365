# FHIR Integration Module

> Architecture: deterministic ORM-to-FHIR projection for ONC g10 / US Core STU7.

## Core Concept

```text
Relational DB (Django ORM) = Source of clinical truth
FHIR Layer                 = Deterministic projection only
```

No hand-authored certification JSON should be persisted as source data.

## Seed Policy

```bash
python manage.py seed_onc_patient
python manage.py seed_onc_data
```

Canonical golden patient:

- Name: `Justin Hu`
- Patient ID: `00000000-0000-4000-a000-000000000001`

Rules:

- `seed_onc_patient` is the canonical ONC/g10 relational seed command.
- `seed_onc_data` is a compatibility wrapper and must not diverge from `seed_onc_patient`.
- All projector validation should assume the relational seed is the source of truth, then verify deterministic FHIR projection against US Core STU7 and the ONC g10 test kit.

## Key Components

- `projectors/`: one projector per FHIR resource type
- `fhir_search/`: parsing and search translation
- `capability_statement.py`: `/metadata` generation
- `projection_contracts.py`: US Core contract layer
- `g10_testkit.py`: executable ONC g10 certification contract layer
- `resource_identity.py`: stable FHIR ids
- `reference_builder.py`: consistent FHIR references
- `terminology.py`: centralized terminology mapping

## Current Standard

- Normative source: US Core STU7
- Executable validation source: ONC Certification g10 Test Kit
- Golden patient workflow:
  `RelationDB -> US Core semantic design -> Golden patient dataset -> Relational seed -> Projector contract -> Deterministic FHIR projection -> Inferno validation`

## Certification Pass Archive

- Pass archive: `docs/onc_single_patient_api_us_core_7_pass_archive.md`
- Machine manifest: `docs/g10_certification_artifacts/single_patient_api_pass_manifest.json`
- Local regression guard:

```powershell
.\verify_onc_single_patient_api.ps1
```

Run the guard before changing projectors, terminology, search parsing, references, CapabilityStatement, SMART/OAuth behavior, or FHIR routing.

## Bulk Data STU2

- Setup guide: `docs/onc_bulk_data_stu2_setup.md`
- Machine manifest: `docs/g10_certification_artifacts/bulk_data_stu2_manifest.json`
- Group export id: `example-group`
- Backend Services client id: `inferno_bulk_client`
- Local guard:

```powershell
.\verify_onc_bulk_data_stu2.ps1 -Seed
```
