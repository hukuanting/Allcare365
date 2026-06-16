# US Core STU7 Architecture Verification Phase (Pre-Implementation)

Status: `LOCK CANDIDATE`  
Date: 2026-04-09 (Asia/Taipei)  
Scope: Inferno US Core STU7 Single Patient API expectations

## A. Verification Inputs

- Must Support catalog (50 profile groups):
  - `docs/uscore_stu7_artifacts/must_support_catalog.json`
- Search catalog (243 search combos):
  - `docs/uscore_stu7_artifacts/search_catalog.json`
- Must Support reference edges:
  - `docs/uscore_stu7_artifacts/reference_edges_raw.json`
  - `docs/uscore_stu7_artifacts/reference_edges_agg.json`
- Base architecture:
  - `docs/uscore_stu7_semantic_projection_architecture.md`

## B. Verification Results Against Inferno Single Patient

### B1. Must Support Coverage Model

Validated that the architecture is sourced from Inferno-generated STU7 metadata and not ad-hoc assumptions.

- Total profile groups parsed: `50`
- Must Support source of truth: Inferno-generated `metadata.yml` per profile
- Contract rule: each profile in minimum ONC-pass scope must have at least one instance in Golden Patient graph unless explicitly out-of-scope.

### B2. Search Expectation Model

Validated architecture has an explicit search contract inventory.

- Total search combos parsed: `243`
- Contract rule:
  - `SHALL` combos must return valid matches for Golden Patient data.
  - `SHOULD` combos in enabled Inferno groups should be supported for stability.

### B3. Must Support Reference Resolution Model

Validated architecture includes explicit reference dependencies from Must Support reference paths.

- Aggregated MS reference edges: `56 raw`, normalized in `reference_edges_agg.json`.
- Critical reference paths in lock scope:
  - `Condition.encounter -> Encounter`
  - `Encounter.participant.individual -> Practitioner`
  - `Encounter.reasonReference -> Condition`
  - `Encounter.location.location -> Location`
  - `Encounter.serviceProvider -> Organization`
  - `Observation.specimen -> Specimen`
  - `DiagnosticReport.result -> Observation`
  - `DiagnosticReport.performer -> Practitioner` (primary)
  - `DiagnosticReport.media.link -> Media`
  - `DocumentReference.author -> Practitioner`
  - `Coverage.payor -> Organization`
  - `MedicationDispense.authorizingPrescription -> MedicationRequest`

### B4. Dependency Ordering Verification

Required ordered chain is confirmed as architectural gate:

`Patient -> Encounter -> Condition -> Observation -> DiagnosticReport -> DocumentReference -> others`

This order is enforced for:

1. seed design dependencies,
2. projector reference resolvability,
3. Inferno reference-resolution tests.

## C. Lock Constraints (to prevent patch cycles)

1. No projector changes without contract update.
2. No new seed field outside relational model schema.
3. All FHIR coding remains projector-time only.
4. Every Must Support element in lock scope must be classified as:
   - relationally sourced, or
   - synthesized at projection time.
5. Every Must Support reference path must resolve to an actual retrievable resource instance.

## D. Approval Gate

Implementation can start only if all are accepted:

1. `docs/uscore_stu7_golden_patient_spec.md`
2. `docs/uscore_stu7_projection_contract_table.md`
3. `docs/uscore_stu7_minimum_onc_pass_dataset.md`
4. this verification report

