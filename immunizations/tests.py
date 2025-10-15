from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import date, datetime, timedelta
import json

from .models import (
    VaccineManufacturer, Vaccine, VaccineLot, ImmunizationSchedule,
    ScheduledVaccination, Immunization, ImmunizationObservation,
    ImmunizationContraindication, PatientImmunizationAlert
)
from patients.models import Patient


class ImmunizationModelsTestCase(TestCase):
    """Test cases for immunization models"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.manufacturer = VaccineManufacturer.objects.create(
            name='Test Manufacturer',
            code='TM001',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.vaccine = Vaccine.objects.create(
            cvx_code='01',
            name='DTP Vaccine',
            short_name='DTP',
            manufacturer=self.manufacturer,
            vaccine_type='Combination',
            doses_required=3,
            interval_days=30,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth=date(1990, 1, 1),
            gender='M',
            created_by=self.user,
            updated_by=self.user
        )
    
    def test_vaccine_manufacturer_creation(self):
        """Test vaccine manufacturer creation"""
        self.assertEqual(self.manufacturer.name, 'Test Manufacturer')
        self.assertEqual(self.manufacturer.code, 'TM001')
        self.assertTrue(self.manufacturer.is_active)
        self.assertIsNotNone(self.manufacturer.uuid)
    
    def test_vaccine_creation(self):
        """Test vaccine creation"""
        self.assertEqual(self.vaccine.cvx_code, '01')
        self.assertEqual(self.vaccine.name, 'DTP Vaccine')
        self.assertEqual(self.vaccine.manufacturer, self.manufacturer)
        self.assertEqual(self.vaccine.doses_required, 3)
        self.assertTrue(self.vaccine.is_active)
    
    def test_vaccine_lot_creation(self):
        """Test vaccine lot creation"""
        lot = VaccineLot.objects.create(
            vaccine=self.vaccine,
            lot_number='LOT001',
            manufacturer=self.manufacturer,
            expiration_date=date.today() + timedelta(days=365),
            quantity_received=100,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(lot.lot_number, 'LOT001')
        self.assertEqual(lot.quantity_available, 100)
        self.assertFalse(lot.is_expired)
    
    def test_vaccine_lot_expired(self):
        """Test expired vaccine lot"""
        expired_lot = VaccineLot.objects.create(
            vaccine=self.vaccine,
            lot_number='EXPIRED001',
            manufacturer=self.manufacturer,
            expiration_date=date.today() - timedelta(days=1),
            quantity_received=50,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertTrue(expired_lot.is_expired)
    
    def test_immunization_creation(self):
        """Test immunization creation"""
        lot = VaccineLot.objects.create(
            vaccine=self.vaccine,
            lot_number='LOT001',
            manufacturer=self.manufacturer,
            expiration_date=date.today() + timedelta(days=365),
            quantity_received=100,
            created_by=self.user,
            updated_by=self.user
        )
        
        immunization = Immunization.objects.create(
            patient=self.patient,
            vaccine=self.vaccine,
            vaccine_lot=lot,
            administered_date=timezone.now(),
            administered_by=self.user,
            amount_administered=0.5,
            amount_administered_unit='ml',
            dose_number=1,
            route='Intramuscular',
            administration_site='Left deltoid',
            completion_status='completed',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(immunization.patient, self.patient)
        self.assertEqual(immunization.vaccine, self.vaccine)
        self.assertEqual(immunization.dose_number, 1)
        self.assertEqual(immunization.completion_status, 'completed')
    
    def test_immunization_observation_creation(self):
        """Test immunization observation creation"""
        immunization = Immunization.objects.create(
            patient=self.patient,
            vaccine=self.vaccine,
            administered_date=timezone.now(),
            administered_by=self.user,
            completion_status='completed',
            created_by=self.user,
            updated_by=self.user
        )
        
        observation = ImmunizationObservation.objects.create(
            immunization=immunization,
            observation_type='local_reaction',
            observation_date=timezone.now(),
            severity='mild',
            description='Mild redness at injection site',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(observation.immunization, immunization)
        self.assertEqual(observation.observation_type, 'local_reaction')
        self.assertEqual(observation.severity, 'mild')
    
    def test_patient_immunization_alert_creation(self):
        """Test patient immunization alert creation"""
        alert = PatientImmunizationAlert.objects.create(
            patient=self.patient,
            vaccine=self.vaccine,
            alert_type='due',
            alert_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            message='DTP vaccine dose 2 is due',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(alert.patient, self.patient)
        self.assertEqual(alert.vaccine, self.vaccine)
        self.assertEqual(alert.alert_type, 'due')
        self.assertTrue(alert.is_active)


class ImmunizationAPITestCase(APITestCase):
    """Test cases for immunization API"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.manufacturer = VaccineManufacturer.objects.create(
            name='Test Manufacturer',
            code='TM001',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.vaccine = Vaccine.objects.create(
            cvx_code='01',
            name='DTP Vaccine',
            manufacturer=self.manufacturer,
            vaccine_type='Combination',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth=date(1990, 1, 1),
            gender='M',
            created_by=self.user,
            updated_by=self.user
        )
    
    def test_vaccine_manufacturer_list(self):
        """Test vaccine manufacturer list API"""
        url = reverse('immunizations:vaccinemanufacturer-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Test Manufacturer')
    
    def test_vaccine_manufacturer_create(self):
        """Test vaccine manufacturer create API"""
        url = reverse('immunizations:vaccinemanufacturer-list')
        data = {
            'name': 'New Manufacturer',
            'code': 'NM001',
            'is_active': True
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Manufacturer')
        self.assertEqual(response.data['code'], 'NM001')
    
    def test_vaccine_list(self):
        """Test vaccine list API"""
        url = reverse('immunizations:vaccine-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'DTP Vaccine')
    
    def test_vaccine_create(self):
        """Test vaccine create API"""
        url = reverse('immunizations:vaccine-list')
        data = {
            'cvx_code': '02',
            'name': 'MMR Vaccine',
            'manufacturer': self.manufacturer.id,
            'vaccine_type': 'Live Virus',
            'doses_required': 2
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'MMR Vaccine')
        self.assertEqual(response.data['cvx_code'], '02')
    
    def test_immunization_create(self):
        """Test immunization create API"""
        url = reverse('immunizations:immunization-list')
        data = {
            'patient': self.patient.id,
            'vaccine': self.vaccine.id,
            'administered_date': timezone.now().isoformat(),
            'administered_by': self.user.id,
            'dose_number': 1,
            'completion_status': 'completed'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['patient'], self.patient.id)
        self.assertEqual(response.data['vaccine'], self.vaccine.id)
        self.assertEqual(response.data['dose_number'], 1)
    
    def test_immunization_patient_history(self):
        """Test patient immunization history API"""
        # Create an immunization
        Immunization.objects.create(
            patient=self.patient,
            vaccine=self.vaccine,
            administered_date=timezone.now(),
            administered_by=self.user,
            completion_status='completed',
            created_by=self.user,
            updated_by=self.user
        )
        
        url = reverse('immunizations:immunization-patient-history')
        response = self.client.get(url, {'patient_id': self.patient.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['immunizations']), 1)
    
    def test_immunization_dashboard(self):
        """Test immunization dashboard API"""
        # Create some test data
        Immunization.objects.create(
            patient=self.patient,
            vaccine=self.vaccine,
            administered_date=timezone.now(),
            administered_by=self.user,
            completion_status='completed',
            created_by=self.user,
            updated_by=self.user
        )
        
        url = reverse('immunizations:immunization-dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_immunizations', response.data)
        self.assertIn('immunizations_today', response.data)
        self.assertIn('recent_immunizations', response.data)


class ImmunizationViewsTestCase(TestCase):
    """Test cases for immunization views"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
        
        self.manufacturer = VaccineManufacturer.objects.create(
            name='Test Manufacturer',
            code='TM001',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.vaccine = Vaccine.objects.create(
            cvx_code='01',
            name='DTP Vaccine',
            manufacturer=self.manufacturer,
            vaccine_type='Combination',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth=date(1990, 1, 1),
            gender='M',
            created_by=self.user,
            updated_by=self.user
        )
    
    def test_immunization_dashboard_view(self):
        """Test immunization dashboard view"""
        url = reverse('immunizations:dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Immunization Dashboard')
    
    def test_immunization_list_view(self):
        """Test immunization list view"""
        url = reverse('immunizations:list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Immunization Records')
    
    def test_patient_immunization_history_view(self):
        """Test patient immunization history view"""
        url = reverse('immunizations:patient_history', args=[self.patient.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.patient.get_full_name())
    
    def test_vaccine_inventory_view(self):
        """Test vaccine inventory view"""
        url = reverse('immunizations:inventory')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Vaccine Inventory')
    
    def test_immunization_detail_view(self):
        """Test immunization detail view"""
        immunization = Immunization.objects.create(
            patient=self.patient,
            vaccine=self.vaccine,
            administered_date=timezone.now(),
            administered_by=self.user,
            completion_status='completed',
            created_by=self.user,
            updated_by=self.user
        )
        
        url = reverse('immunizations:detail', args=[immunization.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.patient.get_full_name())


class ImmunizationBusinessLogicTestCase(TestCase):
    """Test cases for immunization business logic"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.manufacturer = VaccineManufacturer.objects.create(
            name='Test Manufacturer',
            code='TM001',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.vaccine = Vaccine.objects.create(
            cvx_code='01',
            name='DTP Vaccine',
            manufacturer=self.manufacturer,
            vaccine_type='Combination',
            doses_required=3,
            interval_days=30,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth=date(1990, 1, 1),
            gender='M',
            created_by=self.user,
            updated_by=self.user
        )
    
    def test_vaccine_lot_quantity_calculation(self):
        """Test vaccine lot quantity calculations"""
        lot = VaccineLot.objects.create(
            vaccine=self.vaccine,
            lot_number='LOT001',
            manufacturer=self.manufacturer,
            expiration_date=date.today() + timedelta(days=365),
            quantity_received=100,
            quantity_used=20,
            quantity_wasted=5,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(lot.quantity_available, 75)
    
    def test_immunization_series_tracking(self):
        """Test immunization series tracking"""
        # Create first dose
        dose1 = Immunization.objects.create(
            patient=self.patient,
            vaccine=self.vaccine,
            administered_date=timezone.now() - timedelta(days=60),
            administered_by=self.user,
            dose_number=1,
            completion_status='completed',
            created_by=self.user,
            updated_by=self.user
        )
        
        # Create second dose
        dose2 = Immunization.objects.create(
            patient=self.patient,
            vaccine=self.vaccine,
            administered_date=timezone.now() - timedelta(days=30),
            administered_by=self.user,
            dose_number=2,
            completion_status='completed',
            created_by=self.user,
            updated_by=self.user
        )
        
        # Check that patient has received 2 doses
        patient_immunizations = Immunization.objects.filter(
            patient=self.patient,
            vaccine=self.vaccine,
            completion_status='completed'
        ).order_by('dose_number')
        
        self.assertEqual(patient_immunizations.count(), 2)
        self.assertEqual(patient_immunizations.first().dose_number, 1)
        self.assertEqual(patient_immunizations.last().dose_number, 2)
    
    def test_contraindication_checking(self):
        """Test contraindication checking"""
        contraindication = ImmunizationContraindication.objects.create(
            vaccine=self.vaccine,
            contraindication_type='allergy',
            description='Allergic to eggs',
            severity='absolute',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(contraindication.vaccine, self.vaccine)
        self.assertEqual(contraindication.severity, 'absolute')
    
    def test_alert_system(self):
        """Test immunization alert system"""
        alert = PatientImmunizationAlert.objects.create(
            patient=self.patient,
            vaccine=self.vaccine,
            alert_type='due',
            alert_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            message='DTP vaccine dose 2 is due',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertTrue(alert.is_active)
        self.assertEqual(alert.alert_type, 'due')
        
        # Test alert acknowledgment
        alert.acknowledged_by = self.user
        alert.acknowledged_date = timezone.now()
        alert.is_active = False
        alert.save()
        
        self.assertFalse(alert.is_active)
        self.assertIsNotNone(alert.acknowledged_date)
