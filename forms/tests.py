"""
Tests for the forms module
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import datetime, date
import json

from patients.models import Patient
from .models import (
    FormCategory, FormTemplate, FormField, FormSubmission, 
    FormValidationRule, FormAuditLog, StandardizedAssessment, FormReport
)


class FormModelsTestCase(TestCase):
    """Test cases for Forms models"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth=date(1990, 1, 1),
            medical_record_number='MRN123456'
        )
        
        self.category = FormCategory.objects.create(
            name='Clinical Assessment',
            description='Clinical assessment forms'
        )
        
        self.template = FormTemplate.objects.create(
            name='Patient Health Questionnaire',
            category=self.category,
            description='PHQ-9 Depression Assessment',
            version='1.0',
            created_by=self.user
        )
        
    def test_form_category_creation(self):
        """Test FormCategory model creation"""
        self.assertEqual(self.category.name, 'Clinical Assessment')
        self.assertTrue(self.category.is_active)
        self.assertEqual(str(self.category), 'Clinical Assessment')
        
    def test_form_template_creation(self):
        """Test FormTemplate model creation"""
        self.assertEqual(self.template.name, 'Patient Health Questionnaire')
        self.assertEqual(self.template.category, self.category)
        self.assertEqual(self.template.created_by, self.user)
        self.assertTrue(self.template.is_active)
        self.assertEqual(str(self.template), 'Patient Health Questionnaire v1.0')
        
    def test_form_field_creation(self):
        """Test FormField model creation"""
        field = FormField.objects.create(
            template=self.template,
            field_name='mood',
            field_label='How would you rate your mood?',
            field_type='select',
            choices=['Excellent', 'Good', 'Fair', 'Poor'],
            is_required=True,
            display_order=1
        )
        
        self.assertEqual(field.template, self.template)
        self.assertEqual(field.field_name, 'mood')
        self.assertEqual(field.field_type, 'select')
        self.assertTrue(field.is_required)
        self.assertEqual(str(field), f'{self.template.name} - How would you rate your mood?')
        
    def test_form_submission_creation(self):
        """Test FormSubmission model creation"""
        submission = FormSubmission.objects.create(
            template=self.template,
            patient=self.patient,
            submitted_by=self.user,
            form_data={'mood': 'Good'},
            status='submitted'
        )
        
        self.assertEqual(submission.template, self.template)
        self.assertEqual(submission.patient, self.patient)
        self.assertEqual(submission.submitted_by, self.user)
        self.assertEqual(submission.status, 'submitted')
        self.assertEqual(str(submission), f'{self.template.name} - {self.patient} - {submission.submission_date.strftime("%Y-%m-%d")}')
        
    def test_form_validation_rule_creation(self):
        """Test FormValidationRule model creation"""
        field = FormField.objects.create(
            template=self.template,
            field_name='age',
            field_label='Age',
            field_type='number',
            is_required=True,
            display_order=1
        )
        
        rule = FormValidationRule.objects.create(
            template=self.template,
            name='age_range_check',
            description='Age must be between 18 and 100',
            field_dependencies=['age'],
            validation_logic='int(age) >= 18 and int(age) <= 100',
            error_message='Age must be between 18 and 100'
        )
        
        self.assertEqual(rule.template, self.template)
        self.assertEqual(rule.name, 'age_range_check')
        self.assertEqual(rule.error_message, 'Age must be between 18 and 100')
        self.assertEqual(str(rule), f'{self.template.name} - age_range_check')
        
    def test_standardized_assessment_creation(self):
        """Test StandardizedAssessment model creation"""
        assessment = StandardizedAssessment.objects.create(
            template=self.template,
            assessment_type='phq9',
            clinical_use='Depression screening and monitoring',
            scoring_interpretation={'minimal': '0-4', 'mild': '5-9', 'moderate': '10-14'}
        )
        
        self.assertEqual(assessment.template, self.template)
        self.assertEqual(assessment.assessment_type, 'phq9')
        self.assertEqual(str(assessment), assessment.get_assessment_type_display())


