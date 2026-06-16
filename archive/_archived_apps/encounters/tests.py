from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from patients.models import Patient
from .models import Encounter, EncounterForm, EncounterDiagnosis


class EncounterModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testdoctor',
            email='doctor@test.com',
            password='testpass123'
        )
        self.patient = Patient.objects.create(
            first_name='測試',
            last_name='病患',
            date_of_birth='1990-01-01',
            gender='M'
        )
    
    def test_encounter_creation(self):
        encounter = Encounter.objects.create(
            patient=self.patient,
            provider=self.user,
            encounter_date=timezone.now(),
            reason='routine',
            chief_complaint='定期檢查',
            status='completed'
        )
        self.assertEqual(encounter.patient, self.patient)
        self.assertEqual(encounter.provider, self.user)
        self.assertEqual(encounter.reason, 'routine')
        self.assertEqual(encounter.status, 'completed')
    
    def test_bmi_calculation(self):
        encounter = Encounter.objects.create(
            patient=self.patient,
            provider=self.user,
            height=170,  # cm
            weight=70,   # kg
        )
        expected_bmi = round(70 / (1.7 ** 2), 2)
        self.assertEqual(encounter.bmi, expected_bmi)
    
    def test_blood_pressure_display(self):
        encounter = Encounter.objects.create(
            patient=self.patient,
            provider=self.user,
            blood_pressure_systolic=120,
            blood_pressure_diastolic=80
        )
        self.assertEqual(encounter.blood_pressure, "120/80")
    
    def test_encounter_diagnosis_creation(self):
        encounter = Encounter.objects.create(
            patient=self.patient,
            provider=self.user
        )
        diagnosis = EncounterDiagnosis.objects.create(
            encounter=encounter,
            icd_code='Z00.00',
            diagnosis_text='一般健康檢查',
            diagnosis_type='primary'
        )
        self.assertEqual(diagnosis.encounter, encounter)
        self.assertEqual(diagnosis.icd_code, 'Z00.00')
        self.assertEqual(diagnosis.diagnosis_type, 'primary')
    
    def test_encounter_form_creation(self):
        encounter = Encounter.objects.create(
            patient=self.patient,
            provider=self.user
        )
        form = EncounterForm.objects.create(
            encounter=encounter,
            form_type='soap',
            form_name='SOAP記錄',
            form_data={'subjective': '病患主訴', 'objective': '客觀發現'}
        )
        self.assertEqual(form.encounter, encounter)
        self.assertEqual(form.form_type, 'soap')
        self.assertIn('subjective', form.form_data)
