"""
Clinical Decision Support Tests

This module contains tests for the clinical decision support models, views, and APIs.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
import json
import uuid

from .models import (
    RuleCategory, ClinicalRule, ClinicalAlert, DrugInteraction,
    PreventiveCareReminder, PatientReminder, RuleExecution,
    ClinicalProtocol, ProtocolExecution
)
from patients.models import Patient


class CDSModelsTestCase(TestCase):
    """Test CDS models"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth='1980-01-01',
            gender='M',
            medical_record_number='MR001'
        )
        
        self.category = RuleCategory.objects.create(
            name='Medication Safety',
            description='Rules for medication safety checks',
            color='#ff0000'
        )
    
    def test_rule_category_creation(self):
        """Test rule category creation"""
        self.assertEqual(self.category.name, 'Medication Safety')
        self.assertEqual(str(self.category), 'Medication Safety')
        self.assertTrue(self.category.is_active)
    
    def test_clinical_rule_creation(self):
        """Test clinical rule creation"""
        rule = ClinicalRule.objects.create(
            name='High Blood Pressure Alert',
            code='HBP001',
            description='Alert for high blood pressure readings',
            category=self.category,
            rule_type='vital_signs',
            action_type='alert',
            severity='high',
            priority=8,
            condition_logic={'systolic_bp': {'gt': 140}},
            action_config={'create_alert': True},
            created_by=self.user
        )
        
        self.assertEqual(rule.name, 'High Blood Pressure Alert')
        self.assertEqual(rule.code, 'HBP001')
        self.assertEqual(rule.category, self.category)
        self.assertEqual(rule.rule_type, 'vital_signs')
        self.assertEqual(rule.severity, 'high')
        self.assertEqual(rule.priority, 8)
        self.assertTrue(rule.is_active)
        self.assertEqual(str(rule), 'High Blood Pressure Alert (Vital Signs Alert)')
    
    def test_clinical_alert_creation(self):
        """Test clinical alert creation"""
        rule = ClinicalRule.objects.create(
            name='Test Rule',
            code='TEST001',
            category=self.category,
            rule_type='medication_alert',
            action_type='alert',
            severity='medium',
            priority=5,
            description='Test rule for alerts',
            created_by=self.user
        )
        
        alert = ClinicalAlert.objects.create(
            title='Medication Alert',
            message='Patient has allergy to prescribed medication',
            alert_level='critical',
            patient=self.patient,
            rule=rule,
            created_by=self.user
        )
        
        self.assertEqual(alert.title, 'Medication Alert')
        self.assertEqual(alert.alert_level, 'critical')
        self.assertEqual(alert.patient, self.patient)
        self.assertEqual(alert.rule, rule)
        self.assertEqual(alert.status, 'active')
        self.assertIsNone(alert.acknowledged_at)
        self.assertIsNone(alert.acknowledged_by)
    
    def test_drug_interaction_creation(self):
        """Test drug interaction creation"""
        interaction = DrugInteraction.objects.create(
            drug_1='Warfarin',
            drug_2='Aspirin',
            interaction_type='pharmacodynamic',
            severity='major',
            mechanism='Increased bleeding risk through additive antiplatelet effects',
            clinical_effect='High risk of bleeding complications',
            management='Monitor INR closely and consider dose adjustment',
            evidence_level='A',
            created_by=self.user
        )
        
        self.assertEqual(interaction.drug_1, 'Warfarin')
        self.assertEqual(interaction.drug_2, 'Aspirin')
        self.assertEqual(interaction.severity, 'major')
        self.assertTrue(interaction.is_active)
    
    def test_preventive_care_reminder_creation(self):
        """Test preventive care reminder creation"""
        reminder = PreventiveCareReminder.objects.create(
            name='Mammography Screening',
            description='Annual mammography for breast cancer screening',
            reminder_type='screening',
            target_age_min=40,
            target_age_max=74,
            interval_months=12,
            target_gender='F',
            created_by=self.user
        )
        
        self.assertEqual(reminder.name, 'Mammography Screening')
        self.assertEqual(reminder.reminder_type, 'screening')
        self.assertEqual(reminder.target_age_min, 40)
        self.assertEqual(reminder.target_gender, 'F')
        self.assertEqual(reminder.interval_months, 12)
    
    def test_patient_reminder_creation(self):
        """Test patient reminder creation"""
        preventive_reminder = PreventiveCareReminder.objects.create(
            name='Colonoscopy',
            reminder_type='screening',
            target_age_min=50,
            interval_months=120,  # 10 years
            description='Colonoscopy screening for colorectal cancer',
            created_by=self.user
        )
        
        patient_reminder = PatientReminder.objects.create(
            patient=self.patient,
            preventive_care=preventive_reminder,
            due_date='2024-12-31',
            priority=5,
            created_by=self.user
        )
        
        self.assertEqual(patient_reminder.patient, self.patient)
        self.assertEqual(patient_reminder.preventive_care, preventive_reminder)
        self.assertEqual(patient_reminder.status, 'pending')
    
    def test_rule_execution_creation(self):
        """Test rule execution creation"""
        rule = ClinicalRule.objects.create(
            name='Test Rule',
            code='TEST002',
            category=self.category,
            rule_type='medication_alert',
            action_type='alert',
            severity='medium',
            priority=5,
            description='Test rule for execution',
            created_by=self.user
        )
        
        execution = RuleExecution.objects.create(
            rule=rule,
            patient=self.patient,
            execution_time_ms=100,
            status='success',
            input_data={'test': 'data'},
            output_data={'alerts_triggered': 1, 'status': 'completed'},
            condition_met=True,
            alert_generated=True,
            created_by=self.user
        )
        
        self.assertEqual(execution.rule, rule)
        self.assertEqual(execution.patient, self.patient)
        self.assertEqual(execution.status, 'success')
        self.assertEqual(execution.output_data['alerts_triggered'], 1)
        self.assertTrue(execution.condition_met)
        self.assertTrue(execution.alert_generated)
    
    def test_clinical_protocol_creation(self):
        """Test clinical protocol creation"""
        protocol = ClinicalProtocol.objects.create(
            name='Hypertension Management',
            code='HTN001',
            protocol_type='treatment',
            description='Protocol for managing hypertension',
            version='1.0',
            steps=[
                {'step': 1, 'action': 'Measure blood pressure'},
                {'step': 2, 'action': 'Assess cardiovascular risk'}
            ],
            conditions=[
                {'point': 1, 'condition': 'BP > 140/90', 'action': 'Start medication'}
            ],
            created_by=self.user
        )
        
        self.assertEqual(protocol.name, 'Hypertension Management')
        self.assertEqual(protocol.code, 'HTN001')
        self.assertEqual(protocol.protocol_type, 'treatment')
        self.assertEqual(len(protocol.steps), 2)
        self.assertEqual(len(protocol.conditions), 1)
    
    def test_protocol_execution_creation(self):
        """Test protocol execution creation"""
        protocol = ClinicalProtocol.objects.create(
            name='Test Protocol',
            code='TEST001',
            protocol_type='treatment',
            description='Test protocol for execution',
            created_by=self.user
        )
        
        execution = ProtocolExecution.objects.create(
            protocol=protocol,
            patient=self.patient,
            started_by=self.user,
            status='active',
            current_step=1,
            step_results={'current_step': 1}
        )
        
        self.assertEqual(execution.protocol, protocol)
        self.assertEqual(execution.patient, self.patient)
        self.assertEqual(execution.status, 'active')
        self.assertEqual(execution.current_step, 1)


