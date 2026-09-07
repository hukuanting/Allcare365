# Sotera continuous physiological research import

This workflow is for a confidential, deidentified research delivery. It is
not enabled for the public demo deployment and is not a clinical diagnostic
workflow.

## Safety boundary

- Run against the local PostgreSQL database by default. A non-local commit is
  rejected unless `--allow-remote-database` is explicitly supplied after the
  data-use agreement and hosting controls have been reviewed.
- The source HID, session GUID, and device identifiers are one-way
  pseudonymized before persistence.
- AWS credentials, ZIP archives, and partial downloads are ignored by Git.
- Source-invalid numeric rows are counted in the quality report but are not
  inserted as clinical `Observation` rows.
- High-frequency waveform values remain in the Parquet archive. The current
  relational schema receives waveform coverage metadata, not the raw samples.

## Dependencies

The importer uses the pinned `pyarrow` dependency. The delivery download
helper uses the pinned `boto3` dependency.

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Download one pilot archive

The delivery helper reads only its adjacent scoped credential file and does
not modify the user's global AWS configuration.

```powershell
.\venv\Scripts\python.exe data\.delivery-research-tsukuba\download_zips.py
.\venv\Scripts\python.exe data\.delivery-research-tsukuba\download_zips.py SESSION_ID -d $env:TEMP\allcare365-sotera-pilot
```

## Inspect before writing

Dry-run is the default. It verifies ZIP CRC, computes SHA-256, validates the
schema, and reports aggregate numeric validity, waveform coverage, duplicate
timestamps, non-finite values, and calibration quality.

```powershell
.\venv\Scripts\python.exe manage.py import_sotera_session `
  $env:TEMP\allcare365-sotera-pilot\SESSION_ARCHIVE.zip
```

Use `--json` for a machine-readable aggregate report. The report does not
contain raw measurements or source identifiers.

## Commit to the local database

```powershell
.\venv\Scripts\python.exe manage.py import_sotera_session `
  $env:TEMP\allcare365-sotera-pilot\SESSION_ARCHIVE.zip `
  --commit
```

The command creates or records:

- one pseudonymous `Patient` and one device-monitoring `Encounter`;
- valid numeric vital-sign `Observation` rows using LOINC where the source
  semantics are unambiguous;
- device event `Observation` rows using the local Sotera code system;
- one coverage-metadata `Observation` per waveform signal;
- `DataImportBatch` and `DataImportRow` lineage keyed by archive SHA-256;
- a versioned `continuous_signal_quality` analysis job/result;
- a FHIR R4 quality-summary `Observation` and corresponding `Provenance`;
- import and analysis audit records.

The archive SHA-256 makes the operation idempotent. Re-running the same
archive reports `idempotent=True` and does not duplicate observations.

## Interpretation limits

`signal-quality-v1` is a deterministic technical quality analysis. It does
not infer disease risk and does not diagnose the monitored person. Existing
Allcare disease-risk algorithms require demographics, laboratory results,
history, and governed applicability checks that this device session does not
provide.

Importing all waveform values into ordinary PostgreSQL JSON or one row per
sample would be inefficient. Production-scale waveform support should retain
Parquet in controlled object storage and add a database index/catalog plus a
FHIR R4 `Observation.valueSampledData` or document-reference exchange layer,
with chunking, retention, authorization, and audit policy defined first.
