"""
Electronic Prescription (eRx) Tests

This module provides comprehensive tests for the eRx system including
models, serializers, views, and services.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from datetime import date, timedelta

from patients.models import Patient
from .models import (
    ElectronicPrescription,
    PrescriptionRefill,
    PrescriptionHistory,
    DrugFormulary,
    DrugInteraction,
    PharmacyDirectory
)
from .services import ErxService


class ErxModelTests(TestCase):
    """Tests for eRx models"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='doctor',
            email='doctor@example.com',
            password='testpass123'
        )
        
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth=date(1980, 1, 1),
            gender='M',
            phone_home='555-1234',
            email='john@example.com'
        )
        
        self.pharmacy = PharmacyDirectory.objects.create(
            ncpdp_id='1234567',
            name='Test Pharmacy',
            address_line1='123 Main St',
            city='Test City',
            state='NY',
            zip_code='12345',
            phone='555-0123',
            accepts_erx=True
        )
        
        self.prescription = ElectronicPrescription.objects.create(
            patient=self.patient,
            prescriber=self.user,
            drug_name='Test Drug',
            strength='10mg',
            dosage_form='tablet',
            quantity=Decimal('30'),
            days_supply=30,
            refills=3,
            directions='Take 1 tablet daily',
            pharmacy_ncpdp=self.pharmacy.ncpdp_id,
            pharmacy_name=self.pharmacy.name
        )
    
    def test_prescription_creation(self):
        """Test prescription model creation"""
        self.assertEqual(self.prescription.patient, self.patient)
        self.assertEqual(self.prescription.prescriber, self.user)
        self.assertEqual(self.prescription.drug_name, 'Test Drug')
        self.assertEqual(self.prescription.status, 'draft')
        self.assertIsNotNone(self.prescription.prescription_id)
    
    def test_prescription_string_representation(self):
        """Test prescription string representation"""
        str_repr = str(self.prescription)
        self.assertIn('Test Drug', str_repr)
        self.assertIn('John Doe', str_repr)
    
    def test_prescription_refills_remaining(self):
        """Test refills remaining calculation"""
        self.assertEqual(self.prescription.refills_remaining, 3)
        
        # Create a refill
        PrescriptionRefill.objects.create(
            prescription=self.prescription,
            refill_number=1,
            date_filled=timezone.now(),
            quantity_dispensed=Decimal('30'),
            days_supply=30
        )
        
        self.assertEqual(self.prescription.refills_remaining, 2)
    
    def test_prescription_expiration(self):
        """Test prescription expiration"""
        # Set expiration date to yesterday
        self.prescription.expiration_date = timezone.now().date() - timedelta(days=1)
        self.prescription.save()
        
        self.assertTrue(self.prescription.is_expired)
        
        # Set expiration date to tomorrow
        self.prescription.expiration_date = timezone.now().date() + timedelta(days=1)
        self.prescription.save()
        
        self.assertFalse(self.prescription.is_expired)
    
    def test_drug_formulary_creation(self):
        """Test drug formulary creation"""
        formulary = DrugFormulary.objects.create(
            drug_name='Test Drug',
            generic_name='Generic Test',
            formulary_status='preferred',
            tier_level=1,
            copay_amount=Decimal('10.00')
        )
        
        self.assertEqual(formulary.drug_name, 'Test Drug')
        self.assertEqual(formulary.formulary_status, 'preferred')
        self.assertEqual(formulary.tier_level, 1)
    
    def test_drug_interaction_creation(self):
        """Test drug interaction creation"""
        interaction = DrugInteraction.objects.create(
            drug1_name='Drug A',
            drug2_name='Drug B',
            interaction_severity='moderate',
            interaction_description='Test interaction'
        )
        
        self.assertEqual(interaction.drug1_name, 'Drug A')
        self.assertEqual(interaction.drug2_name, 'Drug B')
        self.assertEqual(interaction.interaction_severity, 'moderate')
    
    def test_pharmacy_directory_creation(self):
        """Test pharmacy directory creation"""
        self.assertEqual(self.pharmacy.name, 'Test Pharmacy')
        self.assertEqual(self.pharmacy.city, 'Test City')
        self.assertTrue(self.pharmacy.accepts_erx)
        self.assertTrue(self.pharmacy.is_active)
    
    def test_pharmacy_full_address(self):
        """Test pharmacy full address property"""
        expected_address = "123 Main St, Test City, NY 12345"
        self.assertEqual(self.pharmacy.full_address, expected_address)


