import uuid
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.clinical.health_screening.models import (
    AIAnalysisJob,
    AIAnalysisResult,
    CareTask,
    Consent,
    DataImportBatch,
    DataImportRow,
    Encounter,
    Observation,
    Questionnaire,
    QuestionnaireResponse,
)
from apps.clinical.patients.models import (
    CarePlan,
    Organization,
    Patient,
    PatientPractitionerLink,
    Practitioner,
)
from apps.core.authentication.models import ProductUser
from apps.integration.fhir_integration.models import AuditLog, FHIRResourceMapping


class Command(BaseCommand):
    help = "Seed AllCare365 product database schema v1 sample data."

    def handle(self, *args, **options):
        now = timezone.now()

        doctor_user, _ = User.objects.get_or_create(
            username="seed_doctor",
            defaults={
                "email": "doctor.seed@allcare365.local",
                "first_name": "Ming",
                "last_name": "Chen",
                "is_staff": True,
            },
        )
        if not doctor_user.has_usable_password():
            doctor_user.set_unusable_password()
            doctor_user.save(update_fields=["password"])

        product_user, _ = ProductUser.objects.update_or_create(
            auth_user=doctor_user,
            defaults={
                "display_name": "Dr. Ming Chen",
                "role": "doctor",
                "status": "active",
                "organization_name": "AllCare365 Demo Clinic",
            },
        )

        organization, _ = Organization.objects.update_or_create(
            identifier="AC365-DEMO-CLINIC",
            defaults={
                "name": "AllCare365 Demo Clinic",
                "type": "provider",
                "address_line1": "1 HealthTech Way",
                "city": "Taipei",
                "country": "Taiwan",
            },
        )

        practitioner, _ = Practitioner.objects.update_or_create(
            id=uuid.UUID("30000000-0000-4000-a000-000000000001"),
            defaults={
                "user": doctor_user,
                "identifier": "PRAC-AC365-001",
                "npi": "1234567890",
                "license_number": "TW-MD-0001",
                "first_name": "Ming",
                "last_name": "Chen",
                "specialty": "Family Medicine",
                "organization": organization,
                "email": "doctor.seed@allcare365.local",
                "status": "active",
            },
        )

        patient, _ = Patient.objects.update_or_create(
            id=uuid.UUID("20000000-0000-4000-a000-000000000001"),
            defaults={
                "medical_record_number": "AC365-SEED-001",
                "first_name": "An",
                "last_name": "Lin",
                "date_of_birth": "1988-04-12",
                "sex": "F",
                "phone_number": "+886900000001",
                "email_address": "patient.seed@allcare365.local",
                "status": "active",
                "source_system": "seed_product_schema_v1",
                "source_record_id": "seed-patient-001",
                "last_imported_at": now,
                "metadata_json": {"demo": True},
            },
        )

        PatientPractitionerLink.objects.update_or_create(
            patient=patient,
            practitioner=practitioner,
            link_type="primary_care",
            defaults={
                "role": "primary",
                "status": "active",
                "permissions_json": {"patient_data": "read_write", "ai_review": True},
            },
        )

        encounter, _ = Encounter.objects.update_or_create(
            id=uuid.UUID("40000000-0000-4000-a000-000000000001"),
            defaults={
                "patient": patient,
                "practitioner": practitioner,
                "encounter_type": "wellness_check",
                "status": "finished",
                "reason": "Annual health review",
                "location": "AllCare365 Demo Clinic",
                "started_at": now - timedelta(hours=1),
                "ended_at": now,
                "source_type": "manual",
            },
        )

        observation, _ = Observation.objects.update_or_create(
            id=uuid.UUID("50000000-0000-4000-a000-000000000001"),
            defaults={
                "patient": patient,
                "encounter": encounter,
                "practitioner": practitioner,
                "observation_type": "blood_pressure",
                "category": "vital-signs",
                "source_type": "manual",
                "code_system": "http://loinc.org",
                "code": "85354-9",
                "display": "Blood pressure panel with all children optional",
                "component_json": [
                    {"code": "8480-6", "display": "Systolic blood pressure", "value": 128, "unit": "mmHg"},
                    {"code": "8462-4", "display": "Diastolic blood pressure", "value": 82, "unit": "mmHg"},
                ],
                "status": "final",
                "effective_at": now,
            },
        )
        for obs_id, obs_type, category, code, display, value, unit in [
            ("50000000-0000-4000-a000-000000000002", "body_height", "vital-signs", "8302-2", "Body height", Decimal("162.0"), "cm"),
            ("50000000-0000-4000-a000-000000000003", "body_weight", "vital-signs", "29463-7", "Body weight", Decimal("68.0"), "kg"),
            ("50000000-0000-4000-a000-000000000004", "body_mass_index", "vital-signs", "39156-5", "Body mass index (BMI) [Ratio]", Decimal("25.9"), "kg/m2"),
            ("50000000-0000-4000-a000-000000000005", "heart_rate", "vital-signs", "8867-4", "Heart rate", Decimal("76.0"), "beats/min"),
            ("50000000-0000-4000-a000-000000000006", "fasting_glucose", "laboratory", "2339-0", "Glucose [Mass/volume] in Blood", Decimal("104.0"), "mg/dL"),
            ("50000000-0000-4000-a000-000000000007", "hdl_cholesterol", "laboratory", "2085-9", "HDL Cholesterol [Mass/volume] in Serum or Plasma", Decimal("48.0"), "mg/dL"),
            ("50000000-0000-4000-a000-000000000008", "triglycerides", "laboratory", "2571-8", "Triglyceride [Mass/volume] in Serum or Plasma", Decimal("155.0"), "mg/dL"),
            ("50000000-0000-4000-a000-000000000009", "total_cholesterol", "laboratory", "2093-3", "Cholesterol [Mass/volume] in Serum or Plasma", Decimal("218.0"), "mg/dL"),
            ("50000000-0000-4000-a000-000000000010", "waist_circumference", "vital-signs", "8280-0", "Waist Circumference at umbilicus", Decimal("86.0"), "cm"),
            ("50000000-0000-4000-a000-000000000011", "hip_circumference", "vital-signs", "56074-8", "Hip circumference", Decimal("96.0"), "cm"),
            ("50000000-0000-4000-a000-000000000012", "platelet_count", "laboratory", "777-3", "Platelets [#/volume] in Blood by Automated count", Decimal("210.0"), "10*3/uL"),
            ("50000000-0000-4000-a000-000000000013", "alt_gpt", "laboratory", "1742-6", "Alanine aminotransferase [Enzymatic activity/volume] in Serum or Plasma", Decimal("26.0"), "U/L"),
            ("50000000-0000-4000-a000-000000000014", "ast_got", "laboratory", "1920-8", "Aspartate aminotransferase [Enzymatic activity/volume] in Serum or Plasma", Decimal("24.0"), "U/L"),
            ("50000000-0000-4000-a000-000000000015", "ast_uln", "laboratory", "1916-6", "Aspartate aminotransferase upper reference limit", Decimal("39.0"), "U/L"),
            ("50000000-0000-4000-a000-000000000016", "ggt", "laboratory", "2324-2", "Gamma glutamyl transferase [Enzymatic activity/volume] in Serum or Plasma", Decimal("32.0"), "U/L"),
            ("50000000-0000-4000-a000-000000000017", "albumin", "laboratory", "1751-7", "Albumin [Mass/volume] in Serum or Plasma", Decimal("4.4"), "g/dL"),
            ("50000000-0000-4000-a000-000000000018", "insulin", "laboratory", "20448-7", "Insulin [Units/volume] in Serum or Plasma", Decimal("8.0"), "uIU/mL"),
            ("50000000-0000-4000-a000-000000000019", "urine_albumin_creatinine_ratio", "laboratory", "9318-7", "Albumin/Creatinine [Mass Ratio] in Urine", Decimal("24.0"), "mg/g"),
            ("50000000-0000-4000-a000-000000000020", "alcohol_drinks_per_week", "social-history", "74013-4", "Alcoholic drinks per week", Decimal("0.0"), "{drinks}/wk"),
            ("50000000-0000-4000-a000-000000000021", "apoe_e4", "laboratory", "79713-2", "APOE gene e4 allele", Decimal("0.0"), ""),
        ]:
            Observation.objects.update_or_create(
                id=uuid.UUID(obs_id),
                defaults={
                    "patient": patient,
                    "encounter": encounter,
                    "practitioner": practitioner,
                    "observation_type": obs_type,
                    "category": category,
                    "source_type": "seed",
                    "code_system": "http://loinc.org",
                    "code": code,
                    "display": display,
                    "value_quantity": value,
                    "value_unit": unit,
                    "status": "final",
                    "effective_at": now,
                },
            )

        questionnaire, _ = Questionnaire.objects.update_or_create(
            id=uuid.UUID("60000000-0000-4000-a000-000000000001"),
            defaults={
                "title": "Lifestyle Risk Intake",
                "version": "1.0.0",
                "status": "active",
                "code_system": "http://allcare365.local/questionnaires",
                "code": "lifestyle-risk-intake",
                "questionnaire_json": {
                    "items": [
                        {"linkId": "smoking", "text": "Smoking status", "type": "choice"},
                        {"linkId": "exercise", "text": "Weekly exercise minutes", "type": "integer"},
                    ]
                },
                "scoring_json": {"exercise_low_minutes": 90},
            },
        )

        questionnaire_response, _ = QuestionnaireResponse.objects.update_or_create(
            id=uuid.UUID("70000000-0000-4000-a000-000000000001"),
            defaults={
                "patient": patient,
                "questionnaire": questionnaire,
                "encounter": encounter,
                "authored_at": now,
                "status": "completed",
                "source_type": "manual",
                "response_json": {
                    "smoking": "never",
                    "exercise": 80,
                    "family_history_diabetes": True,
                    "anti_hypertensive_drugs": False,
                    "using_lipid_lowering_drugs": False,
                    "has_diabetes": False,
                    "prediabetes": True,
                    "has_hypertension": False,
                    "vegetables_daily": True,
                    "physical_activity_active": True,
                    "moderate_alcohol": False,
                    "heavy_alcohol": False,
                    "is_smoker": False,
                    "former_smoker": False,
                    "chd_history": False,
                    "cvd_history": False,
                    "pvd_history": False,
                },
                "score_json": {"lifestyle_risk_score": 0.32, "exercise_flag": "below_target"},
            },
        )

        batch, _ = DataImportBatch.objects.update_or_create(
            id=uuid.UUID("80000000-0000-4000-a000-000000000001"),
            defaults={
                "created_by_user": doctor_user,
                "source_type": "csv",
                "original_filename": "seed_health_data.csv",
                "status": "completed",
                "total_rows": 1,
                "processed_rows": 1,
                "success_rows": 1,
                "failed_rows": 0,
                "started_at": now,
                "completed_at": now,
                "summary_json": {"created_observations": 1},
            },
        )

        DataImportRow.objects.update_or_create(
            batch=batch,
            row_number=1,
            defaults={
                "patient": patient,
                "status": "success",
                "target_table": "observations",
                "target_id": observation.id,
                "raw_json": {"mrn": "AC365-SEED-001", "systolic": 128, "diastolic": 82},
                "normalized_json": {"observation_id": str(observation.id)},
            },
        )

        ai_job, _ = AIAnalysisJob.objects.update_or_create(
            id=uuid.UUID("90000000-0000-4000-a000-000000000001"),
            defaults={
                "patient": patient,
                "requested_by_user": doctor_user,
                "encounter": encounter,
                "job_type": "disease_risk_assessment",
                "status": "completed",
                "model_name": "allcare365-deterministic-risk-catalog",
                "model_version": "core-xlsx-2024-12-24",
                "input_json": {
                    "observation_ids": [str(observation.id)],
                    "questionnaire_response_ids": [str(questionnaire_response.id)],
                },
                "started_at": now,
                "completed_at": now,
            },
        )

        ai_result, _ = AIAnalysisResult.objects.update_or_create(
            id=uuid.UUID("91000000-0000-4000-a000-000000000001"),
            defaults={
                "job": ai_job,
                "patient": patient,
                "result_type": "framingham_diabetes",
                "model_version": "core-xlsx-2024-12-24",
                "confidence_score": Decimal("0.8200"),
                "risk_level": "moderate",
                "result_json": {"risk_score": 0.41, "risk_level": "moderate"},
                "explanation_json": {"drivers": ["blood_pressure", "exercise_minutes"]},
                "recommendation_text": "Follow up blood pressure and increase weekly activity.",
                "requires_doctor_review": True,
            },
        )

        care_plan, _ = CarePlan.objects.update_or_create(
            id=uuid.UUID("92000000-0000-4000-a000-000000000001"),
            defaults={
                "patient": patient,
                "care_plan": "Cardiometabolic prevention plan.",
                "assessment_and_plan": "Monitor BP, lifestyle coaching, and follow-up in 30 days.",
                "status": "active",
                "start_date": now.date(),
                "title": "Cardiometabolic follow-up",
                "category": "assess-plan",
                "intent": "plan",
                "period_start": now,
                "source_ai_result_id": ai_result.id,
                "goal_json": {"bp_target": "<130/80", "exercise_minutes": 150},
                "activity_json": [{"activity": "home_bp_monitoring", "frequency": "daily"}],
            },
        )

        care_task, _ = CareTask.objects.update_or_create(
            id=uuid.UUID("93000000-0000-4000-a000-000000000001"),
            defaults={
                "patient": patient,
                "care_plan": care_plan,
                "assigned_practitioner": practitioner,
                "source_ai_result": ai_result,
                "title": "Review home blood pressure log",
                "description": "Review 7-day home BP readings and adjust follow-up plan.",
                "status": "requested",
                "priority": "routine",
                "due_at": now + timedelta(days=30),
            },
        )

        Consent.objects.update_or_create(
            id=uuid.UUID("94000000-0000-4000-a000-000000000001"),
            defaults={
                "patient": patient,
                "practitioner": practitioner,
                "status": "active",
                "category": "treatment",
                "scope": "patient-privacy",
                "granted_at": now,
                "provision_json": {"data": ["Observation", "QuestionnaireResponse", "DiseaseRiskResult"]},
            },
        )

        FHIRResourceMapping.objects.update_or_create(
            local_table="observations",
            local_id=observation.id,
            fhir_resource_type="Observation",
            defaults={
                "patient": patient,
                "fhir_resource_id": f"obs-{str(observation.id)[:8]}",
                "profile_url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-blood-pressure",
                "sync_status": "mapped",
                "last_synced_at": now,
                "fhir_json": {
                    "resourceType": "Observation",
                    "id": f"obs-{str(observation.id)[:8]}",
                    "subject": {"reference": f"Patient/{patient.id}"},
                    "status": "final",
                    "code": {"coding": [{"system": "http://loinc.org", "code": "85354-9"}]},
                },
            },
        )

        AuditLog.objects.create(
            actor_user=doctor_user,
            action="disease_risk_assess",
            target_table="ai_analysis_results",
            target_id=ai_result.id,
            patient=patient,
            ip_address="127.0.0.1",
            user_agent="seed_product_schema_v1",
            metadata_json={
                "flow": "Patient -> Observation/QuestionnaireResponse -> DiseaseRiskAssessment -> CarePlan -> CareTask -> FHIR Mapping",
                "product_user_id": str(product_user.id),
                "care_task_id": str(care_task.id),
            },
        )

        self.stdout.write(self.style.SUCCESS("Seeded AllCare365 product schema v1 sample data."))
        self.stdout.write(f"Patient: {patient.id} / {patient.medical_record_number}")
        self.stdout.write(f"Practitioner: {practitioner.id} / {practitioner.identifier}")
        self.stdout.write(f"Observation: {observation.id}")
        self.stdout.write(f"QuestionnaireResponse: {questionnaire_response.id}")
        self.stdout.write(f"DiseaseRiskResult: {ai_result.id}")
