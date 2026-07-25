# Golden patient conformance gate

The golden patient is a persisted, synthetic conformance record for exercising
the same path as hospital data:

`FHIR R4 Bundle -> relational Patient/Encounter/Observation/Condition/QuestionnaireResponse -> canonical mapping -> risk input repository -> governed catalog -> FHIR RiskAssessment + Provenance`

It is not application mock data. Nothing imports it from an API view, request
handler, calculator, or missing-data fallback. It exists only when an operator
explicitly runs the management command or the conformance test creates it.

## Run the gate

Apply the schema migrations first. They add strict FHIR resource identity,
source ownership, object-level risk/SMART permissions, and persisted SMART
launch/token context tables.

```powershell
.\venv\Scripts\python.exe manage.py migrate
```

```powershell
.\venv\Scripts\python.exe manage.py seed_golden_patient --verify
```

The command exits non-zero with `CommandError` if FHIR ingestion, source
ownership, database persistence, repository mappings, any of the 10 catalog
entries, a RiskAssessment, a Provenance resource, or an input basis reference
fails. Eight currently enabled models must reproduce frozen score/category
vectors; the two liver candidates must remain visible but unexecuted.
The API `execution_summary` must report all eight executable models calculated,
zero insufficient-data models, and zero not-applicable models.

Seeding alone is also available:

```powershell
.\venv\Scripts\python.exe manage.py seed_golden_patient
```

## Isolation and repeatability

- The reserved MRN is `GOLDEN-RISK-001`.
- The trusted FHIR origin namespace is `allcare365:golden-risk:v1`.
- Risk evaluation is frozen at `2026-07-15`, independent of wall-clock age.
- The Patient and every input FHIR resource carry an explicit synthetic
  conformance tag/version.
- Re-running the command replaces only that marked patient's clinical input
  rows before using the production FHIR ingestion service.
- No unrelated Patient row is deleted or updated.
- If the reserved MRN already belongs to an unmarked patient, the command
  fails instead of overwriting it.
- Verification runs intentionally create normal append-only analysis jobs,
  results, audit records, RiskAssessment resources, and Provenance resources;
  these are evidence of each gate execution, not seed duplication.
- The fixture is marked `synthetic=true` and `clinical_use_prohibited=true`;
  normal clinical patient lists and FHIR searches exclude it by default.

The golden record must never receive real clinical data and must never be used
for clinical decisions.

## Risk-analysis demo selector

The risk-analysis UI explicitly requests `GET /api/patients/?include_demo=true`.
That opt-in scope adds only the record matching all reserved Golden Patient
markers (MRN, source system, fixture key, `synthetic=true`, and
`clinical_use_prohibited=true`). It does not expose any other conformance
fixture.

Any active authenticated user may run the disease-risk workflow for this exact
synthetic patient without a Practitioner-Patient care link. This exception is
implemented only in `PatientRiskAccessPolicy`; it does not apply to clinical
patient detail/update routes, SMART launch context, or normal FHIR search.
The UI labels the option `Golden Patient（展示用合成病患）` and displays a
clinical-use prohibition warning.

## FHIR and SMART exposure

- Persisted disease-risk results are available through read/search-only
  `FHIR R4 RiskAssessment` projection, with exact Patient compartment mapping.
- `_revinclude=Provenance:target` returns only a unique persisted Provenance
  resource that actually targets the selected RiskAssessment.
- Unmapped, conflicting, invalid, or cross-subject RiskAssessment rows fail
  closed and are not returned.
- Conformance patients and their risks are excluded from normal FHIR searches.
  A certification environment must explicitly set
  `FHIR_INCLUDE_CONFORMANCE_FIXTURES=true` to expose them.
- A patient-scoped SMART launch requires both an explicit Patient and either a
  current active Practitioner-Patient care link or the dedicated
  `patients.launch_any_patient_smart_context` permission. Launch codes and
  access/refresh tokens retain that exact persisted context.
- Existing patient-scoped tokens that predate persisted SMART context are
  intentionally treated as inactive and must be re-authorized after rollout.

## Compliance evidence and limits

This gate provides repeatable evidence for the FHIR R4/USCDI-oriented data path,
traceable derived risk results, and per-input Provenance references relevant to
the ONC g(10) API program. It proves engineering reproducibility, not clinical
approval. Inferno and official ONC certification procedures remain separate
release gates.
