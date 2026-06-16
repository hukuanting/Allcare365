"""
Smoke verification for the AllCare365 CORE.xlsx disease risk engine.
"""
from datetime import date, datetime, timezone as dt_timezone
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medical_system.settings")

import django

django.setup()

from apps.clinical.health_screening.models import Observation
from apps.clinical.patients.models import Patient
from apps.integration.fhir_integration.models import AuditLog, FHIRResourceMapping
from services.disease_risk_engine import DiseaseRiskAssessmentService
from services.disease_risk_engine.repository import DiseaseRiskInputRepository


def verify_system():
    patient = Patient.objects.filter(medical_record_number="AC365-SEED-001").first()
    if not patient:
        raise SystemExit("Seed patient AC365-SEED-001 not found. Run manage.py seed_product_schema_v1 first.")

    result = DiseaseRiskAssessmentService().calculate_dynamic_risk(str(patient.id))
    if result.get("error"):
        raise SystemExit(result["error"])

    disease_results = result.get("disease_risk_results", [])
    expected_algorithms = {
        "framingham_diabetes",
        "chinese_diabetes",
        "metabolic_syndrome",
        "nafld_fibrosis",
        "framingham_fatty_liver",
        "ausdrisk_diabetes",
        "vascular_caide",
    }
    actual_algorithms = {item.get("algorithm") for item in disease_results}
    missing_algorithms = expected_algorithms - actual_algorithms
    if missing_algorithms:
        raise SystemExit(f"Missing disease risk algorithms: {sorted(missing_algorithms)}")

    missing = result.get("data_summary", {}).get("missing_data", [])
    if missing:
        raise SystemExit(f"Risk input missing data: {missing}")

    mappings = FHIRResourceMapping.objects.filter(
        patient=patient,
        local_table="ai_analysis_results",
        fhir_resource_type="RiskAssessment",
    )
    if not mappings.exists():
        raise SystemExit("FHIR RiskAssessment mapping was not created.")

    audits = AuditLog.objects.filter(patient=patient, action="disease_risk_assess")
    if not audits.exists():
        raise SystemExit("Disease risk audit log was not created.")

    uacr_count = Observation.objects.filter(
        patient=patient,
        observation_type="urine_albumin_creatinine_ratio",
    ).count()

    print("Disease risk engine verification passed.")
    print(f"Patient: {patient.id}")
    print(f"Results: {[(item['algorithm'], item['risk_percentage']) for item in disease_results]}")
    print(f"RiskAssessment mappings: {mappings.count()}")
    print(f"UACR observations: {uacr_count}")


def verify_latest_available_field_selection():
    mrn = "AC365-ABC-SOURCE-TEST"
    Patient.objects.filter(medical_record_number=mrn).delete()
    patient = Patient.objects.create(
        medical_record_number=mrn,
        first_name="ABC",
        last_name="Selector",
        date_of_birth=date(1975, 1, 1),
        sex="M",
    )
    try:
        check_a = datetime(2024, 6, 11, tzinfo=dt_timezone.utc)
        check_b = datetime(2025, 6, 11, tzinfo=dt_timezone.utc)
        check_c = datetime(2026, 5, 11, tzinfo=dt_timezone.utc)

        def add_observation(category, observation_type, code, display, value, unit, effective_at):
            Observation.objects.create(
                patient=patient,
                observation_type=observation_type,
                category=category,
                code_system="http://loinc.org",
                code=code,
                display=display,
                value_quantity=value,
                value_unit=unit,
                effective_at=effective_at,
            )

        add_observation(
            "laboratory",
            "urine_albumin_creatinine_ratio",
            "9318-7",
            "Albumin/Creatinine",
            88,
            "mg/g",
            check_a,
        )
        add_observation("laboratory", "fasting_glucose", "1558-6", "Fasting glucose", 101, "mg/dL", check_a)
        add_observation("laboratory", "fasting_glucose", "1558-6", "Fasting glucose", 112, "mg/dL", check_b)
        add_observation("vital-signs", "body_height", "8302-2", "Body height", 170, "cm", check_a)
        add_observation("vital-signs", "body_height", "8302-2", "Body height", 171, "cm", check_b)
        add_observation("vital-signs", "body_height", "8302-2", "Body height", 172, "cm", check_c)
        add_observation("vital-signs", "body_weight", "29463-7", "Body weight", 80, "kg", check_a)
        add_observation("vital-signs", "body_weight", "29463-7", "Body weight", 78, "kg", check_b)
        add_observation("vital-signs", "body_weight", "29463-7", "Body weight", 76, "kg", check_c)
        add_observation("vital-signs", "waist_circumference", "8280-0", "Waist circumference", 92, "cm", check_a)
        add_observation("vital-signs", "waist_circumference", "8280-0", "Waist circumference", 90, "cm", check_b)
        add_observation("vital-signs", "waist_circumference", "8280-0", "Waist circumference", 88, "cm", check_c)

        snapshot = DiseaseRiskInputRepository().build_snapshot(patient)
        expected_values = {
            "urine_albumin_creatinine_ratio": 88.0,
            "fasting_glucose": 112.0,
            "body_height": 172.0,
            "body_weight": 76.0,
            "waist_circumference": 88.0,
        }
        for field, expected in expected_values.items():
            actual = snapshot.data.get(field)
            if actual != expected:
                raise SystemExit(f"Latest available field selection failed for {field}: {actual} != {expected}")

        expected_dates = {
            "urine_albumin_creatinine_ratio": "2024-06-11",
            "fasting_glucose": "2025-06-11",
            "body_height": "2026-05-11",
            "body_weight": "2026-05-11",
            "waist_circumference": "2026-05-11",
        }
        for field, expected_date in expected_dates.items():
            source_date = str(snapshot.sources.get(field, {}).get("effective_at", ""))
            if not source_date.startswith(expected_date):
                raise SystemExit(f"Source date selection failed for {field}: {source_date}")

        print("Latest available field selection verification passed.")
    finally:
        Patient.objects.filter(id=patient.id).delete()


if __name__ == "__main__":
    verify_system()
    verify_latest_available_field_selection()
