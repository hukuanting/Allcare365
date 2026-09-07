from __future__ import annotations

from typing import Any, Dict, Iterable

from django.db.models import Q

from apps.integration.fhir_integration.models import FHIRResourceMapping

from .models import AIAnalysisJob, AIAnalysisResult, DataImportBatch, Observation
from .sotera_research import DATASET_NAME, SOURCE_TYPE


class SoteraResearchReportService:
    """Build a deidentified, aggregate dashboard payload from persisted results."""

    NUMERIC_ORDER = ("HR", "SPO2", "RR", "CNIBP_SYS", "CNIBP_DIA", "TEMP", "PR")
    WAVEFORM_ORDER = ("SCG", "ECG_II", "IR_PPG", "RED_PPG", "ACC_ECG", "IP")
    AO_JOB_TYPES = ("aortic_opening_detection", "ao_detection")
    AO_OBSERVATION_TYPES = ("aortic_opening", "aortic_opening_timing", "pre_ejection_period")
    AO_CODES = ("aortic-opening", "aortic-opening-time", "ao-timing")

    def latest(self) -> Dict[str, Any]:
        analysis_result = (
            AIAnalysisResult.objects.filter(
                result_type="continuous_signal_quality",
                job__model_name="allcare-continuous-signal-quality",
            )
            .select_related("job", "patient")
            .order_by("-created_at")
            .first()
        )
        if analysis_result is None:
            return {
                "available": False,
                "dataset": DATASET_NAME,
                "message": "No imported Sotera research session is available.",
            }

        report = analysis_result.result_json if isinstance(analysis_result.result_json, dict) else {}
        patient_id = analysis_result.patient_id
        batches = DataImportBatch.objects.filter(source_type=SOURCE_TYPE).order_by(
            "-completed_at", "-created_at"
        )
        batch = next(
            (
                candidate
                for candidate in batches
                if str(candidate.summary_json.get("analysis_job_id", ""))
                == str(analysis_result.job_id)
            ),
            batches.first(),
        )
        source_observations = Observation.objects.filter(
            patient_id=patient_id,
            source_type__startswith=SOURCE_TYPE,
        )
        ao_jobs = AIAnalysisJob.objects.filter(
            patient_id=patient_id,
            job_type__in=self.AO_JOB_TYPES,
        ).count()
        ao_outputs = Observation.objects.filter(patient_id=patient_id).filter(
            Q(observation_type__in=self.AO_OBSERVATION_TYPES) | Q(code__in=self.AO_CODES)
        ).count()
        ground_truth_records = Observation.objects.filter(
            patient_id=patient_id,
            source_type__icontains="ground_truth",
        ).filter(
            Q(observation_type__in=self.AO_OBSERVATION_TYPES) | Q(code__in=self.AO_CODES)
        ).count()

        fhir_mappings = list(
            FHIRResourceMapping.objects.filter(
                local_table="ai_analysis_results",
                local_id=analysis_result.id,
            ).order_by("fhir_resource_type")
        )
        numeric_signals = report.get("numeric_summary", {}).get("signals", {})
        waveform_signals = {
            item.get("signal"): item
            for item in report.get("waveform_summary", {}).get("signals", [])
            if isinstance(item, dict) and item.get("signal")
        }

        return {
            "available": True,
            "dataset": report.get("dataset") or DATASET_NAME,
            "generated_at": analysis_result.created_at.isoformat(),
            "source": {
                "session_pseudonym": report.get("source", {}).get("session_pseudonym"),
                "schema_version": report.get("source", {}).get("schema_version"),
                "crc_verified": bool(report.get("source", {}).get("crc_verified")),
            },
            "session": report.get("session", {}),
            "import": {
                "status": batch.status if batch else "unknown",
                "batch_id": str(batch.id) if batch else None,
                "source_numeric_rows": report.get("numeric_summary", {}).get("source_rows", 0),
                "excluded_numeric_rows": report.get("numeric_summary", {}).get("excluded_rows", 0),
                "database_observations": source_observations.count(),
                "raw_waveform_samples": report.get("waveform_summary", {}).get("raw_samples", 0),
                "raw_waveforms_imported": bool(
                    report.get("waveform_summary", {}).get("raw_waveforms_imported")
                ),
            },
            "quality": report.get("quality", {}),
            "calibration": report.get("calibration_summary", {}),
            "numeric_signals": self._ordered_items(numeric_signals, self.NUMERIC_ORDER),
            "waveform_signals": self._ordered_items(waveform_signals, self.WAVEFORM_ORDER),
            "waveform_coverage": report.get("waveform_summary", {}).get(
                "continuous_signal_coverage_pct", {}
            ),
            "fhir": {
                "resources": [
                    {
                        "resource_type": mapping.fhir_resource_type,
                        "resource_id": mapping.fhir_resource_id,
                        "profile_url": mapping.profile_url,
                        "sync_status": mapping.sync_status,
                    }
                    for mapping in fhir_mappings
                ],
                "quality_result_traceable": {
                    mapping.fhir_resource_type for mapping in fhir_mappings
                } >= {"Observation", "Provenance"},
            },
            "ao_readiness": {
                "status": "completed" if ao_outputs else "not_run",
                "model_runs": ao_jobs,
                "outputs": ao_outputs,
                "ground_truth_records": ground_truth_records,
                "current_conclusion": (
                    "AO output is available in the database."
                    if ao_outputs
                    else "No AO model run or AO output is present in the current system database."
                ),
            },
            "standards": [
                {
                    "name": "FHIR R4",
                    "status": "mapped",
                    "detail": "技術品質結果以 Observation 表達，並用 Provenance 保留來源與方法。",
                },
                {
                    "name": "LOINC + UCUM",
                    "status": "partial",
                    "detail": "常見生命徵象使用標準代碼與單位；SCG 波形索引暫用研究用代碼。",
                },
                {
                    "name": "USCDI",
                    "status": "partial",
                    "detail": "可用生命徵象對應臨床 Observation；原始 SCG 則保留為來源波形。",
                },
                {
                    "name": "ONC",
                    "status": "evaluation",
                    "detail": "本次是研究資料整合測試，不代表 ONC 認證或臨床效能驗證。",
                },
            ],
            "limitations": report.get("limitations", []),
        }

    @staticmethod
    def _ordered_items(values: Any, preferred_order: Iterable[str]) -> list[Dict[str, Any]]:
        if not isinstance(values, dict):
            return []
        ordered = []
        for key in preferred_order:
            item = values.get(key)
            if isinstance(item, dict):
                ordered.append({"signal": key, **item})
        return ordered
