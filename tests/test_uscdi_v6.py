import os
import sys
import django
from django.conf import settings

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medical_system.settings')

# Configure settings manually if needed (minimal for testing)
if not settings.configured:
    settings.configure(
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'apps.integration.fhir_integration',
        ],
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        }
    )
    django.setup()

from apps.integration.fhir_integration.uscdi_v6_mappings import USCDIv6Mapper

def test_uscdi_v6_mapping():
    mapper = USCDIv6Mapper()
    
    # Sample CSV Data simulating input
    sample_data = {
        'PatientID': '12345',
        'Name': 'John Doe',
        'DOB': '1980-01-01',
        'Sex': 'Male',
        'Author': 'Dr. Smith',
        'EntryDate': '2023-10-27T10:00:00',
        'SmokingStatus': 'Never Smoker',
        'HealthConcerns': 'High Blood Pressure',
        'Goals': 'Reduce salt intake',
        'FunctionalStatus': 'Independent',
        'DisabilityStatus': 'None',
        'MentalStatus': 'Alert',
        'SDOHGoals': 'Improve housing situation'
    }
    
    print("Testing USCDI v6 Mapping...")
    result = mapper.map_csv_to_uscdi(sample_data)
    
    if not result['success']:
        print(f"Mapping Failed: {result['error']}")
        return
        
    data = result['data']
    
    # List of all 22 USCDI v6 Data Classes
    all_classes = [
        'allergies', 'care_plan', 'care_team', 'clinical_notes', 'clinical_tests',
        'diagnostic_imaging', 'encounter_information', 'facility_information',
        'family_health_history', 'goals_and_preferences', 'health_insurance_information',
        'health_status_assessments', 'immunizations', 'laboratory', 'medical_devices',
        'medications', 'orders', 'patient_demographics', 'problems', 'procedures',
        'provenance', 'vital_signs'
    ]
    
    print("\nVerifying Data Classes Presence (Total 22):")
    missing_classes = []
    
    # We expect some to be missing in the *data* because the input CSV doesn't have them,
    # but we want to verify the *mapper* supports them (i.e., they are in USCDI_V6_DATA_CLASSES).
    # However, the map_csv_to_uscdi function removes empty classes.
    # So we will check if the mapper *definition* has them, and if the *output* has the ones we provided data for.
    
    # 1. Verify Mapper Definition
    print("\n1. Verifying Mapper Definition:")
    defined_classes = mapper.USCDI_V6_DATA_CLASSES.keys()
    for cls in all_classes:
        if cls in defined_classes:
            # print(f"[PASS] Defined: {cls}")
            pass
        else:
            print(f"[FAIL] Missing definition for: {cls}")
            missing_classes.append(cls)
            
    if not missing_classes:
        print("[PASS] All 22 Data Classes are defined in the Mapper.")
    
    # 2. Verify Data Extraction (for provided fields)
    print("\n2. Verifying Data Extraction for Sample Data:")
    
    expected_present = [
        'patient_demographics', 'provenance', 'health_status_assessments', 'goals_and_preferences'
    ]
    
    for cls in expected_present:
        if cls in data:
            print(f"[PASS] Extracted {cls}: {data[cls]}")
        else:
            print(f"[FAIL] Failed to extract {cls}")

    # 3. Verify Compliance Score Calculation
    print("\n3. Verifying Compliance Score:")
    score = result['compliance_score']
    print(f"Overall Score: {score['overall_score']}%")
    print(f"Present Classes: {score['present_classes']}/{score['total_classes']}")
    
    if score['total_classes'] == 22:
        print("[PASS] Compliance calculator recognizes 22 classes.")
    else:
        print(f"[FAIL] Compliance calculator sees {score['total_classes']} classes, expected 22.")

if __name__ == "__main__":
    test_uscdi_v6_mapping()
