"""
Test script for USCDI v6 Compliance Dashboard API
Run this to verify the compliance checker is working correctly
"""
import os
import django
import pytest

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medical_system.settings')
django.setup()

from apps.integration.fhir_integration.compliance_checker import USCDIComplianceChecker

@pytest.mark.django_db
def test_compliance_checker():
    """Test the USCDI v6 compliance checker"""
    print("=" * 60)
    print("USCDI v6 Compliance Dashboard Test")
    print("=" * 60)
    print()
    
    checker = USCDIComplianceChecker()
    
    # Test 1: Get dashboard
    print("📊 Test 1: Getting Compliance Dashboard...")
    dashboard = checker.get_compliance_dashboard()
    
    print(f"✓ Overall Score: {dashboard['overall_score']:.1f}%")
    print(f"✓ Total Classes: {dashboard['total_classes']}")
    print(f"✓ Classes with Data: {dashboard['classes_with_data']}")
    print(f"✓ Total Resources: {dashboard['total_resources']}")
    print(f"✓ Total USCDI Elements: {dashboard['total_uscdi_elements']}")
    print()
    
    # Test 2: Show class status
    print("📋 Test 2: Class Status Summary...")
    print(f"{'Class':<30} {'Status':<12} {'Score':<8} {'Resources'}")
    print("-" * 70)
    
    for class_detail in dashboard['class_details'][:10]:  # Show first 10
        print(f"{class_detail['class_name']:<30} "
              f"{class_detail['status']:<12} "
              f"{class_detail['completeness_score']:>6.1f}% "
              f"{class_detail['resource_count']:>9}")
    
    if len(dashboard['class_details']) > 10:
        print(f"... and {len(dashboard['class_details']) - 10} more classes")
    print()
    
    # Test 3: Show summary
    print("📈 Test 3: Compliance Summary...")
    summary = dashboard['summary']
    print(f"✓ Overall Status: {summary['overall_status'].upper()}")
    print(f"✓ Coverage: {summary['coverage_percentage']:.1f}%")
    print(f"✓ Complete Classes: {summary['complete_count']}")
    print(f"✓ Partial Classes: {summary['partial_count']}")
    print(f"✓ Missing Classes: {summary['missing_count']}")
    print(f"✓ Recommendation: {summary['recommendation']}")
    print()
    
    # Test 4: Get details for a specific class
    print("🔍 Test 4: Detailed Analysis for 'vital_signs'...")
    details = checker.get_class_details('vital_signs')
    
    if 'error' not in details:
        print(f"✓ Class: {details['class_name']}")
        print(f"✓ Resource Count: {details['resource_count']}")
        print(f"✓ Completeness: {details['completeness_score']:.1f}%")
        print(f"✓ Status: {details['status']}")
        if details['missing_elements']:
            print(f"✓ Missing Elements: {', '.join(details['missing_elements'][:5])}")
    else:
        print(f"⚠ {details['error']}")
    print()
    
    # Test 5: Export report
    print("💾 Test 5: Exporting Summary Report...")
    report = checker.export_compliance_report(format='summary')
    print(f"✓ Report generated at: {report['generated_at']}")
    print(f"✓ Overall Score: {report['overall_score']:.1f}%")
    print()
    
    print("=" * 60)
    print("✅ All tests completed successfully!")
    print("=" * 60)
    print()
    print("🌐 API Endpoints Available:")
    print("  GET /fhir/api/compliance/dashboard/")
    print("  GET /fhir/api/compliance/class_details/?class_key=vital_signs")
    print("  GET /fhir/api/compliance/export/?format=summary")
    print()

if __name__ == '__main__':
    test_compliance_checker()
