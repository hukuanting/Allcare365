from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from patients.models import Patient
from .models import (
    PatientPortalAccess, PortalMessage, PatientPortalSession,
    PatientPortalAuditLog, PatientEducationResource, PatientHealthReminder
)
from datetime import datetime, timedelta
import json


class PatientPortalModelTest(TestCase):
    """Test cases for Patient Portal models"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testpatient',
            email='test@example.com',
            password='testpass123'
        )
        
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth='1980-01-15',
            gender='M',
            phone_home='555-123-4567',
            email='john.doe@email.com',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.portal_access = PatientPortalAccess.objects.create(
            patient=self.patient,
            username='testpatient',
            email='test@example.com',
            is_active=True,
            last_login=timezone.now(),
            created_by=self.user,
            updated_by=self.user
        )
    
    def test_patient_portal_access_creation(self):
        """Test PatientPortalAccess model creation."""
        self.assertEqual(self.portal_access.patient, self.patient)
        self.assertEqual(self.portal_access.username, 'testpatient')
        self.assertTrue(self.portal_access.is_active)
        self.assertIsNotNone(self.portal_access.last_login)
    
    def test_portal_message_creation(self):
        """Test PortalMessage model creation."""
        message = PortalMessage.objects.create(
            patient=self.patient,
            provider=self.user,
            subject='Test Message',
            message='This is a test message',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(message.patient, self.patient)
        self.assertEqual(message.subject, 'Test Message')
        self.assertEqual(message.message, 'This is a test message')
        self.assertFalse(message.is_read_by_patient)
    
    def test_portal_session_creation(self):
        """Test PatientPortalSession model creation."""
        session = PatientPortalSession.objects.create(
            patient=self.patient,
            session_key='test-session-123',
            ip_address='127.0.0.1',
            user_agent='Test Browser',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(session.patient, self.patient)
        self.assertEqual(session.session_key, 'test-session-123')
        self.assertEqual(session.ip_address, '127.0.0.1')
        self.assertTrue(session.is_active)
    
    def test_audit_log_creation(self):
        """Test PatientPortalAuditLog model creation."""
        audit_log = PatientPortalAuditLog.objects.create(
            patient=self.patient,
            action='login',
            description='User logged in',
            ip_address='127.0.0.1',
            user_agent='Test Browser',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(audit_log.patient, self.patient)
        self.assertEqual(audit_log.action, 'login')
        self.assertEqual(audit_log.description, 'User logged in')
        self.assertEqual(audit_log.ip_address, '127.0.0.1')
    
    def test_education_resource_creation(self):
        """Test PatientEducationResource model creation."""
        resource = PatientEducationResource.objects.create(
            title='Understanding Diabetes',
            description='Learn about diabetes management',
            content='This is educational content about diabetes',
            resource_type='article',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(resource.title, 'Understanding Diabetes')
        self.assertEqual(resource.resource_type, 'article')
        self.assertIsNotNone(resource.create_date)
    
    def test_health_reminder_creation(self):
        """Test PatientHealthReminder model creation."""
        reminder_date = timezone.now() + timedelta(days=30)
        reminder = PatientHealthReminder.objects.create(
            patient=self.patient,
            reminder_type='appointment',
            title='Annual Checkup',
            description='Time for your annual physical',
            remind_date=reminder_date,
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(reminder.patient, self.patient)
        self.assertEqual(reminder.reminder_type, 'appointment')
        self.assertEqual(reminder.title, 'Annual Checkup')
        self.assertFalse(reminder.is_completed)


class PatientPortalViewTest(TestCase):
    """Test cases for Patient Portal views"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testpatient',
            email='test@example.com',
            password='testpass123'
        )
        
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth='1980-01-15',
            gender='M',
            phone_home='555-123-4567',
            email='john.doe@email.com',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.portal_access = PatientPortalAccess.objects.create(
            patient=self.patient,
            username='testpatient',
            email='test@example.com',
            is_active=True,
            created_by=self.user,
            updated_by=self.user
        )
    
    def login_patient(self):
        """Helper method to login patient and set session"""
        self.client.login(username='testpatient', password='testpass123')
        session = self.client.session
        session['patient_id'] = str(self.patient.id)
        session.save()
    
    def test_home_view_anonymous(self):
        """Test home view for anonymous users."""
        response = self.client.get(reverse('patient_portal:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Patient Portal')
    
    def test_home_view_authenticated(self):
        """Test home view for authenticated users."""
        self.client.login(username='testpatient', password='testpass123')
        response = self.client.get(reverse('patient_portal:home'))
        self.assertEqual(response.status_code, 200)
    
    def test_login_view_get(self):
        """Test login view GET request."""
        response = self.client.get(reverse('patient_portal:login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Login')
    
    def test_login_view_post_valid(self):
        """Test login view POST request with valid credentials."""
        response = self.client.post(reverse('patient_portal:login'), {
            'username': 'testpatient',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after login
    
    def test_login_view_post_invalid(self):
        """Test login view POST request with invalid credentials."""
        response = self.client.post(reverse('patient_portal:login'), {
            'username': 'testpatient',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid')
    
    def test_logout_view(self):
        """Test logout view."""
        self.client.login(username='testpatient', password='testpass123')
        response = self.client.get(reverse('patient_portal:logout'))
        self.assertEqual(response.status_code, 302)  # Redirect after logout
    
    def test_dashboard_view_anonymous(self):
        """Test dashboard view for anonymous users."""
        response = self.client.get(reverse('patient_portal:dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_dashboard_view_authenticated(self):
        """Test dashboard view for authenticated users."""
        self.login_patient()
        response = self.client.get(reverse('patient_portal:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard')
    
    def test_medical_records_view(self):
        """Test medical records view."""
        self.login_patient()
        response = self.client.get(reverse('patient_portal:medical_records'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Medical Records')
    
    def test_appointments_view(self):
        """Test appointments view."""
        self.login_patient()
        response = self.client.get(reverse('patient_portal:appointments'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Appointments')
    
    def test_prescriptions_view(self):
        """Test prescriptions view."""
        self.login_patient()
        response = self.client.get(reverse('patient_portal:prescriptions'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Prescriptions')
    
    def test_lab_results_view(self):
        """Test lab results view."""
        self.login_patient()
        response = self.client.get(reverse('patient_portal:lab_results'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Lab Results')
    
    def test_messages_view(self):
        """Test messages view."""
        self.login_patient()
        response = self.client.get(reverse('patient_portal:messages'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Messages')
    
    def test_education_view(self):
        """Test education view."""
        self.login_patient()
        response = self.client.get(reverse('patient_portal:education'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Education')
    
    def test_profile_view(self):
        """Test profile view."""
        self.login_patient()
        response = self.client.get(reverse('patient_portal:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Profile')


class PatientPortalAPITest(APITestCase):
    """Test cases for Patient Portal API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testpatient',
            email='test@example.com',
            password='testpass123'
        )
        
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth='1980-01-15',
            gender='M',
            phone_home='555-123-4567',
            email='john.doe@email.com',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.portal_access = PatientPortalAccess.objects.create(
            patient=self.patient,
            username='testpatient',
            email='test@example.com',
            is_active=True,
            created_by=self.user,
            updated_by=self.user
        )
    
    def test_api_login_valid(self):
        """Test API login with valid credentials."""
        url = reverse('patient_portal:api_login')
        data = {
            'username': 'testpatient',
            'password': 'testpass123'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_api_login_invalid(self):
        """Test API login with invalid credentials."""
        url = reverse('patient_portal:api_login')
        data = {
            'username': 'testpatient',
            'password': 'wrongpassword'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_api_dashboard_anonymous(self):
        """Test API dashboard for anonymous users."""
        url = reverse('patient_portal:api_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_api_dashboard_authenticated(self):
        """Test API dashboard for authenticated users."""
        self.client.force_authenticate(user=self.user)
        # Set up patient session
        session = self.client.session
        session['patient_id'] = str(self.patient.id)
        session.save()
        
        url = reverse('patient_portal:api_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_portal_access_viewset(self):
        """Test PatientPortalAccess ViewSet."""
        self.client.force_authenticate(user=self.user)
        url = reverse('patient_portal:patientportalaccess-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_portal_message_viewset(self):
        """Test PortalMessage ViewSet."""
        self.client.force_authenticate(user=self.user)
        url = reverse('patient_portal:portalmessage-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_education_resource_viewset(self):
        """Test PatientEducationResource ViewSet."""
        self.client.force_authenticate(user=self.user)
        url = reverse('patient_portal:patienteducationresource-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_health_reminder_viewset(self):
        """Test PatientHealthReminder ViewSet."""
        self.client.force_authenticate(user=self.user)
        url = reverse('patient_portal:patienthealthreminder-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class PatientPortalSecurityTest(TestCase):
    """Test cases for Patient Portal security features"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testpatient',
            email='test@example.com',
            password='testpass123'
        )
        
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth='1980-01-15',
            gender='M',
            phone_home='555-123-4567',
            email='john.doe@email.com',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.portal_access = PatientPortalAccess.objects.create(
            patient=self.patient,
            username='testpatient',
            email='test@example.com',
            is_active=True,
            created_by=self.user,
            updated_by=self.user
        )
    
    def test_protected_views_require_authentication(self):
        """Test that protected views require authentication."""
        protected_urls = [
            reverse('patient_portal:dashboard'),
            reverse('patient_portal:medical_records'),
            reverse('patient_portal:appointments'),
            reverse('patient_portal:prescriptions'),
            reverse('patient_portal:lab_results'),
            reverse('patient_portal:messages'),
            reverse('patient_portal:education'),
            reverse('patient_portal:profile'),
        ]
        
        for url in protected_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_inactive_portal_access_denied(self):
        """Test that inactive portal access is denied."""
        self.portal_access.is_active = False
        self.portal_access.save()
        
        response = self.client.post(reverse('patient_portal:login'), {
            'username': 'testpatient',
            'password': 'testpass123'
        })
        
        # Should not be able to login with inactive access
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your portal access has been deactivated')
    
    def test_session_creation_on_login(self):
        """Test that session is created on login."""
        initial_sessions = PatientPortalSession.objects.count()
        
        response = self.client.post(reverse('patient_portal:login'), {
            'username': 'testpatient',
            'password': 'testpass123'
        })
        
        # Check that session was created
        self.assertEqual(PatientPortalSession.objects.count(), initial_sessions + 1)
    
    def test_audit_log_creation_on_login(self):
        """Test that audit log is created on login."""
        initial_logs = PatientPortalAuditLog.objects.count()
        
        response = self.client.post(reverse('patient_portal:login'), {
            'username': 'testpatient',
            'password': 'testpass123'
        })
        
        # Check that audit log was created
        self.assertEqual(PatientPortalAuditLog.objects.count(), initial_logs + 1)
