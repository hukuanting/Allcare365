# Source evidence archive

The raw files used during disease-risk model review are intentionally kept
outside Git:

- `docs/Examplar excel files/` contains third-party or collaboration-provided
  Excel, Word, PDF, PowerPoint, and image evidence.
- `data/.delivery-research-tsukuba/` contains confidential Sotera delivery
  instructions, scoped credentials, and research-session retrieval material.

These files are not required for the normal application, API, frontend, or
test suite. They must not be uploaded to a public repository without checking
ownership, licensing, data-use agreements, and institutional approval.

## What is committed

- `docs/risk_model_source_manifest.json` records the last inventory's file
  names, sizes, SHA-256 hashes, extraction status, and governance metadata.
- `services/disease_risk_engine/source_asset_inventory.py` provides the
  read-only inventory implementation.
- `scripts/build_risk_source_manifest.py` rebuilds the manifest when an
  authorized local archive is available.
- `services/disease_risk_engine/formula_catalog.py` is the canonical executable
  formula source. Evidence extraction never executes formulas from source
  documents.

## Rebuild the inventory locally

Place an authorized copy of the evidence files at
`docs/Examplar excel files/`, then run:

```powershell
.\.venv\Scripts\python.exe scripts\build_risk_source_manifest.py
```

The generated manifest is an inventory and review aid, not clinical approval.
Promotion of a model still requires primary-source verification, independent
test vectors, unit/applicability checks, and clinical-owner governance.

For Sotera research archives, use the controlled local workflow in
`docs/SOTERA_RESEARCH_IMPORT.md`. Keep credentials, ZIP files, partial
downloads, and raw measurements outside Git.
