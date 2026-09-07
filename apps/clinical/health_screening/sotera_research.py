from __future__ import annotations

import hashlib
import json
import math
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone as datetime_timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import pandas as pd
from django.db import connection, transaction
from django.utils import timezone
from fhirclient.models.observation import Observation as FHIRObservation
from fhirclient.models.provenance import Provenance as FHIRProvenance

from apps.clinical.patients.models import Patient
from apps.integration.fhir_integration.models import (
    AuditLog,
    FHIRResource,
    FHIRResourceMapping,
)
from apps.integration.fhir_integration.resource_identity import identity

from .models import (
    AIAnalysisJob,
    AIAnalysisResult,
    DataImportBatch,
    DataImportRow,
    Encounter,
    Observation,
)


DATASET_NAME = "sotera_research_tsukuba"
SOURCE_TYPE = "sotera_research_parquet"
IMPORTER_VERSION = "1.0.0"
QUALITY_MODEL_NAME = "allcare-continuous-signal-quality"
QUALITY_MODEL_VERSION = "signal-quality-v1"
FHIR_ORIGIN_NAMESPACE = "allcare365:sotera-research-tsukuba"
LOCAL_CODE_SYSTEM = "https://allcare365.local/fhir/CodeSystem/sotera-signal"
QUALITY_METHOD_URI = (
    "https://allcare365.local/fhir/algorithm/continuous-signal-quality|1.0.0"
)
IDENTITY_NAMESPACE = uuid.UUID("d857a5e1-e8a6-4b2d-98e1-a1561e9dc4bb")


@dataclass(frozen=True)
class SignalSpec:
    observation_type: str
    code_system: str
    code: str
    display: str
    unit: str


NUMERIC_SIGNAL_SPECS = {
    "HR": SignalSpec("heart_rate", "http://loinc.org", "8867-4", "Heart rate", "{beats}/min"),
    "PR": SignalSpec(
        "pulse_rate",
        "http://loinc.org",
        "8889-8",
        "Heart rate by pulse oximetry",
        "{beats}/min",
    ),
    "RR": SignalSpec(
        "respiratory_rate",
        "http://loinc.org",
        "9279-1",
        "Respiratory rate",
        "{breaths}/min",
    ),
    "SPO2": SignalSpec(
        "oxygen_saturation",
        "http://loinc.org",
        "2708-6",
        "Oxygen saturation in arterial blood",
        "%",
    ),
    # The source describes a numeric skin temperature. LOINC 39106-0 is a
    # nominal skin-temperature finding, so retaining the vendor code avoids
    # falsely asserting a quantitative LOINC semantic.
    "TEMP": SignalSpec(
        "skin_temperature",
        LOCAL_CODE_SYSTEM,
        "TEMP",
        "Sotera skin temperature",
        "Cel",
    ),
    "BP_SYS": SignalSpec(
        "systolic_blood_pressure",
        "http://loinc.org",
        "8480-6",
        "Systolic blood pressure",
        "mm[Hg]",
    ),
    "BP_DIA": SignalSpec(
        "diastolic_blood_pressure",
        "http://loinc.org",
        "8462-4",
        "Diastolic blood pressure",
        "mm[Hg]",
    ),
    "BP_MAP": SignalSpec(
        "mean_blood_pressure",
        "http://loinc.org",
        "8478-0",
        "Mean blood pressure",
        "mm[Hg]",
    ),
    "CNIBP_SYS": SignalSpec(
        "continuous_noninvasive_systolic_blood_pressure",
        "http://loinc.org",
        "8480-6",
        "Continuous noninvasive systolic blood pressure",
        "mm[Hg]",
    ),
    "CNIBP_DIA": SignalSpec(
        "continuous_noninvasive_diastolic_blood_pressure",
        "http://loinc.org",
        "8462-4",
        "Continuous noninvasive diastolic blood pressure",
        "mm[Hg]",
    ),
    "CNIBP_MAP": SignalSpec(
        "continuous_noninvasive_mean_blood_pressure",
        "http://loinc.org",
        "8478-0",
        "Continuous noninvasive mean blood pressure",
        "mm[Hg]",
    ),
}


EVENT_SIGNAL_DISPLAYS = {
    "ALARM": "Sotera device alarm event",
    "LTAA": "Sotera long-term alarm annotation",
    "POSTURE": "Sotera posture event",
}


REQUIRED_ARCHIVE_MEMBERS = {
    "manifest.json",
    "numerics.parquet",
    "signal_coverage.parquet",
    "cal_events.parquet",
}


NUMERIC_REQUIRED_COLUMNS = {
    "unix_ts",
    "signal",
    "value",
    "label",
    "device_id",
    "is_event",
    "is_valid",
}


COVERAGE_REQUIRED_COLUMNS = {
    "signal",
    "n_samples",
    "n_channels",
    "fs_nominal",
    "n_segments",
    "covered_sec",
    "longest_segment_sec",
    "unix_ts_min",
    "unix_ts_max",
    "n_duplicate_ts",
    "n_nan",
    "n_inf",
    "parquet_bytes",
}


