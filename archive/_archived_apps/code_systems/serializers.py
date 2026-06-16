"""
Code Systems Serializers

This module provides serializers for the code systems API endpoints.
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    CodeSystemVersion, ICD10Code, CPTCode, SNOMEDConcept,
    RxNormConcept, LOINCCode, CodeMapping, CustomCodeSet, CustomCode
)


class CodeSystemVersionSerializer(serializers.ModelSerializer):
    """Serializer for code system versions"""
    
    system_name_display = serializers.CharField(source='get_system_name_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    system = serializers.CharField(source='system_name', read_only=True)  # Add missing system field
    
    class Meta:
        model = CodeSystemVersion
        fields = [
            'id', 'system_name', 'system_name_display', 'system', 'version',
            'revision_date', 'file_name', 'file_checksum', 'status',
            'status_display', 'imported_date', 'records_count',
            'description', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'file_checksum', 'imported_date', 'records_count',
            'created_at', 'updated_at', 'system'
        ]


class ICD10CodeSerializer(serializers.ModelSerializer):
    """Serializer for ICD-10 codes"""
    
    version_info = serializers.StringRelatedField(source='version', read_only=True)
    
    class Meta:
        model = ICD10Code
        fields = [
            'id', 'code', 'short_description', 'long_description',
            'category', 'billable', 'valid_for_coding', 'version',
            'version_info', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CPTCodeSerializer(serializers.ModelSerializer):
    """Serializer for CPT codes"""
    
    version_info = serializers.StringRelatedField(source='version', read_only=True)
    
    class Meta:
        model = CPTCode
        fields = [
            'id', 'code', 'short_description', 'long_description',
            'category', 'modifier_allowed', 'bilateral', 'version',
            'version_info', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SNOMEDConceptSerializer(serializers.ModelSerializer):
    """Serializer for SNOMED CT concepts"""
    
    version_info = serializers.StringRelatedField(source='version', read_only=True)
    
    class Meta:
        model = SNOMEDConcept
        fields = [
            'id', 'concept_id', 'fully_specified_name', 'preferred_term',
            'definition', 'semantic_tag', 'module_id', 'version',
            'version_info', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RxNormConceptSerializer(serializers.ModelSerializer):
    """Serializer for RxNorm concepts"""
    
    version_info = serializers.StringRelatedField(source='version', read_only=True)
    
    class Meta:
        model = RxNormConcept
        fields = [
            'id', 'rxcui', 'concept_name', 'tty', 'source',
            'suppress', 'version', 'version_info', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LOINCCodeSerializer(serializers.ModelSerializer):
    """Serializer for LOINC codes"""
    
    version_info = serializers.StringRelatedField(source='version', read_only=True)
    
    class Meta:
        model = LOINCCode
        fields = [
            'id', 'loinc_num', 'component', 'property', 'time_aspct',
            'system', 'scale_typ', 'method_typ', 'short_name',
            'long_common_name', 'status', 'version', 'version_info',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CodeMappingSerializer(serializers.ModelSerializer):
    """Serializer for code mappings"""
    
    mapping_type_display = serializers.CharField(source='get_mapping_type_display', read_only=True)
    
    class Meta:
        model = CodeMapping
        fields = [
            'id', 'source_system', 'source_code', 'target_system',
            'target_code', 'mapping_type', 'mapping_type_display',
            'confidence', 'notes', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_confidence(self, value):
        """Validate confidence is between 0 and 1"""
        if not 0 <= value <= 1:
            raise serializers.ValidationError("Confidence must be between 0.00 and 1.00")
        return value


class CustomCodeSetSerializer(serializers.ModelSerializer):
    """Serializer for custom code sets"""
    
    codes_count = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomCodeSet
        fields = [
            'id', 'name', 'description', 'prefix', 'codes_count',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'codes_count', 'created_at', 'updated_at']
    
    def get_codes_count(self, obj):
        """Get count of codes in this set"""
        return obj.codes.filter(is_active=True).count()


class CustomCodeSerializer(serializers.ModelSerializer):
    """Serializer for custom codes"""
    
    code_set_name = serializers.CharField(source='code_set.name', read_only=True)
    
    class Meta:
        model = CustomCode
        fields = [
            'id', 'code_set', 'code_set_name', 'code', 'description',
            'sort_order', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# Search and utility serializers
class CodeSearchSerializer(serializers.Serializer):
    """Serializer for code search requests"""
    
    system = serializers.ChoiceField(
        choices=['icd10', 'cpt', 'snomed', 'rxnorm', 'loinc', 'custom'],
        help_text="Code system to search"
    )
    query = serializers.CharField(
        max_length=255,
        help_text="Search query"
    )
    limit = serializers.IntegerField(
        default=50,
        min_value=1,
        max_value=200,
        help_text="Maximum number of results"
    )
    exact_match = serializers.BooleanField(
        default=False,
        help_text="Whether to perform exact match"
    )


class CodeValidationSerializer(serializers.Serializer):
    """Serializer for code validation requests"""
    
    system = serializers.ChoiceField(
        choices=['icd10', 'cpt', 'snomed', 'rxnorm', 'loinc'],
        help_text="Code system"
    )
    code = serializers.CharField(
        max_length=50,
        help_text="Code to validate"
    )


class CodeImportSerializer(serializers.Serializer):
    """Serializer for code import requests"""
    
    system = serializers.ChoiceField(
        choices=['icd10', 'cpt', 'snomed', 'rxnorm', 'loinc'],
        help_text="Code system to import"
    )
    version = serializers.CharField(
        max_length=50,
        help_text="Version identifier"
    )
    revision_date = serializers.DateField(
        help_text="Official revision date"
    )
    file_name = serializers.CharField(
        max_length=255,
        help_text="Source file name"
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional description"
    )


class SystemStatisticsSerializer(serializers.Serializer):
    """Serializer for system statistics"""
    
    system_name = serializers.CharField()
    versions_installed = serializers.IntegerField()
    total_codes = serializers.IntegerField()
    latest_version = serializers.CharField(allow_null=True)


# Bulk operation serializers
class BulkCustomCodeSerializer(serializers.Serializer):
    """Serializer for bulk custom code operations"""
    
    code_set_id = serializers.UUIDField(help_text="Custom code set ID")
    codes = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of codes to add"
    )
    
    def validate_codes(self, value):
        """Validate codes list"""
        if not value:
            raise serializers.ValidationError("Codes list cannot be empty")
        
        for code_data in value:
            if 'code' not in code_data or 'description' not in code_data:
                raise serializers.ValidationError(
                    "Each code must have 'code' and 'description' fields"
                )
        
        return value
