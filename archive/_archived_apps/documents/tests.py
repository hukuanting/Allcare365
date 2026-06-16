"""
Comprehensive tests for the document management system
"""
import os
import tempfile
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from rest_framework.test import APITestCase
from rest_framework import status
from .models import (
    DocumentCategory, DocumentTemplate, Document, DocumentVersion,
    DocumentShare, DocumentSignature, DocumentComment, DocumentAuditLog
)


class DocumentModelTest(TestCase):
    """Test document models"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = DocumentCategory.objects.create(
            name='Test Category',
            description='Test category description',
            created_by=self.user
        )
        
    def test_document_category_creation(self):
        """Test document category creation"""
        self.assertEqual(self.category.name, 'Test Category')
        self.assertEqual(self.category.created_by, self.user)
        self.assertTrue(self.category.is_active)
        
    def test_document_template_creation(self):
        """Test document template creation"""
        template = DocumentTemplate.objects.create(
            name='Test Template',
            category=self.category,
            description='Test template',
            template_type='form',
            created_by=self.user
        )
        self.assertEqual(template.name, 'Test Template')
        self.assertEqual(template.category, self.category)
        self.assertEqual(template.template_type, 'form')
        
    def test_document_creation(self):
        """Test document creation"""
        # Create a temporary file
        test_file = SimpleUploadedFile(
            "test.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        document = Document.objects.create(
            title='Test Document',
            description='Test document description',
            category=self.category,
            file=test_file,
            original_filename='test.pdf',
            mime_type='application/pdf',
            file_size=len(b"file_content"),
            created_by=self.user
        )
        
        self.assertEqual(document.title, 'Test Document')
        self.assertEqual(document.category, self.category)
        self.assertEqual(document.mime_type, 'application/pdf')
        self.assertEqual(document.created_by, self.user)
        self.assertEqual(document.version, '1.0')
        
        # Clean up
        if default_storage.exists(document.file.name):
            default_storage.delete(document.file.name)
            
    def test_document_version_creation(self):
        """Test document version creation"""
        # Create main document
        test_file = SimpleUploadedFile(
            "test.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        document = Document.objects.create(
            title='Test Document',
            category=self.category,
            file=test_file,
            original_filename='test.pdf',
            mime_type='application/pdf',
            file_size=len(b"file_content"),
            created_by=self.user
        )
        
        # Create new version
        new_file = SimpleUploadedFile(
            "test_v2.pdf",
            b"new_file_content",
            content_type="application/pdf"
        )
        
        version = DocumentVersion.objects.create(
            document=document,
            version_number='2.0',
            file=new_file,
            file_size=len(b"new_file_content"),
            version_notes="Updated version",
            created_by=self.user
        )
        
        # Update document version
        document.version = '2.0'
        document.save()
        
        self.assertEqual(version.document, document)
        self.assertEqual(version.version_number, '2.0')
        self.assertEqual(document.version, '2.0')
        
        # Clean up
        if default_storage.exists(document.file.name):
            default_storage.delete(document.file.name)
        if default_storage.exists(version.file.name):
            default_storage.delete(version.file.name)


class DocumentAPITest(APITestCase):
    """Test document API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.category = DocumentCategory.objects.create(
            name='Test Category',
            description='Test category description',
            created_by=self.user
        )
        
    def test_create_document_category(self):
        """Test creating a document category via API"""
        url = reverse('documents:documentcategory-list')
        data = {
            'name': 'New Category',
            'description': 'New category description'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(DocumentCategory.objects.count(), 2)
        
    def test_list_document_categories(self):
        """Test listing document categories"""
        url = reverse('documents:documentcategory-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
    def test_create_document_template(self):
        """Test creating a document template via API"""
        url = reverse('documents:documenttemplate-list')
        
        # Create a test template file
        test_file = SimpleUploadedFile(
            "template.pdf",
            b"template_content",
            content_type="application/pdf"
        )
        
        data = {
            'name': 'Test Template',
            'category_id': self.category.id,
            'description': 'Test template description',
            'template_type': 'form',
            'template_file': test_file
        }
        response = self.client.post(url, data, format='multipart')
        
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Response status: {response.status_code}")
            print(f"Response data: {response.data}")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
    def test_upload_document(self):
        """Test uploading a document via API"""
        url = reverse('documents:document-list')
        
        # Create a temporary file
        test_file = SimpleUploadedFile(
            "test.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        data = {
            'title': 'Test Document',
            'description': 'Test document description',
            'category_id': self.category.id,
            'document_type': 'administrative',
            'file': test_file,
            'original_filename': 'test.pdf',
            'mime_type': 'application/pdf',
            'file_size': len(b"file_content")
        }
        
        response = self.client.post(url, data, format='multipart')
        
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Document upload - Response status: {response.status_code}")
            print(f"Document upload - Response data: {response.data}")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Document.objects.count(), 1)
        
        # Clean up
        document = Document.objects.first()
        if default_storage.exists(document.file.name):
            default_storage.delete(document.file.name)
            
    def test_document_sharing(self):
        """Test document sharing functionality"""
        # Create a document
        test_file = SimpleUploadedFile(
            "test.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        document = Document.objects.create(
            title='Test Document',
            category=self.category,
            file=test_file,
            original_filename='test.pdf',
            mime_type='application/pdf',
            file_size=len(b"file_content"),
            created_by=self.user
        )
        
        # Create another user to share with
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        
        # Share document
        url = reverse('documents:documentshare-list')
        data = {
            'document': document.id,
            'shared_with_user': other_user.id,
            'permission': 'read'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(DocumentShare.objects.count(), 1)
        
        # Clean up
        if default_storage.exists(document.file.name):
            default_storage.delete(document.file.name)


class DocumentViewTest(TestCase):
    """Test document web views"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        self.category = DocumentCategory.objects.create(
            name='Test Category',
            description='Test category description',
            created_by=self.user
        )
        
    def test_document_dashboard_view(self):
        """Test document dashboard view"""
        url = reverse('documents:document_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Document Dashboard')
        
    def test_document_list_view(self):
        """Test document list view"""
        url = reverse('documents:document_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'All Documents')
        
    def test_document_detail_view(self):
        """Test document detail view"""
        # Create a document
        test_file = SimpleUploadedFile(
            "test.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        document = Document.objects.create(
            title='Test Document',
            category=self.category,
            file=test_file,
            original_filename='test.pdf',
            mime_type='application/pdf',
            file_size=len(b"file_content"),
            created_by=self.user
        )
        
        url = reverse('documents:document_detail', kwargs={'pk': document.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Document')
        
        # Clean up
        if default_storage.exists(document.file.name):
            default_storage.delete(document.file.name)
            
    def test_unauthorized_access(self):
        """Test unauthorized access to document views"""
        self.client.logout()
        
        url = reverse('documents:document_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login


class DocumentPermissionTest(TestCase):
    """Test document permissions and security"""
    
    def setUp(self):
        self.owner = User.objects.create_user(
            username='owner',
            email='owner@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        
        self.category = DocumentCategory.objects.create(
            name='Test Category',
            description='Test category description',
            created_by=self.owner
        )
        
        # Create a confidential document
        test_file = SimpleUploadedFile(
            "confidential.pdf",
            b"confidential_content",
            content_type="application/pdf"
        )
        
        self.confidential_doc = Document.objects.create(
            title='Confidential Document',
            category=self.category,
            document_type='confidential',
            file=test_file,
            original_filename='test.pdf',
            mime_type='application/pdf',
            file_size=len(b"confidential_content"),
            is_confidential=True,
            created_by=self.owner
        )
        
    def test_owner_can_access_confidential_document(self):
        """Test that document owner can access confidential documents"""
        client = Client()
        client.login(username='owner', password='testpass123')
        
        url = reverse('documents:document_detail', kwargs={'pk': self.confidential_doc.pk})
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        
    def test_other_user_cannot_access_confidential_document(self):
        """Test that other users cannot access confidential documents"""
        client = Client()
        client.login(username='otheruser', password='testpass123')
        
        url = reverse('documents:document_detail', kwargs={'pk': self.confidential_doc.pk})
        response = client.get(url)
        self.assertEqual(response.status_code, 403)  # Forbidden
        
    def test_shared_user_can_access_shared_document(self):
        """Test that shared users can access shared documents"""
        # Share the document
        DocumentShare.objects.create(
            document=self.confidential_doc,
            shared_with_user=self.other_user,
            can_view=True,
            created_by=self.owner
        )
        
        client = Client()
        client.login(username='otheruser', password='testpass123')
        
        url = reverse('documents:document_detail', kwargs={'pk': self.confidential_doc.pk})
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        
    def tearDown(self):
        """Clean up files after tests"""
        if default_storage.exists(self.confidential_doc.file.name):
            default_storage.delete(self.confidential_doc.file.name)


class DocumentAuditTest(TestCase):
    """Test document audit logging"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.category = DocumentCategory.objects.create(
            name='Test Category',
            description='Test category description',
            created_by=self.user
        )
        
    def test_document_creation_audit(self):
        """Test that document creation is audited"""
        initial_count = DocumentAuditLog.objects.count()
        
        test_file = SimpleUploadedFile(
            "test.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        document = Document.objects.create(
            title='Test Document',
            category=self.category,
            document_type='administrative',
            file=test_file,
            original_filename='test.pdf',
            mime_type='application/pdf',
            file_size=len(b"file_content"),
            created_by=self.user
        )
        
        # Check if audit log was created
        final_count = DocumentAuditLog.objects.count()
        self.assertGreater(final_count, initial_count)
        
        # Check audit log details
        audit_log = DocumentAuditLog.objects.latest('created_at')
        self.assertEqual(audit_log.document, document)
        self.assertEqual(audit_log.user, self.user)
        self.assertEqual(audit_log.action, 'created')
        
        # Clean up
        if default_storage.exists(document.file.name):
            default_storage.delete(document.file.name)
            
    def test_document_access_audit(self):
        """Test that document access is audited"""
        test_file = SimpleUploadedFile(
            "test.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        document = Document.objects.create(
            title='Test Document',
            category=self.category,
            document_type='administrative',
            file=test_file,
            original_filename='test.pdf',
            mime_type='application/pdf',
            file_size=len(b"file_content"),
            created_by=self.user
        )
        
        initial_count = DocumentAuditLog.objects.filter(action='view').count()
        
        # Simulate document access
        client = Client()
        client.login(username='testuser', password='testpass123')
        url = reverse('documents:document_detail', kwargs={'pk': document.pk})
        response = client.get(url)
        
        # Check if access was audited
        final_count = DocumentAuditLog.objects.filter(action='view').count()
        self.assertGreater(final_count, initial_count)
        
        # Clean up
        if default_storage.exists(document.file.name):
            default_storage.delete(document.file.name)


class DocumentSearchTest(TestCase):
    """Test document search functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        self.category = DocumentCategory.objects.create(
            name='Medical Records',
            description='Medical records category',
            created_by=self.user
        )
        
        # Create test documents
        import hashlib
        for i in range(3):
            test_file = SimpleUploadedFile(
                f"test_{i}.pdf",
                f"file_content_{i}".encode(),
                content_type="application/pdf"
            )
            
            file_content = f"file_content_{i}".encode()
            file_hash = hashlib.sha256(file_content).hexdigest()
            
            Document.objects.create(
                title=f'Test Document {i}',
                description=f'This is test document number {i}',
                category=self.category,
                document_type='administrative',
                file=test_file,
                original_filename=f'test_{i}.pdf',
                mime_type='application/pdf',
                file_size=len(file_content),
                file_hash=file_hash,
                created_by=self.user
            )
            
    def test_document_search_by_title(self):
        """Test searching documents by title"""
        url = reverse('documents:document_list')
        response = self.client.get(url, {'q': 'Test Document 1'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Document 1')
        
    def test_document_search_by_category(self):
        """Test filtering documents by category"""
        url = reverse('documents:document_by_category', kwargs={'category_id': self.category.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Medical Records')
        
    def test_empty_search_results(self):
        """Test empty search results"""
        url = reverse('documents:document_list')
        response = self.client.get(url, {'q': 'nonexistent'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No documents found')
        
    def tearDown(self):
        """Clean up files after tests"""
        for document in Document.objects.all():
            if default_storage.exists(document.file.name):
                default_storage.delete(document.file.name)