class FormAPITestCase(APITestCase):
    """Test cases for Forms API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth=date(1990, 1, 1),
            medical_record_number='MRN123456'
        )
        
        self.category = FormCategory.objects.create(
            name='Clinical Assessment',
            description='Clinical assessment forms'
        )
        
        self.template = FormTemplate.objects.create(
            name='Patient Health Questionnaire',
            category=self.category,
            description='PHQ-9 Depression Assessment',
            version='1.0',
            is_published=True,
            created_by=self.user
        )
        
        self.client.force_authenticate(user=self.user)
        
    def test_form_category_list_api(self):
        """Test FormCategory list API endpoint"""
        # Test direct URL
        response = self.client.get('/api/v1/forms/api/categories/')
        
        print(f"Response status: {response.status_code}")
        print(f"Response data: {response.data}")
        print(f"Response type: {type(response.data)}")
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if hasattr(response.data, 'get') and 'results' in response.data:
            # Paginated response
            categories = response.data['results']
        else:
            categories = response.data
            
        self.assertGreaterEqual(len(categories), 1)
        
        # Check our specific category exists
        category_names = [cat['name'] for cat in categories]
        self.assertIn('Clinical Assessment', category_names)
        
    def test_form_template_list_api(self):
        """Test FormTemplate list API endpoint"""
        url = reverse('forms_api:formtemplate-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Handle paginated response
        if hasattr(response.data, 'get') and 'results' in response.data:
            templates = response.data['results']
        else:
            templates = response.data
            
        self.assertGreaterEqual(len(templates), 1)
        
        # Check our specific template exists
        template_names = [tpl['name'] for tpl in templates]
        self.assertIn('Patient Health Questionnaire', template_names)
        
    def test_form_template_create_api(self):
        """Test FormTemplate create API endpoint"""
        url = reverse('forms_api:formtemplate-list')
        data = {
            'name': 'New Form Template',
            'code': 'TEST001',
            'category': self.category.id,
            'form_type': 'assessment',
            'description': 'Test form template',
            'version': '1.0'
        }
        
        response = self.client.post(url, data)
        
        if response.status_code != status.HTTP_201_CREATED:
            print(f"FormTemplate create - Response status: {response.status_code}")
            print(f"FormTemplate create - Response data: {response.data}")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Form Template')
        self.assertEqual(FormTemplate.objects.count(), 2)
        
    def test_form_submission_create_api(self):
        """Test FormSubmission create API endpoint"""
        url = reverse('forms_api:formsubmission-list')
        data = {
            'template': self.template.id,
            'patient': self.patient.id,
            'submitted_by': self.user.id,
            'form_data': {'mood': 'Good'},
            'status': 'submitted'
        }
        
        response = self.client.post(url, data, format='json')
        
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Form submission - Response status: {response.status_code}")
            print(f"Form submission - Response data: {response.data}")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['template'], self.template.id)
        self.assertEqual(FormSubmission.objects.count(), 1)
        
    def test_form_template_fields_api(self):
        """Test FormTemplate fields API endpoint"""
        # Create a field for the template
        field = FormField.objects.create(
            template=self.template,
            field_name='mood',
            field_label='How would you rate your mood?',
            field_type='select',
            choices=['Excellent', 'Good', 'Fair', 'Poor'],
            is_required=True,
            display_order=1
        )
        
        url = reverse('forms_api:formtemplate-detail', kwargs={'pk': self.template.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['form_fields']), 1)
        self.assertEqual(response.data['form_fields'][0]['field_name'], 'mood')


class FormViewsTestCase(TestCase):
    """Test cases for Forms web views"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth=date(1990, 1, 1),
            medical_record_number='MRN123456'
        )
        
        self.category = FormCategory.objects.create(
            name='Clinical Assessment',
            description='Clinical assessment forms'
        )
        
        self.template = FormTemplate.objects.create(
            name='Patient Health Questionnaire',
            category=self.category,
            description='PHQ-9 Depression Assessment',
            version='1.0',
            is_published=True,
            created_by=self.user
        )
        
        self.client.login(username='testuser', password='testpass123')
        
    def test_forms_dashboard_view(self):
        """Test forms dashboard view"""
        url = reverse('forms:dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Forms Dashboard')
        self.assertContains(response, 'Total Forms')
        
    def test_form_template_list_view(self):
        """Test form template list view"""
        url = reverse('forms:template_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Form Templates')
        self.assertContains(response, 'Patient Health Questionnaire')
        
    def test_form_template_detail_view(self):
        """Test form template detail view"""
        url = reverse('forms:template_detail', kwargs={'template_id': self.template.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Patient Health Questionnaire')
        self.assertContains(response, 'PHQ-9 Depression Assessment')
        
    def test_form_fill_view(self):
        """Test form fill view"""
        url = reverse('forms:form_fill', kwargs={'template_id': self.template.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Patient Health Questionnaire')
        self.assertContains(response, 'Form Fields')
        
    def test_form_submission_list_view(self):
        """Test form submission list view"""
        # Create a submission
        FormSubmission.objects.create(
            template=self.template,
            patient=self.patient,
            submitted_by=self.user,
            form_data={'mood': 'Good'},
            status='submitted'
        )
        
        url = reverse('forms:submission_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Form Submissions')
        
    def test_form_analytics_view(self):
        """Test form analytics view"""
        url = reverse('forms:analytics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Form Analytics')


class FormValidationTestCase(TestCase):
    """Test cases for form validation"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth=date(1990, 1, 1),
            medical_record_number='MRN123456'
        )
        
        self.category = FormCategory.objects.create(
            name='Clinical Assessment',
            description='Clinical assessment forms'
        )
        
        self.template = FormTemplate.objects.create(
            name='Patient Health Questionnaire',
            category=self.category,
            description='PHQ-9 Depression Assessment',
            version='1.0',
            created_by=self.user
        )
        
        self.field = FormField.objects.create(
            template=self.template,
            field_name='age',
            field_label='Age',
            field_type='number',
            is_required=True,
            display_order=1
        )
        
        self.validation_rule = FormValidationRule.objects.create(
            template=self.template,
            name='age_range_check',
            description='Age must be between 18 and 100',
            field_dependencies=['age'],
            validation_logic='int(age) >= 18 and int(age) <= 100',
            error_message='Age must be between 18 and 100'
        )
        
    def test_required_field_validation(self):
        """Test required field validation"""
        submission = FormSubmission.objects.create(
            template=self.template,
            patient=self.patient,
            submitted_by=self.user,
            form_data={},  # Empty data
            status='draft'
        )
        
        # Test validation (would need to implement validation logic)
        # This is a placeholder for more complex validation testing
        self.assertIsNotNone(submission)
        
    def test_range_validation(self):
        """Test range validation rule"""
        # Test valid age
        submission1 = FormSubmission.objects.create(
            template=self.template,
            patient=self.patient,
            submitted_by=self.user,
            form_data={'age': 25},
            status='submitted'
        )
        
        # Test invalid age (would need validation implementation)
        submission2 = FormSubmission.objects.create(
            template=self.template,
            patient=self.patient,
            submitted_by=self.user,
            form_data={'age': 150},  # Invalid age
            status='draft'
        )
        
        self.assertIsNotNone(submission1)
        self.assertIsNotNone(submission2)


class FormAuditTestCase(TestCase):
    """Test cases for form audit logging"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.patient = Patient.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth=date(1990, 1, 1),
            medical_record_number='MRN123456'
        )
        
        self.category = FormCategory.objects.create(
            name='Clinical Assessment',
            description='Clinical assessment forms'
        )
        
        self.template = FormTemplate.objects.create(
            name='Patient Health Questionnaire',
            category=self.category,
            description='PHQ-9 Depression Assessment',
            version='1.0',
            created_by=self.user
        )
        
        self.submission = FormSubmission.objects.create(
            template=self.template,
            patient=self.patient,
            submitted_by=self.user,
            form_data={'mood': 'Good'},
            status='submitted'
        )
        
    def test_audit_log_creation(self):
        """Test audit log creation"""
        audit_log = FormAuditLog.objects.create(
            submission=self.submission,
            template=self.template,
            patient=self.patient,
            action='create',
            performed_by=self.user,
            details={'status': 'submitted'},
            ip_address='127.0.0.1'
        )
        
        self.assertEqual(audit_log.submission, self.submission)
        self.assertEqual(audit_log.action, 'create')
        self.assertEqual(audit_log.performed_by, self.user)
        self.assertIn('create - Patient Health Questionnaire', str(audit_log))
        
    def test_audit_log_data_integrity(self):
        """Test audit log data integrity"""
        audit_log = FormAuditLog.objects.create(
            submission=self.submission,
            template=self.template,
            patient=self.patient,
            action='update',
            performed_by=self.user,
            details={'status': 'reviewed'},
            ip_address='127.0.0.1'
        )
        
        self.assertIsNotNone(audit_log.timestamp)
        self.assertIsInstance(audit_log.details, dict)
        self.assertEqual(audit_log.details['status'], 'reviewed')
