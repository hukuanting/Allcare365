from datetime import date
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medical_system.settings")

import django

django.setup()

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Patient, PatientAllergy, PatientDocument, PatientMedication


class PatientModelTest(TestCase):
    def setUp(self):
        self.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1985, 5, 15),
            sex="M",
            phone_number="1234567890",
            email_address="john@example.com",
        )

    def test_patient_creation(self):
        self.assertEqual(self.patient.first_name, "John")
        self.assertEqual(self.patient.last_name, "Doe")
        self.assertEqual(self.patient.full_name, "DoeJohn")
        self.assertEqual(self.patient.get_full_name(), "DoeJohn")

    def test_patient_str_representation(self):
        self.assertEqual(str(self.patient), "DoeJohn")


class PatientRelatedDataTest(TestCase):
    def setUp(self):
        self.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1985, 5, 15),
            sex="M",
        )

    def test_patient_allergy_creation(self):
        allergy = PatientAllergy.objects.create(
            patient=self.patient,
            allergy_type="non_medication",
            substance="Peanut",
            reaction="Rash",
            severity="mild",
        )

        self.assertEqual(allergy.substance, "Peanut")
        self.assertEqual(self.patient.allergies.count(), 1)

    def test_patient_medication_and_note_creation(self):
        PatientMedication.objects.create(
            patient=self.patient,
            medication="Vitamin D",
            dose_unit_of_measure="1000 IU",
            dispense_status="active",
        )
        PatientDocument.objects.create(
            patient=self.patient,
            note_type="progress",
            content="Routine follow-up note.",
        )

        self.assertEqual(self.patient.medications.count(), 1)
        self.assertEqual(self.patient.clinical_notes.count(), 1)


class PatientAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(user=self.user)

        self.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1985, 5, 15),
            sex="M",
            phone_number="1234567890",
            email_address="john@example.com",
        )

    def test_get_patient_list(self):
        response = self.client.get("/api/patients/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_patient_detail(self):
        response = self.client.get(f"/api/patients/{self.patient.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_patient(self):
        data = {
            "first_name": "Jane",
            "last_name": "Smith",
            "date_of_birth": "1990-01-01",
            "sex": "F",
            "phone_number": "0987654321",
            "email_address": "jane@example.com",
        }
        response = self.client.post("/api/patients/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
