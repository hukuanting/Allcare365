"""
Therapy Groups Tests
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import date, time, timedelta
from rest_framework.test import APITestCase
from rest_framework import status
from patients.models import Patient
from .models import (
    TherapyGroup, TherapyGroupParticipant, TherapySession, 
    SessionAttendance, TherapyGroupNote
)


class TherapyGroupModelTest(TestCase):
    """Test cases for TherapyGroup model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='therapist1',
            email='therapist1@example.com',
            password='testpass123'
        )
        
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth=date(1990, 1, 1),
            medical_record_number='MRN123456'
        )
        
        self.therapy_group = TherapyGroup.objects.create(
            name='Group Therapy - Anxiety',
            description='Group therapy for anxiety disorders',
            therapy_type='group',
            start_date=date.today(),
            session_duration=60,
            max_participants=8,
            primary_therapist=self.user
        )
    
    def test_therapy_group_creation(self):
        """Test TherapyGroup model creation"""
        self.assertEqual(self.therapy_group.name, 'Group Therapy - Anxiety')
        self.assertEqual(self.therapy_group.therapy_type, 'group')
        self.assertEqual(self.therapy_group.primary_therapist, self.user)
        self.assertTrue(self.therapy_group.is_active)
        self.assertEqual(str(self.therapy_group), 'Group Therapy - Anxiety (Group Therapy)')
    
    def test_therapy_group_properties(self):
        """Test TherapyGroup model properties"""
        # Initially no participants
        self.assertEqual(self.therapy_group.current_participants_count, 0)
        self.assertEqual(self.therapy_group.available_slots, 8)
        self.assertFalse(self.therapy_group.is_full)
        
        # Add a participant
        participant = TherapyGroupParticipant.objects.create(
            group=self.therapy_group,
            patient=self.patient
        )
        
        # Refresh from database
        self.therapy_group.refresh_from_db()
        self.assertEqual(self.therapy_group.current_participants_count, 1)
        self.assertEqual(self.therapy_group.available_slots, 7)


class TherapyGroupParticipantModelTest(TestCase):
    """Test cases for TherapyGroupParticipant model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='therapist1',
            email='therapist1@example.com',
            password='testpass123'
        )
        
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth=date(1990, 1, 1),
            medical_record_number='MRN123456'
        )
        
        self.therapy_group = TherapyGroup.objects.create(
            name='Group Therapy - Anxiety',
            therapy_type='group',
            start_date=date.today(),
            session_duration=60,
            max_participants=8,
            primary_therapist=self.user
        )
        
        self.participant = TherapyGroupParticipant.objects.create(
            group=self.therapy_group,
            patient=self.patient,
            presenting_concerns='Anxiety and panic attacks'
        )
    
    def test_participant_creation(self):
        """Test TherapyGroupParticipant model creation"""
        self.assertEqual(self.participant.group, self.therapy_group)
        self.assertEqual(self.participant.patient, self.patient)
        self.assertEqual(self.participant.status, 'active')
        self.assertEqual(str(self.participant), f'{self.patient} in {self.therapy_group.name}')
    
    def test_attendance_rate(self):
        """Test attendance rate calculation"""
        # Initially no sessions
        self.assertEqual(self.participant.attendance_rate, 0)
        
        # Add some attendance data
        self.participant.sessions_attended = 8
        self.participant.sessions_missed = 2
        self.participant.save()
        
        self.assertEqual(self.participant.attendance_rate, 80.0)


class TherapySessionModelTest(TestCase):
    """Test cases for TherapySession model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='therapist1',
            email='therapist1@example.com',
            password='testpass123'
        )
        
        self.therapy_group = TherapyGroup.objects.create(
            name='Group Therapy - Anxiety',
            therapy_type='group',
            start_date=date.today(),
            session_duration=60,
            max_participants=8,
            primary_therapist=self.user
        )
        
        self.session = TherapySession.objects.create(
            group=self.therapy_group,
            session_number=1,
            scheduled_date=date.today(),
            scheduled_time=time(10, 0),
            duration=60,
            topic='Introduction and Goal Setting',
            therapist=self.user
        )
    
    def test_session_creation(self):
        """Test TherapySession model creation"""
        self.assertEqual(self.session.group, self.therapy_group)
        self.assertEqual(self.session.session_number, 1)
        self.assertEqual(self.session.therapist, self.user)
        self.assertEqual(self.session.status, 'scheduled')
        self.assertEqual(str(self.session), f'{self.therapy_group.name} - Session 1')


class TherapyGroupAPITest(APITestCase):
    """Test cases for TherapyGroup API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='therapist1',
            email='therapist1@example.com',
            password='testpass123'
        )
        
        self.client.force_authenticate(user=self.user)
        
        self.therapy_group = TherapyGroup.objects.create(
            name='Group Therapy - Anxiety',
            description='Group therapy for anxiety disorders',
            therapy_type='group',
            start_date=date.today(),
            session_duration=60,
            max_participants=8,
            primary_therapist=self.user
        )
    
    def test_therapy_group_list_api(self):
        """Test TherapyGroup list API endpoint"""
        url = '/api/v1/therapy-groups/api/groups/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Group Therapy - Anxiety')
    
    def test_therapy_group_create_api(self):
        """Test TherapyGroup create API endpoint"""
        url = '/api/v1/therapy-groups/api/groups/'
        data = {
            'name': 'Group Therapy - Depression',
            'description': 'Group therapy for depression',
            'therapy_type': 'group',
            'start_date': date.today().isoformat(),
            'session_duration': 90,
            'max_participants': 6,
            'primary_therapist': self.user.id
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Group Therapy - Depression')
        
        # Verify created in database
        self.assertTrue(
            TherapyGroup.objects.filter(name='Group Therapy - Depression').exists()
        )
    
    def test_therapy_group_detail_api(self):
        """Test TherapyGroup detail API endpoint"""
        url = f'/api/v1/therapy-groups/api/groups/{self.therapy_group.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Group Therapy - Anxiety')
        self.assertEqual(response.data['primary_therapist'], self.user.id)


class TherapyGroupViewTest(TestCase):
    """Test cases for TherapyGroup web views"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='therapist1',
            email='therapist1@example.com',
            password='testpass123'
        )
        
        self.therapy_group = TherapyGroup.objects.create(
            name='Group Therapy - Anxiety',
            description='Group therapy for anxiety disorders',
            therapy_type='group',
            start_date=date.today(),
            session_duration=60,
            max_participants=8,
            primary_therapist=self.user
        )
        
        self.client.login(username='therapist1', password='testpass123')
    
    def test_therapy_groups_dashboard_view(self):
        """Test therapy groups dashboard view"""
        url = reverse('therapy_groups:dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Therapy Groups Dashboard')
        self.assertContains(response, 'Total Groups')
    
    def test_therapy_group_list_view(self):
        """Test therapy group list view"""
        url = reverse('therapy_groups:group_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Therapy Groups')
        self.assertContains(response, 'Group Therapy - Anxiety')
    
    def test_therapy_group_detail_view(self):
        """Test therapy group detail view"""
        url = reverse('therapy_groups:group_detail', kwargs={'group_id': self.therapy_group.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Group Therapy - Anxiety')
        self.assertContains(response, 'Group therapy for anxiety disorders')
