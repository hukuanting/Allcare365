"""Seed a small set of active-schema demo patients."""

from __future__ import annotations

from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.clinical.patients.models import Patient, PatientAllergy, PatientDocument, PatientMedication


class Command(BaseCommand):
    help = "Create sample patients using the current USCDI-aligned patient schema"

    def handle(self, *args, **options):
        admin_user, _ = User.objects.get_or_create(
            username="admin",
            defaults={"is_staff": True, "is_superuser": True},
        )

        patients_data = [
            {
                "medical_record_number": "DEMO-001",
                "first_name": "Ming",
                "last_name": "Wang",
                "date_of_birth": date(1985, 3, 15),
                "sex": "M",
                "phone_number": "0912345678",
                "email_address": "ming.wang@example.com",
                "current_address_line1": "No. 1 Renai Road",
                "city": "Taipei",
                "state": "Taipei",
                "postal_code": "100",
                "occupation": "Engineer",
            },
            {
                "medical_record_number": "DEMO-002",
                "first_name": "Mei",
                "last_name": "Li",
                "date_of_birth": date(1990, 8, 22),
                "sex": "F",
                "phone_number": "0923456789",
                "email_address": "mei.li@example.com",
                "current_address_line1": "No. 88 Zhongshan Road",
                "city": "New Taipei",
                "state": "New Taipei",
                "postal_code": "220",
                "occupation": "Nurse",
            },
            {
                "medical_record_number": "DEMO-003",
                "first_name": "Alex",
                "last_name": "Chen",
                "date_of_birth": date(1978, 12, 5),
                "sex": "M",
                "phone_number": "0934567890",
                "email_address": "alex.chen@example.com",
                "current_address_line1": "No. 77 Minzu Road",
                "city": "Kaohsiung",
                "state": "Kaohsiung",
                "postal_code": "813",
                "occupation": "Teacher",
            },
        ]

        created_count = 0
        for patient_data in patients_data:
            patient, created = Patient.objects.get_or_create(
                medical_record_number=patient_data["medical_record_number"],
                defaults={**patient_data, "created_by": admin_user},
            )
            if not created:
                self.stdout.write(self.style.WARNING(f"Patient already exists: {patient.full_name}"))
                continue

            created_count += 1
            self._create_sample_data_for_patient(patient, admin_user)
            self.stdout.write(self.style.SUCCESS(f"Created patient: {patient.full_name}"))

        self.stdout.write(self.style.SUCCESS(f"Created {created_count} demo patients"))

    def _create_sample_data_for_patient(self, patient, admin_user):
        PatientAllergy.objects.create(
            patient=patient,
            allergy_type="non_medication",
            substance="Peanut",
            reaction="Rash",
            severity="mild",
            created_by=admin_user,
        )
        PatientMedication.objects.create(
            patient=patient,
            medication="Vitamin D",
            dose_unit_of_measure="1000 IU",
            route_of_administration="oral",
            indication="Supplement",
            dispense_status="active",
            start_date=timezone.now().date() - timedelta(days=90),
            created_by=admin_user,
        )
        PatientDocument.objects.create(
            patient=patient,
            note_type="progress",
            content="Demo clinical note generated for local development.",
            document_date=timezone.now(),
            created_by=admin_user,
        )