class ErxServiceTests(TestCase):
    """Tests for eRx services"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='doctor',
            email='doctor@example.com',
            password='testpass123'
        )
        
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth=date(1980, 1, 1),
            gender='M',
            phone_home='555-1234',
            email='john@example.com'
        )
        
        self.pharmacy = PharmacyDirectory.objects.create(
            ncpdp_id='1234567',
            name='Test Pharmacy',
            address_line1='123 Main St',
            city='Test City',
            state='NY',
            zip_code='12345',
            phone='555-0123',
            accepts_erx=True
        )
    
    def test_create_prescription(self):
        """Test prescription creation service"""
        prescription_data = {
            'drug_name': 'Test Drug',
            'strength': '10mg',
            'dosage_form': 'tablet',
            'quantity': Decimal('30'),
            'days_supply': 30,
            'refills': 3,
            'directions': 'Take 1 tablet daily',
            'pharmacy_ncpdp': self.pharmacy.ncpdp_id,
            'pharmacy_name': self.pharmacy.name
        }
        
        prescription = ErxService.create_prescription(
            self.patient,
            self.user,
            prescription_data
        )
        
        self.assertIsNotNone(prescription)
        self.assertEqual(prescription.patient, self.patient)
        self.assertEqual(prescription.prescriber, self.user)
        self.assertEqual(prescription.drug_name, 'Test Drug')
        
        # Check that history was created
        history = PrescriptionHistory.objects.filter(prescription=prescription)
        self.assertTrue(history.exists())
    
    def test_validate_prescription(self):
        """Test prescription validation"""
        prescription = ElectronicPrescription.objects.create(
            patient=self.patient,
            prescriber=self.user,
            drug_name='Test Drug',
            strength='10mg',
            dosage_form='tablet',
            quantity=Decimal('30'),
            days_supply=30,
            refills=3,
            directions='Take 1 tablet daily',
            pharmacy_ncpdp=self.pharmacy.ncpdp_id,
            pharmacy_name=self.pharmacy.name
        )
        
        # Valid prescription
        self.assertTrue(ErxService.validate_prescription(prescription))
        
        # Invalid prescription (missing directions)
        prescription.directions = ''
        self.assertFalse(ErxService.validate_prescription(prescription))
    
    def test_search_pharmacies(self):
        """Test pharmacy search"""
        # Create additional pharmacies
        PharmacyDirectory.objects.create(
            ncpdp_id='2345678',
            name='Another Pharmacy',
            address_line1='456 Oak St',
            city='Another City',
            state='NY',
            zip_code='54321',
            phone='555-0456',
            accepts_erx=True
        )
        
        # Search by name
        results = ErxService.search_pharmacies({'search_term': 'Test'})
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, 'Test Pharmacy')
        
        # Search by city
        results = ErxService.search_pharmacies({'city': 'Test City'})
        self.assertEqual(len(results), 1)
        
        # Search by state
        results = ErxService.search_pharmacies({'state': 'NY'})
        self.assertEqual(len(results), 2)
    
    def test_check_drug_interactions(self):
        """Test drug interaction checking"""
        # Create drug interactions
        DrugInteraction.objects.create(
            drug1_name='Drug A',
            drug2_name='Drug B',
            interaction_severity='moderate',
            interaction_description='Test interaction'
        )
        
        # Create existing prescription
        ElectronicPrescription.objects.create(
            patient=self.patient,
            prescriber=self.user,
            drug_name='Drug A',
            strength='10mg',
            dosage_form='tablet',
            quantity=Decimal('30'),
            days_supply=30,
            refills=3,
            directions='Take 1 tablet daily',
            status='sent',
            pharmacy_ncpdp=self.pharmacy.ncpdp_id,
            pharmacy_name=self.pharmacy.name,
            expiration_date=timezone.now().date() + timedelta(days=30)
        )
        
        # Check for interactions
        interactions = ErxService.check_drug_interactions('Drug B', self.patient)
        self.assertEqual(len(interactions), 1)
        self.assertEqual(interactions[0]['severity'], 'moderate')


class ErxAPITests(APITestCase):
    """Tests for eRx API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='doctor',
            email='doctor@example.com',
            password='testpass123'
        )
        
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth=date(1980, 1, 1),
            gender='M',
            phone_home='555-1234',
            email='john@example.com'
        )
        
        self.pharmacy = PharmacyDirectory.objects.create(
            ncpdp_id='1234567',
            name='Test Pharmacy',
            address_line1='123 Main St',
            city='Test City',
            state='NY',
            zip_code='12345',
            phone='555-0123',
            accepts_erx=True
        )
        
        self.prescription = ElectronicPrescription.objects.create(
            patient=self.patient,
            prescriber=self.user,
            drug_name='Test Drug',
            strength='10mg',
            dosage_form='tablet',
            quantity=Decimal('30'),
            days_supply=30,
            refills=3,
            directions='Take 1 tablet daily',
            pharmacy_ncpdp=self.pharmacy.ncpdp_id,
            pharmacy_name=self.pharmacy.name
        )
    
    def test_prescription_list_requires_authentication(self):
        """Test that prescription list requires authentication"""
        url = '/api/v1/erx/api/v1/prescriptions/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_prescription_list_authenticated(self):
        """Test prescription list with authentication"""
        self.client.force_authenticate(user=self.user)
        url = '/api/v1/erx/api/v1/prescriptions/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_create_prescription_api(self):
        """Test prescription creation via API"""
        self.client.force_authenticate(user=self.user)
        url = '/api/v1/erx/api/v1/prescriptions/'
        
        data = {
            'patient': self.patient.id,
            'drug_name': 'New Drug',
            'strength': '5mg',
            'dosage_form': 'tablet',
            'quantity': '60',
            'days_supply': 30,
            'refills': 2,
            'directions': 'Take 2 tablets daily',
            'pharmacy_ncpdp': self.pharmacy.ncpdp_id,
            'pharmacy_name': self.pharmacy.name
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check that prescription was created
        # The response should contain the prescription_id
        self.assertIn('prescription_id', response.data)
        prescription = ElectronicPrescription.objects.get(
            prescription_id=response.data['prescription_id']
        )
        self.assertEqual(prescription.drug_name, 'New Drug')
        self.assertEqual(prescription.prescriber, self.user)
    
    def test_send_prescription_api(self):
        """Test sending prescription via API"""
        self.client.force_authenticate(user=self.user)
        url = f'/api/v1/erx/api/v1/prescriptions/{self.prescription.id}/send_prescription/'
        
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that prescription status was updated
        self.prescription.refresh_from_db()
        self.assertEqual(self.prescription.status, 'sent')
        self.assertIsNotNone(self.prescription.date_sent)
    
    def test_cancel_prescription_api(self):
        """Test cancelling prescription via API"""
        self.client.force_authenticate(user=self.user)
        url = f'/api/v1/erx/api/v1/prescriptions/{self.prescription.id}/cancel_prescription/'
        
        data = {'reason': 'Patient request'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that prescription status was updated
        self.prescription.refresh_from_db()
        self.assertEqual(self.prescription.status, 'cancelled')
    
    def test_check_drug_interactions_api(self):
        """Test drug interaction check via API"""
        self.client.force_authenticate(user=self.user)
        url = '/api/v1/erx/api/v1/prescriptions/check_interactions/'
        
        # Create a drug interaction
        DrugInteraction.objects.create(
            drug1_name='Drug A',
            drug2_name='Drug B',
            interaction_severity='major',
            interaction_description='Serious interaction'
        )
        
        data = {'drugs': ['Drug A', 'Drug B']}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that interaction was found
        self.assertEqual(response.data['interaction_count'], 1)
        self.assertEqual(response.data['interactions'][0]['severity'], 'major')
    
    def test_pharmacy_search_api(self):
        """Test pharmacy search via API"""
        self.client.force_authenticate(user=self.user)
        
        # Create additional pharmacy (setup already created one)
        PharmacyDirectory.objects.create(
            ncpdp_id='7654321',
            name='Another Pharmacy',
            address_line1='456 Oak St',
            city='Another City',
            state='NY',
            zip_code='54321',
            phone='555-0456',
            accepts_erx=True
        )
        
        url = '/api/v1/erx/api/v1/pharmacies/'
        response = self.client.get(url, {'search': 'Test'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Test Pharmacy')


class ErxIntegrationTests(TestCase):
    """Integration tests for complete eRx workflows"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='doctor',
            email='doctor@example.com',
            password='testpass123'
        )
        
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth=date(1980, 1, 1),
            gender='M',
            phone_home='555-1234',
            email='john@example.com'
        )
        
        self.pharmacy = PharmacyDirectory.objects.create(
            ncpdp_id='1234567',
            name='Test Pharmacy',
            address_line1='123 Main St',
            city='Test City',
            state='NY',
            zip_code='12345',
            phone='555-0123',
            accepts_erx=True
        )
    
    def test_complete_prescription_workflow(self):
        """Test complete prescription workflow"""
        # Create prescription
        prescription_data = {
            'drug_name': 'Test Drug',
            'strength': '10mg',
            'dosage_form': 'tablet',
            'quantity': Decimal('30'),
            'days_supply': 30,
            'refills': 3,
            'directions': 'Take 1 tablet daily',
            'pharmacy_ncpdp': self.pharmacy.ncpdp_id,
            'pharmacy_name': self.pharmacy.name
        }
        
        prescription = ErxService.create_prescription(
            self.patient,
            self.user,
            prescription_data
        )
        
        # Verify prescription was created
        self.assertIsNotNone(prescription)
        self.assertEqual(prescription.status, 'draft')
        
        # Send prescription
        success = ErxService.send_prescription(prescription, self.user)
        self.assertTrue(success)
        
        prescription.refresh_from_db()
        self.assertEqual(prescription.status, 'sent')
        self.assertIsNotNone(prescription.date_sent)
        
        # Process refill
        refill_data = {
            'date_filled': timezone.now(),
            'quantity_dispensed': Decimal('30'),
            'days_supply': 30
        }
        
        refill = ErxService.process_refill(prescription, refill_data, self.user)
        self.assertIsNotNone(refill)
        self.assertEqual(refill.refill_number, 1)
        self.assertEqual(prescription.refills_remaining, 2)
        
        # Verify history was created
        history = PrescriptionHistory.objects.filter(prescription=prescription)
        self.assertTrue(history.exists())
        
        # Check for creation, sending, and refill actions
        actions = [h.action for h in history]
        self.assertIn('created', actions)
        self.assertIn('sent', actions)
