"""
Code Systems Tests

This module contains comprehensive tests for the code systems functionality.
"""

from datetime import date
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    CodeSystemVersion, ICD10Code, CPTCode, SNOMEDConcept,
    RxNormConcept, LOINCCode, CodeMapping, CustomCodeSet, CustomCode
)
from .services import CodeImportService, CodeValidationService, CodeSystemService
from .serializers import CodeSystemVersionSerializer, ICD10CodeSerializer, CPTCodeSerializer, SNOMEDConceptSerializer, RxNormConceptSerializer, LOINCCodeSerializer, CodeMappingSerializer, CustomCodeSetSerializer, CustomCodeSerializer

class TestCodeSystemVersionModel(TestCase):
    def setUp(self):
        self.version = CodeSystemVersion.objects.create(
            system_name="Test System",
            revision_date="2025-01-01",
            status='current'
        )

    def test_code_system_version_creation(self):
        self.assertEqual(self.version.system_name, "Test System")
        self.assertEqual(str(self.version.revision_date), "2025-01-01")
        self.assertEqual(self.version.status, 'current')
        self.assertEqual(str(self.version), "Test System (2025-01-01)")

class TestCodeSystemModels(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.version = CodeSystemVersion.objects.create(
            system_name="ICD-10-CM",
            revision_date="2025-01-01",
            status='current',
            created_by=self.user
        )
        
        # Create test ICD-10 code
        self.icd_code = ICD10Code.objects.create(
            code='A00.1',
            short_description='Cholera due to Vibrio cholerae',
            long_description='Cholera due to Vibrio cholerae 01, biovar cholerae',
            category='A00-A09',
            billable=True,
            version=self.version,
            created_by=self.user
        )
        
        # Create test SNOMED concept
        self.snomed = SNOMEDConcept.objects.create(
            concept_id='100000001',
            preferred_term='Clinical Finding',
            fully_specified_name='Clinical Finding',
            semantic_tag='finding',
            version=self.version,
            created_by=self.user
        )
        
        # Create test RxNorm concept
        self.rxnorm = RxNormConcept.objects.create(
            rxcui='12345',
            preferred_term='Aspirin 81 MG Oral Tablet',
            tty='IN',
            version=self.version,
            created_by=self.user
        )
        
        # Create test LOINC code
        self.loinc = LOINCCode.objects.create(
            loinc_num='12345-6',
            short_name='Some LOINC Test',
            component='Some LOINC Test',
            property='MCnc',
            time_aspct='Pt',
            system='Ser/Plas',
            scale_typ='Qn',
            version=self.version,
            created_by=self.user
        )
        
        # Create test code mapping
        self.mapping = CodeMapping.objects.create(
            source_system='icd10',
            source_code='A01',
            target_system='snomed',
            target_code='100000001',
            mapping_type='equivalent',
            created_by=self.user
        )
        
        # Create test custom code set
        self.custom_set = CustomCodeSet.objects.create(
            name='Test Set',
            description='A test code set',
            created_by=self.user
        )
        
        # Create test custom code
        self.custom_code = CustomCode.objects.create(
            code_set=self.custom_set,
            code='C01',
            description='Custom Code 1',
            created_by=self.user
        )
    
    def test_code_system_version_creation(self):
        """Test creating a code system version"""
        self.assertEqual(self.version.system_name, "ICD-10-CM")
        self.assertEqual(str(self.version.revision_date), "2025-01-01")
        self.assertEqual(self.version.status, 'current')
        self.assertEqual(self.version.created_by, self.user)
    
    def test_icd10_code_creation(self):
        """Test creating an ICD-10 code"""
        code = ICD10Code.objects.create(
            code='A00.2',
            short_description='Cholera due to Vibrio cholerae',
            long_description='Cholera due to Vibrio cholerae 01, biovar cholerae',
            category='A00-A09',
            billable=True,
            valid_for_coding=True,
            version=self.version,
            created_by=self.user
        )
        
        self.assertEqual(code.code, 'A00.2')
        self.assertTrue(code.billable)
        self.assertTrue(code.valid_for_coding)
        self.assertEqual(code.version, self.version)
    
    def test_cpt_code_creation(self):
        """Test creating a CPT code"""
        code = CPTCode.objects.create(
            code='99213',
            short_description='Office visit, established patient',
            long_description='Office or other outpatient visit for the evaluation and management of an established patient',
            category='Evaluation and Management',
            modifier_allowed=True,
            version=self.version,
            created_by=self.user
        )
        
        self.assertEqual(code.code, '99213')
        self.assertTrue(code.modifier_allowed)
        self.assertEqual(code.category, 'Evaluation and Management')
    
    def test_snomed_concept_creation(self):
        """Test creating a SNOMED concept"""
        concept = SNOMEDConcept.objects.create(
            concept_id='22298006',
            preferred_term='Myocardial infarction',
            fully_specified_name='Myocardial infarction (disorder)',
            semantic_tag='disorder',
            module_id='900000000000207008',
            version=self.version,
            created_by=self.user
        )
        
        self.assertEqual(concept.concept_id, '22298006')
        self.assertEqual(concept.semantic_tag, 'disorder')
        self.assertEqual(concept.module_id, '900000000000207008')
    
    def test_rxnorm_concept_creation(self):
        """Test creating an RxNorm concept"""
        concept = RxNormConcept.objects.create(
            rxcui='161',
            preferred_term='Aspirin',
            tty='IN',
            version=self.version,
            created_by=self.user
        )
        
        self.assertEqual(concept.rxcui, '161')
        self.assertEqual(concept.preferred_term, 'Aspirin')
        self.assertEqual(concept.tty, 'IN')
    
    def test_loinc_code_creation(self):
        """Test creating a LOINC code"""
        code = LOINCCode.objects.create(
            loinc_num='1234-5',
            short_name='Glucose',
            component='Glucose',
            property='MCnc',
            time_aspct='Pt',
            system='Ser/Plas',
            scale_typ='Qn',
            version=self.version,
            created_by=self.user
        )
        
        self.assertEqual(code.loinc_num, '1234-5')
        self.assertEqual(code.component, 'Glucose')
        self.assertEqual(code.property, 'MCnc')
    
    def test_code_mapping_creation(self):
        """Test creating a code mapping"""
        mapping = CodeMapping.objects.create(
            source_system='icd10',
            source_code='A00.0',
            target_system='snomed',
            target_code='22298006',
            mapping_type='equivalent',
            created_by=self.user
        )
        
        self.assertEqual(mapping.source_system, 'icd10')
        self.assertEqual(mapping.target_system, 'snomed')
        self.assertEqual(mapping.mapping_type, 'equivalent')
    
    def test_custom_code_set_creation(self):
        """Test creating a custom code set"""
        code_set = CustomCodeSet.objects.create(
            name='Test Code Set',
            description='A test code set',
            created_by=self.user
        )
        
        self.assertEqual(code_set.name, 'Test Code Set')
        self.assertEqual(code_set.description, 'A test code set')
    
    def test_custom_code_creation(self):
        """Test creating a custom code"""
        code_set = CustomCodeSet.objects.create(
            name='Test Code Set',
            description='A test code set',
            created_by=self.user
        )
        
        code = CustomCode.objects.create(
            code_set=code_set,
            code='TEST01',
            description='Test code 01',
            created_by=self.user
        )
        
        self.assertEqual(code.code, 'TEST01')
        self.assertEqual(code.code_set, code_set)
    
    def test_str_methods(self):
        """Test string representation of models"""
        self.assertEqual(str(self.version), "ICD-10-CM (2025-01-01)")
        self.assertEqual(str(self.icd_code), "A00.1 - Cholera due to Vibrio cholerae")
        self.assertEqual(str(self.snomed), "100000001 | Clinical Finding")
        self.assertEqual(str(self.rxnorm), "12345 | Aspirin 81 MG Oral Tablet")
        self.assertEqual(str(self.loinc), "12345-6 | Some LOINC Test")
        self.assertEqual(str(self.mapping), "A01 -> 100000001")
        self.assertEqual(str(self.custom_set), "Test Set")
        self.assertEqual(str(self.custom_code), "C01 | Custom Code 1")

class TestCodeSystemVersionAPI(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_authenticate(user=self.user)
        self.version = CodeSystemVersion.objects.create(
            system_name="ICD-10-CM",
            revision_date="2025-01-01",
            status='current'
        )
        self.url = reverse('code_systems_api:codesystemversion-list')

    def test_get_code_system_versions(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['system_name'], 'ICD-10-CM')

    def test_create_code_system_version(self):
        data = {
            'system_name': 'New System',
            'revision_date': '2025-02-01',
            'status': 'current'
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CodeSystemVersion.objects.count(), 2)
        self.assertEqual(CodeSystemVersion.objects.get(id=response.data['id']).system_name, 'New System')

    def test_update_code_system_version(self):
        url = reverse('code_systems_api:codesystemversion-detail', kwargs={'pk': self.version.pk})
        data = {
            'system_name': 'ICD-10-CM Updated',
            'revision_date': '2025-01-02',
            'status': 'archived'
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.version.refresh_from_db()
        self.assertEqual(self.version.system_name, 'ICD-10-CM Updated')
        self.assertEqual(str(self.version.revision_date), '2025-01-02')
        self.assertEqual(self.version.status, 'archived')

    def test_delete_code_system_version(self):
        url = reverse('code_systems_api:codesystemversion-detail', kwargs={'pk': self.version.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(CodeSystemVersion.objects.count(), 0)


class TestCodeImportService(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.version = CodeSystemVersion.objects.create(
            system_name="Test System",
            revision_date="2025-01-01",
            status='current'
        )
        self.service = CodeImportService(version_id=self.version.id)

    def test_import_icd10_codes(self):
        """Test importing ICD-10 codes"""
        csv_content = "code,short_description,long_description,category,billable\n" \
                      "A01,Cholera due to Vibrio cholerae,Cholera due to Vibrio cholerae 01,A00-A09,true\n" \
                      "B02,Cholera due to Vibrio cholerae 01,Cholera due to Vibrio cholerae 01 biovar eltor,A00-A09,true"
        
        file_obj = SimpleUploadedFile(
            "test_codes.csv",
            csv_content.encode('utf-8'),
            content_type="text/csv"
        )
        
        task_id = self.service.import_codes(
            system='icd10',
            file_obj=file_obj,
            file_format='csv',
            user=self.user
        )
        
        self.assertIsInstance(task_id, str)
        self.assertTrue(ICD10Code.objects.filter(code="A01", version=self.version).exists())
        self.assertTrue(ICD10Code.objects.filter(code="B02", version=self.version).exists())

    def test_import_cpt_codes(self):
        """Test importing CPT codes"""
        csv_content = "code,short_description,long_description,category,modifier_allowed\n" \
                      "99213,Office visit, established patient,Office or other outpatient visit for the evaluation and management of an established patient,True\n" \
                      "99214,Office visit, new patient,Office or other outpatient visit for the evaluation and management of a new patient,True"
        
        file_obj = SimpleUploadedFile(
            "test_codes.csv",
            csv_content.encode('utf-8'),
            content_type="text/csv"
        )
        
        task_id = self.service.import_codes(
            system='cpt',
            file_obj=file_obj,
            file_format='csv',
            user=self.user
        )
        
        self.assertIsInstance(task_id, str)
        self.assertTrue(CPTCode.objects.filter(code="99213", version=self.version).exists())
        self.assertTrue(CPTCode.objects.filter(code="99214", version=self.version).exists())

    def test_import_snomed_codes(self):
        """Test importing SNOMED codes"""
        csv_content = "concept_id,preferred_term,fully_specified_name,semantic_tag\n" \
                      "100000001,Clinical Finding,Clinical Finding,finding\n" \
                      "100000002,Procedure,Procedure,procedure"
        
        file_obj = SimpleUploadedFile(
            "test_codes.csv",
            csv_content.encode('utf-8'),
            content_type="text/csv"
        )
        
        task_id = self.service.import_codes(
            system='snomed',
            file_obj=file_obj,
            file_format='csv',
            user=self.user
        )
        
        self.assertIsInstance(task_id, str)
        self.assertTrue(SNOMEDConcept.objects.filter(concept_id="100000001", version=self.version).exists())
        self.assertTrue(SNOMEDConcept.objects.filter(concept_id="100000002", version=self.version).exists())

    def test_import_rxnorm_codes(self):
        """Test importing RxNorm codes"""
        csv_content = "rxcui,preferred_term,tty\n" \
                      "12345,Aspirin,IN\n" \
                      "67890,Tylenol,IN"
        
        file_obj = SimpleUploadedFile(
            "test_codes.csv",
            csv_content.encode('utf-8'),
            content_type="text/csv"
        )
        
        task_id = self.service.import_codes(
            system='rxnorm',
            file_obj=file_obj,
            file_format='csv',
            user=self.user
        )
        
        self.assertIsInstance(task_id, str)
        self.assertTrue(RxNormConcept.objects.filter(rxcui="12345", version=self.version).exists())
        self.assertTrue(RxNormConcept.objects.filter(rxcui="67890", version=self.version).exists())

    def test_import_loinc_codes(self):
        """Test importing LOINC codes"""
        csv_content = "loinc_num,short_name,component,property,time_aspct,system,scale_typ\n" \
                      "12345-6,Some LOINC Test,Some LOINC Test,MCnc,Pt,Ser/Plas,Qn\n" \
                      "78901-2,Another LOINC Test,Another LOINC Test,MCnc,Pt,Ser/Plas,Qn"
        
        file_obj = SimpleUploadedFile(
            "test_codes.csv",
            csv_content.encode('utf-8'),
            content_type="text/csv"
        )
        
        task_id = self.service.import_codes(
            system='loinc',
            file_obj=file_obj,
            file_format='csv',
            user=self.user
        )
        
        self.assertIsInstance(task_id, str)
        self.assertTrue(LOINCCode.objects.filter(loinc_num="12345-6", version=self.version).exists())
        self.assertTrue(LOINCCode.objects.filter(loinc_num="78901-2", version=self.version).exists())

    def test_import_invalid_system(self):
        file_obj = SimpleUploadedFile("test.csv", b"content", content_type="text/csv")
        with self.assertRaises(ValueError):
            self.service.import_codes(system='invalid_system', file_obj=file_obj, file_format='csv', user=self.user)


class TestCodeValidationService(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.version = CodeSystemVersion.objects.create(
            system_name="ICD-10-CM",
            revision_date="2025-01-01",
            status='current'
        )
        ICD10Code.objects.create(code='A00.0-BASIC', short_description='Cholera', version=self.version, created_by=self.user)
        self.service = CodeValidationService(version_id=self.version.id)
    
    def test_validate_code(self):
        """Test code validation"""
        # Test valid code
        is_valid = self.service.validate_code('icd10', 'A00.0')
        self.assertTrue(is_valid)
        
        # Test invalid code
        is_valid = self.service.validate_code('icd10', 'INVALID')
        self.assertFalse(is_valid)
    
    def test_get_code_info(self):
        """Test getting code information"""
        info = CodeSystemService.get_code_info('icd10', 'A00.0')
        
        self.assertIsNotNone(info)
        self.assertEqual(info['code'], 'A00.0')
        self.assertEqual(info['system'], 'icd10')
        self.assertTrue(info['billable'])


class CodeSystemServiceTest(TestCase):
    """Test code system services"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Create test version
        self.version = CodeSystemVersion.objects.create(
            system_name='icd10',
            version='2024',
            revision_date=date.today(),
            status='current',
            created_by=self.user
        )
        
        # Create test ICD-10 codes
        self.icd_codes = [
            ICD10Code.objects.create(
                code='A00.0-SEARCH',
                short_description='Cholera due to Vibrio cholerae',
                long_description='Cholera due to Vibrio cholerae 01, biovar cholerae',
                category='A00-A09',
                billable=True,
                version=self.version,
                created_by=self.user
            ),
            ICD10Code.objects.create(
                code='A00.1-TEST',
                short_description='Cholera due to Vibrio cholerae 01',
                long_description='Cholera due to Vibrio cholerae 01, biovar eltor',
                category='A00-A09',
                billable=True,
                version=self.version,
                created_by=self.user
            )
        ]
    
    def test_search_icd10_codes(self):
        """Test searching ICD-10 codes"""
        results = CodeSystemService.search_codes('icd10', 'cholera')
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['system'], 'icd10')
        self.assertIn('cholera', results[0]['description'].lower())
    
    def test_search_exact_match(self):
        """Test exact match search"""
        results = CodeSystemService.search_codes('icd10', 'A00.0', exact_match=True)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['code'], 'A00.0')
    
    def test_search_with_limit(self):
        """Test search with limit"""
        results = CodeSystemService.search_codes('icd10', 'cholera', limit=1)
        
        self.assertEqual(len(results), 1)
    
    def test_validate_code(self):
        """Test code validation"""
        # Test valid code
        is_valid = CodeValidationService.validate_code('icd10', 'A00.0')
        self.assertTrue(is_valid)
        
        # Test invalid code
        is_valid = CodeValidationService.validate_code('icd10', 'INVALID')
        self.assertFalse(is_valid)
    
    def test_get_code_info(self):
        """Test getting code information"""
        info = CodeSystemService.get_code_info('icd10', 'A00.0')
        
        self.assertIsNotNone(info)
        self.assertEqual(info['code'], 'A00.0')
        self.assertEqual(info['system'], 'icd10')
        self.assertTrue(info['billable'])


class CodeSystemAPITest(APITestCase):
    """Test code system API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_authenticate(user=self.user)
        self.version = CodeSystemVersion.objects.create(
            system_name="ICD-10-CM",
            revision_date="2025-01-01",
            status='current',
            created_by=self.user
        )
        self.icd_code = ICD10Code.objects.create(
            code='A00.0',
            short_description='Cholera due to Vibrio cholerae',
            long_description='Cholera due to Vibrio cholerae 01, biovar cholerae',
            category='A00-A09',
            billable=True,
            version=self.version,
            created_by=self.user
        )

    def test_get_code_system_versions(self):
        """Test getting code system versions"""
        url = reverse('code_systems_api:codesystemversion-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['system_name'], 'ICD-10-CM')

    def test_get_current_versions(self):
        """Test getting current versions"""
        url = reverse('code_systems_api:codesystemversion-list') + '?status=current'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_get_icd10_codes(self):
        """Test getting ICD-10 codes"""
        url = reverse('code_systems_api:icd10code-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_get_billable_codes(self):
        """Test getting billable codes"""
        url = reverse('code_systems_api:icd10code-list') + '?billable=true'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_search_codes(self):
        """Test code search endpoint"""
        url = reverse('code_systems_api:icd10code-list') + '?search=Cholera'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_search_specific_system(self):
        """Test searching specific system"""
        url = reverse('code_systems_api:icd10code-list') + '?search=Cholera'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_validate_codes(self):
        """Test code validation endpoint"""
        url = reverse('code_systems_api:icd10code-validate-code')
        response = self.client.post(url, {'code': 'A00.0'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_valid'])

    def test_get_stats(self):
        """Test getting system statistics"""
        url = reverse('code_systems_api:codesystemversion-stats')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['icd10']['total_codes'], 1)

    def test_get_system_stats(self):
        """Test getting specific system statistics"""
        url = reverse('code_systems_api:codesystemversion-detail-stats', kwargs={'pk': self.version.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_codes'], 1)

    def test_create_icd10_code(self):
        """Test creating an ICD-10 code"""
        url = reverse('code_systems_api:icd10code-list')
        data = {
            'code': 'B00.0',
            'short_description': 'Test Cholera',
            'long_description': 'Test Cholera',
            'category': 'A00-A09',
            'billable': True,
            'version': self.version.pk
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(ICD10Code.objects.filter(code='B00.0').exists())

    def test_update_icd10_code(self):
        """Test updating an ICD-10 code"""
        url = reverse('code_systems_api:icd10code-detail', kwargs={'pk': self.icd_code.pk})
        data = {
            'short_description': 'Cholera Updated'
        }
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.icd_code.refresh_from_db()
        self.assertEqual(self.icd_code.short_description, 'Cholera Updated')

    def test_delete_icd10_code(self):
        """Test deleting an ICD-10 code"""
        url = reverse('code_systems_api:icd10code-detail', kwargs={'pk': self.icd_code.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ICD10Code.objects.filter(pk=self.icd_code.pk).exists())

    def test_unauthorized_access(self):
        """Test unauthorized access"""
        self.client.force_authenticate(user=None)
        url = reverse('code_systems_api:codesystemversion-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CodeSystemSerializerTest(APITestCase):
    """Test code system serializers"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_authenticate(user=self.user)
        self.version = CodeSystemVersion.objects.create(
            system_name="ICD-10-CM",
            revision_date="2025-01-01",
            status='current'
        )
        self.icd_code = ICD10Code.objects.create(
            code='A00.0',
            short_description='Cholera due to Vibrio cholerae',
            long_description='Cholera due to Vibrio cholerae 01',
            category='A00-A09',
            billable=True,
            version=self.version,
            created_by=self.user
        )
    
    def test_code_system_version_serializer(self):
        """Test code system version serializer"""
        serializer = CodeSystemVersionSerializer(instance=self.version)
        data = serializer.data
        
        self.assertEqual(data['system'], 'ICD-10-CM')  # Changed from 'icd10' to actual system_name
        self.assertEqual(data['version'], '2024')
        self.assertTrue(data['is_current'])
    
    def test_icd10_code_serializer(self):
        """Test ICD-10 code serializer"""
        code = ICD10Code.objects.create(
            code='A00.0-SER',
            short_description='Cholera due to Vibrio cholerae',
            long_description='Cholera due to Vibrio cholerae 01',
            category='A00-A09',
            billable=True,
            version=self.version,
            created_by=self.user
        )
        
        serializer = ICD10CodeSerializer(instance=code)
        data = serializer.data
        
        self.assertEqual(data['code'], 'A00.0')
        self.assertEqual(data['category'], 'A00-A09')
        self.assertTrue(data['billable'])
    
    def test_serializer_validation(self):
        """Test serializer validation"""
        # Test valid data
        data = {
            'code': 'A00.0',
            'short_description': 'Test code',
            'long_description': 'Test code description',
            'category': 'A00-A09',
            'billable': True,
            'version': str(self.version.id)
        }
        
        serializer = ICD10CodeSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
        # Test invalid data (missing required fields)
        invalid_data = {
            'short_description': 'Test code'
        }
        
        serializer = ICD10CodeSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('code', serializer.errors)
    
    def test_create_with_serializer(self):
        """Test creating object with serializer"""
        data = {
            'code': 'A00.0',
            'short_description': 'Test code',
            'long_description': 'Test code description',
            'category': 'A00-A09',
            'billable': True,
            'version': str(self.version.id)
        }
        
        serializer = ICD10CodeSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
        code = serializer.save(created_by=self.user)
        self.assertEqual(code.code, 'A00.0')
        self.assertEqual(code.created_by, self.user)
    
    def test_update_with_serializer(self):
        """Test updating object with serializer"""
        code = ICD10Code.objects.create(
            code='A00.0',
            short_description='Original description',
            long_description='Original long description',
            category='A00-A09',
            billable=True,
            version=self.version,
            created_by=self.user
        )
        
        data = {
            'code': 'A00.0',
            'short_description': 'Updated description',
            'long_description': 'Updated long description',
            'category': 'A00-A09',
            'billable': True,
            'version': str(self.version.id)
        }
        
        serializer = ICD10CodeSerializer(instance=code, data=data)
        self.assertTrue(serializer.is_valid())
        
        updated_code = serializer.save(updated_by=self.user)
        self.assertEqual(updated_code.short_description, 'Updated description')
        self.assertEqual(updated_code.updated_by, self.user)


class CodeSystemAdminTest(APITestCase):
    """Test code system admin functionality"""
    
    def setUp(self):
        self.user = User.objects.create_superuser(username='admin', password='adminpassword', email='admin@example.com')
        self.client.force_authenticate(user=self.user)
        self.version = CodeSystemVersion.objects.create(
            system_name="ICD-10-CM",
            revision_date="2025-01-01",
            status='current'
        )
        self.icd_code = ICD10Code.objects.create(
            code='A00.0',
            short_description='Cholera due to Vibrio cholerae',
            long_description='Cholera due to Vibrio cholerae 01',
            category='A00-A09',
            billable=True,
            version=self.version,
            created_by=self.user
        )
    
    def test_admin_access(self):
        """Test admin access to code system models"""
        # Test code system versions admin
        response = self.client.get('/admin/code_systems/codesystemversion/')
        self.assertEqual(response.status_code, 200)
        
        # Test ICD-10 codes admin
        response = self.client.get('/admin/code_systems/icd10code/')
        self.assertEqual(response.status_code, 200)
    
    def test_admin_create_code(self):
        """Test creating code through admin"""
        data = {
            'code': 'A00.0',
            'short_description': 'Test code',
            'long_description': 'Test code description',
            'category': 'A00-A09',
            'billable': True,
            'valid_for_coding': True,
            'version': str(self.version.id),
            'is_active': True
        }
        
        response = self.client.post('/admin/code_systems/icd10code/add/', data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful creation
        
        # Check if code was created
        self.assertTrue(ICD10Code.objects.filter(code='A00.0').exists())
    
    def test_admin_search(self):
        """Test admin search functionality"""
        # Create test code
        ICD10Code.objects.create(
            code='A00.3',
            short_description='Cholera due to Vibrio cholerae',
            long_description='Cholera due to Vibrio cholerae 01',
            category='A00-A09',
            billable=True,
            version=self.version,
            created_by=self.user
        )
        
        # Test search
        response = self.client.get('/admin/code_systems/icd10code/', {'q': 'cholera'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'A00.3')
    
    def test_admin_filters(self):
        """Test admin list filters"""
        # Create test codes
        ICD10Code.objects.create(
            code='A00.4',
            short_description='Billable code',
            category='A00-A09',
            billable=True,
            version=self.version,
            created_by=self.user
        )
        
        ICD10Code.objects.create(
            code='A00.5',
            short_description='Non-billable code',
            category='A00-A09',
            billable=False,
            version=self.version,
            created_by=self.user
        )
        
        # Test billable filter
        response = self.client.get('/admin/code_systems/icd10code/', {'billable__exact': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'A00.4')
        self.assertNotContains(response, 'A00.5')


class CodeSystemIntegrationTest(APITestCase):
    """Integration tests for code systems"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.force_authenticate(user=self.user)

    def test_full_workflow(self):
        """Test complete workflow from creation to search"""
        # Create a code system version
        version_data = {
            'system_name': 'ICD-10-CM',
            'revision_date': '2025-01-01',
            'status': 'current'
        }
        response = self.client.post(reverse('codesystemversion-list'), version_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        version_id = response.data['id']

        # Import codes
        csv_content = "code,short_description,long_description,category,billable\n" \
                      "A01,Cholera due to Vibrio cholerae,Cholera due to Vibrio cholerae 01,A00-A09,true\n" \
                      "B02,Cholera due to Vibrio cholerae 01,Cholera due to Vibrio cholerae 01 biovar eltor,A00-A09,true"
        
        file_obj = SimpleUploadedFile(
            "test_codes.csv",
            csv_content.encode('utf-8'),
            content_type="text/csv"
        )
        
        task_id = CodeImportService(version_id=version_id).import_codes(
            system='icd10',
            file_obj=file_obj,
            file_format='csv',
            user=self.user
        )
        
        self.assertIsInstance(task_id, str)
        self.assertTrue(ICD10Code.objects.filter(code="A01", version__id=version_id).exists())
        self.assertTrue(ICD10Code.objects.filter(code="B02", version__id=version_id).exists())

        # Search for the code
        search_response = self.client.get(reverse('code_systems:code-search'), {'q': 'A01.1'})
        self.assertEqual(search_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(search_response.data), 1)
        self.assertEqual(search_response.data[0]['code'], 'A01.1')

    def test_code_mapping_workflow(self):
        """Test code mapping workflow"""
        # Create code system versions
        icd_version = CodeSystemVersion.objects.create(
            system_name="ICD-10-CM",
            revision_date="2025-01-01",
            status='current'
        )
        snomed_version = CodeSystemVersion.objects.create(
            system_name="SNOMED-CT",
            revision_date="2025-01-01",
            status='current'
        )

        # Create codes
        icd_code = ICD10Code.objects.create(
            code='A00.0',
            short_description='Cholera due to Vibrio cholerae',
            category='A00-A09',
            billable=True,
            version=icd_version,
            created_by=self.user
        )
        
        snomed_concept = SNOMEDConcept.objects.create(
            concept_id='22298006',
            preferred_term='Myocardial infarction',
            fully_specified_name='Myocardial infarction (disorder)',
            semantic_tag='disorder',
            version=snomed_version,
            created_by=self.user
        )
        
        # Create mapping
        mapping_data = {
            'source_system': 'icd10',
            'source_code': 'A00.0',
            'source_description': 'Cholera due to Vibrio cholerae',
            'target_system': 'snomed',
            'target_code': '22298006',
            'target_description': 'Myocardial infarction',
            'mapping_type': 'equivalent',
            'equivalence': 'equivalent',
            'version': str(icd_version.id)
        }
        
        url = reverse('code_systems:codemapping-list')
        response = self.client.post(url, mapping_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Search for mapping
        url = reverse('code_systems:code-mapping-search')
        response = self.client.get(url, {
            'from_code': 'A00.0',
            'mapping_type': 'equivalent'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['source_code'], 'A00.0')
        self.assertEqual(response.data[0]['target_code'], '22298006')
    
    def test_custom_code_set_workflow(self):
        """Test custom code set workflow"""
        # Create custom code set
        set_data = {
            'name': 'Emergency Codes',
            'description': 'Common codes for emergency situations',
            'category': 'emergency'
        }
        
        url = reverse('code_systems:customcodeset-list')
        response = self.client.post(url, set_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        set_id = response.data['id']
        
        # Add custom codes
        codes_data = [
            {
                'code_set': set_id,
                'code': 'EMG001',
                'description': 'Cardiac arrest'
            },
            {
                'code_set': set_id,
                'code': 'EMG002',
                'description': 'Respiratory failure'
            }
        ]
        
        url = reverse('code_systems:customcode-list')
        for code_data in codes_data:
            response = self.client.post(url, code_data, format='json')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Get codes in set
        url = reverse('code_systems:customcodeset-codes', kwargs={'pk': set_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        
        # Verify codes
        codes = response.data['results']
        self.assertEqual(codes[0]['code'], 'EMG001')
        self.assertEqual(codes[1]['code'], 'EMG002')
