"""
Initialize Document Management System

This command sets up the document management system with:
- Default document categories
- Standard document templates
- Initial configurations
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from documents.models import DocumentCategory, DocumentTemplate
import json


class Command(BaseCommand):
    help = 'Initialize document management system with default categories and templates'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset existing categories and templates',
        )
        
        parser.add_argument(
            '--create-groups',
            action='store_true',
            help='Create default user groups with permissions',
        )
    
    def handle(self, *args, **options):
        """Execute the command"""
        self.stdout.write(
            self.style.SUCCESS('🏥 Initializing Document Management System...')
        )
        
        try:
            if options['create_groups']:
                self.create_user_groups()
            
            if options['reset']:
                self.reset_data()
            
            self.create_document_categories()
            self.create_document_templates()
            
            self.stdout.write(
                self.style.SUCCESS('✅ Document management system initialized successfully!')
            )
            
        except Exception as e:
            raise CommandError(f'❌ Failed to initialize document system: {str(e)}')
    
    def create_user_groups(self):
        """Create user groups with appropriate permissions"""
        self.stdout.write('📋 Creating user groups...')
        
        # Get content types for permissions
        doc_ct = ContentType.objects.get_for_model(DocumentCategory)
        template_ct = ContentType.objects.get_for_model(DocumentTemplate)
        
        groups_config = [
            {
                'name': 'Document Administrators',
                'description': 'Full document management access',
                'permissions': [
                    'documents.add_documentcategory',
                    'documents.change_documentcategory',
                    'documents.delete_documentcategory',
                    'documents.view_documentcategory',
                    'documents.add_documenttemplate',
                    'documents.change_documenttemplate',
                    'documents.delete_documenttemplate',
                    'documents.view_documenttemplate',
                    'documents.add_document',
                    'documents.change_document',
                    'documents.delete_document',
                    'documents.view_document',
                    'documents.share_document',
                    'documents.sign_document',
                    'documents.view_restricted',
                    'documents.view_confidential',
                ]
            },
            {
                'name': 'Document Managers',
                'description': 'Document management with restrictions',
                'permissions': [
                    'documents.view_documentcategory',
                    'documents.view_documenttemplate',
                    'documents.add_document',
                    'documents.change_document',
                    'documents.view_document',
                    'documents.share_document',
                    'documents.sign_document',
                    'documents.view_restricted',
                ]
            },
            {
                'name': 'Document Users',
                'description': 'Basic document access',
                'permissions': [
                    'documents.view_documentcategory',
                    'documents.view_documenttemplate',
                    'documents.add_document',
                    'documents.view_document',
                    'documents.sign_document',
                ]
            },
            {
                'name': 'Internal Users',
                'description': 'Internal document access',
                'permissions': [
                    'documents.view_document',
                    'documents.add_document',
                ]
            }
        ]
        
        for group_config in groups_config:
            group, created = Group.objects.get_or_create(
                name=group_config['name']
            )
            
            if created:
                self.stdout.write(f'  ➕ Created group: {group.name}')
            else:
                self.stdout.write(f'  📝 Updated group: {group.name}')
            
            # Clear existing permissions
            group.permissions.clear()
            
            # Add permissions
            for perm_code in group_config['permissions']:
                try:
                    app_label, codename = perm_code.split('.')
                    permission = Permission.objects.get(
                        content_type__app_label=app_label,
                        codename=codename
                    )
                    group.permissions.add(permission)
                except Permission.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'    ⚠️  Permission not found: {perm_code}')
                    )
        
        self.stdout.write(self.style.SUCCESS('✅ User groups created'))
    
    def reset_data(self):
        """Reset existing data"""
        self.stdout.write('🔄 Resetting existing data...')
        
        DocumentTemplate.objects.filter(is_active=True).update(is_active=False)
        DocumentCategory.objects.filter(is_active=True).update(is_active=False)
        
        self.stdout.write('✅ Data reset complete')
    
    def create_document_categories(self):
        """Create default document categories"""
        self.stdout.write('📁 Creating document categories...')
        
        categories = [
            {
                'name': 'Patient Records',
                'description': 'Medical records and patient documentation',
                'access_level': 'confidential',
                'requires_signature': True,
                'allowed_file_types': ['pdf', 'doc', 'docx', 'jpg', 'png'],
                'max_file_size_mb': 50,
                'subcategories': [
                    {
                        'name': 'Medical History',
                        'description': 'Patient medical history documents',
                        'requires_signature': True,
                    },
                    {
                        'name': 'Diagnostic Reports',
                        'description': 'Lab results, imaging, and diagnostic reports',
                        'requires_signature': True,
                    },
                    {
                        'name': 'Treatment Plans',
                        'description': 'Treatment and care plans',
                        'requires_signature': True,
                    },
                    {
                        'name': 'Prescriptions',
                        'description': 'Medication prescriptions and orders',
                        'requires_signature': True,
                    }
                ]
            },
            {
                'name': 'Administrative Documents',
                'description': 'Administrative and operational documents',
                'access_level': 'internal',
                'requires_signature': False,
                'allowed_file_types': ['pdf', 'doc', 'docx', 'xls', 'xlsx'],
                'max_file_size_mb': 25,
                'subcategories': [
                    {
                        'name': 'Policies',
                        'description': 'Organizational policies and procedures',
                    },
                    {
                        'name': 'Forms',
                        'description': 'Standard forms and templates',
                    },
                    {
                        'name': 'Reports',
                        'description': 'Administrative reports and analytics',
                    }
                ]
            },
            {
                'name': 'Legal Documents',
                'description': 'Legal and compliance documents',
                'access_level': 'restricted',
                'requires_signature': True,
                'allowed_file_types': ['pdf', 'doc', 'docx'],
                'max_file_size_mb': 25,
                'subcategories': [
                    {
                        'name': 'Consent Forms',
                        'description': 'Patient consent and authorization forms',
                        'requires_signature': True,
                    },
                    {
                        'name': 'Contracts',
                        'description': 'Legal contracts and agreements',
                        'requires_signature': True,
                    },
                    {
                        'name': 'Compliance',
                        'description': 'Regulatory compliance documents',
                    }
                ]
            },
            {
                'name': 'Insurance Documents',
                'description': 'Insurance and billing related documents',
                'access_level': 'restricted',
                'requires_signature': False,
                'allowed_file_types': ['pdf', 'doc', 'docx', 'jpg', 'png'],
                'max_file_size_mb': 25,
                'subcategories': [
                    {
                        'name': 'Insurance Claims',
                        'description': 'Insurance claim forms and documentation',
                    },
                    {
                        'name': 'Pre-authorizations',
                        'description': 'Insurance pre-authorization documents',
                    },
                    {
                        'name': 'Billing Records',
                        'description': 'Billing and payment records',
                    }
                ]
            },
            {
                'name': 'Educational Materials',
                'description': 'Patient education and reference materials',
                'access_level': 'public',
                'requires_signature': False,
                'allowed_file_types': ['pdf', 'doc', 'docx', 'jpg', 'png', 'mp4'],
                'max_file_size_mb': 100,
                'subcategories': [
                    {
                        'name': 'Patient Education',
                        'description': 'Educational materials for patients',
                    },
                    {
                        'name': 'Clinical Guidelines',
                        'description': 'Clinical practice guidelines and protocols',
                    },
                    {
                        'name': 'Training Materials',
                        'description': 'Staff training and educational resources',
                    }
                ]
            },
            {
                'name': 'Quality Assurance',
                'description': 'Quality assurance and improvement documents',
                'access_level': 'internal',
                'requires_signature': True,
                'allowed_file_types': ['pdf', 'doc', 'docx', 'xls', 'xlsx'],
                'max_file_size_mb': 25,
                'subcategories': [
                    {
                        'name': 'Audit Reports',
                        'description': 'Quality audit reports and findings',
                        'requires_signature': True,
                    },
                    {
                        'name': 'Performance Metrics',
                        'description': 'Performance measurement and metrics',
                    },
                    {
                        'name': 'Improvement Plans',
                        'description': 'Quality improvement initiatives and plans',
                        'requires_signature': True,
                    }
                ]
            }
        ]
        
        for cat_data in categories:
            subcats_data = cat_data.pop('subcategories', [])
            
            category, created = DocumentCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults=cat_data
            )
            
            if created:
                self.stdout.write(f'  ➕ Created category: {category.name}')
            else:
                # Update existing category
                for key, value in cat_data.items():
                    setattr(category, key, value)
                category.save()
                self.stdout.write(f'  📝 Updated category: {category.name}')
            
            # Create subcategories
            for subcat_data in subcats_data:
                subcat_data['parent_category'] = category
                subcat_data['access_level'] = category.access_level
                subcat_data['allowed_file_types'] = category.allowed_file_types
                subcat_data['max_file_size_mb'] = category.max_file_size_mb
                
                subcategory, created = DocumentCategory.objects.get_or_create(
                    name=subcat_data['name'],
                    parent_category=category,
                    defaults=subcat_data
                )
                
                if created:
                    self.stdout.write(f'    ➕ Created subcategory: {subcategory.name}')
                else:
                    # Update existing subcategory
                    for key, value in subcat_data.items():
                        setattr(subcategory, key, value)
                    subcategory.save()
                    self.stdout.write(f'    📝 Updated subcategory: {subcategory.name}')
        
        self.stdout.write(self.style.SUCCESS('✅ Document categories created'))
    
    def create_document_templates(self):
        """Create default document templates"""
        self.stdout.write('📄 Creating document templates...')
        
        templates = [
            {
                'name': 'Patient Intake Form',
                'description': 'Standard patient intake and registration form',
                'category_name': 'Forms',
                'template_type': 'form',
                'is_default': True,
                'version': '1.0',
                'form_fields': {
                    'patient_info': {
                        'first_name': {'type': 'text', 'required': True},
                        'last_name': {'type': 'text', 'required': True},
                        'date_of_birth': {'type': 'date', 'required': True},
                        'gender': {'type': 'select', 'options': ['Male', 'Female', 'Other']},
                        'phone': {'type': 'tel', 'required': True},
                        'email': {'type': 'email'},
                        'address': {'type': 'textarea'},
                    },
                    'insurance': {
                        'insurance_provider': {'type': 'text'},
                        'policy_number': {'type': 'text'},
                        'group_number': {'type': 'text'},
                    },
                    'emergency_contact': {
                        'contact_name': {'type': 'text', 'required': True},
                        'relationship': {'type': 'text'},
                        'phone': {'type': 'tel', 'required': True},
                    }
                }
            },
            {
                'name': 'Consent for Treatment',
                'description': 'General consent for medical treatment',
                'category_name': 'Consent Forms',
                'template_type': 'consent',
                'is_default': True,
                'version': '1.0',
                'form_fields': {
                    'consent': {
                        'patient_name': {'type': 'text', 'required': True},
                        'treatment_description': {'type': 'textarea', 'required': True},
                        'risks_explained': {'type': 'checkbox', 'required': True},
                        'alternatives_discussed': {'type': 'checkbox', 'required': True},
                        'patient_signature': {'type': 'signature', 'required': True},
                        'date_signed': {'type': 'date', 'required': True},
                    }
                }
            },
            {
                'name': 'Prescription Template',
                'description': 'Standard prescription form',
                'category_name': 'Prescriptions',
                'template_type': 'form',
                'is_default': True,
                'version': '1.0',
                'form_fields': {
                    'prescription': {
                        'patient_name': {'type': 'text', 'required': True},
                        'medication_name': {'type': 'text', 'required': True},
                        'dosage': {'type': 'text', 'required': True},
                        'frequency': {'type': 'text', 'required': True},
                        'duration': {'type': 'text', 'required': True},
                        'instructions': {'type': 'textarea'},
                        'prescriber_signature': {'type': 'signature', 'required': True},
                        'date_prescribed': {'type': 'date', 'required': True},
                    }
                }
            },
            {
                'name': 'Lab Report Template',
                'description': 'Standard laboratory report format',
                'category_name': 'Diagnostic Reports',
                'template_type': 'report',
                'is_default': True,
                'version': '1.0',
                'form_fields': {
                    'lab_report': {
                        'patient_name': {'type': 'text', 'required': True},
                        'test_date': {'type': 'date', 'required': True},
                        'test_type': {'type': 'text', 'required': True},
                        'results': {'type': 'textarea', 'required': True},
                        'normal_ranges': {'type': 'textarea'},
                        'interpretation': {'type': 'textarea'},
                        'technician_signature': {'type': 'signature', 'required': True},
                    }
                }
            },
            {
                'name': 'Discharge Summary',
                'description': 'Patient discharge summary template',
                'category_name': 'Medical History',
                'template_type': 'report',
                'is_default': True,
                'version': '1.0',
                'form_fields': {
                    'discharge': {
                        'patient_name': {'type': 'text', 'required': True},
                        'admission_date': {'type': 'date', 'required': True},
                        'discharge_date': {'type': 'date', 'required': True},
                        'diagnosis': {'type': 'textarea', 'required': True},
                        'treatment_summary': {'type': 'textarea', 'required': True},
                        'medications': {'type': 'textarea'},
                        'follow_up_instructions': {'type': 'textarea'},
                        'physician_signature': {'type': 'signature', 'required': True},
                    }
                }
            }
        ]
        
        for template_data in templates:
            category_name = template_data.pop('category_name')
            
            try:
                category = DocumentCategory.objects.get(name=category_name, is_active=True)
                template_data['category'] = category
                
                template, created = DocumentTemplate.objects.get_or_create(
                    name=template_data['name'],
                    category=category,
                    defaults=template_data
                )
                
                if created:
                    self.stdout.write(f'  ➕ Created template: {template.name}')
                else:
                    # Update existing template
                    for key, value in template_data.items():
                        setattr(template, key, value)
                    template.save()
                    self.stdout.write(f'  📝 Updated template: {template.name}')
                    
            except DocumentCategory.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f'  ⚠️  Category not found: {category_name}')
                )
        
        self.stdout.write(self.style.SUCCESS('✅ Document templates created'))
    
    def get_category_counts(self):
        """Get category and template counts"""
        categories_count = DocumentCategory.objects.filter(is_active=True).count()
        templates_count = DocumentTemplate.objects.filter(is_active=True).count()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'📊 Summary: {categories_count} categories, {templates_count} templates'
            )
        )
