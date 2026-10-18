from datetime import date
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "medical_system.settings")

import django

django.setup()

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Patient, PatientAllergy, PatientDocument, PatientMedication, PatientPractitionerLink, PatientUserLink, Practitioner


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
        practitioner = Practitioner.objects.create(
            user=self.user,
            first_name="Test",
            last_name="Clinician",
        )
        PatientPractitionerLink.objects.create(
            patient=self.patient,
            practitioner=practitioner,
            permissions_json={"patient_data": "read_write"},
        )

    def test_get_patient_list(self):
        response = self.client.get("/api/patients/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_patient_detail(self):
        response = self.client.get(f"/api/patients/{self.patient.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_patient(self):
        self.user.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="patients", codename="create_patient_records"
            )
        )
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

    def test_unlinked_patient_is_not_listed_or_retrieved(self):
        unrelated = Patient.objects.create(first_name="Private", last_name="Record")

        response = self.client.get("/api/patients/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([str(item["id"]) for item in response.data["results"]], [str(self.patient.id)])

        response = self.client.get(f"/api/patients/{unrelated.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_read_only_care_link_cannot_write(self):
        PatientPractitionerLink.objects.filter(patient=self.patient).update(
            permissions_json={"patient_data": "read"}
        )

        response = self.client.patch(
            f"/api/patients/{self.patient.id}/",
            {"first_name": "Changed"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patient_user_link_is_read_only_and_cannot_access_another_patient(self):
        patient_user = User.objects.create_user(username="linked-patient", password="testpass123")
        PatientUserLink.objects.create(user=patient_user, patient=self.patient)
        unrelated = Patient.objects.create(first_name="Private", last_name="Record")
        self.client.force_authenticate(user=patient_user)

        response = self.client.get("/api/patients/")
        self.assertEqual([str(item["id"]) for item in response.data["results"]], [str(self.patient.id)])

        response = self.client.patch(
            f"/api/patients/{self.patient.id}/", {"first_name": "Changed"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.get(f"/api/patients/{unrelated.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
