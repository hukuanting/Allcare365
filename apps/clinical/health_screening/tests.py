from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.clinical.patients.models import Patient

from .ingestion_service import HealthScreeningIngestionService
from .models import HealthScreening


class HealthScreeningModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testdoctor",
            email="doctor@test.com",
            password="testpass123",
        )
        self.patient = Patient.objects.create(
            first_name="Test",
            last_name="Patient",
            date_of_birth=date(1990, 1, 1),
            sex="M",
        )

    def test_health_screening_creation_uses_current_encounter_schema(self):
        screening = HealthScreening.objects.create(
            patient=self.patient,
            screening_date=timezone.now().date(),
            created_by=self.user,
        )

        self.assertEqual(screening.patient, self.patient)
        self.assertEqual(screening.created_by, self.user)
        self.assertEqual(screening.encounter_type, "annual_physical")

    def test_ingestion_normalizes_vital_signs_and_derives_average_pressure(self):
        screening = HealthScreeningIngestionService().create_screening(
            {
                "patient_id": str(self.patient.id),
                "screening_date": timezone.now().date().isoformat(),
                "vital_signs": {
                    "height_cm": 170,
                    "weight_kg": 70,
                    "systolic_bp_mmhg": 120,
                    "diastolic_bp_mmhg": 80,
                },
            }
        )

        vital_signs = screening.vital_signs
        self.assertEqual(float(vital_signs.body_height), 170.0)
        self.assertEqual(float(vital_signs.body_weight), 70.0)
        self.assertEqual(vital_signs.systolic_blood_pressure, 120)
        self.assertEqual(vital_signs.diastolic_blood_pressure, 80)
        self.assertEqual(vital_signs.average_blood_pressure, 93)


class HealthScreeningAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testdoctor",
            email="doctor@test.com",
            password="testpass123",
        )
        self.patient = Patient.objects.create(
            first_name="Test",
            last_name="Patient",
            date_of_birth=date(1990, 1, 1),
            sex="M",
        )
        self.client.force_authenticate(user=self.user)

    def test_create_health_screening(self):
        data = {
            "patient_id": str(self.patient.id),
            "screening_date": "2024-01-15",
            "screening_type": "annual_physical",
            "vital_signs": {
                "height_cm": 170,
                "weight_kg": 70,
                "systolic_bp_mmhg": 120,
                "diastolic_bp_mmhg": 80,
            },
            "laboratory_results": {
                "fasting_glucose": 95,
                "total_cholesterol": 200,
                "hdl_cholesterol": 50,
                "ldl_cholesterol": 130,
            },
        }

        response = self.client.post(
            "/api/health-screening/screenings/",
            data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        screening = HealthScreening.objects.get(id=response.data["id"])
        self.assertTrue(hasattr(screening, "vital_signs"))
        self.assertEqual(screening.lab_results.count(), 4)

    def test_list_health_screenings(self):
        HealthScreening.objects.create(
            patient=self.patient,
            screening_date=timezone.now().date(),
        )

        response = self.client.get("/api/health-screening/screenings/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
