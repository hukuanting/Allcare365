from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from patients.models import Patient
from .models import HealthScreening, VitalSigns, LaboratoryResults


class HealthScreeningModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testdoctor',
            email='doctor@test.com',
            password='testpass123'
        )
        self.patient = Patient.objects.create(
            first_name='測試',
            last_name='患者',
            date_of_birth='1990-01-01',
            gender='M'
        )
    
    def test_health_screening_creation(self):
        screening = HealthScreening.objects.create(
            patient=self.patient,
            screening_date=timezone.now().date(),
            provider=self.user,
            age_at_screening=33
        )
        self.assertEqual(screening.patient, self.patient)
        self.assertEqual(screening.provider, self.user)
        self.assertEqual(screening.age_at_screening, 33)
    
    def test_vital_signs_auto_calculation(self):
        screening = HealthScreening.objects.create(
            patient=self.patient,
            screening_date=timezone.now().date(),
            provider=self.user
        )
        
        vital_signs = VitalSigns.objects.create(
            health_screening=screening,
            height_cm=170,
            weight_kg=70,
            waist_circumference_cm=85,
            hip_circumference_cm=95,
            systolic_bp_mmhg=120,
            diastolic_bp_mmhg=80
        )
        
        # 檢查自動計算的值
        self.assertEqual(vital_signs.bmi, 24.2)  # 70 / (1.7^2) = 24.22
        self.assertEqual(vital_signs.pulse_pressure_mmhg, 40)  # 120 - 80
        self.assertEqual(float(vital_signs.mean_arterial_pressure_mmhg), 93.3)  # 80 + 40/3
        self.assertEqual(float(vital_signs.waist_hip_ratio), 0.895)  # 85/95
        self.assertEqual(float(vital_signs.waist_height_ratio), 0.5)  # 85/170


class HealthScreeningAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testdoctor',
            email='doctor@test.com',
            password='testpass123'
        )
        self.patient = Patient.objects.create(
            first_name='測試',
            last_name='患者',
            date_of_birth='1990-01-01',
            gender='M'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_create_health_screening(self):
        data = {
            'patient': self.patient.id,
            'screening_date': '2024-01-15',
            'screening_type': 'annual_physical',
            'age_at_screening': 33,
            'vital_signs': {
                'height_cm': 170,
                'weight_kg': 70,
                'systolic_bp_mmhg': 120,
                'diastolic_bp_mmhg': 80
            },
            'laboratory_results': {
                'fasting_glucose_mgdl': 95,
                'total_cholesterol_mgdl': 200,
                'hdl_cholesterol_mgdl': 50,
                'ldl_cholesterol_mgdl': 130
            }
        }
        
        response = self.client.post('/health-screening/api/screenings/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 檢查是否創建了相關記錄
        screening = HealthScreening.objects.get(id=response.data['id'])
        self.assertTrue(hasattr(screening, 'vital_signs'))
        self.assertTrue(hasattr(screening, 'laboratory_results'))
    
    def test_list_health_screenings(self):
        HealthScreening.objects.create(
            patient=self.patient,
            screening_date=timezone.now().date(),
            provider=self.user
        )
        
        response = self.client.get('/health-screening/api/screenings/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
