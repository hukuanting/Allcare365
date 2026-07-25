import json
import uuid
from datetime import date, datetime
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import pandas as pd
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.clinical.patients.models import Patient
from apps.integration.fhir_integration.models import FHIRResource, FHIRResourceMapping

from .models import (
    DataImportBatch,
    DataImportRow,
    Encounter,
    HealthScreening,
    HealthStatusAssessment,
    LaboratoryResults,
    Observation,
    Problem,
    Questionnaire,
    QuestionnaireResponse,
    VitalSigns,
)


FHIR_LOINC_MAP = {
    "8302-2": ("vital", "body_height"),
    "29463-7": ("vital", "body_weight"),
    "8867-4": ("vital", "heart_rate"),
    "9279-1": ("vital", "respiratory_rate"),
    "8310-5": ("vital", "body_temperature"),
    "2708-6": ("vital", "pulse_oximetry"),
    "59408-5": ("vital", "pulse_oximetry"),
    "8480-6": ("vital", "systolic_blood_pressure"),
    "8462-4": ("vital", "diastolic_blood_pressure"),
    "2345-7": ("lab", "Glucose", "mg/dL"),
    "2339-0": ("lab", "Glucose", "mg/dL"),
    "4548-4": ("lab", "Hemoglobin A1c", "%"),
    "2093-3": ("lab", "Total Cholesterol", "mg/dL"),
    "2085-9": ("lab", "HDL Cholesterol", "mg/dL"),
    "2089-1": ("lab", "LDL Cholesterol", "mg/dL"),
    "2571-8": ("lab", "Triglycerides", "mg/dL"),
    "2160-0": ("lab", "Creatinine", "mg/dL"),
    "33914-3": ("lab", "eGFR", "mL/min/1.73m2"),
    "48642-3": ("lab", "eGFR", "mL/min/1.73m2"),
    "62238-1": ("lab", "eGFR", "mL/min/1.73m2"),
    "98979-8": ("lab", "eGFR", "mL/min/1.73m2"),
}


RELATIONALLY_MAPPED_FHIR_TYPES = frozenset(
    {
        "Patient",
        "Encounter",
        "Observation",
        "Condition",
        "QuestionnaireResponse",
    }
)


LAB_FIELD_MAP = {
    "fasting_glucose": ("Glucose", "mg/dL"),
    "fpg": ("Glucose", "mg/dL"),
    "glucose": ("Glucose", "mg/dL"),
    "hba1c": ("Hemoglobin A1c", "%"),
    "wbc_count": ("Leukocytes", "10*3/uL"),
    "rbc_count": ("Erythrocytes", "10*6/uL"),
    "platelet_count": ("Platelets", "10*3/uL"),
    "triglycerides": ("Triglycerides", "mg/dL"),
    "tg": ("Triglycerides", "mg/dL"),
    "total_cholesterol": ("Total Cholesterol", "mg/dL"),
    "tc": ("Total Cholesterol", "mg/dL"),
    "hdl_cholesterol": ("HDL Cholesterol", "mg/dL"),
    "hdl": ("HDL Cholesterol", "mg/dL"),
    "ldl_cholesterol": ("LDL Cholesterol", "mg/dL"),
    "ldl": ("LDL Cholesterol", "mg/dL"),
    "serum_creatinine": ("Creatinine", "mg/dL"),
    "creatinine": ("Creatinine", "mg/dL"),
    "egfr": ("eGFR", "mL/min/1.73m2"),
    "estimated_glomerular_filtration_rate": ("eGFR", "mL/min/1.73m2"),
    "alt_gpt": ("ALT", "U/L"),
    "ast_got": ("AST", "U/L"),
    "ast_uln": ("AST ULN", "U/L"),
    "ggt": ("GGT", "U/L"),
    "albumin": ("Albumin", "g/dL"),
    "insulin": ("Insulin", "uIU/mL"),
    "urine_albumin": ("Urine Albumin", "mg/dL"),
    "urine_creatinine": ("Urine Creatinine", "mg/dL"),
    "urine_albumin_creatinine_ratio": ("Urine Albumin-Creatinine Ratio", "mg/g"),
    "uacr": ("Urine Albumin-Creatinine Ratio", "mg/g"),
    "uric_acid": ("Uric Acid", "mg/dL"),
    "hs_crp": ("High sensitivity CRP", "mg/L"),
}


LAB_OBSERVATION_DEFINITIONS = {
    "fasting_glucose": ("2339-0", "Glucose [Mass/volume] in Blood", "mg/dL"),
    "fpg": ("2339-0", "Glucose [Mass/volume] in Blood", "mg/dL"),
    "glucose": ("2345-7", "Glucose [Mass/volume] in Serum or Plasma", "mg/dL"),
    "hba1c": ("4548-4", "Hemoglobin A1c/Hemoglobin.total in Blood", "%"),
    "total_cholesterol": ("2093-3", "Cholesterol [Mass/volume] in Serum or Plasma", "mg/dL"),
    "tc": ("2093-3", "Cholesterol [Mass/volume] in Serum or Plasma", "mg/dL"),
    "hdl_cholesterol": ("2085-9", "HDL Cholesterol [Mass/volume] in Serum or Plasma", "mg/dL"),
    "hdl": ("2085-9", "HDL Cholesterol [Mass/volume] in Serum or Plasma", "mg/dL"),
    "ldl_cholesterol": ("2089-1", "LDL Cholesterol [Mass/volume] in Serum or Plasma", "mg/dL"),
    "ldl": ("2089-1", "LDL Cholesterol [Mass/volume] in Serum or Plasma", "mg/dL"),
    "triglycerides": ("2571-8", "Triglyceride [Mass/volume] in Serum or Plasma", "mg/dL"),
    "tg": ("2571-8", "Triglyceride [Mass/volume] in Serum or Plasma", "mg/dL"),
    "creatinine": ("2160-0", "Creatinine [Mass/volume] in Serum or Plasma", "mg/dL"),
    "serum_creatinine": ("2160-0", "Creatinine [Mass/volume] in Serum or Plasma", "mg/dL"),
    "egfr": ("33914-3", "Glomerular filtration rate/1.73 sq M.predicted", "mL/min/1.73m2"),
    "estimated_glomerular_filtration_rate": ("33914-3", "Glomerular filtration rate/1.73 sq M.predicted", "mL/min/1.73m2"),
    "alt_gpt": ("1742-6", "Alanine aminotransferase [Enzymatic activity/volume] in Serum or Plasma", "U/L"),
    "ast_got": ("1920-8", "Aspartate aminotransferase [Enzymatic activity/volume] in Serum or Plasma", "U/L"),
    "ast_uln": ("1916-6", "Aspartate aminotransferase upper reference limit", "U/L"),
    "ggt": ("2324-2", "Gamma glutamyl transferase [Enzymatic activity/volume] in Serum or Plasma", "U/L"),
    "platelet_count": ("777-3", "Platelets [#/volume] in Blood by Automated count", "10*3/uL"),
    "albumin": ("1751-7", "Albumin [Mass/volume] in Serum or Plasma", "g/dL"),
    "insulin": ("20448-7", "Insulin [Units/volume] in Serum or Plasma", "uIU/mL"),
    "urine_albumin": ("1754-1", "Albumin [Mass/volume] in Urine", "mg/dL"),
    "urine_creatinine": ("2161-8", "Creatinine [Mass/volume] in Urine", "mg/dL"),
    "urine_albumin_creatinine_ratio": ("9318-7", "Albumin/Creatinine [Mass Ratio] in Urine", "mg/g"),
    "uacr": ("9318-7", "Albumin/Creatinine [Mass Ratio] in Urine", "mg/g"),
    "uric_acid": ("3084-1", "Urate [Mass/volume] in Serum or Plasma", "mg/dL"),
    "hs_crp": ("30522-7", "C reactive protein [Mass/volume] in Serum or Plasma by High sensitivity method", "mg/L"),
}


VITAL_OBSERVATION_DEFINITIONS = {
    "body_height": ("8302-2", "Body height", "cm"),
    "body_weight": ("29463-7", "Body weight", "kg"),
    "heart_rate": ("8867-4", "Heart rate", "beats/min"),
    "respiratory_rate": ("9279-1", "Respiratory rate", "breaths/min"),
    "body_temperature": ("8310-5", "Body temperature", "Cel"),
    "pulse_oximetry": ("2708-6", "Oxygen saturation in Arterial blood", "%"),
}


CORE_OBSERVATION_DEFINITIONS = {
    "waist_circumference": {
        "code": "8280-0",
        "display": "Waist Circumference at umbilicus",
        "unit": "cm",
        "category": "vital-signs",
        "aliases": ["waist_circumference", "waist", "Waist", "WC"],
    },
    "hip_circumference": {
        "code": "56074-8",
        "display": "Hip circumference",
        "unit": "cm",
        "category": "vital-signs",
        "aliases": ["hip_circumference", "hip", "Hip"],
    },
    "neck_circumference": {
        "code": "9843-4",
        "display": "Head and Neck Circumference",
        "unit": "cm",
        "category": "vital-signs",
        "aliases": ["neck_circumference", "neck", "Neck"],
    },
    "alcohol_drinks_per_week": {
        "code": "74013-4",
        "display": "Alcoholic drinks per week",
        "unit": "{drinks}/wk",
        "category": "social-history",
        "aliases": ["alcohol_drinks_per_week", "drinks_per_week", "Drinks per week"],
    },
    "apoe_e4": {
        "code": "79713-2",
        "display": "APOE gene e4 allele",
        "unit": "",
        "category": "laboratory",
        "aliases": ["apoe_e4", "APOE4", "APOE e4"],
    },
}


VITAL_FIELD_ALIASES = {
    "systolic_blood_pressure": ["systolic_blood_pressure", "systolic_bp_mmhg", "systolic_bp", "sbp"],
    "diastolic_blood_pressure": ["diastolic_blood_pressure", "diastolic_bp_mmhg", "diastolic_bp", "dbp"],
    "heart_rate": ["heart_rate", "pulse_rate_bpm", "pulse_rate", "pulse"],
    "respiratory_rate": ["respiratory_rate"],
    "body_temperature": ["body_temperature", "temperature"],
    "body_height": ["body_height", "height_cm", "height"],
    "body_weight": ["body_weight", "weight_kg", "weight"],
    "pulse_oximetry": ["pulse_oximetry", "spo2"],
    "inhaled_oxygen_concentration": ["inhaled_oxygen_concentration", "oxygen_concentration"],
    "bmi_percentile": ["bmi_percentile"],
    "weight_for_length_percentile": ["weight_for_length_percentile"],
    "head_circumference_percentile": ["head_circumference_percentile"],
}


RowTransform = Callable[[Dict[str, Any], int], Dict[str, Any]]


