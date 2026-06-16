import json
from datetime import date, datetime
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import pandas as pd
from django.db import transaction
from django.utils import timezone

from apps.clinical.patients.models import Patient
from apps.integration.fhir_integration.models import FHIRResource

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
}


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

    def import_fhir(self, fhir_data: Any, data_format: str = "json") -> Dict[str, Any]:
        if isinstance(fhir_data, str) and data_format == "json":
            fhir_data = json.loads(fhir_data)

        resources = self._extract_fhir_resources(fhir_data)
        patient_map: Dict[str, Patient] = {}
        created_patients = 0
        created_screenings = 0
        errors = []

        for resource in resources:
            if resource.get("resourceType") != "Patient":
                continue
            try:
                patient, created = self._upsert_patient_from_fhir(resource)
                created_patients += 1 if created else 0
                resource_id = resource.get("id")
                if resource_id:
                    patient_map[resource_id] = patient
                    patient_map[f"Patient/{resource_id}"] = patient
                self._persist_fhir_resource(resource)
            except Exception as exc:
                errors.append(f"Patient/{resource.get('id', 'unknown')}: {exc}")

        for resource in resources:
            if resource.get("resourceType") == "Patient":
                continue
            try:
                self._persist_fhir_resource(resource)
                if resource.get("resourceType") == "Observation":
                    if self._ingest_fhir_observation(resource, patient_map):
                        created_screenings += 1
                elif resource.get("resourceType") == "Condition":
                    self._ingest_fhir_condition(resource, patient_map)
            except Exception as exc:
                errors.append(f"{resource.get('resourceType')}/{resource.get('id', 'unknown')}: {exc}")

        return {
            "success_count": len(resources) - len(errors),
            "error_count": len(errors),
            "total_count": len(resources),
            "created_patients": created_patients,
            "created_screenings": created_screenings,
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
        if (
            data.get("systolic_blood_pressure") is not None
            and data.get("diastolic_blood_pressure") is not None
            and data.get("average_blood_pressure") is None
        ):
            data["average_blood_pressure"] = round(
                (data["systolic_blood_pressure"] + 2 * data["diastolic_blood_pressure"]) / 3
            )
        return VitalSigns.objects.create(health_screening=screening, **data)

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

    def _extract_fhir_resources(self, fhir_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not isinstance(fhir_data, dict):
            raise ValueError("FHIR data must be a JSON object")
        if fhir_data.get("resourceType") == "Bundle":
            return [entry.get("resource") for entry in fhir_data.get("entry", []) if entry.get("resource")]
        if fhir_data.get("resourceType"):
            return [fhir_data]
        raise ValueError("FHIR resourceType is required")

    def _upsert_patient_from_fhir(self, resource: Dict[str, Any]) -> Tuple[Patient, bool]:
        identifiers = resource.get("identifier") or []
        mrn = next((item.get("value") for item in identifiers if item.get("value")), None) or resource.get("id")
        if not mrn:
            raise ValueError("FHIR Patient.id or identifier is required")

        name = (resource.get("name") or [{}])[0]
        given = name.get("given") or []
        first_name = " ".join(given) if isinstance(given, list) else str(given)
        last_name = name.get("family") or str(mrn)
        birth_date = self._parse_date(resource.get("birthDate")) or date(1900, 1, 1)

        return Patient.objects.update_or_create(
            medical_record_number=str(mrn),
            defaults={
                "first_name": first_name or "Unknown",
                "last_name": last_name,
                "date_of_birth": birth_date,
                "sex": self._normalize_sex(resource.get("gender")),
                "status": "active" if resource.get("active", True) else "inactive",
            },
        )

    def _ingest_fhir_observation(self, resource: Dict[str, Any], patient_map: Dict[str, Patient]) -> bool:
        patient = self._patient_from_reference(resource.get("subject", {}).get("reference"), patient_map)
        if not patient:
            raise ValueError("Observation subject could not be resolved")

        effective_value = resource.get("effectiveDateTime") or resource.get("effectivePeriod", {}).get("start")
        screening_date = self._parse_date(effective_value) or timezone.now().date()
        screening_time = self._parse_datetime(effective_value) or timezone.now()
        screening = HealthScreening.objects.create(
            patient=patient,
            screening_date=screening_date,
            encounter_type="fhir_import",
            encounter_time=screening_time,
        )
        encounter = Encounter.objects.create(
            patient=patient,
            source_screening=screening,
            encounter_type="fhir_import",
            status="finished",
            reason="FHIR Observation import",
            started_at=screening_time,
            ended_at=screening_time,
            source_type="fhir_import",
            metadata_json={"fhir_observation_id": resource.get("id")},
        )

        if resource.get("component"):
            vital_data = {}
            components = []
            for component in resource["component"]:
                loinc = self._loinc_code(component.get("code", {}))
                mapping = FHIR_LOINC_MAP.get(loinc)
                if mapping and mapping[0] == "vital":
                    vital_data[mapping[1]] = component.get("valueQuantity", {}).get("value")
                coding = (component.get("code", {}).get("coding") or [{}])[0]
                quantity = component.get("valueQuantity") or {}
                components.append(
                    {
                        "code": coding.get("code") or loinc,
                        "display": coding.get("display") or component.get("code", {}).get("text") or "",
                        "value": quantity.get("value"),
                        "unit": quantity.get("unit") or quantity.get("code") or "",
                    }
                )
            if vital_data:
                self._create_vital_signs(screening, vital_data)
            loinc = self._loinc_code(resource.get("code", {}))
            coding = (resource.get("code", {}).get("coding") or [{}])[0]
            Observation.objects.create(
                patient=patient,
                encounter=encounter,
                observation_type=self._slug(coding.get("display") or resource.get("code", {}).get("text") or loinc or "fhir_observation"),
                category=self._fhir_category(resource) or "vital-signs",
                source_type="fhir_import",
                code_system=coding.get("system") or "http://loinc.org",
                code=coding.get("code") or loinc or "",
                display=coding.get("display") or resource.get("code", {}).get("text") or "",
                component_json=components,
                status=resource.get("status") or "final",
                effective_at=screening_time,
                source_payload_json=self._json_safe(resource),
            )
            return True

        loinc = self._loinc_code(resource.get("code", {}))
        mapping = FHIR_LOINC_MAP.get(loinc)
        value = resource.get("valueQuantity", {}).get("value")
        unit = resource.get("valueQuantity", {}).get("unit") or ""
        if mapping and mapping[0] == "vital":
            self._create_vital_signs(screening, {mapping[1]: value})
        elif mapping and mapping[0] == "lab":
            LaboratoryResults.objects.create(
                health_screening=screening,
                test_name=mapping[1],
                value_result=str(value),
                result_unit=unit or mapping[2],
                result_status=resource.get("status") or "final",
            )
        coding = (resource.get("code", {}).get("coding") or [{}])[0]
        Observation.objects.create(
            patient=patient,
            encounter=encounter,
            observation_type=mapping[1] if mapping else self._slug(coding.get("display") or resource.get("code", {}).get("text") or loinc or "fhir_observation"),
            category=self._fhir_category(resource) or ("laboratory" if mapping and mapping[0] == "lab" else "vital-signs"),
            source_type="fhir_import",
            code_system=coding.get("system") or "http://loinc.org",
            code=coding.get("code") or loinc or "",
            display=coding.get("display") or resource.get("code", {}).get("text") or (mapping[1] if mapping else ""),
            value_quantity=self._as_decimal(value),
            value_unit=unit or (mapping[2] if mapping and len(mapping) > 2 else ""),
            value_json={} if value not in [None, ""] else {"raw_value": resource.get("valueString") or resource.get("valueCodeableConcept")},
            status=resource.get("status") or "final",
            effective_at=screening_time,
            source_payload_json=self._json_safe(resource),
        )
        return True

    def _ingest_fhir_condition(self, resource: Dict[str, Any], patient_map: Dict[str, Patient]) -> None:
        patient = self._patient_from_reference(resource.get("subject", {}).get("reference"), patient_map)
        if not patient:
            raise ValueError("Condition subject could not be resolved")

        name = resource.get("code", {}).get("text")
        if not name:
            codings = resource.get("code", {}).get("coding") or []
            name = codings[0].get("display") if codings else None
        if not name:
            name = "FHIR Condition"
        status_code = "active"
        status_codings = resource.get("clinicalStatus", {}).get("coding") or []
        if status_codings:
            status_code = status_codings[0].get("code") or "active"

        Problem.objects.get_or_create(patient=patient, problem_name=name, defaults={"status": status_code})

    def _persist_fhir_resource(self, resource: Dict[str, Any]) -> None:
        resource_type = resource.get("resourceType")
        resource_id = resource.get("id")
        if not resource_type or not resource_id:
            return
        FHIRResource.objects.update_or_create(
            resource_type=resource_type,
            resource_id=resource_id,
            defaults={"resource_data": resource},
        )

    def _patient_from_reference(self, reference: Optional[str], patient_map: Dict[str, Patient]) -> Optional[Patient]:
        if not reference:
            return None
        if reference in patient_map:
            return patient_map[reference]
        patient_id = reference.split("/")[-1]
        return patient_map.get(patient_id) or Patient.objects.filter(id=patient_id).first() or Patient.objects.filter(medical_record_number=patient_id).first()

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
