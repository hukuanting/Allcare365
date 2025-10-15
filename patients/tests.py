from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import date, datetime, timedelta
from .models import (
    Patient, PatientAllergy, PatientMedication, PatientVitals,
    PatientNote, EmergencyContact
)
from administration.models import Provider


class PatientModelTest(TestCase):
    """測試患者模型"""
    
    def setUp(self):
        """設置測試數據"""
        self.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1985, 5, 15),
            gender="M",
            phone_home="1234567890",
            email="john@example.com"
        )
    
    def test_patient_creation(self):
        """測試患者創建"""
        self.assertEqual(self.patient.first_name, "John")
        self.assertEqual(self.patient.last_name, "Doe")
        self.assertEqual(self.patient.full_name, "John Doe")
        self.assertEqual(self.patient.get_full_name(), "John Doe")
    
    def test_patient_str_representation(self):
        """測試患者字符串表示"""
        self.assertEqual(str(self.patient), "Doe, John")


class EmergencyContactTest(TestCase):
    """測試緊急聯絡人模型"""
    
    def setUp(self):
        """設置測試數據"""
        self.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1985, 5, 15),
            gender="M"
        )
        self.emergency_contact = EmergencyContact.objects.create(
            patient=self.patient,
            name="Jane Doe",
            relationship="Wife",
            phone="1234567890",
            is_primary=True
        )
    
    def test_emergency_contact_creation(self):
        """測試緊急聯絡人創建"""
        self.assertEqual(self.emergency_contact.name, "Jane Doe")
        self.assertEqual(self.emergency_contact.relationship, "Wife")
        self.assertTrue(self.emergency_contact.is_primary)
    
    def test_emergency_contact_str_representation(self):
        """測試緊急聯絡人字符串表示"""
        expected = "John Doe - Jane Doe (Wife)"
        self.assertEqual(str(self.emergency_contact), expected)


class PatientAPITest(APITestCase):
    """測試患者 API"""
    
    def setUp(self):
        """設置測試數據"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1985, 5, 15),
            gender="M",
            phone_home="1234567890",
            email="john@example.com"
        )
    
    def test_get_patient_list(self):
        """測試獲取患者列表"""
        response = self.client.get('/api/v1/patients/patients/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_get_patient_detail(self):
        """測試獲取患者詳情"""
        response = self.client.get(f'/api/v1/patients/patients/{self.patient.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_create_patient(self):
        """測試創建患者"""
        data = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'date_of_birth': '1990-01-01',
            'gender': 'F',
            'phone_home': '0987654321',
            'email': 'jane@example.com'
        }
        response = self.client.post('/api/v1/patients/patients/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