class HealthScreeningIngestionService:
    """Shared ingestion boundary for manual entry, CSV bulk import, and FHIR import."""

    def parse_file_preview(self, file_obj) -> Dict[str, Any]:
        rows = self._read_tabular_file(file_obj)
        headers = list(rows[0].keys()) if rows else []
        return {
            "headers": headers,
            "row_count": len(rows),
            "sample_data": rows[:10],
        }

    def bulk_import_file(
        self,
        file_obj,
        *,
        source_type: Optional[str] = None,
        original_filename: Optional[str] = None,
        limit: Optional[int] = None,
        dry_run: bool = False,
        skip_existing: bool = False,
        row_transform: Optional[RowTransform] = None,
    ) -> Dict[str, Any]:
        rows = self._read_tabular_file(file_obj)
        inferred_source_type = "excel" if (getattr(file_obj, "name", "") or "").lower().endswith((".xlsx", ".xls")) else "csv"
        return self.bulk_import_rows(
            rows,
            source_type=source_type or inferred_source_type,
            original_filename=original_filename or getattr(file_obj, "name", "") or "",
            limit=limit,
            dry_run=dry_run,
            skip_existing=skip_existing,
            row_transform=row_transform,
        )

    def bulk_import_rows(
        self,
        rows: List[Dict[str, Any]],
        *,
        source_type: str = "csv",
        original_filename: str = "",
        limit: Optional[int] = None,
        dry_run: bool = False,
        skip_existing: bool = False,
        row_transform: Optional[RowTransform] = None,
    ) -> Dict[str, Any]:
        if limit is not None:
            rows = rows[:limit]

        errors = []
        created = 0
        skipped = 0
        validated = 0
        batch = DataImportBatch.objects.create(
            source_type=source_type,
            original_filename=original_filename,
            status="validating" if dry_run else "processing",
            total_rows=len(rows),
            started_at=timezone.now(),
            import_options_json={
                "dry_run": dry_run,
                "limit": limit,
                "skip_existing": skip_existing,
            },
        )

        for index, row in enumerate(rows, start=1):
            raw_row = dict(row)
            import_row = DataImportRow.objects.create(
                batch=batch,
                row_number=index,
                status="validating" if dry_run else "processing",
                raw_json=self._json_safe({str(key): value for key, value in raw_row.items()}),
            )
            try:
                if row_transform:
                    row = row_transform(raw_row, index)
                with transaction.atomic():
                    payload = self._row_to_screening_payload(row, create_patient=not dry_run)
                    encounter_identifier = payload.get("encounter_identifier")
                    if skip_existing and encounter_identifier:
                        existing = HealthScreening.objects.filter(encounter_identifier=encounter_identifier).first()
                        if existing:
                            skipped += 1
                            import_row.patient = existing.patient
                            import_row.status = "skipped"
                            import_row.target_table = "health_screening_healthscreening"
                            import_row.target_id = existing.id
                            import_row.normalized_json = self._json_safe(payload)
                            import_row.save(update_fields=["patient", "status", "target_table", "target_id", "normalized_json", "updated_at"])
                            continue

                    if dry_run:
                        validated += 1
                        import_row.status = "validated"
                        import_row.normalized_json = self._json_safe(payload)
                        import_row.save(update_fields=["status", "normalized_json", "updated_at"])
                        continue

                    screening = self.create_screening(payload)
                    created += 1
                    import_row.patient = screening.patient
                    import_row.status = "success"
                    import_row.target_table = "health_screening_healthscreening"
                    import_row.target_id = screening.id
                    import_row.normalized_json = self._json_safe(payload)
                    import_row.save(update_fields=["patient", "status", "target_table", "target_id", "normalized_json", "updated_at"])
            except Exception as exc:
                errors.append({"row": index, "error": str(exc)})
                import_row.status = "failed"
                import_row.error_message = str(exc)
                import_row.save(update_fields=["status", "error_message", "updated_at"])

        batch.status = "validated" if dry_run and not errors else "completed" if not errors else "completed_with_errors"
        batch.processed_rows = len(rows)
        batch.success_rows = created
        batch.failed_rows = len(errors)
        batch.completed_at = timezone.now()
        batch.summary_json = {
            "success_count": created,
            "validated_count": validated,
            "skipped_count": skipped,
            "error_count": len(errors),
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

        return {
            "success_count": created,
            "validated_count": validated,
            "skipped_count": skipped,
            "error_count": len(errors),
            "total_count": len(rows),
            "batch_id": str(batch.id),
            "errors": errors,
        }

    @transaction.atomic
    def import_fhir(
        self,
        fhir_data: Any,
        data_format: str = "json",
        source_namespace: Optional[str] = None,
    ) -> Dict[str, Any]:
        if isinstance(fhir_data, str) and data_format == "json":
            fhir_data = json.loads(fhir_data)

        source_namespace = self._fhir_source_namespace(fhir_data, source_namespace)
        entries = self._extract_fhir_entries(fhir_data)
        self._preflight_fhir_resource_collisions(entries, source_namespace)
        resources = [entry["resource"] for entry in entries]
        patient_map: Dict[Any, Patient] = {}
        imported_patients: Dict[str, Patient] = {}
        clinical_contexts: Dict[Tuple[str, str], Tuple[HealthScreening, Encounter]] = {}
        encounter_resources = self._fhir_resource_reference_map(entries, "Encounter")
        created_patients = 0
        created_screenings = 0
        created_observations = 0
        created_questionnaire_responses = 0
        errors = []

        for entry in entries:
            resource = entry["resource"]
            if resource.get("resourceType") != "Patient":
                continue
            try:
                with transaction.atomic():
                    patient, created = self._upsert_patient_from_fhir(
                        resource,
                        source_namespace,
                    )
                    persisted_resource = self._persist_fhir_resource(
                        resource,
                        patient=patient,
                        local_object=patient,
                        source_namespace=source_namespace,
                    )
                    self._sync_fhir_mapping(
                        persisted_resource,
                        resource,
                        patient,
                        patient,
                        source_namespace,
                    )
                    self._register_fhir_patient_references(
                        patient_map,
                        patient,
                        resource,
                        entry.get("fullUrl"),
                    )
                created_patients += 1 if created else 0
                imported_patients[str(patient.id)] = patient
            except Exception as exc:
                errors.append(f"Patient/{resource.get('id', 'unknown')}: {exc}")

        for entry in entries:
            resource = entry["resource"]
            if resource.get("resourceType") != "Encounter":
                continue
            try:
                with transaction.atomic():
                    context_created, patient, encounter = self._ingest_fhir_encounter(
                        resource,
                        entry.get("fullUrl"),
                        patient_map,
                        clinical_contexts,
                        encounter_resources,
                        source_namespace,
                    )
                    persisted_resource = self._persist_fhir_resource(
                        resource,
                        patient=patient,
                        local_object=encounter,
                        source_namespace=source_namespace,
                    )
                    self._sync_fhir_mapping(
                        persisted_resource,
                        resource,
                        encounter,
                        patient,
                        source_namespace,
                    )
                imported_patients[str(patient.id)] = patient
                if context_created:
                    created_screenings += 1
            except Exception as exc:
                errors.append(f"Encounter/{resource.get('id', 'unknown')}: {exc}")

        for entry in entries:
            resource = entry["resource"]
            if resource.get("resourceType") in {"Patient", "Encounter"}:
                continue
            try:
                with transaction.atomic():
                    if resource.get("resourceType") == "Observation":
                        context_created, patient, observation = self._ingest_fhir_observation(
                            resource,
                            patient_map,
                            clinical_contexts=clinical_contexts,
                            encounter_resources=encounter_resources,
                            source_namespace=source_namespace,
                        )
                        persisted_resource = self._persist_fhir_resource(
                            resource,
                            patient=patient,
                            local_object=observation,
                            source_namespace=source_namespace,
                        )
                        self._sync_fhir_mapping(
                            persisted_resource,
                            resource,
                            observation,
                            patient,
                            source_namespace,
                        )
                        imported_patients[str(patient.id)] = patient
                        created_observations += 1
                        if context_created:
                            created_screenings += 1
                    elif resource.get("resourceType") == "Condition":
                        patient, problem = self._ingest_fhir_condition(
                            resource,
                            patient_map,
                            source_namespace,
                        )
                        persisted_resource = self._persist_fhir_resource(
                            resource,
                            patient=patient,
                            local_object=problem,
                            source_namespace=source_namespace,
                        )
                        self._sync_fhir_mapping(
                            persisted_resource,
                            resource,
                            problem,
                            patient,
                            source_namespace,
                        )
                        imported_patients[str(patient.id)] = patient
                    elif resource.get("resourceType") == "QuestionnaireResponse":
                        patient, questionnaire_response = self._ingest_fhir_questionnaire_response(
                            resource,
                            patient_map,
                            source_namespace,
                        )
                        persisted_resource = self._persist_fhir_resource(
                            resource,
                            patient=patient,
                            local_object=questionnaire_response,
                            source_namespace=source_namespace,
                        )
                        self._sync_fhir_mapping(
                            persisted_resource,
                            resource,
                            questionnaire_response,
                            patient,
                            source_namespace,
                        )
                        imported_patients[str(patient.id)] = patient
                        created_questionnaire_responses += 1
                    else:
                        self._persist_fhir_resource(
                            resource,
                            source_namespace=source_namespace,
                        )
            except Exception as exc:
                errors.append(f"{resource.get('resourceType')}/{resource.get('id', 'unknown')}: {exc}")

        patient_summaries = [
            {
                "id": str(patient.id),
                "medical_record_number": patient.medical_record_number,
                "display_name": f"{patient.last_name}{patient.first_name}".strip(),
            }
            for patient in imported_patients.values()
        ]
        if errors:
            transaction.set_rollback(True)
            patient_summaries = []
            created_patients = 0
            created_screenings = 0
            created_observations = 0
            created_questionnaire_responses = 0
        return {
            "success_count": 0 if errors else len(resources),
            "error_count": len(errors),
            "total_count": len(resources),
            "created_patients": created_patients,
            "created_screenings": created_screenings,
            "created_observations": created_observations,
            "created_questionnaire_responses": created_questionnaire_responses,
            "patient_ids": [patient["id"] for patient in patient_summaries],
            "patients": patient_summaries,
            "primary_patient_id": patient_summaries[0]["id"] if len(patient_summaries) == 1 else None,
            "errors": errors,
        }

    @transaction.atomic
    def create_screening(self, payload: Dict[str, Any]) -> HealthScreening:
        patient = self._resolve_patient(payload)
        screening_date = self._parse_date(self._first(payload, ["screening_date", "CheckDate", "date"])) or timezone.now().date()
        encounter_time = self._parse_datetime(self._first(payload, ["encounter_time", "screening_datetime"])) or timezone.now()
        vital_payload = self._core_source_payload(payload, "vital_signs")
        lab_payload = self._core_source_payload(payload, "laboratory_results", "labs")
        assessment_payload = self._core_source_payload(payload, "assessments", "lifestyle", "hq")
        problem_payload = self._core_source_payload(payload, "problems", "lifestyle", "hq")

        screening = HealthScreening.objects.create(
            patient=patient,
            encounter_type=self._first(payload, ["encounter_type", "screening_type"]) or "annual_physical",
            encounter_identifier=self._first(payload, ["encounter_identifier"]) or "",
            encounter_time=encounter_time,
            encounter_location=self._first(payload, ["encounter_location"]) or "",
            encounter_disposition=self._first(payload, ["encounter_disposition"]) or "",
            screening_date=screening_date,
        )

        self._create_vital_signs(screening, vital_payload)
        self._create_labs(screening, lab_payload)
        self._create_assessment(screening, assessment_payload)
        self._create_problems(patient, problem_payload)
        self._project_to_product_schema(screening, payload)

        return screening

    def _read_tabular_file(self, file_obj) -> List[Dict[str, Any]]:
        filename = (getattr(file_obj, "name", "") or "").lower()
        if filename.endswith((".xlsx", ".xls")):
            frame = pd.read_excel(file_obj)
        else:
            try:
                frame = pd.read_csv(file_obj, low_memory=False)
            except UnicodeDecodeError:
                file_obj.seek(0)
                frame = pd.read_csv(file_obj, encoding="utf-8-sig", low_memory=False)

        frame = frame.where(pd.notnull(frame), None)
        return frame.to_dict("records")

    def _row_to_screening_payload(self, row: Dict[str, Any], *, create_patient: bool = True) -> Dict[str, Any]:
        normalized = {str(key).strip(): value for key, value in row.items()}
        patient = self._get_value(normalized, ["patient", "patient_id", "ID", "MRN", "medical_record_number"])
        if not patient:
            raise ValueError("Missing patient identifier")

        if create_patient:
            patient_obj = self._get_or_create_patient_from_row(normalized, str(patient))
            patient_ref = str(patient_obj.id)
        else:
            birth_date = self._parse_date(self._get_value(normalized, ["BirthDate", "birth_date", "date_of_birth"]))
            if not birth_date:
                raise ValueError(f"Missing birth date for patient {patient}")
            patient_ref = str(patient)

        payload = dict(normalized)
        payload["patient"] = patient_ref
        payload["screening_date"] = self._get_value(normalized, ["screening_date", "CheckDate", "date"]) or timezone.now().date().isoformat()
        payload["encounter_type"] = self._get_value(normalized, ["encounter_type", "Source"]) or "bulk_health_check"
        payload["encounter_identifier"] = self._get_value(normalized, ["encounter_identifier", "EncounterID", "encounter_id"]) or ""
        payload["encounter_location"] = self._get_value(normalized, ["encounter_location", "Source", "location"]) or ""
        payload["source_type"] = self._get_value(normalized, ["source_type", "SourceType"]) or "manual"
        payload["vital_signs"] = {
            "height_cm": self._get_value(normalized, ["height_cm", "Height"]),
            "weight_kg": self._get_value(normalized, ["weight_kg", "Weight"]),
            "systolic_bp": self._get_value(normalized, ["systolic_bp", "SBP"]),
            "diastolic_bp": self._get_value(normalized, ["diastolic_bp", "DBP"]),
            "pulse_rate": self._get_value(normalized, ["pulse_rate", "PulseRate"]),
        }
        payload["a1_key_in"] = {
            "waist_circumference": self._get_value(normalized, ["waist_circumference", "Waist", "WC"]),
            "hip_circumference": self._get_value(normalized, ["hip_circumference", "Hip"]),
            "alcohol_drinks_per_week": self._get_value(normalized, ["drinks_per_week", "Drinks per week"]),
            "apoe_e4": self._get_value(normalized, ["apoe_e4", "APOE4", "APOE e4"]),
        }
        payload["laboratory_results"] = {
            "fasting_glucose": self._get_value(normalized, ["fasting_glucose", "FPG"]),
            "hba1c": self._get_value(normalized, ["hba1c", "HbA1C"]),
            "wbc_count": self._get_value(normalized, ["wbc_count", "WBC"]),
            "platelet_count": self._get_value(normalized, ["platelet_count", "Platelet"]),
            "triglycerides": self._get_value(normalized, ["triglycerides", "TG"]),
            "total_cholesterol": self._get_value(normalized, ["total_cholesterol", "TC"]),
            "hdl_cholesterol": self._get_value(normalized, ["hdl_cholesterol", "HDL"]),
            "ldl_cholesterol": self._get_value(normalized, ["ldl_cholesterol", "LDL"]),
            "creatinine": self._get_value(normalized, ["creatinine", "Creatinine"]),
            "alt_gpt": self._get_value(normalized, ["alt_gpt", "ALT", "GPT"]),
            "ast_got": self._get_value(normalized, ["ast_got", "AST", "GOT"]),
            "ast_uln": self._get_value(normalized, ["ast_uln", "AST ULN"]),
            "ggt": self._get_value(normalized, ["ggt", "GGT"]),
            "albumin": self._get_value(normalized, ["albumin", "Albumin"]),
            "insulin": self._get_value(normalized, ["insulin", "Insulin"]),
            "urine_albumin_creatinine_ratio": self._get_value(normalized, ["urine_albumin_creatinine_ratio", "UACR"]),
        }
        payload["hq"] = {
            "family_history_diabetes": self._as_bool(self._get_value(normalized, ["family_history_diabetes", "HQ_FAMILY_DM"])),
            "prediabetes": self._as_bool(self._get_value(normalized, ["prediabetes", "PreDM"])),
            "dm_treated": self._as_bool(self._get_value(normalized, ["dm_treated", "DM treated"])),
            "hypertension_treated": self._as_bool(self._get_value(normalized, ["hypertension_treated", "HTN treated"])),
            "lipid_lowering_treated": self._as_bool(self._get_value(normalized, ["lipid_lowering_treated", "Dys RX"])),
            "vegetables_daily": self._as_bool(self._get_value(normalized, ["vegetables_daily", "HQ_VEGE"])),
            "physical_activity_active": self._as_bool(self._get_value(normalized, ["physical_activity_active", "HQ_Exercise"])),
            "current_smoker": self._as_bool(self._get_value(normalized, ["current_smoker", "HQ_SMOKE"])),
            "former_smoker": self._as_bool(self._get_value(normalized, ["former_smoker", "FORMER Smoker"])),
            "moderate_alcohol": self._as_bool(self._get_value(normalized, ["moderate_alcohol", "Mod Drink"])),
            "heavy_alcohol": self._as_bool(self._get_value(normalized, ["heavy_alcohol", "Heavy Drink"])),
            "chd_history": self._as_bool(self._get_value(normalized, ["chd_history", "CHD"])),
            "cvd_history": self._as_bool(self._get_value(normalized, ["cvd_history", "CVD"])),
            "pvd_history": self._as_bool(self._get_value(normalized, ["pvd_history", "PVD"])),
        }
        payload["lifestyle"] = {
            "smoking_status": "current" if self._as_bool(self._get_value(normalized, ["HQ_SMOKE", "is_current_smoker"])) else "",
            "physical_activity": self._get_value(normalized, ["HQ_Exercise", "exercise_score"]) or "",
            "has_diabetes": self._as_bool(self._get_value(normalized, ["HQ_Diabetes", "has_diabetes"])),
            "has_hypertension": self._as_bool(self._get_value(normalized, ["HQ_BP_Treat", "hypertension_treated"])),
        }
        return payload

    def _get_or_create_patient_from_row(self, row: Dict[str, Any], mrn: str) -> Patient:
        patient = Patient.objects.filter(medical_record_number=mrn).first()
        if patient:
            return patient

        birth_date = self._parse_date(self._get_value(row, ["BirthDate", "birth_date", "date_of_birth"]))
        if not birth_date:
            raise ValueError(f"Missing birth date for patient {mrn}")

        sex = self._normalize_sex(self._get_value(row, ["SEX", "sex", "gender"]))
        source_system = self._get_value(row, ["source_system", "SourceSystem"]) or ""
        source_record_id = self._get_value(row, ["source_record_id", "SourceRecordID", "ID"]) or ""
        return Patient.objects.create(
            medical_record_number=mrn,
            first_name=str(self._get_value(row, ["first_name", "FirstName"]) or "Unknown"),
            last_name=str(self._get_value(row, ["last_name", "LastName", "full_name"]) or mrn),
            date_of_birth=birth_date,
            sex=sex,
            status="active",
            source_system=str(source_system),
            source_record_id=str(source_record_id),
            last_imported_at=timezone.now(),
            metadata_json=self._json_safe({
                "source": source_system,
                "source_record_id": source_record_id,
            }),
        )

    def _resolve_patient(self, payload: Dict[str, Any]) -> Patient:
        patient_value = self._first(payload, ["patient", "patient_id", "medical_record_number"])
        if not patient_value:
            raise ValueError("Missing patient")

        patient = Patient.objects.filter(id=patient_value).first()
        if not patient:
            patient = Patient.objects.filter(medical_record_number=str(patient_value)).first()
        if not patient:
            raise ValueError(f"Patient not found: {patient_value}")
        return patient

    def _create_vital_signs(self, screening: HealthScreening, payload: Dict[str, Any]) -> Optional[VitalSigns]:
        data = {}
        for model_field, aliases in VITAL_FIELD_ALIASES.items():
            raw_value = self._get_value(payload, aliases)
            numeric_value = self._as_decimal(raw_value)
            if numeric_value is not None:
                data[model_field] = numeric_value

        if not data:
            return None
        vital_signs, _ = VitalSigns.objects.get_or_create(health_screening=screening)
        if (
            (data.get("systolic_blood_pressure") is not None or vital_signs.systolic_blood_pressure is not None)
            and (data.get("diastolic_blood_pressure") is not None or vital_signs.diastolic_blood_pressure is not None)
            and data.get("average_blood_pressure") is None
        ):
            systolic = data.get("systolic_blood_pressure", vital_signs.systolic_blood_pressure)
            diastolic = data.get("diastolic_blood_pressure", vital_signs.diastolic_blood_pressure)
            data["average_blood_pressure"] = round(
                (systolic + 2 * diastolic) / 3
            )
        for field, value in data.items():
            setattr(vital_signs, field, value)
        vital_signs.save()
        return vital_signs

    def _create_labs(self, screening: HealthScreening, payload: Any) -> int:
        created = 0
        if isinstance(payload, list):
            for lab in payload:
                if not isinstance(lab, dict):
                    continue
                test_name = lab.get("test_name") or lab.get("name")
                value = lab.get("value_result") or lab.get("result_value") or lab.get("value")
                if test_name and value not in [None, ""]:
                    LaboratoryResults.objects.create(
                        health_screening=screening,
                        test_name=str(test_name),
                        value_result=str(value),
                        result_unit=str(lab.get("result_unit") or lab.get("unit") or ""),
                        result_status=str(lab.get("result_status") or "final"),
                    )
                    created += 1
            return created

        if not isinstance(payload, dict):
            return 0

        normalized = {str(key).lower(): value for key, value in payload.items()}
        for field, (test_name, unit) in LAB_FIELD_MAP.items():
            value = normalized.get(field.lower())
            if value in [None, ""]:
                continue
            LaboratoryResults.objects.create(
                health_screening=screening,
                test_name=test_name,
                value_result=str(value),
                result_unit=unit,
                result_status="final",
            )
            created += 1
        return created

    def _create_assessment(self, screening: HealthScreening, payload: Dict[str, Any]) -> Optional[HealthStatusAssessment]:
        if not isinstance(payload, dict):
            return None

        data = {
            "smoking_status": self._first(payload, ["smoking_status", "smoking_history"]) or "",
            "alcohol_use": self._first(payload, ["alcohol_use", "alcohol_frequency"]) or "",
            "physical_activity": self._first(payload, ["physical_activity", "exercise_score", "exercise_frequency"]) or "",
            "substance_use": self._first(payload, ["substance_use"]) or "",
            "sdoh_assessment": self._first(payload, ["sdoh_assessment"]) or "",
            "health_concerns": self._first(payload, ["health_concerns"]) or "",
        }
        if not any(data.values()):
            return None
        return HealthStatusAssessment.objects.create(health_screening=screening, **data)

    def _create_problems(self, patient: Patient, payload: Dict[str, Any]) -> int:
        if not isinstance(payload, dict):
            return 0

        problem_flags = {
            "has_diabetes": "Diabetes mellitus",
            "personal_diabetes": "Diabetes mellitus",
            "has_hypertension": "Hypertension",
            "personal_hypertension": "Hypertension",
            "has_dyslipidemia": "Dyslipidemia",
            "personal_hyperlipidemia": "Dyslipidemia",
            "personal_stroke": "History of stroke",
        }
        created = 0
        for field, name in problem_flags.items():
            if self._as_bool(payload.get(field)):
                Problem.objects.get_or_create(patient=patient, problem_name=name, defaults={"status": "active"})
                created += 1
        return created

    def _project_to_product_schema(self, screening: HealthScreening, payload: Dict[str, Any]) -> None:
        source_type = str(payload.get("source_type") or "manual")
        encounter = Encounter.objects.create(
            patient=screening.patient,
            source_screening=screening,
            encounter_type=screening.encounter_type or "health_intake",
            status="finished",
            reason="Health intake",
            location=screening.encounter_location or "",
            started_at=screening.encounter_time or timezone.now(),
            ended_at=screening.encounter_time or timezone.now(),
            source_type=source_type,
            metadata_json={
                "screening_id": str(screening.id),
                "encounter_identifier": screening.encounter_identifier,
            },
        )
        core_payload = self._core_source_payload(payload)
        vital_payload = self._core_source_payload(payload, "vital_signs")
        lab_payload = self._core_source_payload(payload, "laboratory_results", "labs")
        self._create_product_vital_observations(screening, encounter, vital_payload, source_type=source_type)
        self._create_product_lab_observations(screening, encounter, lab_payload, source_type=source_type)
        self._create_core_observations(screening, encounter, core_payload, source_type=source_type)
        self._create_product_questionnaire_response(screening, encounter, payload, source_type=source_type)

    def _create_product_vital_observations(self, screening: HealthScreening, encounter: Encounter, payload: Dict[str, Any], *, source_type: str = "manual") -> None:
        if not isinstance(payload, dict):
            return

        vital_values = {}
        for model_field, aliases in VITAL_FIELD_ALIASES.items():
            raw_value = self._get_value(payload, aliases)
            value = self._as_decimal(raw_value)
            if value is not None:
                vital_values[model_field] = value

        systolic = vital_values.get("systolic_blood_pressure")
        diastolic = vital_values.get("diastolic_blood_pressure")
        if systolic is not None or diastolic is not None:
            Observation.objects.create(
                patient=screening.patient,
                encounter=encounter,
                observation_type="blood_pressure",
                category="vital-signs",
                source_type=source_type,
                code_system="http://loinc.org",
                code="85354-9",
                display="Blood pressure panel with all children optional",
                component_json=[
                    {"code": "8480-6", "display": "Systolic blood pressure", "value": systolic, "unit": "mmHg"},
                    {"code": "8462-4", "display": "Diastolic blood pressure", "value": diastolic, "unit": "mmHg"},
                ],
                status="final",
                effective_at=screening.encounter_time or timezone.now(),
                source_payload_json=self._json_safe(payload),
            )

        for field, (code, display, unit) in VITAL_OBSERVATION_DEFINITIONS.items():
            value = vital_values.get(field)
            if value is None:
                continue
            Observation.objects.create(
                patient=screening.patient,
                encounter=encounter,
                observation_type=field,
                category="vital-signs",
                source_type=source_type,
                code_system="http://loinc.org",
                code=code,
                display=display,
                value_quantity=value,
                value_unit=unit,
                status="final",
                effective_at=screening.encounter_time or timezone.now(),
                source_payload_json=self._json_safe(payload),
            )

        height = vital_values.get("body_height")
        weight = vital_values.get("body_weight")
        if height and weight:
            bmi = round(float(weight) / ((float(height) / 100) ** 2), 2)
            Observation.objects.create(
                patient=screening.patient,
                encounter=encounter,
                observation_type="body_mass_index",
                category="vital-signs",
                source_type=f"{source_type}:derived",
                code_system="http://loinc.org",
                code="39156-5",
                display="Body mass index (BMI) [Ratio]",
                value_quantity=bmi,
                value_unit="kg/m2",
                status="final",
                effective_at=screening.encounter_time or timezone.now(),
                source_payload_json=self._json_safe({"derived_from": ["body_height", "body_weight"], "source": payload}),
            )

    def _create_product_lab_observations(self, screening: HealthScreening, encounter: Encounter, payload: Any, *, source_type: str = "manual") -> None:
        if isinstance(payload, list):
            for lab in payload:
                if not isinstance(lab, dict):
                    continue
                self._create_product_lab_observation_from_dict(screening, encounter, lab, source_type=source_type)
            return

        if not isinstance(payload, dict):
            return

        normalized = {str(key).lower(): value for key, value in payload.items()}
        for field, (code, display, unit) in LAB_OBSERVATION_DEFINITIONS.items():
            value = self._as_decimal(normalized.get(field.lower()))
            if value is None:
                continue
            Observation.objects.create(
                patient=screening.patient,
                encounter=encounter,
                observation_type=field,
                category="laboratory",
                source_type=source_type,
                code_system="http://loinc.org",
                code=code,
                display=display,
                value_quantity=value,
                value_unit=unit,
                status="final",
                effective_at=screening.encounter_time or timezone.now(),
                source_payload_json=self._json_safe(payload),
            )

    def _create_core_observations(self, screening: HealthScreening, encounter: Encounter, payload: Dict[str, Any], *, source_type: str = "manual") -> None:
        if not isinstance(payload, dict):
            return
        for field, definition in CORE_OBSERVATION_DEFINITIONS.items():
            value = self._as_decimal(self._get_value(payload, [field, *definition["aliases"]]))
            if value is None:
                continue
            Observation.objects.create(
                patient=screening.patient,
                encounter=encounter,
                observation_type=field,
                category=definition["category"],
                source_type=source_type,
                code_system="http://loinc.org",
                code=definition["code"],
                display=definition["display"],
                value_quantity=value,
                value_unit=definition["unit"],
                status="final",
                effective_at=screening.encounter_time or timezone.now(),
                source_payload_json=self._json_safe(payload),
            )

    def _create_product_lab_observation_from_dict(
        self,
        screening: HealthScreening,
        encounter: Encounter,
        lab: Dict[str, Any],
        *,
        source_type: str = "manual",
    ) -> None:
        test_name = lab.get("test_name") or lab.get("name") or lab.get("display") or "Unknown lab"
        value = self._as_decimal(lab.get("value_result") or lab.get("result_value") or lab.get("value"))
        if value is None:
            return
        code = str(lab.get("code") or lab.get("loinc") or "")
        observation_type = self._slug(test_name)
        definition = LAB_OBSERVATION_DEFINITIONS.get(observation_type)
        if definition and not code:
            code, display, unit = definition
        else:
            display = str(test_name)
            unit = str(lab.get("result_unit") or lab.get("unit") or "")
        Observation.objects.create(
            patient=screening.patient,
            encounter=encounter,
            observation_type=observation_type,
            category=str(lab.get("category") or "laboratory"),
            source_type=source_type,
            code_system=str(lab.get("code_system") or ("http://loinc.org" if code else "")),
            code=code,
            display=display,
            value_quantity=value,
            value_unit=unit,
            value_json={"raw_test_name": test_name},
            status=str(lab.get("result_status") or lab.get("status") or "final"),
            effective_at=screening.encounter_time or timezone.now(),
            source_payload_json=self._json_safe(lab),
        )

    def _create_product_questionnaire_response(
        self,
        screening: HealthScreening,
        encounter: Encounter,
        payload: Dict[str, Any],
        *,
        source_type: str = "manual",
    ) -> None:
        response_json = {}
        for key in ("questionnaire", "questionnaire_response", "hq", "assessments", "lifestyle", "problems"):
            value = payload.get(key)
            if isinstance(value, dict):
                response_json[key] = value
        if not response_json:
            return

        questionnaire, _ = Questionnaire.objects.get_or_create(
            title="CORE HQ Intake",
            version="1.0.0",
            defaults={
                "status": "active",
                "code_system": "https://allcare365.local/questionnaires",
                "code": "core-hq-intake",
                "questionnaire_json": {"source": "CORE.xlsx", "sheet": "HQ"},
            },
        )
        QuestionnaireResponse.objects.create(
            patient=screening.patient,
            questionnaire=questionnaire,
            encounter=encounter,
            authored_at=screening.encounter_time or timezone.now(),
            status="completed",
            source_type=source_type,
            response_json=response_json,
            score_json={},
            metadata_json={"source_screening_id": str(screening.id), "source": "CORE.xlsx/HQ"},
        )

    def _extract_fhir_entries(self, fhir_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not isinstance(fhir_data, dict):
            raise ValueError("FHIR data must be a JSON object")
        if fhir_data.get("resourceType") == "Bundle":
            return [
                {"resource": entry["resource"], "fullUrl": entry.get("fullUrl")}
                for entry in fhir_data.get("entry", [])
                if isinstance(entry, dict) and isinstance(entry.get("resource"), dict)
            ]
        if fhir_data.get("resourceType"):
            return [{"resource": fhir_data, "fullUrl": None}]
        raise ValueError("FHIR resourceType is required")

    def _extract_fhir_resources(self, fhir_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [entry["resource"] for entry in self._extract_fhir_entries(fhir_data)]

    @staticmethod
    def _fhir_source_namespace(
        fhir_data: Dict[str, Any],
        explicit_namespace: Optional[str],
    ) -> str:
        namespace = str(explicit_namespace or "").strip()
        if not namespace:
            namespace = str(
                getattr(settings, "FHIR_DEFAULT_ORIGIN_NAMESPACE", "") or ""
            ).strip()
        if not namespace:
            raise ValueError(
                "source_namespace is required for FHIR import; configure a stable trusted "
                "namespace or supply it explicitly"
            )
        if namespace == "unspecified":
            raise ValueError("source_namespace cannot use the reserved value 'unspecified'")
        if len(namespace) > 200:
            raise ValueError("source_namespace cannot exceed 200 characters")
        return namespace

    def _preflight_fhir_resource_collisions(
        self,
        entries: List[Dict[str, Any]],
        source_namespace: str,
    ) -> None:
        seen: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for entry in entries:
            resource = entry["resource"]
            resource_type = str(resource.get("resourceType") or "").strip()
            resource_id = str(resource.get("id") or "").strip()
            if not resource_type or not resource_id:
                continue
            key = (resource_type, resource_id)
            if key in seen and seen[key] != resource:
                raise ValueError(
                    f"FHIR {resource_type}/{resource_id} is duplicated with conflicting data in the bundle"
                )
            seen[key] = resource

            persisted = FHIRResource.objects.filter(
                resource_type=resource_type,
                resource_id=resource_id,
            ).first()
            mappings = list(
                FHIRResourceMapping.objects.filter(
                    fhir_resource_type=resource_type,
                    fhir_resource_id=resource_id,
                )[:2]
            )
            if len(mappings) > 1:
                raise ValueError(f"FHIR {resource_type}/{resource_id} has multiple owners")
            if persisted is None:
                if mappings:
                    raise ValueError(
                        f"FHIR {resource_type}/{resource_id} has an ownership mapping "
                        "without a persisted resource"
                    )
                continue
            existing_namespace = str(persisted.origin_namespace or "unspecified").strip()
            if existing_namespace != source_namespace:
                raise ValueError(
                    f"FHIR {resource_type}/{resource_id} belongs to source namespace "
                    f"{existing_namespace}, not {source_namespace}"
                )
            if not mappings:
                if resource_type not in RELATIONALLY_MAPPED_FHIR_TYPES:
                    continue
                raise ValueError(
                    f"FHIR {resource_type}/{resource_id} exists without ownership mapping"
                )
            mapping = mappings[0]
            mapping_namespace = str(
                (mapping.metadata_json or {}).get("source_namespace") or ""
            ).strip()
            if mapping_namespace and mapping_namespace != source_namespace:
                raise ValueError(
                    f"FHIR {resource_type}/{resource_id} belongs to source namespace "
                    f"{mapping_namespace}, not {source_namespace}"
                )
            if mapping.patient_id is None:
                raise ValueError(f"FHIR {resource_type}/{resource_id} has no patient owner")
            if persisted.resource_data == resource:
                continue

            if resource_type == "Patient":
                incoming_mrn_identity = self._fhir_patient_mrn_identity(resource)
                mapped_patient = mapping.patient
                if incoming_mrn_identity:
                    incoming_mrn_system, incoming_mrn = incoming_mrn_identity
                    mapped_mrn_system = str(
                        (mapped_patient.metadata_json or {}).get("fhir_mrn_system") or ""
                    ).strip()
                    if mapped_patient.medical_record_number not in (None, incoming_mrn):
                        raise ValueError(
                            f"FHIR Patient/{resource_id} conflicts with its mapped patient identity"
                        )
                    if mapped_mrn_system and mapped_mrn_system != incoming_mrn_system:
                        raise ValueError(
                            f"FHIR Patient/{resource_id} conflicts with its mapped MRN system"
                        )
                continue

            existing_reference = str(
                ((persisted.resource_data or {}).get("subject") or {}).get("reference") or ""
            ).strip()
            incoming_reference = str(
                (resource.get("subject") or {}).get("reference") or ""
            ).strip()
            if existing_reference == incoming_reference:
                continue
            incoming_owner = self._patient_from_reference(
                incoming_reference,
                {},
                source_namespace,
            )
            if incoming_owner is None or incoming_owner.id != mapping.patient_id:
                raise ValueError(
                    f"FHIR {resource_type}/{resource_id} is owned by another patient/source"
                )

    def _fhir_resource_reference_map(
        self,
        entries: List[Dict[str, Any]],
        resource_type: str,
    ) -> Dict[str, Dict[str, Any]]:
        resource_map: Dict[str, Dict[str, Any]] = {}
        for entry in entries:
            resource = entry["resource"]
            if resource.get("resourceType") != resource_type:
                continue
            resource_id = resource.get("id")
            full_url = entry.get("fullUrl")
            for key in (resource_id, f"{resource_type}/{resource_id}" if resource_id else None, full_url):
                if key:
                    normalized_key = str(key)
                    existing = resource_map.get(normalized_key)
                    if existing is not None and existing != resource:
                        raise ValueError(
                            f"FHIR {resource_type} reference {normalized_key} is duplicated with conflicting data"
                        )
                    resource_map[normalized_key] = resource
        return resource_map

    def _register_fhir_patient_references(
        self,
        patient_map: Dict[Any, Patient],
        patient: Patient,
        resource: Dict[str, Any],
        full_url: Optional[str],
    ) -> None:
        resource_id = resource.get("id")
        keys = [
            resource_id,
            f"Patient/{resource_id}" if resource_id else None,
            full_url,
        ]
        keys.extend(
            identifier_key
            for identifier in resource.get("identifier") or []
            if (identifier_key := self._fhir_patient_identifier_key(identifier))
        )
        conflicts = [
            str(key)
            for key in keys
            if key
            and key in patient_map
            and patient_map[key].id != patient.id
        ]
        if conflicts:
            raise ValueError(
                f"FHIR patient reference is ambiguous: {', '.join(sorted(set(conflicts)))}"
            )
        for key in keys:
            if key:
                patient_map[key] = patient

    def _upsert_patient_from_fhir(
        self,
        resource: Dict[str, Any],
        source_namespace: str,
    ) -> Tuple[Patient, bool]:
        resource_id = str(resource.get("id") or "").strip()
        if not resource_id:
            raise ValueError("FHIR Patient.id is required for source identity")

        mrn_identity = self._fhir_patient_mrn_identity(resource)
        mrn_system = mrn_identity[0] if mrn_identity else ""
        mrn = mrn_identity[1] if mrn_identity else None
        source_mappings = list(
            FHIRResourceMapping.objects.filter(
                fhir_resource_type="Patient",
                fhir_resource_id=resource_id,
            )[:2]
        )
        if len(source_mappings) > 1:
            raise ValueError(f"FHIR Patient/{resource_id} has multiple relational mappings")
        direct_id_matches = []
        try:
            direct_patient_id = uuid.UUID(resource_id)
        except (TypeError, ValueError):
            pass
        else:
            direct_id_matches = list(
                Patient.objects.filter(
                    id=direct_patient_id,
                    metadata_json__fhir_source_namespace=source_namespace,
                )
            )
        source_candidates = {
            str(patient.id): patient
            for patient in [
                *(
                    [source_mappings[0].patient]
                    if source_mappings and source_mappings[0].patient_id
                    else []
                ),
                *direct_id_matches,
                *Patient.objects.filter(
                    metadata_json__fhir_patient_id=resource_id,
                    metadata_json__fhir_source_namespace=source_namespace,
                ),
                *Patient.objects.filter(
                    source_system="fhir_import",
                    source_record_id=resource_id,
                    metadata_json__fhir_source_namespace=source_namespace,
                ),
            ]
        }
        if len(source_candidates) > 1:
            raise ValueError(f"FHIR Patient/{resource_id} resolves to multiple local patients")
        source_patient = next(iter(source_candidates.values()), None)

        mrn_matches = (
            list(
                Patient.objects.filter(
                    medical_record_number=mrn,
                    metadata_json__fhir_mrn_system=mrn_system,
                    metadata_json__fhir_source_namespace=source_namespace,
                )[:2]
            )
            if mrn and mrn_system
            else []
        )
        if len(mrn_matches) > 1:
            raise ValueError(f"FHIR MRN {mrn} resolves to multiple local patients")
        mrn_patient = mrn_matches[0] if mrn_matches else None
        if source_patient and mrn_patient and source_patient.id != mrn_patient.id:
            raise ValueError(
                f"FHIR Patient/{resource_id} source identity conflicts with MRN {mrn}"
            )

        patient = source_patient or mrn_patient
        if patient is not None:
            existing_fhir_id = str((patient.metadata_json or {}).get("fhir_patient_id") or "").strip()
            if existing_fhir_id and existing_fhir_id != resource_id:
                raise ValueError(
                    f"MRN {mrn} is already bound to FHIR Patient/{existing_fhir_id}"
                )
            existing_namespace = str(
                (patient.metadata_json or {}).get("fhir_source_namespace") or "unspecified"
            )
            if existing_fhir_id and existing_namespace != source_namespace:
                raise ValueError(
                    f"FHIR Patient/{resource_id} belongs to source namespace "
                    f"{existing_namespace}, not {source_namespace}"
                )
            existing_mrn_system = str(
                (patient.metadata_json or {}).get("fhir_mrn_system") or ""
            ).strip()
            if mrn and patient.medical_record_number not in (None, "", mrn):
                raise ValueError(
                    f"FHIR Patient/{resource_id} conflicts with its persisted MRN"
                )
            if mrn_system and existing_mrn_system and existing_mrn_system != mrn_system:
                raise ValueError(
                    f"FHIR Patient/{resource_id} conflicts with its persisted MRN system"
                )

        first_name, last_name = self._fhir_patient_name(resource)
        birth_date = self._parse_date(resource.get("birthDate"))
        gender_present = resource.get("gender") not in (None, "")
        sex = self._normalize_sex(resource.get("gender")) if gender_present else ""
        status = None
        if resource.get("active") is True:
            status = "active"
        elif resource.get("active") is False:
            status = "inactive"

        if patient is None:
            metadata = {
                "fhir_patient_id": resource_id,
                "fhir_source_namespace": source_namespace,
            }
            if mrn_system:
                metadata["fhir_mrn_system"] = mrn_system
            patient = Patient.objects.create(
                medical_record_number=mrn,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=birth_date,
                sex=sex,
                status=status or "unknown",
                source_system="fhir_import",
                source_record_id=resource_id,
                last_imported_at=timezone.now(),
                metadata_json=metadata,
            )
            return patient, True

        update_fields = ["source_system", "source_record_id", "last_imported_at", "metadata_json"]
        patient.source_system = "fhir_import"
        patient.source_record_id = resource_id
        patient.last_imported_at = timezone.now()
        metadata = dict(patient.metadata_json or {})
        metadata["fhir_patient_id"] = resource_id
        metadata["fhir_source_namespace"] = source_namespace
        if mrn_system:
            metadata["fhir_mrn_system"] = mrn_system
        patient.metadata_json = metadata

        supplied_values = {
            "medical_record_number": mrn,
            "first_name": first_name,
            "last_name": last_name,
            "date_of_birth": birth_date,
            "sex": sex if gender_present else None,
            "status": status,
        }
        for field, value in supplied_values.items():
            if value in (None, ""):
                continue
            setattr(patient, field, value)
            update_fields.append(field)
        patient.save(update_fields=[*dict.fromkeys(update_fields), "updated_at"])
        return patient, False

    def _fhir_patient_mrn_identity(
        self,
        resource: Dict[str, Any],
    ) -> Optional[Tuple[str, str]]:
        identities = {
            (
                str(identifier.get("system") or "").strip(),
                str(identifier.get("value")).strip(),
            )
            for identifier in resource.get("identifier") or []
            if self._is_explicit_mrn_identifier(identifier) and identifier.get("value")
        }
        if len(identities) > 1:
            raise ValueError("FHIR Patient has conflicting MRN identifiers")
        return next(iter(identities), None)

    def _fhir_patient_mrn(self, resource: Dict[str, Any]) -> Optional[str]:
        identity = self._fhir_patient_mrn_identity(resource)
        return identity[1] if identity else None

    def _fhir_patient_identifier_key(
        self,
        identifier: Any,
    ) -> Optional[Tuple[str, str, str]]:
        if not self._is_explicit_mrn_identifier(identifier):
            return None
        system = str(identifier.get("system") or "").strip()
        value = str(identifier.get("value") or "").strip()
        if not system or not value:
            return None
        return ("identifier", system, value)

    @staticmethod
    def _is_explicit_mrn_identifier(identifier: Any) -> bool:
        if not isinstance(identifier, dict) or not identifier.get("value"):
            return False
        type_codes = {
            str(coding.get("code") or "").strip().upper()
            for coding in (identifier.get("type") or {}).get("coding") or []
            if isinstance(coding, dict)
        }
        system = str(identifier.get("system") or "").strip().lower()
        normalized_system = system.replace("_", "-")
        return (
            "MR" in type_codes
            or "mrn" in normalized_system
            or "medical-record" in normalized_system
        )

    @staticmethod
    def _fhir_patient_name(resource: Dict[str, Any]) -> Tuple[str, str]:
        names = [name for name in resource.get("name") or [] if isinstance(name, dict)]
        name = next((item for item in names if item.get("use") == "official"), None)
        name = name or (names[0] if names else {})
        given = name.get("given") or []
        first_name = " ".join(str(value) for value in given if value) if isinstance(given, list) else str(given or "")
        last_name = str(name.get("family") or name.get("text") or "")
        return first_name.strip(), last_name.strip()

    def _ingest_fhir_observation(
        self,
        resource: Dict[str, Any],
        patient_map: Dict[Any, Patient],
        *,
        clinical_contexts: Optional[Dict[Tuple[str, str], Tuple[HealthScreening, Encounter]]] = None,
        encounter_resources: Optional[Dict[str, Dict[str, Any]]] = None,
        source_namespace: str,
    ) -> Tuple[bool, Patient, Observation]:
        patient = self._patient_from_subject(
            resource.get("subject") or {},
            patient_map,
            source_namespace,
        )
        if not patient:
            raise ValueError("Observation subject could not be resolved")

        resource_id = str(resource.get("id") or "").strip()
        if not resource_id:
            raise ValueError("FHIR Observation.id is required")

        effective_value = resource.get("effectiveDateTime") or resource.get("effectivePeriod", {}).get("start")
        screening_date = self._parse_date(effective_value) or timezone.now().date()
        screening_time = self._parse_datetime(effective_value) or timezone.now()
        screening, encounter, context_created = self._get_or_create_fhir_clinical_context(
            resource,
            patient,
            screening_date,
            screening_time,
            clinical_contexts if clinical_contexts is not None else {},
            encounter_resources or {},
        )

        loinc = self._loinc_code(resource.get("code", {}))
        mapping = FHIR_LOINC_MAP.get(loinc)
        coding = (resource.get("code", {}).get("coding") or [{}])[0]
        display = coding.get("display") or resource.get("code", {}).get("text") or ""
        code = coding.get("code") or loinc or ""
        if not code and not display:
            raise ValueError("FHIR Observation.code is required for relational mapping")

        category = self._fhir_category(resource)
        if not category and mapping:
            category = "laboratory" if mapping[0] == "lab" else "vital-signs"
        category = category or "unknown"
        observation_type = mapping[1] if mapping else self._slug(display or code)

        quantity = resource.get("valueQuantity") or {}
        components = []
        if resource.get("component"):
            for component in resource["component"]:
                component_loinc = self._loinc_code(component.get("code", {}))
                component_coding = (component.get("code", {}).get("coding") or [{}])[0]
                component_quantity = component.get("valueQuantity") or {}
                components.append(
                    {
                        "code": component_coding.get("code") or component_loinc or "",
                        "display": component_coding.get("display") or component.get("code", {}).get("text") or "",
                        "value": component_quantity.get("value"),
                        "unit": component_quantity.get("unit") or "",
                    }
                )

        value = quantity.get("value")
        value_string = str(resource.get("valueString") or "")
        value_boolean = resource.get("valueBoolean") if "valueBoolean" in resource else None
        value_json = {}
        if value in (None, "") and not value_string and value_boolean is None:
            raw_value = resource.get("valueCodeableConcept")
            if raw_value is not None:
                value_json = {"raw_value": raw_value}

        defaults = {
            "encounter": encounter,
            "observation_type": observation_type,
            "category": category,
            "source_type": "fhir_import",
            "code_system": coding.get("system") or ("http://loinc.org" if loinc else ""),
            "code": code,
            "display": display,
            "value_quantity": self._as_decimal(value),
            "value_unit": quantity.get("unit") or "",
            "value_string": value_string,
            "value_boolean": value_boolean,
            "value_json": value_json,
            "component_json": components,
            "status": resource.get("status") or "unknown",
            "effective_at": screening_time,
            "issued_at": self._parse_datetime(resource.get("issued")),
            "source_payload_json": self._json_safe(resource),
        }
        observation = self._existing_fhir_local(Observation, "Observation", resource_id)
        if observation is None:
            legacy_matches = list(
                Observation.objects.filter(
                    source_type="fhir_import",
                    source_payload_json__id=resource_id,
                )[:2]
            )
            if len(legacy_matches) > 1:
                raise ValueError(f"FHIR Observation/{resource_id} maps to multiple local observations")
            observation = legacy_matches[0] if legacy_matches else None
        if observation is not None and observation.patient_id != patient.id:
            raise ValueError(f"FHIR Observation/{resource_id} is already bound to another patient")
        if observation is None:
            observation = Observation.objects.create(patient=patient, **defaults)
        else:
            for field, field_value in defaults.items():
                setattr(observation, field, field_value)
            observation.save(update_fields=[*defaults.keys(), "updated_at"])
        return context_created, patient, observation

    def _ingest_fhir_condition(
        self,
        resource: Dict[str, Any],
        patient_map: Dict[Any, Patient],
        source_namespace: str,
    ) -> Tuple[Patient, Problem]:
        patient = self._patient_from_subject(
            resource.get("subject") or {},
            patient_map,
            source_namespace,
        )
        if not patient:
            raise ValueError("Condition subject could not be resolved")

        resource_id = str(resource.get("id") or "").strip()
        if not resource_id:
            raise ValueError("FHIR Condition.id is required")
        name = resource.get("code", {}).get("text")
        codings = resource.get("code", {}).get("coding") or []
        if not name:
            name = next(
                (
                    coding.get("display") or coding.get("code")
                    for coding in codings
                    if isinstance(coding, dict) and (coding.get("display") or coding.get("code"))
                ),
                None,
            )
        if not name:
            raise ValueError("FHIR Condition.code requires text, display, or code")
        status_code = "unknown"
        status_codings = resource.get("clinicalStatus", {}).get("coding") or []
        status_code = next(
            (
                str(coding.get("code"))
                for coding in status_codings
                if isinstance(coding, dict) and coding.get("code")
            ),
            "unknown",
        )

        problem = self._existing_fhir_local(Problem, "Condition", resource_id)
        if problem is not None and problem.patient_id != patient.id:
            raise ValueError(f"FHIR Condition/{resource_id} is already bound to another patient")
        if problem is None:
            problem = Problem.objects.create(
                patient=patient,
                problem_name=str(name)[:200],
                status=status_code,
            )
        else:
            problem.problem_name = str(name)[:200]
            problem.status = status_code
            problem.save(update_fields=["problem_name", "status", "updated_at"])
        return patient, problem

    def _ingest_fhir_questionnaire_response(
        self,
        resource: Dict[str, Any],
        patient_map: Dict[Any, Patient],
        source_namespace: str,
    ) -> Tuple[Patient, QuestionnaireResponse]:
        patient = self._patient_from_subject(
            resource.get("subject") or {},
            patient_map,
            source_namespace,
        )
        if not patient:
            raise ValueError("QuestionnaireResponse subject could not be resolved")

        resource_id = str(resource.get("id") or "").strip()
        if not resource_id:
            raise ValueError("FHIR QuestionnaireResponse.id is required")

        response_json: Dict[str, Any] = {}
        self._collect_fhir_questionnaire_items(resource.get("item") or [], response_json)
        questionnaire_reference = str(resource.get("questionnaire") or "").strip()
        questionnaire = None
        if questionnaire_reference:
            questionnaire, _ = Questionnaire.objects.get_or_create(
                title=questionnaire_reference[:200],
                version="FHIR-R4",
                defaults={
                    "status": "unknown",
                    "code_system": "http://hl7.org/fhir/Questionnaire",
                    "code": self._slug(questionnaire_reference)[:100],
                    "questionnaire_json": {"reference": questionnaire_reference},
                },
            )
        authored_at = self._parse_datetime(resource.get("authored")) or timezone.now()
        defaults = {
            "questionnaire": questionnaire,
            "authored_at": authored_at,
            "status": resource.get("status") or "unknown",
            "source_type": "fhir_import",
            "response_json": response_json,
            "score_json": {},
            "metadata_json": {
                "fhir_resource_id": resource_id,
                "questionnaire_reference": questionnaire_reference,
            },
        }
        existing = self._existing_fhir_local(
            QuestionnaireResponse,
            "QuestionnaireResponse",
            resource_id,
        )
        if existing is None and resource_id:
            legacy_matches = list(
                QuestionnaireResponse.objects.filter(
                    metadata_json__fhir_resource_id=resource_id,
                )[:2]
            )
            if len(legacy_matches) > 1:
                raise ValueError(
                    f"FHIR QuestionnaireResponse/{resource_id} maps to multiple local responses"
                )
            existing = legacy_matches[0] if legacy_matches else None
        if existing is not None and existing.patient_id != patient.id:
            raise ValueError(
                f"FHIR QuestionnaireResponse/{resource_id} is already bound to another patient"
            )
        if existing:
            for field, value in defaults.items():
                setattr(existing, field, value)
            existing.save(update_fields=[*defaults.keys(), "updated_at"])
            questionnaire_response = existing
        else:
            questionnaire_response = QuestionnaireResponse.objects.create(patient=patient, **defaults)
        return patient, questionnaire_response

    def _collect_fhir_questionnaire_items(
        self,
        items: Iterable[Dict[str, Any]],
        target: Dict[str, Any],
    ) -> None:
        for item in items:
            if not isinstance(item, dict):
                continue
            link_id = str(item.get("linkId") or item.get("text") or "").strip()
            answers = item.get("answer") or []
            values = []
            for answer in answers:
                if not isinstance(answer, dict):
                    continue
                value = self._fhir_questionnaire_answer_value(answer)
                if value is not None:
                    values.append(value)
                self._collect_fhir_questionnaire_items(answer.get("item") or [], target)
            if link_id and values:
                target[link_id] = values[0] if len(values) == 1 else values
            self._collect_fhir_questionnaire_items(item.get("item") or [], target)

    def _fhir_questionnaire_answer_value(self, answer: Dict[str, Any]) -> Any:
        for key in (
            "valueBoolean",
            "valueInteger",
            "valueDecimal",
            "valueString",
            "valueDate",
            "valueDateTime",
        ):
            if key in answer:
                return answer[key]
        coding = answer.get("valueCoding")
        if isinstance(coding, dict):
            return coding.get("code") or coding.get("display")
        concept = answer.get("valueCodeableConcept")
        if isinstance(concept, dict):
            codings = concept.get("coding") or []
            if codings:
                return codings[0].get("code") or codings[0].get("display")
            return concept.get("text")
        quantity = answer.get("valueQuantity")
        if isinstance(quantity, dict):
            return quantity.get("value")
        return None

    def _ingest_fhir_encounter(
        self,
        resource: Dict[str, Any],
        full_url: Optional[str],
        patient_map: Dict[Any, Patient],
        clinical_contexts: Dict[Tuple[str, str], Tuple[HealthScreening, Encounter]],
        encounter_resources: Dict[str, Dict[str, Any]],
        source_namespace: str,
    ) -> Tuple[bool, Patient, Encounter]:
        patient = self._patient_from_subject(
            resource.get("subject") or {},
            patient_map,
            source_namespace,
        )
        if not patient:
            raise ValueError("Encounter subject could not be resolved")
        resource_id = str(resource.get("id") or "").strip()
        if not resource_id:
            raise ValueError("FHIR Encounter.id is required")

        encounter_reference = str(full_url or f"Encounter/{resource_id}")
        period = resource.get("period") or {}
        context_time = self._parse_datetime(period.get("start")) or timezone.now()
        context_date = self._parse_date(period.get("start")) or context_time.date()
        _, encounter, context_created = self._get_or_create_fhir_clinical_context(
            {
                "encounter": {"reference": encounter_reference},
                "effectiveDateTime": period.get("start"),
            },
            patient,
            context_date,
            context_time,
            clinical_contexts,
            encounter_resources,
        )
        for token in {encounter_reference, resource_id, f"Encounter/{resource_id}", full_url}:
            if token:
                clinical_contexts[(str(patient.id), str(token))] = (
                    encounter.source_screening,
                    encounter,
                )
        return context_created, patient, encounter

    def _get_or_create_fhir_clinical_context(
        self,
        observation: Dict[str, Any],
        patient: Patient,
        screening_date: date,
        screening_time: datetime,
        clinical_contexts: Dict[Tuple[str, str], Tuple[HealthScreening, Encounter]],
        encounter_resources: Dict[str, Dict[str, Any]],
    ) -> Tuple[HealthScreening, Encounter, bool]:
        encounter_reference = str((observation.get("encounter") or {}).get("reference") or "")
        encounter_resource = encounter_resources.get(encounter_reference)
        if not encounter_resource and encounter_reference:
            encounter_resource = encounter_resources.get(encounter_reference.split("/")[-1])

        period = (encounter_resource or {}).get("period") or {}
        context_time = self._parse_datetime(period.get("start")) or screening_time
        context_date = self._parse_date(period.get("start")) or screening_date
        encounter_resource_id = (encounter_resource or {}).get("id")
        context_tokens = {
            token
            for token in (
                encounter_reference,
                encounter_resource_id,
                f"Encounter/{encounter_resource_id}" if encounter_resource_id else None,
            )
            if token
        }
        if not context_tokens:
            context_tokens = {f"date:{context_date.isoformat()}"}
        for context_token in context_tokens:
            context_key = (str(patient.id), str(context_token))
            if context_key in clinical_contexts:
                screening, encounter = clinical_contexts[context_key]
                return screening, encounter, False

        identifier_token = encounter_resource_id or (
            encounter_reference.split("/")[-1] if encounter_reference else f"DATE-{context_date.isoformat()}"
        )
        encounter_identifier = f"FHIR-{identifier_token}"[:100]
        screenings = list(
            HealthScreening.objects.filter(
                patient=patient,
                encounter_identifier=encounter_identifier,
                is_active=True,
            )
            .order_by("created_at")
            [:2]
        )
        if len(screenings) > 1:
            raise ValueError(f"FHIR Encounter/{identifier_token} maps to multiple screenings")
        screening = screenings[0] if screenings else None
        screening_created = screening is None
        if screening is None:
            screening = HealthScreening.objects.create(
                patient=patient,
                screening_date=context_date,
                encounter_type=self._fhir_encounter_type(encounter_resource),
                encounter_identifier=encounter_identifier,
                encounter_time=context_time,
            )
        else:
            screening.screening_date = context_date
            screening.encounter_type = self._fhir_encounter_type(encounter_resource)
            screening.encounter_time = context_time
            screening.save(
                update_fields=[
                    "screening_date",
                    "encounter_type",
                    "encounter_time",
                    "updated_at",
                ]
            )

        encounters = list(
            Encounter.objects.filter(
                source_screening=screening,
                source_type="fhir_import",
                is_active=True,
            ).order_by("created_at")[:2]
        )
        if len(encounters) > 1:
            raise ValueError(f"FHIR Encounter/{identifier_token} maps to multiple local encounters")
        encounter = encounters[0] if encounters else None
        encounter_defaults = {
            "encounter_type": self._fhir_encounter_type(encounter_resource),
            "status": (encounter_resource or {}).get("status") or "unknown",
            "reason": self._fhir_encounter_reason(encounter_resource),
            "location": self._fhir_encounter_location(encounter_resource),
            "started_at": context_time,
            "ended_at": self._parse_datetime(period.get("end")),
            "source_type": "fhir_import",
            "metadata_json": {
                "fhir_encounter_reference": encounter_reference,
                "fhir_encounter_id": encounter_resource_id,
            },
        }
        if encounter is None:
            encounter = Encounter.objects.create(
                patient=patient,
                source_screening=screening,
                **encounter_defaults,
            )
        else:
            if encounter.patient_id != patient.id:
                raise ValueError(f"FHIR Encounter/{identifier_token} is already bound to another patient")
            for field, field_value in encounter_defaults.items():
                setattr(encounter, field, field_value)
            encounter.save(update_fields=[*encounter_defaults.keys(), "updated_at"])

        for context_token in context_tokens:
            clinical_contexts[(str(patient.id), str(context_token))] = (screening, encounter)
        return screening, encounter, screening_created

    def _fhir_encounter_type(self, resource: Optional[Dict[str, Any]]) -> str:
        if not resource:
            return "fhir_import"
        for concept in resource.get("type") or []:
            coding = (concept.get("coding") or [{}])[0]
            value = coding.get("display") or coding.get("code") or concept.get("text")
            if value:
                return str(value)[:100]
        encounter_class = resource.get("class") or {}
        return str(encounter_class.get("display") or encounter_class.get("code") or "fhir_import")[:100]

    def _fhir_encounter_reason(self, resource: Optional[Dict[str, Any]]) -> str:
        if not resource:
            return ""
        reasons = resource.get("reasonCode") or []
        if not reasons:
            return ""
        reason = reasons[0]
        coding = (reason.get("coding") or [{}])[0]
        return str(reason.get("text") or coding.get("display") or coding.get("code") or "")[:250]

    def _fhir_encounter_location(self, resource: Optional[Dict[str, Any]]) -> str:
        if not resource:
            return ""
        locations = resource.get("location") or []
        if not locations:
            return ""
        location = locations[0].get("location") or {}
        return str(location.get("display") or location.get("reference") or "")[:250]

    def _persist_fhir_resource(
        self,
        resource: Dict[str, Any],
        *,
        source_namespace: str,
        patient: Optional[Patient] = None,
        local_object: Any = None,
    ) -> FHIRResource:
        resource_type = str(resource.get("resourceType") or "").strip()
        resource_id = str(resource.get("id") or "").strip()
        if not resource_type or not resource_id:
            raise ValueError("FHIR resourceType and id are required for persistence")
        existing_resource = FHIRResource.objects.filter(
            resource_type=resource_type,
            resource_id=resource_id,
        ).first()
        if existing_resource is not None:
            existing_namespace = str(
                existing_resource.origin_namespace or "unspecified"
            ).strip()
            if existing_namespace != source_namespace:
                raise ValueError(
                    f"FHIR {resource_type}/{resource_id} belongs to source namespace "
                    f"{existing_namespace}, not {source_namespace}"
                )
            if patient is not None:
                self._assert_fhir_resource_ownership(
                    existing_resource,
                    resource,
                    patient,
                    local_object,
                )
        persisted_resource, _ = FHIRResource.objects.update_or_create(
            resource_type=resource_type,
            resource_id=resource_id,
            defaults={
                "resource_data": self._json_safe(resource),
                "origin_namespace": source_namespace,
                "is_active": True,
            },
        )
        return persisted_resource

    def _assert_fhir_resource_ownership(
        self,
        persisted_resource: FHIRResource,
        incoming_resource: Dict[str, Any],
        patient: Patient,
        local_object: Any,
    ) -> None:
        resource_type = persisted_resource.resource_type
        resource_id = persisted_resource.resource_id
        mappings = list(
            FHIRResourceMapping.objects.filter(
                fhir_resource_type=resource_type,
                fhir_resource_id=resource_id,
            )[:2]
        )
        if len(mappings) > 1:
            raise ValueError(f"FHIR {resource_type}/{resource_id} has multiple owners")
        if mappings:
            mapping = mappings[0]
            if mapping.patient_id and mapping.patient_id != patient.id:
                raise ValueError(
                    f"FHIR {resource_type}/{resource_id} is owned by another patient"
                )
            if local_object is not None:
                local_table = local_object._meta.db_table
                if mapping.local_table != local_table:
                    raise ValueError(
                        f"FHIR {resource_type}/{resource_id} is owned by {mapping.local_table}"
                    )
                if mapping.local_id != local_object.pk and local_object.__class__.objects.filter(
                    pk=mapping.local_id
                ).exists():
                    raise ValueError(
                        f"FHIR {resource_type}/{resource_id} is owned by another local row"
                    )
            return

        raise ValueError(
            f"FHIR {resource_type}/{resource_id} exists without ownership mapping"
        )

    def _sync_fhir_mapping(
        self,
        persisted_resource: FHIRResource,
        resource: Dict[str, Any],
        local_object: Any,
        patient: Patient,
        source_namespace: str,
    ) -> FHIRResourceMapping:
        resource_type = persisted_resource.resource_type
        resource_id = persisted_resource.resource_id
        local_table = local_object._meta.db_table
        local_id = local_object.pk

        fhir_mappings = list(
            FHIRResourceMapping.objects.filter(
                fhir_resource_type=resource_type,
                fhir_resource_id=resource_id,
            )[:2]
        )
        if len(fhir_mappings) > 1:
            raise ValueError(f"FHIR {resource_type}/{resource_id} has multiple relational mappings")
        fhir_mapping = fhir_mappings[0] if fhir_mappings else None
        local_mapping = FHIRResourceMapping.objects.filter(
            local_table=local_table,
            local_id=local_id,
            fhir_resource_type=resource_type,
        ).first()
        if fhir_mapping and local_mapping and fhir_mapping.id != local_mapping.id:
            raise ValueError(
                f"FHIR {resource_type}/{resource_id} conflicts with the existing local mapping"
            )

        mapping = fhir_mapping or local_mapping
        if mapping is not None:
            if mapping.local_table != local_table:
                raise ValueError(
                    f"FHIR {resource_type}/{resource_id} is already mapped to {mapping.local_table}"
                )
            if mapping.patient_id and mapping.patient_id != patient.id:
                raise ValueError(
                    f"FHIR {resource_type}/{resource_id} is already mapped to another patient"
                )
            if local_mapping and local_mapping.fhir_resource_id != resource_id:
                raise ValueError(
                    f"{local_table}/{local_id} is already mapped to a different {resource_type}"
                )

        profiles = (resource.get("meta") or {}).get("profile") or []
        if isinstance(profiles, str):
            profiles = [profiles]
        values = {
            "patient": patient,
            "fhir_resource_ref": persisted_resource,
            "local_table": local_table,
            "local_id": local_id,
            "fhir_resource_type": resource_type,
            "fhir_resource_id": resource_id,
            "profile_url": str(profiles[0]) if profiles else "",
            "fhir_json": self._json_safe(resource),
            "sync_status": "synced",
            "last_synced_at": timezone.now(),
            "error_message": "",
            "metadata_json": {
                "source": "fhir_import",
                "source_namespace": source_namespace,
            },
        }
        if mapping is None:
            mapping = FHIRResourceMapping.objects.create(**values)
        else:
            for field, value in values.items():
                setattr(mapping, field, value)
            mapping.save(update_fields=[*values.keys(), "updated_at"])
        return mapping

    def _existing_fhir_local(
        self,
        model,
        resource_type: str,
        resource_id: str,
    ):
        if not resource_id:
            return None
        mappings = list(
            FHIRResourceMapping.objects.filter(
                fhir_resource_type=resource_type,
                fhir_resource_id=resource_id,
            )[:2]
        )
        if len(mappings) > 1:
            raise ValueError(f"FHIR {resource_type}/{resource_id} has multiple relational mappings")
        if not mappings:
            return None
        mapping = mappings[0]
        if mapping.local_table != model._meta.db_table:
            raise ValueError(
                f"FHIR {resource_type}/{resource_id} is mapped to unexpected table {mapping.local_table}"
            )
        return model.objects.filter(pk=mapping.local_id).first()

    def _patient_from_reference(
        self,
        reference: Optional[str],
        patient_map: Dict[Any, Patient],
        source_namespace: str,
    ) -> Optional[Patient]:
        if not reference:
            return None
        reference = str(reference).strip()
        if reference in patient_map:
            return patient_map[reference]
        patient_id = reference.rstrip("/").split("/")[-1]
        mapped_patient = patient_map.get(patient_id) or patient_map.get(f"Patient/{patient_id}")
        if mapped_patient:
            return mapped_patient

        mappings = list(
            FHIRResourceMapping.objects.filter(
                fhir_resource_type="Patient",
                fhir_resource_id=patient_id,
            ).select_related("patient", "fhir_resource_ref")[:2]
        )
        if len(mappings) > 1:
            raise ValueError(f"Patient reference {reference} has multiple relational mappings")
        if mappings:
            mapping = mappings[0]
            mapping_namespace = str(
                (
                    mapping.fhir_resource_ref.origin_namespace
                    if mapping.fhir_resource_ref_id
                    else (mapping.metadata_json or {}).get("source_namespace")
                )
                or "unspecified"
            ).strip()
            if mapping_namespace != source_namespace:
                raise ValueError(
                    f"Patient reference {reference} belongs to source namespace "
                    f"{mapping_namespace}, not {source_namespace}"
                )
            if mapping.patient_id is None:
                raise ValueError(f"Patient reference {reference} has no patient owner")
            return mapping.patient

        candidates: Dict[str, Patient] = {}
        try:
            direct_patient_id = uuid.UUID(patient_id)
        except (TypeError, ValueError):
            pass
        else:
            for patient in Patient.objects.filter(
                id=direct_patient_id,
                metadata_json__fhir_source_namespace=source_namespace,
            ):
                candidates[str(patient.id)] = patient
        for patient in Patient.objects.filter(
            metadata_json__fhir_patient_id=patient_id,
            metadata_json__fhir_source_namespace=source_namespace,
        )[:2]:
            candidates[str(patient.id)] = patient
        for patient in Patient.objects.filter(
            source_system="fhir_import",
            source_record_id=patient_id,
            metadata_json__fhir_source_namespace=source_namespace,
        )[:2]:
            candidates[str(patient.id)] = patient
        if len(candidates) > 1:
            raise ValueError(f"Patient reference {reference} resolves to multiple local patients")
        return next(iter(candidates.values()), None)

    def _patient_from_subject(
        self,
        subject: Dict[str, Any],
        patient_map: Dict[Any, Patient],
        source_namespace: str,
    ) -> Optional[Patient]:
        patient = self._patient_from_reference(
            subject.get("reference"),
            patient_map,
            source_namespace,
        )
        if patient:
            return patient
        identifier = subject.get("identifier") or {}
        identifier_key = self._fhir_patient_identifier_key(identifier)
        if identifier_key is None:
            return None
        mapped_patient = patient_map.get(identifier_key)
        if mapped_patient:
            return mapped_patient
        _, identifier_system, identifier_value = identifier_key
        matches = list(
            Patient.objects.filter(
                medical_record_number=identifier_value,
                metadata_json__fhir_mrn_system=identifier_system,
                metadata_json__fhir_source_namespace=source_namespace,
            )[:2]
        )
        if len(matches) > 1:
            raise ValueError(
                f"Patient identifier {identifier_value} resolves to multiple local patients"
            )
        return matches[0] if matches else None

    def _loinc_code(self, code: Dict[str, Any]) -> Optional[str]:
        for coding in code.get("coding") or []:
            if coding.get("system") == "http://loinc.org":
                return coding.get("code")
        return None

    def _fhir_category(self, resource: Dict[str, Any]) -> str:
        for category in resource.get("category") or []:
            for coding in category.get("coding") or []:
                if coding.get("code"):
                    return coding["code"]
        return ""

    def _get_value(self, data: Dict[str, Any], keys: Iterable[str]) -> Any:
        lowered = {str(key).lower(): value for key, value in data.items()}
        for key in keys:
            value = data.get(key)
            if not self._is_missing(value):
                return value
            value = lowered.get(str(key).lower())
            if not self._is_missing(value):
                return value
        return None

    def _core_source_payload(self, payload: Dict[str, Any], *section_keys: str) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            return {}
        nested_source_keys = {
            "a1_key_in",
            "a1KeyIn",
            "core_a1_key_in",
            "hq",
            "questionnaire",
            "questionnaire_response",
            "vital_signs",
            "laboratory_results",
            "labs",
            "assessments",
            "lifestyle",
            "problems",
        }
        merged = {
            key: value
            for key, value in payload.items()
            if key not in nested_source_keys and not isinstance(value, (dict, list))
        }
        for key in ("a1_key_in", "a1KeyIn", "core_a1_key_in"):
            value = payload.get(key)
            if isinstance(value, dict):
                merged.update(value)
        for key in section_keys:
            value = payload.get(key)
            if isinstance(value, dict):
                merged.update(value)
        return merged

    def _first(self, data: Dict[str, Any], keys: Iterable[str]) -> Any:
        if not isinstance(data, dict):
            return None
        return self._get_value(data, keys)

    def _parse_date(self, value: Any) -> Optional[date]:
        if self._is_missing(value):
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            return None
        return parsed.date()

    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        if self._is_missing(value):
            return None
        if isinstance(value, datetime):
            return value
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            return None
        if timezone.is_naive(parsed.to_pydatetime()):
            return timezone.make_aware(parsed.to_pydatetime())
        return parsed.to_pydatetime()

    def _as_decimal(self, value: Any) -> Optional[Any]:
        if self._is_missing(value):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _as_bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if self._is_missing(value):
            return False
        return str(value).strip().lower() in {"1", "true", "yes", "y", "current", "treated"}

    def _normalize_sex(self, value: Any) -> str:
        normalized = str(value or "").strip().lower()
        if normalized in {"m", "male"}:
            return "M"
        if normalized in {"f", "female"}:
            return "F"
        if normalized in {"o", "other"}:
            return "O"
        return "U"

    def _slug(self, value: Any) -> str:
        normalized = "".join(char.lower() if char.isalnum() else "_" for char in str(value or ""))
        while "__" in normalized:
            normalized = normalized.replace("__", "_")
        return normalized.strip("_")[:100] or "observation"

    def _json_safe(self, value: Any) -> Any:
        if self._is_missing(value):
            return None
        if isinstance(value, dict):
            return {str(key): self._json_safe(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._json_safe(item) for item in value]
        if isinstance(value, tuple):
            return [self._json_safe(item) for item in value]
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if hasattr(value, "isoformat") and not isinstance(value, str):
            try:
                return value.isoformat()
            except (TypeError, ValueError):
                pass
        if value != value:
            return None
        return value

    def _is_missing(self, value: Any) -> bool:
        if value in [None, ""]:
            return True
        if isinstance(value, (dict, list, tuple, set)):
            return False
        try:
            return bool(pd.isna(value))
        except (TypeError, ValueError):
            return False
