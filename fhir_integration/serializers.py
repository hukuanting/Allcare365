"""
FHIR R4 Serializers for API endpoints
"""
from rest_framework import serializers
from .models import FHIRResource, USCDIDataElement, FHIRPatientResource
import json


class FHIRResourceSerializer(serializers.ModelSerializer):
    """Serializer for FHIR Resources"""
    
    class Meta:
        model = FHIRResource
        fields = ['id', 'resource_type', 'resource_id', 'version_id', 
                 'last_updated', 'resource_data', 'is_active']
        read_only_fields = ['id', 'last_updated']
    
    def validate_resource_data(self, value):
        """Validate FHIR resource data structure"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Resource data must be a valid JSON object")
        
        if 'resourceType' not in value:
            raise serializers.ValidationError("Resource data must contain 'resourceType'")
        
        return value


class USCDIDataElementSerializer(serializers.ModelSerializer):
    """Serializer for USCDI Data Elements"""
    
    class Meta:
        model = USCDIDataElement
        fields = ['id', 'uscdi_class', 'data_element', 'fhir_resource', 'is_required']


class FHIRPatientSerializer(serializers.ModelSerializer):
    """Serializer for FHIR Patient Resources"""
    fhir_data = serializers.SerializerMethodField()
    
    class Meta:
        model = FHIRPatientResource
        fields = ['patient', 'identifier_system', 'identifier_value', 'fhir_data']
    
    def get_fhir_data(self, obj):
        """Get FHIR representation of patient"""
        try:
            fhir_patient = obj.to_fhir()
            return fhir_patient.dict()
        except Exception as e:
            return {"error": str(e)}


class BulkHealthDataSerializer(serializers.Serializer):
    """Serializer for bulk health data import"""
    file = serializers.FileField()
    data_format = serializers.ChoiceField(choices=[
        ('csv', 'CSV'),
        ('xlsx', 'Excel'),
        ('json', 'JSON'),
        ('fhir', 'FHIR Bundle')
    ])
    patient_id = serializers.UUIDField(required=False)
    
    def validate_file(self, value):
        """Validate uploaded file"""
        max_size = 50 * 1024 * 1024  # 50MB
        if value.size > max_size:
            raise serializers.ValidationError("File size cannot exceed 50MB")
        
        allowed_extensions = ['.csv', '.xlsx', '.json']
        file_extension = value.name.lower().split('.')[-1]
        if f'.{file_extension}' not in allowed_extensions:
            raise serializers.ValidationError(
                f"File type not supported. Allowed: {', '.join(allowed_extensions)}"
            )
        
        return value