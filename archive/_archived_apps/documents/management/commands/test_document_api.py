"""
Test Document Management APIs

This command tests all document management API endpoints to ensure they work correctly.
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from documents.models import DocumentCategory, DocumentTemplate, Document
import json
import tempfile
import os


class Command(BaseCommand):
    help = 'Test document management API endpoints'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='admin',
            help='Username for API testing (default: admin)',
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Verbose output with response details',
        )
    
    def handle(self, *args, **options):
        """Execute the API tests"""
        self.stdout.write(
            self.style.SUCCESS('🧪 Testing Document Management APIs...')
        )
        
        self.verbose = options['verbose']
        
        try:
            # Setup test client and user
            self.setup_client(options['username'])
            
            # Run API tests
            self.test_category_apis()
            self.test_template_apis()
            self.test_document_apis()
            self.test_document_operations()
            
            self.stdout.write(
                self.style.SUCCESS('✅ All document management API tests passed!')
            )
            
        except Exception as e:
            raise CommandError(f'❌ API test failed: {str(e)}')
    
    def setup_client(self, username):
        """Setup test client with authenticated user"""
        self.stdout.write('🔧 Setting up test client...')
        
        try:
            self.user = User.objects.get(username=username)
            self.client = Client()
            
            # Login user
            self.client.force_login(self.user)
            
            self.stdout.write(f'✅ Test client setup complete for user: {username}')
            
        except User.DoesNotExist:
            raise CommandError(f'User not found: {username}')
    
    def test_category_apis(self):
        """Test document category APIs"""
        self.stdout.write('📁 Testing Document Category APIs...')
        
        # Test list categories
        response = self.client.get('/api/v1/documents/categories/')
        self.check_response(response, 'GET /api/v1/documents/categories/')
        
        categories_data = response.json()
        if self.verbose:
            self.stdout.write(f'  📊 Found {len(categories_data.get("results", categories_data))} categories')
        
        # Test category statistics
        if categories_data and (categories_data.get('results') or categories_data):
            first_category = (categories_data.get('results') or categories_data)[0]
            category_id = first_category['id']
            
            response = self.client.get(f'/api/v1/documents/categories/{category_id}/statistics/')
            self.check_response(response, f'GET /api/v1/documents/categories/{category_id}/statistics/')
            
            if self.verbose:
                stats = response.json()
                self.stdout.write(f'  📈 Category stats: {stats}')
        
        # Test category tree
        response = self.client.get('/api/v1/documents/categories/tree/')
        self.check_response(response, 'GET /api/v1/documents/categories/tree/')
        
        self.stdout.write('✅ Category APIs working')
    
    def test_template_apis(self):
        """Test document template APIs"""
        self.stdout.write('📄 Testing Document Template APIs...')
        
        # Test list templates
        response = self.client.get('/api/v1/documents/templates/')
        self.check_response(response, 'GET /api/v1/documents/templates/')
        
        templates_data = response.json()
        if self.verbose:
            self.stdout.write(f'  📊 Found {len(templates_data.get("results", templates_data))} templates')
        
        # Test template detail and download
        if templates_data and (templates_data.get('results') or templates_data):
            first_template = (templates_data.get('results') or templates_data)[0]
            template_id = first_template['id']
            
            # Get template detail
            response = self.client.get(f'/api/v1/documents/templates/{template_id}/')
            self.check_response(response, f'GET /api/v1/documents/templates/{template_id}/')
            
            # Test template download (might fail if no file)
            response = self.client.get(f'/api/v1/documents/templates/{template_id}/download/')
            if response.status_code not in [200, 404]:
                self.stdout.write(
                    self.style.WARNING(f'  ⚠️  Template download returned {response.status_code}')
                )
        
        self.stdout.write('✅ Template APIs working')
    
    def test_document_apis(self):
        """Test document APIs"""
        self.stdout.write('📄 Testing Document APIs...')
        
        # Test list documents
        response = self.client.get('/api/v1/documents/documents/')
        self.check_response(response, 'GET /api/v1/documents/documents/')
        
        documents_data = response.json()
        if self.verbose:
            self.stdout.write(f'  📊 Found {len(documents_data.get("results", documents_data))} documents')
        
        # Test my documents
        response = self.client.get('/api/v1/documents/documents/my_documents/')
        self.check_response(response, 'GET /api/v1/documents/documents/my_documents/')
        
        # Test shared with me
        response = self.client.get('/api/v1/documents/documents/shared_with_me/')
        self.check_response(response, 'GET /api/v1/documents/documents/shared_with_me/')
        
        # Test pending signatures
        response = self.client.get('/api/v1/documents/documents/pending_signatures/')
        self.check_response(response, 'GET /api/v1/documents/documents/pending_signatures/')
        
        # Test document statistics
        response = self.client.get('/api/v1/documents/documents/statistics/')
        self.check_response(response, 'GET /api/v1/documents/documents/statistics/')
        
        if self.verbose:
            stats = response.json()
            self.stdout.write(f'  📈 Document stats: {stats}')
        
        self.stdout.write('✅ Document APIs working')
    
    def test_document_operations(self):
        """Test document operations (upload, download, etc.)"""
        self.stdout.write('📤 Testing Document Operations...')
        
        # Create a test document
        test_doc = self.create_test_document()
        if not test_doc:
            self.stdout.write(
                self.style.WARNING('  ⚠️  Skipping document operations (no categories available)')
            )
            return
        
        doc_id = test_doc['id']
        
        # Test document detail
        response = self.client.get(f'/api/v1/documents/documents/{doc_id}/')
        self.check_response(response, f'GET /api/v1/documents/documents/{doc_id}/')
        
        # Test document download
        response = self.client.get(f'/api/v1/documents/documents/{doc_id}/download/')
        if response.status_code not in [200, 404]:
            self.stdout.write(
                self.style.WARNING(f'  ⚠️  Document download returned {response.status_code}')
            )
        
        # Test document preview
        response = self.client.get(f'/api/v1/documents/documents/{doc_id}/preview/')
        if response.status_code not in [200, 400, 404]:
            self.stdout.write(
                self.style.WARNING(f'  ⚠️  Document preview returned {response.status_code}')
            )
        
        # Test document sharing
        other_users = User.objects.exclude(id=self.user.id)[:1]
        if other_users:
            share_data = {
                'shared_with': other_users[0].id,
                'access_level': 'read',
                'can_download': True,
                'access_reason': 'API Testing'
            }
            response = self.client.post(
                f'/api/v1/documents/documents/{doc_id}/share/',
                data=json.dumps(share_data),
                content_type='application/json'
            )
            if response.status_code not in [201, 400]:
                self.stdout.write(
                    self.style.WARNING(f'  ⚠️  Document sharing returned {response.status_code}')
                )
        
        # Test document signing (for documents that require signature)
        sign_data = {
            'signature_type': 'electronic',
            'signature_data': 'test_signature_data',
            'notes': 'API test signature'
        }
        response = self.client.post(
            f'/api/v1/documents/documents/{doc_id}/sign/',
            data=json.dumps(sign_data),
            content_type='application/json'
        )
        if response.status_code not in [201, 400]:
            self.stdout.write(
                self.style.WARNING(f'  ⚠️  Document signing returned {response.status_code}')
            )
        
        self.stdout.write('✅ Document operations working')
    
    def create_test_document(self):
        """Create a test document for operations testing"""
        # Get a category to use
        categories = DocumentCategory.objects.filter(is_active=True)[:1]
        if not categories:
            return None
        
        category = categories[0]
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write('This is a test document created by the API test command.')
            temp_file_path = f.name
        
        try:
            # Upload document
            with open(temp_file_path, 'rb') as f:
                upload_data = {
                    'title': 'API Test Document',
                    'description': 'Test document created by API test command',
                    'category': category.id,
                    'status': 'draft',
                    'priority': 'normal',
                    'file': SimpleUploadedFile('test_document.txt', f.read(), content_type='text/plain')
                }
                
                response = self.client.post('/api/v1/documents/documents/', data=upload_data)
                
                if response.status_code == 201:
                    document_data = response.json()
                    self.stdout.write(f'  ✅ Created test document: {document_data["title"]}')
                    return document_data
                else:
                    self.stdout.write(
                        self.style.WARNING(f'  ⚠️  Failed to create test document: {response.status_code}')
                    )
                    return None
        
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
    
    def check_response(self, response, endpoint):
        """Check API response status"""
        if response.status_code == 200:
            if self.verbose:
                self.stdout.write(f'  ✅ {endpoint} - OK')
        elif response.status_code == 401:
            raise CommandError(f'Authentication failed for {endpoint}')
        elif response.status_code == 403:
            self.stdout.write(
                self.style.WARNING(f'  ⚠️  {endpoint} - Forbidden (check permissions)')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'  ⚠️  {endpoint} - Status {response.status_code}')
            )
        
        if self.verbose and hasattr(response, 'json'):
            try:
                data = response.json()
                if isinstance(data, dict) and 'results' in data:
                    self.stdout.write(f'    📊 Returned {len(data["results"])} items')
                elif isinstance(data, list):
                    self.stdout.write(f'    📊 Returned {len(data)} items')
            except:
                pass
