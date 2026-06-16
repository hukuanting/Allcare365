from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import date, datetime, timedelta
from decimal import Decimal
from .models import (
    Invoice, InvoiceLineItem, Payment, InsuranceProvider, 
    BillingCode, FeeSchedule, PatientInsurance
)
from patients.models import Patient
from administration.models import Provider


class BillingModelTest(TestCase):
    """測試帳務模型"""
    
    def setUp(self):
        """設置測試數據"""
        self.patient = Patient.objects.create(
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1985, 5, 15),
            gender="M"
        )
        
        self.insurance_provider = InsuranceProvider.objects.create(
            name="Blue Cross Blue Shield",
            type="commercial"
        )
        
        self.billing_code = BillingCode.objects.create(
            code="99213",
            description="Office visit",
            code_type="CPT"
        )
        
        self.fee_schedule = FeeSchedule.objects.create(
            insurance_provider=self.insurance_provider,
            billing_code=self.billing_code,
            fee_amount=Decimal("150.00"),
            effective_date=date.today()
        )
    
    def test_insurance_provider_creation(self):
        """測試保險提供者創建"""
        self.assertEqual(self.insurance_provider.name, "Blue Cross Blue Shield")
        self.assertEqual(self.insurance_provider.type, "commercial")
    
    def test_billing_code_creation(self):
        """測試帳務代碼創建"""
        self.assertEqual(self.billing_code.code, "99213")
        self.assertEqual(self.billing_code.description, "Office visit")
    
    def test_fee_schedule_str_representation(self):
        """測試費用表字符串表示"""
        expected = "99213 - Blue Cross Blue Shield: $150.00"
        self.assertEqual(str(self.fee_schedule), expected)


class BillingAPITest(APITestCase):
    """測試帳務 API"""
    
    def setUp(self):
        """設置測試數據"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_get_invoice_list(self):
        """測試獲取發票列表"""
        response = self.client.get('/api/v1/billing/invoices/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_get_insurance_provider_list(self):
        """測試獲取保險提供者列表"""
        response = self.client.get('/api/v1/billing/insurance-providers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