class SoteraResearchSessionService:
    """Inspect and import one confidential Sotera research session archive.

    The active Allcare schema can efficiently retain the low-rate numeric
    stream as relational Observation rows. High-frequency waveform samples
    remain in the source Parquet archive; only their coverage/segment summary
    is persisted here. Treating those summaries as the raw waveform would be
    misleading, so the distinction is explicit in every result.
    """

    def __init__(self, archive_path: Path | str, *, verify_crc: bool = True):
        self.archive_path = Path(archive_path).resolve()
        self.verify_crc = verify_crc
        self._loaded: Optional[Dict[str, Any]] = None
        self._report: Optional[Dict[str, Any]] = None

    def inspect(self) -> Dict[str, Any]:
        if self._report is None:
            self._loaded = self._load_archive()
            self._report = self._build_report(self._loaded)
        return self._report

    def run(
        self,
        *,
        commit: bool = False,
        actor_user=None,
        allow_remote_database: bool = False,
    ) -> Dict[str, Any]:
        report = self.inspect()
        response = {
            **report,
            "committed": False,
            "idempotent": False,
        }
        if not commit:
            return response

        self._assert_safe_database(allow_remote_database=allow_remote_database)
        return self._commit(
            report,
            self._loaded or {},
            actor_user=actor_user,
        )

    def _load_archive(self) -> Dict[str, Any]:
        if not self.archive_path.is_file():
            raise ValueError("Sotera session archive was not found")
        if not zipfile.is_zipfile(self.archive_path):
            raise ValueError("Sotera session archive is not a valid ZIP file")

        archive_sha256 = self._sha256(self.archive_path)
        with zipfile.ZipFile(self.archive_path) as archive:
            names = set(archive.namelist())
            missing = sorted(REQUIRED_ARCHIVE_MEMBERS - names)
            if missing:
                raise ValueError(
                    "Sotera archive is missing required member(s): " + ", ".join(missing)
                )

            bad_member = archive.testzip() if self.verify_crc else None
            if bad_member:
                raise ValueError("Sotera archive failed CRC validation")

            manifest = json.loads(archive.read("manifest.json"))
            numerics = pd.read_parquet(archive.open("numerics.parquet"))
            coverage = pd.read_parquet(archive.open("signal_coverage.parquet"))
            calibration = pd.read_parquet(archive.open("cal_events.parquet"))

        self._require_columns("numerics.parquet", numerics, NUMERIC_REQUIRED_COLUMNS)
        self._require_columns(
            "signal_coverage.parquet",
            coverage,
            COVERAGE_REQUIRED_COLUMNS,
        )
        if "quality_flag" not in calibration.columns or "has_waveform" not in calibration.columns:
            raise ValueError("cal_events.parquet is missing quality metadata")

        schema_version = self._as_int(manifest.get("schema_version"))
        if schema_version != 2:
            raise ValueError(f"Unsupported Sotera schema_version: {schema_version}")

        unix_start = self._as_int(manifest.get("unix_start"))
        unix_stop = self._as_int(manifest.get("unix_stop"))
        duration_sec = self._as_int(manifest.get("duration_sec"))
        if unix_start is None or unix_stop is None or unix_stop <= unix_start:
            raise ValueError("Sotera manifest contains an invalid session time range")
        if duration_sec is None or duration_sec <= 0:
            duration_sec = unix_stop - unix_start

        expected_waveforms = {
            f"waveforms/{signal}.parquet"
            for signal in coverage["signal"].dropna().astype(str)
        }
        missing_waveforms = sorted(expected_waveforms - names)
        if missing_waveforms:
            raise ValueError(
                "Sotera archive coverage references missing waveform member(s): "
                + ", ".join(missing_waveforms)
            )

        source_token = "|".join(
            str(manifest.get(key) or "") for key in ("hid", "session_guid")
        )
        if not source_token.strip("|"):
            raise ValueError("Sotera manifest has no stable source identity")
        source_identity_hash = hashlib.sha256(
            f"{DATASET_NAME}|{source_token}".encode("utf-8")
        ).hexdigest()

        return {
            "archive_sha256": archive_sha256,
            "crc_verified": self.verify_crc,
            "manifest": manifest,
            "numerics": numerics,
            "coverage": coverage,
            "calibration": calibration,
            "source_identity_hash": source_identity_hash,
            "schema_version": schema_version,
            "unix_start": unix_start,
            "unix_stop": unix_stop,
            "duration_sec": duration_sec,
        }

    def _build_report(self, loaded: Dict[str, Any]) -> Dict[str, Any]:
        numerics = loaded["numerics"]
        coverage = loaded["coverage"]
        calibration = loaded["calibration"]
        duration_sec = loaded["duration_sec"]

        numeric_signals: Dict[str, Dict[str, Any]] = {}
        planned_numeric_observations = 0
        excluded_numeric_rows = 0
        for signal_value, group in numerics.groupby("signal", dropna=False, sort=True):
            signal = str(signal_value)
            event_mask = group["is_event"].fillna(False).astype(bool)
            valid_mask = (
                group["is_valid"].fillna(False).astype(bool)
                & group["value"].notna()
                & ~event_mask
            )
            importable_event_mask = event_mask & signal_value_not_missing(group["label"], group["value"])
            values = pd.to_numeric(group.loc[valid_mask, "value"], errors="coerce").dropna()
            mapped = signal in NUMERIC_SIGNAL_SPECS or signal in EVENT_SIGNAL_DISPLAYS
            importable_rows = (
                int(valid_mask.sum()) if signal in NUMERIC_SIGNAL_SPECS else 0
            ) + (
                int(importable_event_mask.sum()) if signal in EVENT_SIGNAL_DISPLAYS else 0
            )
            planned_numeric_observations += importable_rows
            excluded_numeric_rows += len(group) - importable_rows
            numeric_signals[signal] = {
                "rows": int(len(group)),
                "valid_rows": int(valid_mask.sum()),
                "event_rows": int(event_mask.sum()),
                "importable_rows": importable_rows,
                "excluded_rows": int(len(group) - importable_rows),
                "mapped": mapped,
                "unit": self._signal_unit(signal, loaded["manifest"]),
                "valid_pct": self._round(100.0 * valid_mask.sum() / len(group), 2),
                "min": self._series_stat(values, "min"),
                "median": self._series_stat(values, "median"),
                "mean": self._series_stat(values, "mean"),
                "max": self._series_stat(values, "max"),
            }

        waveform_signals = []
        for row in coverage.sort_values("signal").itertuples(index=False):
            covered_sec = self._as_float(row.covered_sec) or 0.0
            waveform_signals.append(
                {
                    "signal": str(row.signal),
                    "n_samples": self._as_int(row.n_samples) or 0,
                    "n_channels": self._as_int(row.n_channels) or 0,
                    "fs_nominal_hz": self._round(self._as_float(row.fs_nominal), 4),
                    "n_segments": self._as_int(row.n_segments) or 0,
                    "covered_sec": self._round(covered_sec, 3),
                    "coverage_pct": self._round(100.0 * covered_sec / duration_sec, 2),
                    "longest_segment_sec": self._round(
                        self._as_float(row.longest_segment_sec),
                        3,
                    ),
                    "n_duplicate_ts": self._as_int(row.n_duplicate_ts) or 0,
                    "n_nan": self._as_int(row.n_nan) or 0,
                    "n_inf": self._as_int(row.n_inf) or 0,
                    "parquet_bytes": self._as_int(row.parquet_bytes) or 0,
                }
            )

        continuous_waveforms = [
            item for item in waveform_signals if item["signal"] != "BP_PRES"
        ]
        coverage_values = [
            float(item["coverage_pct"])
            for item in continuous_waveforms
            if item["coverage_pct"] is not None
        ]
        calibration_counts = {
            str(key): int(value)
            for key, value in calibration["quality_flag"]
            .fillna("missing")
            .value_counts()
            .sort_index()
            .items()
        }
        calibration_with_waveform = int(
            calibration["has_waveform"].fillna(False).astype(bool).sum()
        )

        quality_findings = []
        low_validity = {
            signal: details["valid_pct"]
            for signal, details in numeric_signals.items()
            if signal in NUMERIC_SIGNAL_SPECS
            and details["rows"]
            and details["valid_pct"] is not None
            and float(details["valid_pct"]) < 90.0
        }
        if low_validity:
            quality_findings.append(
                {
                    "code": "numeric_validity_below_90_pct",
                    "signals": low_validity,
                }
            )
        if coverage_values and min(coverage_values) < 80.0:
            quality_findings.append(
                {
                    "code": "continuous_waveform_coverage_below_80_pct",
                    "minimum_coverage_pct": self._round(min(coverage_values), 2),
                }
            )
        duplicate_count = sum(item["n_duplicate_ts"] for item in waveform_signals)
        if duplicate_count:
            quality_findings.append(
                {
                    "code": "duplicate_waveform_timestamps",
                    "count": duplicate_count,
                }
            )
        nonfinite_count = sum(
            item["n_nan"] + item["n_inf"] for item in waveform_signals
        )
        if nonfinite_count:
            quality_findings.append(
                {
                    "code": "nonfinite_waveform_values",
                    "count": nonfinite_count,
                }
            )
        if calibration_counts.get("poor", 0):
            quality_findings.append(
                {
                    "code": "poor_calibration_event",
                    "count": calibration_counts["poor"],
                }
            )

        quality_status = "complete" if not quality_findings else "partial_coverage"
        session_start = self._utc_datetime(loaded["unix_start"])
        session_stop = self._utc_datetime(loaded["unix_stop"])
        waveform_observations = len(waveform_signals)
        report = {
            "dataset": DATASET_NAME,
            "importer_version": IMPORTER_VERSION,
            "quality_model_version": QUALITY_MODEL_VERSION,
            "source": {
                "session_pseudonym": "session-" + loaded["source_identity_hash"][:12],
                "source_identity_sha256": loaded["source_identity_hash"],
                "archive_sha256": loaded["archive_sha256"],
                "schema_version": loaded["schema_version"],
                "manifest_status": str(loaded["manifest"].get("status") or ""),
                "crc_verified": bool(loaded["crc_verified"]),
            },
            "session": {
                "start_utc": session_start.isoformat(),
                "stop_utc": session_stop.isoformat(),
                "duration_sec": duration_sec,
                "duration_hours": self._round(duration_sec / 3600.0, 3),
            },
            "numeric_summary": {
                "source_rows": int(len(numerics)),
                "planned_observations": planned_numeric_observations,
                "excluded_rows": excluded_numeric_rows,
                "signals": numeric_signals,
            },
            "waveform_summary": {
                "raw_samples": int(sum(item["n_samples"] for item in waveform_signals)),
                "signals": waveform_signals,
                "continuous_signal_coverage_pct": {
                    "min": self._round(min(coverage_values), 2) if coverage_values else None,
                    "median": self._round(float(pd.Series(coverage_values).median()), 2)
                    if coverage_values
                    else None,
                    "max": self._round(max(coverage_values), 2) if coverage_values else None,
                },
                "raw_waveforms_imported": False,
                "metadata_observations_planned": waveform_observations,
            },
            "calibration_summary": {
                "events": int(len(calibration)),
                "quality_counts": calibration_counts,
                "events_with_waveform": calibration_with_waveform,
            },
            "quality": {
                "status": quality_status,
                "findings": quality_findings,
                "scope": "technical_data_quality_only",
            },
            "planned_database_observations": (
                planned_numeric_observations + waveform_observations
            ),
            "limitations": [
                "The high-frequency waveform values remain in the source Parquet archive; only coverage metadata is imported.",
                "Rows marked invalid by the source are summarized but excluded from clinical Observation records.",
                "This report is technical data-quality analysis, not disease-risk estimation or diagnosis.",
            ],
        }
        return report

    @transaction.atomic
    def _commit(
        self,
        report: Dict[str, Any],
        loaded: Dict[str, Any],
        *,
        actor_user=None,
    ) -> Dict[str, Any]:
        source_hash = loaded["source_identity_hash"]
        archive_hash = loaded["archive_sha256"]
        batch_id = uuid.uuid5(IDENTITY_NAMESPACE, f"batch:{archive_hash}")
        existing_batch = DataImportBatch.objects.select_for_update().filter(id=batch_id).first()
        if existing_batch is not None:
            patient = Patient.objects.filter(
                source_system=DATASET_NAME,
                source_record_id=source_hash,
            ).first()
            encounter = Encounter.objects.filter(
                id=uuid.uuid5(IDENTITY_NAMESPACE, f"encounter:{source_hash}")
            ).first()
            analysis_job = AIAnalysisJob.objects.filter(
                id=uuid.uuid5(IDENTITY_NAMESPACE, f"quality-job:{archive_hash}")
            ).first()
            return {
                **report,
                "committed": True,
                "idempotent": True,
                "batch_id": str(existing_batch.id),
                "patient_id": str(patient.id) if patient else None,
                "encounter_id": str(encounter.id) if encounter else None,
                "analysis_job_id": str(analysis_job.id) if analysis_job else None,
                "imported_observations": int(existing_batch.success_rows),
            }

        actor = actor_user if getattr(actor_user, "is_authenticated", False) else None
        now = timezone.now()
        patient_id = uuid.uuid5(IDENTITY_NAMESPACE, f"patient:{source_hash}")
        patient, patient_created = Patient.objects.select_for_update().get_or_create(
            id=patient_id,
            defaults={
                "first_name": report["source"]["session_pseudonym"],
                "last_name": "Sotera Research",
                "medical_record_number": "SOTERA-" + source_hash[:16].upper(),
                "status": "research",
                "source_system": DATASET_NAME,
                "source_record_id": source_hash,
                "last_imported_at": now,
                "metadata_json": {
                    "deidentified_research_record": True,
                    "pseudonymization": "sha256-hid-session-guid-v1",
                    "dataset": DATASET_NAME,
                },
                "created_by": actor,
                "updated_by": actor,
            },
        )
        if not patient_created and (
            patient.source_system != DATASET_NAME
            or patient.source_record_id != source_hash
        ):
            raise ValueError("Deterministic research patient identity is owned by another source")

        encounter_id = uuid.uuid5(IDENTITY_NAMESPACE, f"encounter:{source_hash}")
        encounter, encounter_created = Encounter.objects.select_for_update().get_or_create(
            id=encounter_id,
            defaults={
                "patient": patient,
                "encounter_type": "research_device_monitoring",
                "status": "finished",
                "reason": "Sotera continuous physiological monitoring research session",
                "location": "deidentified research site",
                "started_at": self._utc_datetime(loaded["unix_start"]),
                "ended_at": self._utc_datetime(loaded["unix_stop"]),
                "source_type": SOURCE_TYPE,
                "metadata_json": {
                    "archive_sha256": archive_hash,
                    "source_identity_sha256": source_hash,
                    "schema_version": loaded["schema_version"],
                    "duration_sec": loaded["duration_sec"],
                },
                "created_by": actor,
                "updated_by": actor,
            },
        )
        if not encounter_created and encounter.patient_id != patient.id:
            raise ValueError("Deterministic research encounter is owned by another patient")

        total_source_rows = len(loaded["numerics"]) + len(loaded["coverage"])
        batch = DataImportBatch.objects.create(
            id=batch_id,
            created_by_user=actor,
            source_type=SOURCE_TYPE,
            original_filename="sotera-" + archive_hash[:12] + ".zip",
            status="processing",
            total_rows=total_source_rows,
            processed_rows=0,
            success_rows=0,
            failed_rows=0,
            started_at=now,
            import_options_json={
                "archive_sha256": archive_hash,
                "source_identity_sha256": source_hash,
                "schema_version": loaded["schema_version"],
                "importer_version": IMPORTER_VERSION,
                "raw_waveforms_imported": False,
            },
            summary_json={},
            created_by=actor,
            updated_by=actor,
        )

        numeric_count = self._create_numeric_observations(
            loaded["numerics"],
            patient=patient,
            encounter=encounter,
            source_hash=source_hash,
            archive_hash=archive_hash,
            actor=actor,
        )
        waveform_metadata_count = self._create_waveform_metadata_observations(
            loaded["coverage"],
            patient=patient,
            encounter=encounter,
            source_hash=source_hash,
            archive_hash=archive_hash,
            duration_sec=loaded["duration_sec"],
            actor=actor,
        )
        imported_count = numeric_count + waveform_metadata_count

        DataImportRow.objects.bulk_create(
            [
                DataImportRow(
                    batch=batch,
                    patient=patient,
                    row_number=1,
                    status="completed",
                    target_table="observations",
                    raw_json={
                        "member": "numerics.parquet",
                        "archive_sha256": archive_hash,
                    },
                    normalized_json=report["numeric_summary"],
                ),
                DataImportRow(
                    batch=batch,
                    patient=patient,
                    row_number=2,
                    status="completed",
                    target_table="observations",
                    raw_json={
                        "member": "signal_coverage.parquet",
                        "archive_sha256": archive_hash,
                    },
                    normalized_json=report["waveform_summary"],
                ),
                DataImportRow(
                    batch=batch,
                    patient=patient,
                    row_number=3,
                    status="completed",
                    target_table="ai_analysis_results",
                    raw_json={
                        "member": "cal_events.parquet",
                        "archive_sha256": archive_hash,
                    },
                    normalized_json=report["calibration_summary"],
                ),
            ],
            batch_size=3,
        )

        analysis_job, analysis_result = self._persist_analysis(
            report,
            patient=patient,
            encounter=encounter,
            archive_hash=archive_hash,
            actor=actor,
        )
        self._persist_fhir_analysis(
            report,
            patient=patient,
            analysis_result=analysis_result,
            archive_hash=archive_hash,
        )

        batch.status = "completed"
        batch.processed_rows = total_source_rows
        batch.success_rows = imported_count
        batch.failed_rows = 0
        batch.completed_at = timezone.now()
        batch.summary_json = {
            **report,
            "imported_numeric_observations": numeric_count,
            "imported_waveform_metadata_observations": waveform_metadata_count,
            "analysis_job_id": str(analysis_job.id),
        }
        batch.save(
            update_fields=[
                "status",
                "processed_rows",
                "success_rows",
                "failed_rows",
                "completed_at",
                "summary_json",
                "updated_at",
            ]
        )

        AuditLog.objects.create(
            actor_user=actor,
            patient=patient,
            action="research_session_import",
            target_table="data_import_batches",
            target_id=batch.id,
            metadata_json={
                "dataset": DATASET_NAME,
                "archive_sha256": archive_hash,
                "importer_version": IMPORTER_VERSION,
                "observation_count": imported_count,
                "raw_waveforms_imported": False,
            },
        )
        AuditLog.objects.create(
            actor_user=actor,
            patient=patient,
            action="signal_quality_analyze",
            target_table="ai_analysis_jobs",
            target_id=analysis_job.id,
            metadata_json={
                "model_name": QUALITY_MODEL_NAME,
                "model_version": QUALITY_MODEL_VERSION,
                "quality_status": report["quality"]["status"],
                "analysis_result_id": str(analysis_result.id),
            },
        )

        return {
            **report,
            "committed": True,
            "idempotent": False,
            "batch_id": str(batch.id),
            "patient_id": str(patient.id),
            "encounter_id": str(encounter.id),
            "analysis_job_id": str(analysis_job.id),
            "analysis_result_id": str(analysis_result.id),
            "imported_observations": imported_count,
            "imported_numeric_observations": numeric_count,
            "imported_waveform_metadata_observations": waveform_metadata_count,
        }

    def _create_numeric_observations(
        self,
        frame: pd.DataFrame,
        *,
        patient: Patient,
        encounter: Encounter,
        source_hash: str,
        archive_hash: str,
        actor,
    ) -> int:
        created = 0
        batch_size = 2000
        objects = []
        for row in frame.itertuples(index=True):
            signal = str(row.signal)
            is_event = bool(row.is_event) if not pd.isna(row.is_event) else False
            is_valid = bool(row.is_valid) if not pd.isna(row.is_valid) else False
            effective_at = self._utc_datetime(row.unix_ts)
            device_pseudonym = self._device_pseudonym(source_hash, row.device_id)
            source_payload = {
                "dataset": DATASET_NAME,
                "archive_sha256": archive_hash,
                "source_row": int(row.Index),
                "signal": signal,
                "device_pseudonym": device_pseudonym,
            }
            observation_id = uuid.uuid5(
                IDENTITY_NAMESPACE,
                f"numeric:{source_hash}:{int(row.Index)}",
            )

            if is_event and signal in EVENT_SIGNAL_DISPLAYS:
                label = self._event_label(row.label, row.value)
                if not label:
                    continue
                objects.append(
                    Observation(
                        id=observation_id,
                        patient=patient,
                        encounter=encounter,
                        observation_type="device_event",
                        category="activity",
                        source_type=SOURCE_TYPE + "_event",
                        code_system=LOCAL_CODE_SYSTEM,
                        code=signal,
                        display=EVENT_SIGNAL_DISPLAYS[signal],
                        value_string=label[:500],
                        status="final",
                        effective_at=effective_at,
                        issued_at=effective_at,
                        device_identifier=device_pseudonym,
                        source_payload_json=source_payload,
                        created_by=actor,
                        updated_by=actor,
                    )
                )
            elif is_valid and signal in NUMERIC_SIGNAL_SPECS and not pd.isna(row.value):
                spec = NUMERIC_SIGNAL_SPECS[signal]
                source_payload["source_quality_valid"] = True
                objects.append(
                    Observation(
                        id=observation_id,
                        patient=patient,
                        encounter=encounter,
                        observation_type=spec.observation_type,
                        category="vital-signs",
                        source_type=SOURCE_TYPE + "_numeric",
                        code_system=spec.code_system,
                        code=spec.code,
                        display=spec.display,
                        value_quantity=self._decimal(row.value),
                        value_unit=spec.unit,
                        status="final",
                        effective_at=effective_at,
                        issued_at=effective_at,
                        device_identifier=device_pseudonym,
                        source_payload_json=source_payload,
                        created_by=actor,
                        updated_by=actor,
                    )
                )
            else:
                continue

            if len(objects) >= batch_size:
                Observation.objects.bulk_create(objects, batch_size=batch_size)
                created += len(objects)
                objects = []

        if objects:
            Observation.objects.bulk_create(objects, batch_size=batch_size)
            created += len(objects)
        return created

    def _create_waveform_metadata_observations(
        self,
        frame: pd.DataFrame,
        *,
        patient: Patient,
        encounter: Encounter,
        source_hash: str,
        archive_hash: str,
        duration_sec: int,
        actor,
    ) -> int:
        objects = []
        for row in frame.sort_values("signal").itertuples(index=False):
            signal = str(row.signal)
            covered_sec = self._as_float(row.covered_sec) or 0.0
            coverage_pct = 100.0 * covered_sec / duration_sec
            effective_at = self._utc_datetime(row.unix_ts_min)
            issued_at = self._utc_datetime(row.unix_ts_max)
            objects.append(
                Observation(
                    id=uuid.uuid5(
                        IDENTITY_NAMESPACE,
                        f"waveform-metadata:{source_hash}:{signal}",
                    ),
                    patient=patient,
                    encounter=encounter,
                    observation_type="waveform_coverage",
                    category="activity",
                    source_type=SOURCE_TYPE + "_waveform_metadata",
                    code_system=LOCAL_CODE_SYSTEM,
                    code=f"{signal}-coverage",
                    display=f"{signal} waveform coverage",
                    value_quantity=self._decimal(covered_sec),
                    value_unit="s",
                    value_json={
                        "signal": signal,
                        "n_samples": self._as_int(row.n_samples) or 0,
                        "n_channels": self._as_int(row.n_channels) or 0,
                        "fs_nominal_hz": self._as_float(row.fs_nominal),
                        "n_segments": self._as_int(row.n_segments) or 0,
                        "coverage_pct": self._round(coverage_pct, 2),
                        "longest_segment_sec": self._as_float(row.longest_segment_sec),
                        "n_duplicate_ts": self._as_int(row.n_duplicate_ts) or 0,
                        "n_nan": self._as_int(row.n_nan) or 0,
                        "n_inf": self._as_int(row.n_inf) or 0,
                        "raw_waveform_imported": False,
                    },
                    status="final",
                    effective_at=effective_at,
                    issued_at=issued_at,
                    source_payload_json={
                        "dataset": DATASET_NAME,
                        "archive_sha256": archive_hash,
                        "member": f"waveforms/{signal}.parquet",
                    },
                    created_by=actor,
                    updated_by=actor,
                )
            )
        Observation.objects.bulk_create(objects, batch_size=100)
        return len(objects)

    def _persist_analysis(
        self,
        report: Dict[str, Any],
        *,
        patient: Patient,
        encounter: Encounter,
        archive_hash: str,
        actor,
    ) -> tuple[AIAnalysisJob, AIAnalysisResult]:
        job = AIAnalysisJob.objects.create(
            id=uuid.uuid5(IDENTITY_NAMESPACE, f"quality-job:{archive_hash}"),
            patient=patient,
            requested_by_user=actor,
            encounter=encounter,
            job_type="continuous_signal_quality",
            status="completed",
            model_name=QUALITY_MODEL_NAME,
            model_version=QUALITY_MODEL_VERSION,
            input_json={
                "dataset": DATASET_NAME,
                "archive_sha256": archive_hash,
                "schema_version": report["source"]["schema_version"],
                "source_rows": report["numeric_summary"]["source_rows"],
                "waveform_samples": report["waveform_summary"]["raw_samples"],
                "method_uri": QUALITY_METHOD_URI,
            },
            started_at=timezone.now(),
            completed_at=timezone.now(),
            created_by=actor,
            updated_by=actor,
        )
        result = AIAnalysisResult.objects.create(
            id=uuid.uuid5(IDENTITY_NAMESPACE, f"quality-result:{archive_hash}"),
            job=job,
            patient=patient,
            result_type="continuous_signal_quality",
            model_version=QUALITY_MODEL_VERSION,
            confidence_score=None,
            risk_level="",
            result_json=report,
            explanation_json={
                "method_uri": QUALITY_METHOD_URI,
                "scope": "technical_data_quality_only",
                "source_flags_used": ["is_valid", "is_event"],
                "waveform_metrics_used": [
                    "coverage",
                    "segments",
                    "duplicates",
                    "nan",
                    "inf",
                ],
                "raw_waveforms_imported": False,
            },
            recommendation_text=(
                "Technical quality result only; review waveform gaps, source-invalid rows, "
                "and calibration quality before research analysis. Not for diagnosis."
            ),
            requires_doctor_review=False,
            created_by=actor,
            updated_by=actor,
        )
        return job, result

    def _persist_fhir_analysis(
        self,
        report: Dict[str, Any],
        *,
        patient: Patient,
        analysis_result: AIAnalysisResult,
        archive_hash: str,
    ) -> None:
        result_token = str(analysis_result.id).replace("-", "")[:24]
        observation_id = f"signal-quality-{result_token}"
        patient_fhir_id = identity.patient_id(patient)
        coverage = report["waveform_summary"]["continuous_signal_coverage_pct"]
        fhir_json = {
            "resourceType": "Observation",
            "id": observation_id,
            "status": "final",
            "code": {
                "coding": [
                    {
                        "system": LOCAL_CODE_SYSTEM,
                        "code": "continuous-signal-quality",
                        "display": "Continuous physiological signal quality",
                    }
                ],
                "text": "Continuous physiological signal quality",
            },
            "subject": {"reference": f"Patient/{patient_fhir_id}"},
            "effectivePeriod": {
                "start": report["session"]["start_utc"],
                "end": report["session"]["stop_utc"],
            },
            "issued": timezone.now().isoformat(),
            "valueCodeableConcept": {
                "coding": [
                    {
                        "system": LOCAL_CODE_SYSTEM,
                        "code": report["quality"]["status"],
                    }
                ],
                "text": report["quality"]["status"],
            },
            "method": {
                "coding": [
                    {
                        "system": "https://allcare365.local/fhir/CodeSystem/analysis-method",
                        "code": QUALITY_MODEL_VERSION,
                        "display": "Allcare continuous signal quality analysis",
                    }
                ]
            },
            "component": [
                self._fhir_quantity_component(
                    "importable-numeric-observations",
                    "Importable numeric observations",
                    report["numeric_summary"]["planned_observations"],
                    "{count}",
                ),
                self._fhir_quantity_component(
                    "raw-waveform-samples",
                    "Raw waveform samples in source archive",
                    report["waveform_summary"]["raw_samples"],
                    "{count}",
                ),
                self._fhir_quantity_component(
                    "median-waveform-coverage",
                    "Median continuous waveform coverage",
                    coverage["median"],
                    "%",
                ),
            ],
            "note": [
                {
                    "text": (
                        "Technical data-quality summary only. Raw waveform values remain in "
                        "the source Parquet archive and this result is not a diagnosis."
                    )
                }
            ],
        }
        FHIRObservation(fhir_json, strict=True)
        observation_resource = self._upsert_owned_fhir_resource(
            resource_type="Observation",
            resource_id=observation_id,
            resource_data=fhir_json,
        )
        FHIRResourceMapping.objects.update_or_create(
            local_table="ai_analysis_results",
            local_id=analysis_result.id,
            fhir_resource_type="Observation",
            defaults={
                "patient": patient,
                "fhir_resource_ref": observation_resource,
                "fhir_resource_id": observation_id,
                "profile_url": "http://hl7.org/fhir/StructureDefinition/Observation",
                "fhir_json": fhir_json,
                "sync_status": "mapped",
                "last_synced_at": timezone.now(),
                "metadata_json": {
                    "model_version": QUALITY_MODEL_VERSION,
                    "method_uri": QUALITY_METHOD_URI,
                    "archive_sha256": archive_hash,
                },
            },
        )

        provenance_id = f"provenance-{observation_id}"
        provenance_json = {
            "resourceType": "Provenance",
            "id": provenance_id,
            "target": [{"reference": f"Observation/{observation_id}"}],
            "recorded": timezone.now().isoformat(),
            "policy": [QUALITY_METHOD_URI],
            "activity": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v3-DataOperation",
                        "code": "CREATE",
                        "display": "create",
                    }
                ],
                "text": "Deterministic continuous signal quality analysis",
            },
            "agent": [
                {
                    "type": {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/provenance-participant-type",
                                "code": "assembler",
                                "display": "Assembler",
                            }
                        ]
                    },
                    "who": {"display": f"{QUALITY_MODEL_NAME} {QUALITY_MODEL_VERSION}"},
                }
            ],
            "entity": [
                {
                    "role": "source",
                    "what": {
                        "identifier": {
                            "system": "urn:ietf:rfc:3986",
                            "value": f"urn:sha256:{archive_hash}",
                        },
                        "display": "Confidential Sotera research session archive",
                    },
                }
            ],
        }
        FHIRProvenance(provenance_json, strict=True)
        provenance_resource = self._upsert_owned_fhir_resource(
            resource_type="Provenance",
            resource_id=provenance_id,
            resource_data=provenance_json,
        )
        FHIRResourceMapping.objects.update_or_create(
            local_table="ai_analysis_results",
            local_id=analysis_result.id,
            fhir_resource_type="Provenance",
            defaults={
                "patient": patient,
                "fhir_resource_ref": provenance_resource,
                "fhir_resource_id": provenance_id,
                "profile_url": "http://hl7.org/fhir/StructureDefinition/Provenance",
                "fhir_json": provenance_json,
                "sync_status": "mapped",
                "last_synced_at": timezone.now(),
                "metadata_json": {
                    "target": f"Observation/{observation_id}",
                    "model_version": QUALITY_MODEL_VERSION,
                },
            },
        )

    def _upsert_owned_fhir_resource(
        self,
        *,
        resource_type: str,
        resource_id: str,
        resource_data: Dict[str, Any],
    ) -> FHIRResource:
        resource, created = FHIRResource.objects.select_for_update().get_or_create(
            resource_type=resource_type,
            resource_id=resource_id,
            defaults={
                "origin_namespace": FHIR_ORIGIN_NAMESPACE,
                "resource_data": resource_data,
            },
        )
        if not created:
            if resource.origin_namespace != FHIR_ORIGIN_NAMESPACE:
                raise ValueError(
                    f"FHIR {resource_type}/{resource_id} is owned by another source"
                )
            resource.resource_data = resource_data
            resource.save(update_fields=["resource_data", "last_updated"])
        return resource

    def _assert_safe_database(self, *, allow_remote_database: bool) -> None:
        host = str(connection.settings_dict.get("HOST") or "").strip().lower()
        local_hosts = {"", "localhost", "127.0.0.1", "::1"}
        if host not in local_hosts and not allow_remote_database:
            raise ValueError(
                "Refusing to import confidential research data into a non-local database; "
                "pass allow_remote_database only after confirming the DUA and hosting controls"
            )
        connection.ensure_connection()

    @staticmethod
    def _require_columns(name: str, frame: pd.DataFrame, required: Iterable[str]) -> None:
        missing = sorted(set(required) - set(frame.columns))
        if missing:
            raise ValueError(f"{name} is missing column(s): {', '.join(missing)}")

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(8 * 1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _utc_datetime(value: Any) -> datetime:
        numeric = float(value)
        if not math.isfinite(numeric):
            raise ValueError("Sotera timestamp is not finite")
        return datetime.fromtimestamp(numeric, tz=datetime_timezone.utc)

    @staticmethod
    def _as_int(value: Any) -> Optional[int]:
        if value is None or pd.isna(value):
            return None
        return int(value)

    @staticmethod
    def _as_float(value: Any) -> Optional[float]:
        if value is None or pd.isna(value):
            return None
        numeric = float(value)
        return numeric if math.isfinite(numeric) else None

    @staticmethod
    def _round(value: Optional[float], places: int) -> Optional[float]:
        if value is None or not math.isfinite(float(value)):
            return None
        return round(float(value), places)

    def _series_stat(self, values: pd.Series, operation: str) -> Optional[float]:
        if values.empty:
            return None
        result = getattr(values, operation)()
        return self._round(self._as_float(result), 4)

    @staticmethod
    def _decimal(value: Any) -> Decimal:
        return Decimal(str(float(value))).quantize(
            Decimal("0.0001"),
            rounding=ROUND_HALF_UP,
        )

    @staticmethod
    def _event_label(label: Any, value: Any) -> str:
        if label is not None and not pd.isna(label) and str(label).strip():
            return str(label).strip()
        if value is not None and not pd.isna(value):
            return str(value).strip()
        return ""

    @staticmethod
    def _device_pseudonym(source_hash: str, device_id: Any) -> str:
        if device_id is None or pd.isna(device_id):
            return ""
        digest = hashlib.sha256(
            f"{source_hash}|device|{int(device_id)}".encode("utf-8")
        ).hexdigest()
        return "device-" + digest[:20]

    @staticmethod
    def _signal_unit(signal: str, manifest: Dict[str, Any]) -> str:
        if signal in NUMERIC_SIGNAL_SPECS:
            return NUMERIC_SIGNAL_SPECS[signal].unit
        base_signal = signal.split("_", 1)[0]
        units = manifest.get("units") if isinstance(manifest.get("units"), dict) else {}
        return str(units.get(signal) or units.get(base_signal) or "")

    @staticmethod
    def _fhir_quantity_component(
        code: str,
        display: str,
        value: Any,
        unit: str,
    ) -> Dict[str, Any]:
        return {
            "code": {
                "coding": [
                    {
                        "system": LOCAL_CODE_SYSTEM,
                        "code": code,
                        "display": display,
                    }
                ]
            },
            "valueQuantity": {
                "value": value,
                "unit": unit,
                "system": "http://unitsofmeasure.org",
                "code": unit,
            },
        }


def signal_value_not_missing(labels: pd.Series, values: pd.Series) -> pd.Series:
    """Return a bool mask without treating zero-valued event codes as missing."""

    label_present = labels.notna() & labels.astype(str).str.strip().ne("")
    return label_present | values.notna()
