"""
Simplified laboratory management test suite.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal

from .models import (
    LabProvider, LabTestCategory, LabTestType, LabOrder, LabOrderItem,
    LabResult, LabMessage, QualityControlLog
)
from patients.models import Patient
from administration.models import Provider, Facility


class LabProviderModelTest(TestCase):
    """Test cases for LabProvider model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_lab_provider_creation(self):
        """Test creating a lab provider"""
        provider = LabProvider.objects.create(
            name='Test Lab',
            contact_name='John Doe',
            phone='555-1234',
            email='contact@testlab.com',
            interface_type='hl7',
            average_turnaround_time=24,
            is_preferred=True,
            created_by=self.user
        )
        
        self.assertEqual(provider.name, 'Test Lab')
        self.assertEqual(provider.contact_name, 'John Doe')
        self.assertEqual(provider.interface_type, 'hl7')
        self.assertTrue(provider.is_preferred)
        self.assertTrue(provider.is_active)
        self.assertEqual(str(provider), 'Test Lab')


class LabTestCategoryModelTest(TestCase):
    """Test cases for LabTestCategory model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_category_creation(self):
        """Test creating a lab test category"""
        category = LabTestCategory.objects.create(
            name='Chemistry',
            code='CHEM',
            description='Chemistry tests',
            sort_order=1,
            created_by=self.user
        )
        
        self.assertEqual(category.name, 'Chemistry')
        self.assertEqual(category.code, 'CHEM')
        self.assertEqual(category.sort_order, 1)
        self.assertEqual(str(category), 'Chemistry')


class LabTestTypeModelTest(TestCase):
    """Test cases for LabTestType model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.category = LabTestCategory.objects.create(
            name='Chemistry',
            code='CHEM',
            created_by=self.user
        )
    
    def test_test_type_creation(self):
        """Test creating a lab test type"""
        test_type = LabTestType.objects.create(
            name='Complete Blood Count',
            short_name='CBC',
            category=self.category,
            loinc_code='58410-2',
            cpt_code='85025',
            specimen_type='blood',
            units='count',
            reference_range_male='4.5-11.0',
            reference_range_female='4.5-11.0',
            result_type='numeric',
            average_tat=24,
            cost=Decimal('50.00'),
            created_by=self.user
        )
        
        self.assertEqual(test_type.name, 'Complete Blood Count')
        self.assertEqual(test_type.short_name, 'CBC')
        self.assertEqual(test_type.category, self.category)
        self.assertEqual(test_type.specimen_type, 'blood')
        self.assertEqual(test_type.cost, Decimal('50.00'))
        self.assertEqual(str(test_type), 'Complete Blood Count (blood)')


class LabOrderModelTest(TestCase):
    """Test cases for LabOrder model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.facility = Facility.objects.create(
            name='Test Facility',
            facility_type='clinic',
            street_address='123 Test St',
            city='Test City',
            state='Test State',
            zip_code='12345',
            phone='555-1234',
            created_by=self.user
        )
        
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth='1990-01-01',
            gender='M',
            created_by=self.user
        )
        
        self.provider = Provider.objects.create(
            user=self.user,
            provider_type='physician',
            primary_specialty='Internal Medicine',
            license_number='12345',
            created_by=self.user
        )
        
        self.lab_provider = LabProvider.objects.create(
            name='Test Lab',
            interface_type='hl7',
            created_by=self.user
        )
    
    def test_lab_order_creation(self):
        """Test creating a lab order"""
        order = LabOrder.objects.create(
            patient=self.patient,
            provider=self.provider,
            lab_provider=self.lab_provider,
            priority='routine',
            clinical_info='Routine screening',
            created_by=self.user
        )
        
        self.assertEqual(order.patient, self.patient)
        self.assertEqual(order.provider, self.provider)
        self.assertEqual(order.priority, 'routine')
        self.assertEqual(order.status, 'pending')
        self.assertTrue(order.order_number)  # Should be auto-generated
        self.assertIn('LAB', order.order_number)


class LabMessageModelTest(TestCase):
    """Test cases for LabMessage model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.lab_provider = LabProvider.objects.create(
            name='Test Lab',
            interface_type='hl7',
            created_by=self.user
        )
    
    def test_message_creation(self):
        """Test creating an HL7 message"""
        message = LabMessage.objects.create(
            lab_provider=self.lab_provider,
            message_type='ORU',
            raw_message='MSH|^~\&|Lab|Test|EMR|Clinic|...',
            processing_status='pending',
            created_by=self.user
        )
        
        self.assertEqual(message.lab_provider, self.lab_provider)
        self.assertEqual(message.message_type, 'ORU')
        self.assertEqual(message.processing_status, 'pending')
        self.assertIn('ORU', str(message))


class QualityControlLogModelTest(TestCase):
    """Test cases for QualityControlLog model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.lab_provider = LabProvider.objects.create(
            name='Test Lab',
            interface_type='hl7',
            created_by=self.user
        )
        
        self.category = LabTestCategory.objects.create(
            name='Chemistry',
            code='CHEM',
            created_by=self.user
        )
        
        self.test_type = LabTestType.objects.create(
            name='Glucose',
            category=self.category,
            specimen_type='blood',
            created_by=self.user
        )
    
    def test_qc_log_creation(self):
        """Test creating a QC log"""
        qc_log = QualityControlLog.objects.create(
            lab_provider=self.lab_provider,
            test_type=self.test_type,
            qc_type='control',
            control_lot='LOT123',
            expected_value='100',
            measured_value='98',
            acceptable_range='95-105',
            passed=True,
            performed_by='Tech A',
            created_by=self.user
        )
        
        self.assertEqual(qc_log.lab_provider, self.lab_provider)
        self.assertEqual(qc_log.test_type, self.test_type)
        self.assertEqual(qc_log.qc_type, 'control')
        self.assertTrue(qc_log.passed)
        self.assertEqual(qc_log.performed_by, 'Tech A')