class CDSViewsTestCase(TestCase):
    """Test CDS web views"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth='1980-01-01',
            gender='M',
            medical_record_number='MR001'
        )
        
        self.category = RuleCategory.objects.create(
            name='Test Category',
            description='Test category description'
        )
        
        self.rule = ClinicalRule.objects.create(
            name='Test Rule',
            code='TEST001',
            category=self.category,
            rule_type='medication_alert',
            action_type='alert',
            severity='medium',
            priority=5,
            description='Test rule for views',
            created_by=self.user
        )
        
        self.alert = ClinicalAlert.objects.create(
            title='Test Alert',
            message='Test alert message',
            alert_level='high',
            patient=self.patient,
            rule=self.rule,
            created_by=self.user
        )
    
    def test_dashboard_view_requires_login(self):
        """Test that dashboard requires login"""
        response = self.client.get(reverse('clinical_decision_support:dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_dashboard_view_authenticated(self):
        """Test dashboard view with authenticated user"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('clinical_decision_support:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Clinical Decision Support Dashboard')
    
    def test_rules_list_view(self):
        """Test rules list view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('clinical_decision_support:rules_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Rule')
    
    def test_rule_detail_view(self):
        """Test rule detail view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('clinical_decision_support:rule_detail', args=[self.rule.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Rule')
    
    def test_alerts_list_view(self):
        """Test alerts list view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('clinical_decision_support:alerts_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Alert')
    
    def test_acknowledge_alert_view(self):
        """Test acknowledge alert view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('clinical_decision_support:acknowledge_alert', args=[self.alert.id]))
        self.assertEqual(response.status_code, 302)  # Redirect after POST
        
        # Check that alert was acknowledged
        self.alert.refresh_from_db()
        self.assertIsNotNone(self.alert.acknowledged_at)
        self.assertEqual(self.alert.acknowledged_by, self.user)
    
    def test_drug_interactions_view(self):
        """Test drug interactions view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('clinical_decision_support:drug_interactions'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Drug Interactions')
    
    def test_preventive_care_view(self):
        """Test preventive care view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('clinical_decision_support:preventive_care'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Preventive Care')
    
    def test_protocols_list_view(self):
        """Test protocols list view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('clinical_decision_support:protocols_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Clinical Protocols')


class CDSAPITestCase(APITestCase):
    """Test CDS API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth='1980-01-01',
            gender='M',
            medical_record_number='MR001'
        )
        
        self.category = RuleCategory.objects.create(
            name='Test Category',
            description='Test category description'
        )
        
        self.rule = ClinicalRule.objects.create(
            name='Test Rule',
            code='TEST001',
            category=self.category,
            rule_type='medication_alert',
            action_type='alert',
            severity='medium',
            priority=5,
            description='Test rule for API',
            created_by=self.user
        )
        
        self.client.force_authenticate(user=self.user)
    
    def test_rule_categories_api(self):
        """Test rule categories API"""
        url = reverse('clinical_decision_support:rulecategory-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check that we have at least one category (from setUp)
        self.assertGreaterEqual(len(response.data['results']), 1)
        # Check that our test category is in the results
        category_names = [cat['name'] for cat in response.data['results']]
        self.assertIn('Test Category', category_names)
    
    def test_clinical_rules_api(self):
        """Test clinical rules API"""
        url = reverse('clinical_decision_support:clinicalrule-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check that we have at least one rule (from setUp)
        self.assertGreaterEqual(len(response.data['results']), 1)
        # Check that our test rule is in the results
        rule_names = [rule['name'] for rule in response.data['results']]
        self.assertIn('Test Rule', rule_names)
    
    def test_execute_rule_api(self):
        """Test execute rule API"""
        url = reverse('clinical_decision_support:clinicalrule-execute', args=[self.rule.id])
        data = {'patient_id': str(self.patient.id)}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('execution_id', response.data)
    
    def test_clinical_alerts_api(self):
        """Test clinical alerts API"""
        alert = ClinicalAlert.objects.create(
            title='Test Alert',
            message='Test alert message',
            alert_level='high',
            patient=self.patient,
            rule=self.rule,
            created_by=self.user
        )
        
        url = reverse('clinical_decision_support:clinicalalert-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check that we have at least one alert
        self.assertGreaterEqual(len(response.data['results']), 1)
        # Check that our test alert is in the results
        alert_titles = [alert['title'] for alert in response.data['results']]
        self.assertIn('Test Alert', alert_titles)
    
    def test_acknowledge_alert_api(self):
        """Test acknowledge alert API"""
        alert = ClinicalAlert.objects.create(
            title='Test Alert',
            message='Test alert message',
            alert_level='high',
            patient=self.patient,
            rule=self.rule,
            created_by=self.user
        )
        
        url = reverse('clinical_decision_support:clinicalalert-acknowledge', args=[alert.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'acknowledged')
        
        # Check that alert was acknowledged
        alert.refresh_from_db()
        self.assertIsNotNone(alert.acknowledged_at)
    
    def test_drug_interactions_api(self):
        """Test drug interactions API"""
        interaction = DrugInteraction.objects.create(
            drug_1='Warfarin',
            drug_2='Aspirin',
            interaction_type='pharmacodynamic',
            severity='major',
            mechanism='Increased bleeding risk',
            clinical_effect='Bleeding complications',
            management='Monitor INR closely',
            created_by=self.user
        )
        
        url = reverse('clinical_decision_support:druginteraction-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check that we have at least one interaction
        self.assertGreaterEqual(len(response.data['results']), 1)
        # Check that our test interaction is in the results
        drug_pairs = [(inter['drug_1'], inter['drug_2']) for inter in response.data['results']]
        self.assertIn(('Warfarin', 'Aspirin'), drug_pairs)
    
    def test_check_drug_interactions_api(self):
        """Test check drug interactions API"""
        # Create a specific interaction for this test
        interaction = DrugInteraction.objects.create(
            drug_1='TestDrug1',
            drug_2='TestDrug2',
            interaction_type='pharmacodynamic',
            severity='major',
            mechanism='Test mechanism',
            clinical_effect='Test effect',
            management='Test management',
            created_by=self.user
        )
        
        # Verify interaction was created
        self.assertTrue(interaction.is_active)
        self.assertEqual(DrugInteraction.objects.filter(drug_1='TestDrug1').count(), 1)
        
        url = reverse('clinical_decision_support:druginteraction-check-interactions')
        data = {'medications': ['TestDrug1', 'TestDrug2']}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertEqual(len(response.data['interactions']), 1)
        self.assertEqual(response.data['interactions'][0]['drug_1'], 'TestDrug1')
        self.assertEqual(response.data['interactions'][0]['drug_2'], 'TestDrug2')
    
    def test_preventive_care_reminders_api(self):
        """Test preventive care reminders API"""
        reminder = PreventiveCareReminder.objects.create(
            name='Test Mammography',
            reminder_type='screening',
            description='Test mammography screening reminder',
            target_age_min=40,
            interval_months=12,
            created_by=self.user
        )
        
        url = reverse('clinical_decision_support:preventivecarereminder-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check that we have at least one reminder
        self.assertGreaterEqual(len(response.data['results']), 1)
        # Check that our test reminder is in the results
        reminder_names = [rem['name'] for rem in response.data['results']]
        self.assertIn('Test Mammography', reminder_names)
    
    def test_clinical_protocols_api(self):
        """Test clinical protocols API"""
        protocol = ClinicalProtocol.objects.create(
            name='Test Protocol',
            code='TEST_PROTOCOL',
            protocol_type='treatment',
            description='Test protocol for API',
            created_by=self.user
        )
        
        url = reverse('clinical_decision_support:clinicalprotocol-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Test Protocol')
    
    def test_execute_protocol_api(self):
        """Test execute protocol API"""
        protocol = ClinicalProtocol.objects.create(
            name='Test Protocol',
            code='TEST_PROTOCOL',
            protocol_type='treatment',
            description='Test protocol for execution',
            created_by=self.user
        )
        
        url = reverse('clinical_decision_support:clinicalprotocol-execute', args=[protocol.id])
        data = {'patient_id': str(self.patient.id)}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('execution_id', response.data)
    
    def test_unauthorized_access(self):
        """Test that API requires authentication"""
        self.client.force_authenticate(user=None)
        url = reverse('clinical_decision_support:clinicalrule-list')
        response = self.client.get(url)
        # DRF returns 403 for unauthenticated requests with IsAuthenticated permission
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class CDSIntegrationTestCase(TestCase):
    """Test CDS integration scenarios"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth='1980-01-01',
            gender='M',
            medical_record_number='MR001'
        )
        
        self.category = RuleCategory.objects.create(
            name='Integration Test Category',
            description='Test category for integration tests'
        )
    
    def test_complete_workflow(self):
        """Test complete CDS workflow"""
        # Create a rule
        rule = ClinicalRule.objects.create(
            name='Integration Test Rule',
            code='INT001',
            category=self.category,
            rule_type='medication_alert',
            action_type='alert',
            severity='high',
            priority=8,
            description='Integration test rule',
            condition_logic={'medication': {'name': 'Aspirin'}},
            action_config={'create_alert': True},
            created_by=self.user
        )
        
        # Execute the rule
        execution = RuleExecution.objects.create(
            rule=rule,
            patient=self.patient,
            execution_time_ms=150,
            status='success',
            input_data={'test': True},
            output_data={'alerts_triggered': 1, 'status': 'completed'},
            condition_met=True,
            alert_generated=True,
            created_by=self.user
        )
        
        # Create an alert
        alert = ClinicalAlert.objects.create(
            title='Integration Test Alert',
            message='This is a test alert from rule execution',
            alert_level='high',
            patient=self.patient,
            rule=rule,
            created_by=self.user
        )
        
        # Verify the workflow
        self.assertEqual(execution.rule, rule)
        self.assertEqual(execution.patient, self.patient)
        self.assertEqual(alert.rule, rule)
        self.assertEqual(alert.patient, self.patient)
        
        # Acknowledge the alert
        alert.acknowledged_by = self.user
        alert.acknowledged_at = timezone.now()
        alert.save()
        
        self.assertIsNotNone(alert.acknowledged_at)
        self.assertEqual(alert.acknowledged_by, self.user)
    
    def test_drug_interaction_workflow(self):
        """Test drug interaction checking workflow"""
        # Create drug interactions
        interaction1 = DrugInteraction.objects.create(
            drug_1='Warfarin',
            drug_2='Aspirin',
            interaction_type='pharmacodynamic',
            severity='major',
            mechanism='Increased bleeding risk',
            clinical_effect='Enhanced bleeding risk',
            management='Monitor INR closely',
            created_by=self.user
        )
        
        interaction2 = DrugInteraction.objects.create(
            drug_1='Metformin',
            drug_2='Insulin',
            interaction_type='pharmacokinetic',
            severity='moderate',
            mechanism='Enhanced glucose lowering effect',
            clinical_effect='Risk of hypoglycemia',
            management='Monitor blood glucose',
            created_by=self.user
        )
        
        # Test checking interactions
        medications = ['Warfarin', 'Aspirin', 'Metformin']
        found_interactions = []
        
        for i, med1 in enumerate(medications):
            for med2 in medications[i+1:]:
                interaction = DrugInteraction.objects.filter(
                    drug_1=med1, drug_2=med2,
                    is_active=True
                ).first()
                if not interaction:
                    interaction = DrugInteraction.objects.filter(
                        drug_1=med2, drug_2=med1,
                        is_active=True
                    ).first()
                
                if interaction:
                    found_interactions.append(interaction)
        
        self.assertEqual(len(found_interactions), 1)
        self.assertEqual(found_interactions[0].drug_1, 'Warfarin')
        self.assertEqual(found_interactions[0].drug_2, 'Aspirin')
    
    def test_preventive_care_workflow(self):
        """Test preventive care reminder workflow"""
        # Create preventive care reminder
        preventive_reminder = PreventiveCareReminder.objects.create(
            name='Colonoscopy Screening',
            description='Colorectal cancer screening',
            reminder_type='screening',
            target_age_min=50,
            target_age_max=75,
            interval_months=120,  # 10 years
            created_by=self.user
        )
        
        # Create patient reminder
        patient_reminder = PatientReminder.objects.create(
            patient=self.patient,
            preventive_care=preventive_reminder,
            due_date='2024-12-31',
            priority=5,
            created_by=self.user
        )
        
        # Verify the workflow
        self.assertEqual(patient_reminder.preventive_care, preventive_reminder)
        self.assertEqual(patient_reminder.patient, self.patient)
        self.assertEqual(patient_reminder.status, 'pending')
        
        # Complete the reminder
        patient_reminder.status = 'completed'
        patient_reminder.completed_at = timezone.now()
        patient_reminder.save()
        
        self.assertEqual(patient_reminder.status, 'completed')
        self.assertIsNotNone(patient_reminder.completed_at)
