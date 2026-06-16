"""
USCDI v6 Compliance Dashboard API Views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .compliance_checker import USCDIComplianceChecker


class USCDIComplianceViewSet(viewsets.ViewSet):
    """
    USCDI v6 Compliance Dashboard API
    Provides compliance analysis and visualization data
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """
        Get comprehensive USCDI v6 compliance dashboard
        Returns overall compliance score and detailed class analysis
        
        Example: GET /fhir/compliance/dashboard/
        """
        checker = USCDIComplianceChecker()
        dashboard_data = checker.get_compliance_dashboard()
        return Response(dashboard_data)
    
    @action(detail=False, methods=['get'])
    def class_details(self, request):
        """
        Get detailed analysis for a specific USCDI class
        Query param: class_key (e.g., 'vital_signs', 'patient_demographics')
        
        Example: GET /fhir/compliance/class_details/?class_key=vital_signs
        """
        class_key = request.query_params.get('class_key')
        if not class_key:
            return Response(
                {"error": "Missing required parameter: class_key"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        checker = USCDIComplianceChecker()
        details = checker.get_class_details(class_key)
        
        if "error" in details:
            return Response(details, status=status.HTTP_404_NOT_FOUND)
        
        return Response(details)
    
    @action(detail=False, methods=['get'])
    def export(self, request):
        """
        Export compliance report
        Query param: format ('json' or 'summary')
        
        Example: GET /fhir/compliance/export/?format=summary
        """
        export_format = request.query_params.get('format', 'json')
        
        checker = USCDIComplianceChecker()
        report = checker.export_compliance_report(format=export_format)
        
        if "error" in report:
            return Response(report, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(report)
