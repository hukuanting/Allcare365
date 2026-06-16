import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import io

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medical_system.settings')

import django
django.setup()

from django.contrib.auth.models import User
from apps.integration.fhir_integration.services import BulkDataProcessor
from apps.integration.fhir_integration.models import FHIRResource, USCDIDataElement

@pytest.mark.django_db
class TestBackendIngestion:
    def setup_method(self):
        self.processor = BulkDataProcessor()
        self.user = User.objects.create_user(username='testuser', password='password')

    def test_process_tabular_data_uscdi_v6(self):
        # Create sample CSV data
        csv_content = "patient_id,first_name,last_name,dob,gender,systolic_bp,diastolic_bp\n" \
                      "P001,John,Doe,1980-01-01,M,120,80"
        file = io.BytesIO(csv_content.encode('utf-8'))
        file.name = "test.csv"
        
        # Mock USCDIv6Mapper to return success with internal mapping format
        with patch('apps.integration.fhir_integration.services.USCDIv6Mapper') as MockMapper:
            mock_instance = MockMapper.return_value
            mock_instance.map_csv_to_uscdi.return_value = {
                'success': True,
                'data': {
                    'patient_demographics': {
                        'patient_id': 'P001',
                        'first_name': 'John',
                        'last_name': 'Doe'
                    },
                    'vital_signs': {
                        'systolic_bp': 120,
                        'diastolic_bp': 80
                    },
                    'provenance': {
                        'author': 'Dr. Test'
                    }
                }
            }
            
            result = self.processor.process_file(file, 'csv', user=self.user)
            
            assert result['status'] == 'success'
            assert result['processed_records'] == 1
            assert len(result['created_resources']) == 3
            
            # Verify DB objects
            assert FHIRResource.objects.count() == 3
            assert USCDIDataElement.objects.count() == 3
            
            patient_resource = FHIRResource.objects.get(resource_type='Patient')
            assert patient_resource.resource_data['family_name'] == 'Doe' if 'family_name' in patient_resource.resource_data else patient_resource.resource_data['last_name'] == 'Doe'
            
            vital_resource = FHIRResource.objects.get(resource_type='Observation', resource_data__systolic_bp=120)
            assert vital_resource.resource_data['systolic_bp'] == 120
