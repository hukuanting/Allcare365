from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import date, datetime, timedelta
from .models import (
    Provider, Facility, Department, UserProfile, AuditLog, SystemSetting
)


class ProviderModelTest(TestCase):
    """測試醫療提供者模型"""
    
    def setUp(self):
        """設置測試數據"""
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
            primary_specialty='Cardiology',
            license_number='MD12345',
            phone='1234567890'
        )
    
    def test_provider_creation(self):
        """測試醫療提供者創建"""
        self.assertEqual(self.provider.user.first_name, 'Jane')
        self.assertEqual(self.provider.user.last_name, 'Smith')
        self.assertEqual(self.provider.provider_type, 'physician')
    
    def test_provider_str_representation(self):
        """測試醫療提供者字符串表示"""
        self.assertEqual(str(self.provider), "Dr. Jane Smith")
    
    def test_provider_full_name(self):
        """測試醫療提供者全名方法"""
        self.assertEqual(self.provider.full_name, "Jane Smith")


class FacilityModelTest(TestCase):
    """測試醫療設施模型"""
    
    def setUp(self):
        """設置測試數據"""
        self.facility = Facility.objects.create(
            name="Test Hospital",
            facility_type="hospital",
            street_address="123 Main St",
            city="Test City",
            state="Test State",
            zip_code="12345"
        )
    
    def test_facility_creation(self):
        """測試醫療設施創建"""
        self.assertEqual(self.facility.name, "Test Hospital")
        self.assertEqual(self.facility.facility_type, "hospital")
    
    def test_facility_str_representation(self):
        """測試醫療設施字符串表示"""
        self.assertEqual(str(self.facility), "Test Hospital")


class SystemSettingModelTest(TestCase):
    """測試系統設定模型"""
    
    def setUp(self):
        """設置測試數據"""
        self.system_setting = SystemSetting.objects.create(
            category="general",
            key="test_setting",
            value="test_value",
            data_type="string",
            description="Test setting"
        )
    
    def test_system_setting_creation(self):
        """測試系統設定創建"""
        self.assertEqual(self.system_setting.category, "general")
        self.assertEqual(self.system_setting.key, "test_setting")
        self.assertEqual(self.system_setting.value, "test_value")
    
    def test_system_setting_str_representation(self):
        """測試系統設定字符串表示"""
        self.assertEqual(str(self.system_setting), "general.test_setting")


class AdministrationAPITest(APITestCase):
    """測試管理 API"""
    
    def setUp(self):
        """設置測試數據"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_get_provider_list(self):
        """測試獲取醫療提供者列表"""
        response = self.client.get('/api/v1/administration/providers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_get_facility_list(self):
        """測試獲取醫療設施列表"""
        response = self.client.get('/api/v1/administration/facilities/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
