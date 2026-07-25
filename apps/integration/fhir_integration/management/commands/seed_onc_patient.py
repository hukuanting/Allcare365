"""
Relational-only ONC seed fixture.

This command intentionally seeds only Django model fields and clinical truth
data. All FHIR semantics (codes, categories, status mapping, references) are
projected later by FHIR projectors/TerminologyService.

The fixture owns only the explicitly selected patient. It must never delete or
rewrite unrelated patient records in a shared development or validation
database.
"""

from datetime import date, datetime, timezone

from django.core.management.base import BaseCommand

from apps.clinical.health_screening.models import (
    HealthScreening,
    HealthStatusAssessment,
    Immunization,
    LaboratoryResults,
    Problem,
    Procedure,
    VitalSigns,
)
from apps.clinical.patients.models import (
    AdvanceDirective,
    CarePlan,
    CareTeamMember,
    InsuranceData,
    MedicalDevice,
    MedicalOrder,
    Patient,
    PatientAllergy,
    PatientDocument,
    PatientMedication,
)


class Command(BaseCommand):
    help = (
        "Seed one synthetic ONC patient using relational model fields only "
        "(no FHIR-shaped data)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--patient-id",
            type=str,
            default="00000000-0000-4000-a000-000000000001",
            help="UUID for the seeded Patient primary key.",
        )

    def handle(self, *args, **options):
        patient_id = options["patient_id"]

        dt_now = datetime(2026, 4, 8, 10, 0, 0, tzinfo=timezone.utc)
        dt_visit_1 = datetime(2026, 3, 1, 9, 0, 0, tzinfo=timezone.utc)
        dt_visit_2 = datetime(2026, 4, 1, 14, 30, 0, tzinfo=timezone.utc)

        patient, created = Patient.objects.update_or_create(
            id=patient_id,
            defaults={
                "first_name": "Justin",
                "last_name": "Hu",
                "middle_name": "",
                "name_suffix": "",
                "previous_name": "",
                "date_of_birth": date(1985, 1, 1),
                "sex": "male",
                "race": "Asian",
                "ethnicity": "Not Hispanic or Latino",
                "tribal_affiliation": "",
                "current_address_line1": "123 Interoperability Lane",
                "current_address_line2": "",
                "city": "Boston",
                "state": "MA",
                "postal_code": "02134",
                "country": "US",
                "previous_address": "",
                "phone_number": "15558675309",
                "phone_number_type": "mobile",
                "email_address": "justin.hu@example.com",
                "preferred_language": "en-US",
                "interpreter_needed": False,
                "related_person_name": "Jordan Smith",
                "relationship_type": "spouse",
                "occupation": "Software engineer",
                "occupation_industry": "Healthcare IT",
                "medical_record_number": "ONC-2026-001",
                "status": "active",
                "source_system": "allcare365-onc-certification",
                "source_record_id": str(patient_id),
                "metadata_json": {
                    "certification_fixture": "onc-g10-us-core",
                    "synthetic": True,
                    "clinical_use_prohibited": True,
                    "fhir_mrn_system": "https://allcare365.local/fhir/identifier/onc-certification-mrn",
                },
                "is_active": True,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"{'Created' if created else 'Updated'} patient {patient.id}"
            )
        )

        self._reset_existing_fixture(patient)
        self._seed_care_team(patient)
        outpatient, inpatient = self._seed_encounters(patient, dt_visit_1, dt_visit_2)
        self._seed_vitals(outpatient, inpatient)
        self._seed_labs(outpatient, inpatient)
        self._seed_health_status(outpatient, inpatient)
        self._seed_conditions(patient)
        self._seed_allergies(patient)
        self._seed_medications(patient)
        self._seed_immunizations(patient, dt_now)
        self._seed_procedures(patient, dt_visit_1, dt_visit_2)
        self._seed_coverage(patient)
        self._seed_care_plan(patient)
        self._seed_advance_directive(patient)
        self._seed_documents(patient, dt_now)
        self._seed_orders(patient, dt_now)
        self._seed_device(patient)

        self.stdout.write(self.style.SUCCESS("Relational ONC seed complete."))

    def _reset_existing_fixture(self, patient):
        from apps.clinical.health_screening.models import (
            ClinicalTestResult,
            HealthScreening,
            HealthStatusAssessment,
            LaboratoryResults,
            VitalSigns,
        )
        from apps.clinical.patients.models import (
            AdvanceDirective,
            CarePlan,
            CareTeamMember,
            InsuranceData,
            MedicalDevice,
            MedicalOrder,
            PatientAllergy,
            PatientDocument,
            PatientMedication,
        )

        screenings = HealthScreening.objects.filter(patient=patient)
        VitalSigns.objects.filter(health_screening__in=screenings).delete()
        LaboratoryResults.objects.filter(health_screening__in=screenings).delete()
        HealthStatusAssessment.objects.filter(health_screening__in=screenings).delete()
        ClinicalTestResult.objects.filter(health_screening__in=screenings).delete()
        screenings.delete()

        CareTeamMember.objects.filter(patient=patient).delete()
        PatientAllergy.objects.filter(patient=patient).delete()
        PatientMedication.objects.filter(patient=patient).delete()
        InsuranceData.objects.filter(patient=patient).delete()
        CarePlan.objects.filter(patient=patient).delete()
        AdvanceDirective.objects.filter(patient=patient).delete()
        PatientDocument.objects.filter(patient=patient).delete()
        MedicalOrder.objects.filter(patient=patient).delete()
        MedicalDevice.objects.filter(patient=patient).delete()

        patient.problems.all().delete()
        patient.immunizations.all().delete()
        patient.procedures.all().delete()

    def _seed_care_team(self, patient):
        members = [
            {
                "name": "Dr. Adam Careful",
                "identifier": "1234567890",
                "role": "primary care physician",
                "location": "Main Clinic",
                "telecom": "555-100-2000",
            },
            {
                "name": "Dr. Helen Heart",
                "identifier": "9876543210",
                "role": "cardiologist",
                "location": "Cardiology Clinic",
                "telecom": "555-200-3000",
            },
            {
                "name": "Nurse Carol Quinn",
                "identifier": "RN-001",
                "role": "care coordinator",
                "location": "Main Clinic",
                "telecom": "555-300-4000",
            },
            {
                "name": "Jordan Smith",
                "identifier": "FAM-001",
                "role": "related person",
                "location": "",
                "telecom": "555-400-5000",
            },
        ]
        for row in members:
            CareTeamMember.objects.update_or_create(
                patient=patient,
                name=row["name"],
                defaults=row,
            )

    def _seed_encounters(self, patient, dt_visit_1, dt_visit_2):
        outpatient, _ = HealthScreening.objects.update_or_create(
            patient=patient,
            encounter_identifier="ENC-2026-OP-001",
            defaults={
                "encounter_type": "outpatient",
                "encounter_time": dt_visit_1,
                "encounter_location": "Primary Care",
                "encounter_disposition": "home",
                "screening_date": dt_visit_1.date(),
                "is_active": True,
            },
        )
        inpatient, _ = HealthScreening.objects.update_or_create(
            patient=patient,
            encounter_identifier="ENC-2026-IP-001",
            defaults={
                "encounter_type": "inpatient",
                "encounter_time": dt_visit_2,
                "encounter_location": "Cardiology Unit",
                "encounter_disposition": "home",
                "screening_date": dt_visit_2.date(),
                "is_active": True,
            },
        )
        return outpatient, inpatient

    def _seed_vitals(self, outpatient, inpatient):
        VitalSigns.objects.update_or_create(
            health_screening=outpatient,
            defaults={
                "systolic_blood_pressure": 145,
                "diastolic_blood_pressure": 92,
                "average_blood_pressure": 108,
                "heart_rate": 82,
                "respiratory_rate": 16,
                "body_temperature": "36.8",
                "body_height": "175.0",
                "body_weight": "85.0",
                "pulse_oximetry": "98.0",
                "inhaled_oxygen_concentration": "21.0",
                "bmi_percentile": None,
                "weight_for_length_percentile": None,
                "head_circumference_percentile": None,
                "is_active": True,
            },
        )
        VitalSigns.objects.update_or_create(
            health_screening=inpatient,
            defaults={
                "systolic_blood_pressure": 132,
                "diastolic_blood_pressure": 80,
                "average_blood_pressure": 97,
                "heart_rate": 76,
                "respiratory_rate": 16,
                "body_temperature": "36.7",
                "body_height": "175.0",
                "body_weight": "84.2",
                "pulse_oximetry": "98.0",
                "inhaled_oxygen_concentration": "21.0",
                "bmi_percentile": None,
                "weight_for_length_percentile": None,
                "head_circumference_percentile": None,
                "is_active": True,
            },
        )

    def _seed_labs(self, outpatient, inpatient):
        labs = [
            {
                "health_screening": outpatient,
                "test_name": "Glucose",
                "value_result": "95",
                "result_unit": "mg/dL",
                "result_status": "final",
                "result_reference_range": "70-99",
                "result_interpretation": "normal",
                "specimen_type": "blood",
                "specimen_source_site": "venous",
                "specimen_identifier": "SP-GLU-001",
                "specimen_condition": "acceptable",
            },
            {
                "health_screening": outpatient,
                "test_name": "Hemoglobin A1c",
                "value_result": "7.2",
                "result_unit": "%",
                "result_status": "final",
                "result_reference_range": "4.0-5.6",
                "result_interpretation": "high",
                "specimen_type": "blood",
                "specimen_source_site": "venous",
                "specimen_identifier": "SP-A1C-001",
                "specimen_condition": "acceptable",
            },
            {
                "health_screening": inpatient,
                "test_name": "Total Cholesterol",
                "value_result": "215",
                "result_unit": "mg/dL",
                "result_status": "final",
                "result_reference_range": "<200",
                "result_interpretation": "high",
                "specimen_type": "blood",
                "specimen_source_site": "venous",
                "specimen_identifier": "SP-CHOL-001",
                "specimen_condition": "acceptable",
            },
        ]
        for row in labs:
            LaboratoryResults.objects.update_or_create(
                health_screening=row["health_screening"],
                test_name=row["test_name"],
                defaults=row,
            )

    def _seed_health_status(self, outpatient, inpatient):
        HealthStatusAssessment.objects.update_or_create(
            health_screening=outpatient,
            defaults={
                "health_concerns": "Hypertension and diabetes follow-up.",
                "functional_status": "Independent in daily activities.",
                "disability_status": "None reported.",
                "mental_cognitive_status": "Alert and oriented.",
                "pregnancy_status": "not pregnant",
                "alcohol_use": "Occasional social drinking.",
                "substance_use": "Denies illicit substance use.",
                "physical_activity": "Walks 30 minutes 5 days per week.",
                "sdoh_assessment": "Stable housing and food access.",
                "smoking_status": "Former smoker, quit 5 years ago.",
                "is_active": True,
            },
        )
        HealthStatusAssessment.objects.update_or_create(
            health_screening=inpatient,
            defaults={
                "health_concerns": "Blood pressure management after admission.",
                "functional_status": "Ambulatory.",
                "disability_status": "None reported.",
                "mental_cognitive_status": "Alert and oriented.",
                "pregnancy_status": "not pregnant",
                "alcohol_use": "Occasional social drinking.",
                "substance_use": "Denies illicit substance use.",
                "physical_activity": "Limited during hospitalization.",
                "sdoh_assessment": "No acute social barriers identified.",
                "smoking_status": "Former smoker, quit 5 years ago.",
                "is_active": True,
            },
        )

    def _seed_conditions(self, patient):
        problems = [
            {
                "problem_name": "Essential hypertension",
                "sdoh_problem": False,
                "date_of_onset": date(2020, 6, 1),
                "date_of_diagnosis": date(2020, 6, 15),
                "date_of_resolution": None,
                "status": "active",
            },
            {
                "problem_name": "Type 2 diabetes mellitus",
                "sdoh_problem": False,
                "date_of_onset": date(2019, 3, 15),
                "date_of_diagnosis": date(2019, 4, 1),
                "date_of_resolution": None,
                "status": "active",
            },
            {
                "problem_name": "Acute bronchitis",
                "sdoh_problem": False,
                "date_of_onset": date(2024, 12, 1),
                "date_of_diagnosis": date(2024, 12, 1),
                "date_of_resolution": date(2025, 1, 5),
                "status": "resolved",
            },
        ]
        for row in problems:
            Problem.objects.update_or_create(
                patient=patient,
                problem_name=row["problem_name"],
                defaults=row,
            )

    def _seed_allergies(self, patient):
        allergies = [
            {
                "allergy_type": "medication",
                "substance": "Penicillin",
                "reaction": "Anaphylaxis",
                "severity": "severe",
                "is_active": True,
            },
            {
                "allergy_type": "non_medication",
                "substance": "Peanuts",
                "reaction": "Hives",
                "severity": "moderate",
                "is_active": True,
            },
        ]
        for row in allergies:
            PatientAllergy.objects.update_or_create(
                patient=patient,
                substance=row["substance"],
                defaults=row,
            )

    def _seed_medications(self, patient):
        meds = [
            {
                "medication": "Lisinopril 10 mg tablet",
                "dose_unit_of_measure": "mg",
                "route_of_administration": "oral",
                "indication": "hypertension",
                "dispense_status": "active",
                "medication_instructions": "Take one tablet daily.",
                "medication_adherence": "good",
                "start_date": date(2024, 1, 15),
                "end_date": None,
                "is_active": True,
            },
            {
                "medication": "Metformin 500 mg tablet",
                "dose_unit_of_measure": "mg",
                "route_of_administration": "oral",
                "indication": "type 2 diabetes mellitus",
                "dispense_status": "active",
                "medication_instructions": "Take one tablet twice daily with meals.",
                "medication_adherence": "good",
                "start_date": date(2023, 3, 1),
                "end_date": None,
                "is_active": True,
            },
            {
                "medication": "Amlodipine 5 mg tablet",
                "dose_unit_of_measure": "mg",
                "route_of_administration": "oral",
                "indication": "hypertension",
                "dispense_status": "stopped",
                "medication_instructions": "Take one tablet daily.",
                "medication_adherence": "fair",
                "start_date": date(2024, 4, 8),
                "end_date": date(2026, 1, 8),
                "is_active": True,
            },
        ]
        for row in meds:
            PatientMedication.objects.update_or_create(
                patient=patient,
                medication=row["medication"],
                defaults=row,
            )

    def _seed_immunizations(self, patient, dt_now):
        records = [
            {
                "vaccine_name": "COVID-19 mRNA booster",
                "administration_date": dt_now,
                "lot_number": "LOT-2026-C19-001",
                "is_active": True,
            },
            {
                "vaccine_name": "Seasonal influenza vaccine",
                "administration_date": datetime(2025, 10, 1, tzinfo=timezone.utc),
                "lot_number": "LOT-2025-FLU-001",
                "is_active": True,
            },
        ]
        for row in records:
            Immunization.objects.update_or_create(
                patient=patient,
                vaccine_name=row["vaccine_name"],
                defaults=row,
            )

    def _seed_procedures(self, patient, dt_visit_1, dt_visit_2):
        procedures = [
            {
                "procedure_name": "Medication reconciliation",
                "performance_time": dt_visit_1,
                "sdoh_intervention": "",
                "reason_for_referral": "Post-visit medication review",
                "is_active": True,
            },
            {
                "procedure_name": "Electrocardiogram",
                "performance_time": dt_visit_2,
                "sdoh_intervention": "",
                "reason_for_referral": "Evaluation for elevated blood pressure",
                "is_active": True,
            },
        ]
        for row in procedures:
            Procedure.objects.update_or_create(
                patient=patient,
                procedure_name=row["procedure_name"],
                defaults=row,
            )

    def _seed_coverage(self, patient):
        coverage_rows = [
            {
                "coverage_status": "active",
                "coverage_type": "HMO",
                "relationship_to_subscriber": "self",
                "member_identifier": "MB-BCBS-123456",
                "subscriber_identifier": "SUB-BCBS-123456",
                "group_identifier": "GRP-789",
                "payer_identifier": "Blue Cross Blue Shield",
                "is_active": True,
            },
            {
                "coverage_status": "active",
                "coverage_type": "PPO",
                "relationship_to_subscriber": "self",
                "member_identifier": "MB-AETNA-654321",
                "subscriber_identifier": "SUB-AETNA-654321",
                "group_identifier": "GRP-456",
                "payer_identifier": "Aetna",
                "is_active": True,
            },
        ]
        for row in coverage_rows:
            InsuranceData.objects.update_or_create(
                patient=patient,
                payer_identifier=row["payer_identifier"],
                member_identifier=row["member_identifier"],
                defaults=row,
            )

    def _seed_care_plan(self, patient):
        CarePlan.objects.update_or_create(
            patient=patient,
            defaults={
                "care_plan": (
                    "Chronic disease management: home blood pressure monitoring, "
                    "medication adherence, and nutrition counseling."
                ),
                "assessment_and_plan": (
                    "Blood pressure above goal and A1c mildly elevated. Continue "
                    "current therapy and repeat labs in three months."
                ),
                "status": "active",
                "start_date": date(2025, 4, 8),
                "is_active": True,
            },
        )

    def _seed_advance_directive(self, patient):
        AdvanceDirective.objects.update_or_create(
            patient=patient,
            defaults={
                "patient_goals": "Maintain independence and avoid prolonged suffering.",
                "sdoh_goals": "Maintain transportation access for follow-up care.",
                "advance_directive_observation": "Prefers comfort-focused care if prognosis is poor.",
                "care_experience_preference": "Wants family involved in major decisions.",
                "treatment_intervention_preference": "Declines CPR in terminal condition.",
                "is_active": True,
            },
        )

    def _seed_documents(self, patient, dt_now):
        docs = [
            {
                "note_type": "progress",
                "content": (
                    "Follow-up visit: home blood pressure improving, no chest pain, "
                    "continues medications as prescribed."
                ),
                "document_date": dt_now,
                "is_active": True,
            },
            {
                "note_type": "discharge_summary",
                "content": (
                    "Admitted for elevated blood pressure, stabilized with medication "
                    "adjustment, discharged home in stable condition."
                ),
                "document_date": datetime(2026, 4, 2, 11, 0, 0, tzinfo=timezone.utc),
                "is_active": True,
            },
            {
                "note_type": "consultation",
                "content": (
                    "Cardiology consultation: no acute ischemic findings, outpatient "
                    "follow-up recommended."
                ),
                "document_date": datetime(2026, 4, 1, 16, 0, 0, tzinfo=timezone.utc),
                "is_active": True,
            },
        ]
        for row in docs:
            PatientDocument.objects.update_or_create(
                patient=patient,
                note_type=row["note_type"],
                document_date=row["document_date"],
                defaults=row,
            )

    def _seed_orders(self, patient, dt_now):
        orders = [
            {
                "order_type": "laboratory",
                "order_detail": "Repeat lipid panel in 3 months.",
                "order_date": dt_now,
                "is_active": True,
            },
            {
                "order_type": "procedure",
                "order_detail": "Annual diabetic eye exam referral.",
                "order_date": dt_now,
                "is_active": True,
            },
        ]
        for row in orders:
            MedicalOrder.objects.update_or_create(
                patient=patient,
                order_type=row["order_type"],
                order_detail=row["order_detail"],
                defaults=row,
            )

    def _seed_device(self, patient):
        MedicalDevice.objects.update_or_create(
            patient=patient,
            device_name="Cardiac pacemaker",
            defaults={
                "udi": "UDI-00844588003288-SN-12345",
                "implant_date": date(2021, 4, 8),
                "status": "active",
                "is_active": True,
            },
        )
