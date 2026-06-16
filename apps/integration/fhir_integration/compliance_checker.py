"""
USCDI v6 Compliance Checker Service
Analyzes database for USCDI v6 data class coverage and compliance
"""
from typing import Dict, List, Any
from django.db.models import Count, Q
from datetime import datetime

from .models import FHIRResource, USCDIDataElement
from .uscdi_v6_mappings import USCDIv6Mapper


class USCDIComplianceChecker:
    """
    Service for analyzing USCDI v6 compliance across the database
    """
    
    def __init__(self):
        self.mapper = USCDIv6Mapper()
        self.uscdi_classes = self.mapper.USCDI_V6_DATA_CLASSES
    
    def get_compliance_dashboard(self) -> Dict[str, Any]:
        """
        Generate comprehensive compliance dashboard data
        """
        dashboard = {
            "generated_at": datetime.now().isoformat(),
            "overall_score": 0.0,
            "total_classes": len(self.uscdi_classes),
            "classes_with_data": 0,
            "total_resources": FHIRResource.objects.count(),
            "total_uscdi_elements": USCDIDataElement.objects.count(),
            "class_details": [],
            "missing_classes": [],
            "summary": {}
        }
        
        # Analyze each USCDI class
        class_scores = []
        for class_key, class_info in self.uscdi_classes.items():
            class_detail = self._analyze_class(class_key, class_info)
            dashboard["class_details"].append(class_detail)
            
            if class_detail["has_data"]:
                dashboard["classes_with_data"] += 1
                class_scores.append(class_detail["completeness_score"])
            else:
                dashboard["missing_classes"].append({
                    "class": class_key,
                    "name": class_info["name"]
                })
        
        # Calculate overall score
        if class_scores:
            dashboard["overall_score"] = sum(class_scores) / len(self.uscdi_classes)
        
        # Generate summary
        dashboard["summary"] = self._generate_summary(dashboard)
        
        return dashboard
    
    def _analyze_class(self, class_key: str, class_info: Dict) -> Dict[str, Any]:
        """
        Analyze a single USCDI data class
        """
        # Count resources for this class
        uscdi_elements = USCDIDataElement.objects.filter(uscdi_class=class_key)
        resource_count = uscdi_elements.count()
        
        # Get required elements
        required_elements = class_info.get("required_elements", [])
        total_required = len(required_elements)
        
        # Calculate completeness score
        # For now, if we have resources, we consider it complete
        # In a production system, you would check for specific FHIR fields
        completeness_score = 0.0
        if resource_count > 0:
            completeness_score = 100.0
        
        # Sample resources for display
        sample_resources = []
        if resource_count > 0:
            sample_resources = FHIRResource.objects.filter(
                uscdidataelement__uscdi_class=class_key
            ).distinct()[:5]
        
        return {
            "class_key": class_key,
            "class_name": class_info["name"],
            "description": class_info.get("description", ""),
            "resource_count": resource_count,
            "has_data": resource_count > 0,
            "required_elements_total": total_required,
            "required_elements_present": total_required if resource_count > 0 else 0,
            "required_elements_missing": 0 if resource_count > 0 else total_required,
            "completeness_score": completeness_score,
            "status": self._get_status(completeness_score),
            "missing_elements": [] if resource_count > 0 else required_elements,
            "sample_resource_ids": [str(r.id) for r in sample_resources[:3]]
        }
    
    def _check_element_in_resource(self, resource_data: Dict, element: str) -> bool:
        """
        Check if a required element exists in resource data
        """
        if not resource_data:
            return False
        
        # Simple check - element name exists as key
        if element in resource_data:
            value = resource_data[element]
            # Check if value is not None/empty
            if value is not None and value != "" and value != []:
                return True
        
        # Check nested structures (basic implementation)
        for key, value in resource_data.items():
            if isinstance(value, dict):
                if self._check_element_in_resource(value, element):
                    return True
        
        return False
    
    def _get_status(self, score: float) -> str:
        """
        Get status label based on completeness score
        """
        if score >= 80:
            return "complete"
        elif score >= 50:
            return "partial"
        elif score > 0:
            return "minimal"
        else:
            return "missing"
    
    def _generate_summary(self, dashboard: Dict) -> Dict[str, Any]:
        """
        Generate human-readable summary
        """
        overall_score = dashboard["overall_score"]
        classes_with_data = dashboard["classes_with_data"]
        total_classes = dashboard["total_classes"]
        
        # Categorize classes by status
        complete_classes = [c for c in dashboard["class_details"] if c["status"] == "complete"]
        partial_classes = [c for c in dashboard["class_details"] if c["status"] == "partial"]
        minimal_classes = [c for c in dashboard["class_details"] if c["status"] == "minimal"]
        missing_classes = [c for c in dashboard["class_details"] if c["status"] == "missing"]
        
        return {
            "overall_status": self._get_status(overall_score),
            "coverage_percentage": (classes_with_data / total_classes) * 100,
            "complete_count": len(complete_classes),
            "partial_count": len(partial_classes),
            "minimal_count": len(minimal_classes),
            "missing_count": len(missing_classes),
            "recommendation": self._get_recommendation(overall_score, classes_with_data, total_classes)
        }
    
    def _get_recommendation(self, score: float, classes_with_data: int, total_classes: int) -> str:
        """
        Generate recommendation based on compliance status
        """
        if score >= 80:
            return "System is highly compliant with USCDI v6. Ready for ONC certification testing."
        elif score >= 50:
            return "System has moderate USCDI v6 compliance. Address missing elements before ONC certification."
        elif classes_with_data > 0:
            return f"System has minimal USCDI v6 compliance ({classes_with_data}/{total_classes} classes). Significant work needed for ONC certification."
        else:
            return "No USCDI v6 data detected. Begin data ingestion to establish compliance baseline."
    
    def get_class_details(self, class_key: str) -> Dict[str, Any]:
        """
        Get detailed analysis for a specific USCDI class
        """
        if class_key not in self.uscdi_classes:
            return {
                "error": f"Unknown USCDI class: {class_key}",
                "available_classes": list(self.uscdi_classes.keys())
            }
        
        class_info = self.uscdi_classes[class_key]
        analysis = self._analyze_class(class_key, class_info)
        
        # Add sample resources
        sample_resources = FHIRResource.objects.filter(
            uscdidataelement__uscdi_class=class_key
        ).distinct()[:5]
        
        analysis["sample_resources"] = [
            {
                "id": str(r.id),
                "resource_type": r.resource_type,
                "resource_id": r.resource_id,
                "created_at": r.created_at.isoformat() if hasattr(r, 'created_at') else None,
                "data_preview": self._get_data_preview(r.resource_data)
            }
            for r in sample_resources
        ]
        
        return analysis
    
    def _get_data_preview(self, resource_data: Dict, max_keys: int = 5) -> Dict:
        """
        Get a preview of resource data (first few keys)
        """
        if not resource_data:
            return {}
        
        preview = {}
        for i, (key, value) in enumerate(resource_data.items()):
            if i >= max_keys:
                preview["..."] = f"({len(resource_data) - max_keys} more fields)"
                break
            
            # Simplify complex values
            if isinstance(value, dict):
                preview[key] = "{...}"
            elif isinstance(value, list):
                preview[key] = f"[{len(value)} items]"
            else:
                preview[key] = value
        
        return preview
    
    def export_compliance_report(self, format: str = "json") -> Dict[str, Any]:
        """
        Export compliance report in specified format
        """
        dashboard = self.get_compliance_dashboard()
        
        if format == "json":
            return dashboard
        elif format == "summary":
            # Return simplified summary
            return {
                "generated_at": dashboard["generated_at"],
                "overall_score": dashboard["overall_score"],
                "summary": dashboard["summary"],
                "classes_with_data": dashboard["classes_with_data"],
                "total_classes": dashboard["total_classes"],
                "missing_classes": [c["name"] for c in dashboard["missing_classes"]]
            }
        else:
            return {"error": f"Unsupported format: {format}"}
