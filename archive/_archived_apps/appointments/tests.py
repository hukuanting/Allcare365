from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import date, datetime, timedelta
from .models import (
    Appointment, AppointmentType, RecurringAppointment, WaitingList
)
from patients.models import Patient
from administration.models import Provider


class AppointmentModelTest(TestCase):
    """測試預約模型"""
    
    def setUp(self):
        """設置測試數據"""
        self.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1985, 5, 15),
            gender="M"
        )
        
        self.user = User.objects.create_user(
            username='testdoctor',
            email='doctor@example.com',
            password='testpass123',
            first_name='Jane',
            last_name='Smith'
        )
        self.provider = Provider.objects.create(
            user=self.user,
            provider_type='physician',
            license_number='MD12345'
        )
        
        self.appointment_type = AppointmentType.objects.create(
            name="Consultation",
            description="General consultation",
            color="#0066cc"
        )
        
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            provider=self.provider,
            appointment_type=self.appointment_type,
            appointment_date=date.today() + timedelta(days=7),
            appointment_time=datetime.now().time(),
            status="scheduled"
        )
    
    def test_appointment_creation(self):
        """測試預約創建"""
        self.assertEqual(self.appointment.patient, self.patient)
        self.assertEqual(self.appointment.provider, self.provider)
        self.assertEqual(self.appointment.status, "scheduled")
    
    def test_appointment_str_representation(self):
        """測試預約字符串表示"""
        expected = f"John Doe - Dr. Jane Smith - {self.appointment.appointment_date}"
        self.assertEqual(str(self.appointment), expected)


class AppointmentAPITest(APITestCase):
    """測試預約 API"""
    
    def setUp(self):
        """設置測試數據"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_get_appointment_list(self):
        """測試獲取預約列表"""
        response = self.client.get('/api/v1/appointments/appointments/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
