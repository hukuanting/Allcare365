"""
Laboratory management serializers for REST API.

This module provides serializers for:
- Laboratory providers and configuration
- Lab test types and categories
- Lab orders and order items
- Lab results and quality control
- HL7 message processing
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from .models import (
    LabProvider, LabTestCategory, LabTestType, LabOrder, LabOrderItem,
    LabResult, LabMessage, QualityControlLog
)


class LabProviderSerializer(serializers.ModelSerializer):
    """Serializer for laboratory providers"""
    
    class Meta:
        model = LabProvider
        fields = [
            'id', 'name', 'contact_name', 'phone', 'email', 'address',
            'interface_type', 'hl7_config', 'api_endpoint', 'api_key',
            'lab_license_number', 'clia_number', 'average_turnaround_time',
            'is_preferred', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'api_key': {'write_only': True},  # Don't expose API key in responses
        }


class LabTestCategorySerializer(serializers.ModelSerializer):
    """Serializer for laboratory test categories"""
    subcategories = serializers.SerializerMethodField()
    
    class Meta:
        model = LabTestCategory
        fields = [
            'id', 'name', 'code', 'description', 'parent_category',
            'sort_order', 'subcategories', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'subcategories']
    
    def get_subcategories(self, obj):
        """Get subcategories if requested"""
        if hasattr(obj, 'subcategories'):
            return LabTestCategorySerializer(obj.subcategories.filter(is_active=True), many=True).data
        return []


class LabTestTypeSerializer(serializers.ModelSerializer):
    """Serializer for laboratory test types"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = LabTestType
        fields = [
            'id', 'name', 'short_name', 'category', 'category_name',
            'loinc_code', 'cpt_code', 'snomed_code', 'specimen_type',
            'specimen_volume', 'collection_instructions', 'units',
            'reference_range_male', 'reference_range_female', 'reference_range_pediatric',
            'critical_low', 'critical_high', 'result_type', 'possible_values',
            'average_tat', 'cost', 'requires_fasting', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'category_name']


class LabOrderItemSerializer(serializers.ModelSerializer):
    """Serializer for lab order items"""
    test_name = serializers.CharField(source='test_type.name', read_only=True)
    test_specimen_type = serializers.CharField(source='test_type.specimen_type', read_only=True)
    test_cost = serializers.DecimalField(source='test_type.cost', max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = LabOrderItem
        fields = [
            'id', 'test_type', 'test_name', 'test_specimen_type', 'test_cost',
            'specimen_id', 'collection_tube', 'status', 'cost',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'test_name', 'test_specimen_type', 'test_cost']


class LabOrderSerializer(serializers.ModelSerializer):
    """Serializer for laboratory orders"""
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    provider_name = serializers.CharField(source='provider.user.get_full_name', read_only=True)
    lab_provider_name = serializers.CharField(source='lab_provider.name', read_only=True)
    order_items = LabOrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = LabOrder
        fields = [
            'id', 'patient', 'patient_name', 'provider', 'provider_name',
            'encounter', 'lab_provider', 'lab_provider_name', 'order_number',
            'order_date', 'priority', 'clinical_info', 'diagnosis_codes',
            'collection_date', 'collection_location', 'collector_name',
            'status', 'status_notes', 'external_order_id', 'hl7_message_id',
            'total_cost', 'insurance_coverage', 'order_items',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'order_number', 'created_at', 'updated_at', 'patient_name',
            'provider_name', 'lab_provider_name', 'order_items'
        ]
    
    def validate(self, data):
        """Validate lab order data"""
        # Ensure collection date is not in the future for non-pending orders
        if data.get('collection_date') and data.get('status') != 'pending':
            if data['collection_date'] > timezone.now():
                raise serializers.ValidationError("Collection date cannot be in the future")
        
        return data


class LabOrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating lab orders with order items"""
    order_items = serializers.ListField(
        child=serializers.DictField(), write_only=True,
        help_text="List of test types to order"
    )
    
    class Meta:
        model = LabOrder
        fields = [
            'id', 'order_number', 'patient', 'provider', 'encounter', 'lab_provider', 'priority',
            'clinical_info', 'diagnosis_codes', 'collection_location',
            'insurance_coverage', 'order_items', 'total_cost', 'status'
        ]
        read_only_fields = ['id', 'order_number', 'total_cost', 'status']
    
    def create(self, validated_data):
        """Create lab order with order items"""
        order_items_data = validated_data.pop('order_items', [])
        
        # Create the lab order
        lab_order = LabOrder.objects.create(**validated_data)
        
        # Create order items
        total_cost = 0
        for item_data in order_items_data:
            test_type_id = item_data.get('test_type')
            if test_type_id:
                try:
                    test_type = LabTestType.objects.get(id=test_type_id)
                    order_item = LabOrderItem.objects.create(
                        lab_order=lab_order,
                        test_type=test_type,
                        cost=item_data.get('cost', test_type.cost),
                        **{k: v for k, v in item_data.items() if k not in ['test_type', 'cost']}
                    )
                    total_cost += test_type.cost
                except LabTestType.DoesNotExist:
                    continue
        
        # Update total cost
        lab_order.total_cost = total_cost
        lab_order.save()
        
        return lab_order
    
    def validate_order_items(self, value):
        """Validate order items"""
        if not value:
            raise serializers.ValidationError("At least one test must be ordered")
        
        # Check for duplicate test types
        test_types = [item.get('test_type') for item in value if item.get('test_type')]
        if len(test_types) != len(set(test_types)):
            raise serializers.ValidationError("Duplicate test types are not allowed")
        
        return value


class LabResultSerializer(serializers.ModelSerializer):
    """Serializer for laboratory results"""
    test_name = serializers.CharField(source='order_item.test_type.name', read_only=True)
    patient_name = serializers.CharField(source='order_item.lab_order.patient.full_name', read_only=True)
    order_number = serializers.CharField(source='order_item.lab_order.order_number', read_only=True)
    verified_by_name = serializers.CharField(source='verified_by.get_full_name', read_only=True)
    
    class Meta:
        model = LabResult
        fields = [
            'id', 'order_item', 'test_name', 'patient_name', 'order_number',
            'result_value', 'result_text', 'units', 'reference_range',
            'abnormal_flag', 'result_date', 'result_status', 'instrument_id',
            'technician_id', 'verified_by', 'verified_by_name', 'verified_date',
            'pathologist_review', 'pathologist_notes', 'external_result_id',
            'hl7_message_id', 'is_critical', 'is_abnormal',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'test_name', 'patient_name',
            'order_number', 'verified_by_name', 'is_critical', 'is_abnormal'
        ]
    
    def validate(self, data):
        """Validate lab result data"""
        # Auto-set verification fields if verified_by is provided
        if data.get('verified_by') and not data.get('verified_date'):
            data['verified_date'] = timezone.now()
        
        # Check for critical values
        order_item = data.get('order_item')
        if order_item:
            test_type = order_item.test_type
            result_value = data.get('result_value', '')
            
            # Auto-detect abnormal flags for numeric results
            if test_type.result_type == 'numeric' and result_value.replace('.', '').isdigit():
                try:
                    numeric_value = float(result_value)
                    
                    # Check critical values
                    if test_type.critical_high and numeric_value >= float(test_type.critical_high):
                        data['abnormal_flag'] = 'HH'
                    elif test_type.critical_low and numeric_value <= float(test_type.critical_low):
                        data['abnormal_flag'] = 'LL'
                    # Add logic for normal high/low ranges if available
                    
                except (ValueError, TypeError):
                    pass
        
        return data


class LabMessageSerializer(serializers.ModelSerializer):
    """Serializer for HL7 messages"""
    lab_provider_name = serializers.CharField(source='lab_provider.name', read_only=True)
    
    class Meta:
        model = LabMessage
        fields = [
            'id', 'lab_provider', 'lab_provider_name', 'message_type',
            'raw_message', 'parsed_data', 'processing_status', 'error_message',
            'lab_order', 'external_message_id', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'lab_provider_name']


class QualityControlLogSerializer(serializers.ModelSerializer):
    """Serializer for quality control logs"""
    lab_provider_name = serializers.CharField(source='lab_provider.name', read_only=True)
    test_name = serializers.CharField(source='test_type.name', read_only=True)
    
    class Meta:
        model = QualityControlLog
        fields = [
            'id', 'lab_provider', 'lab_provider_name', 'test_type', 'test_name',
            'qc_type', 'control_lot', 'expected_value', 'measured_value',
            'acceptable_range', 'passed', 'notes', 'performed_by',
            'instrument_id', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'lab_provider_name', 'test_name']


# Specialized serializers for different use cases

class LabOrderSummarySerializer(serializers.ModelSerializer):
    """Simplified serializer for lab order listings"""
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    provider_name = serializers.CharField(source='provider.user.get_full_name', read_only=True)
    test_count = serializers.SerializerMethodField()
    
    class Meta:
        model = LabOrder
        fields = [
            'id', 'order_number', 'patient_name', 'provider_name',
            'order_date', 'priority', 'status', 'test_count', 'total_cost'
        ]
    
    def get_test_count(self, obj):
        """Get number of tests in order"""
        return obj.order_items.count()


class CriticalResultSerializer(serializers.ModelSerializer):
    """Serializer for critical lab results that need immediate attention"""
    test_name = serializers.CharField(source='order_item.test_type.name', read_only=True)
    patient_name = serializers.CharField(source='order_item.lab_order.patient.full_name', read_only=True)
    provider_name = serializers.CharField(source='order_item.lab_order.provider.user.get_full_name', read_only=True)
    order_number = serializers.CharField(source='order_item.lab_order.order_number', read_only=True)
    
    class Meta:
        model = LabResult
        fields = [
            'id', 'test_name', 'patient_name', 'provider_name', 'order_number',
            'result_value', 'units', 'reference_range', 'abnormal_flag',
            'result_date', 'verified_date', 'pathologist_review'
        ]
    
    def to_representation(self, instance):
        """Only include critical results"""
        representation = super().to_representation(instance)
        if not instance.is_critical:
            return None
        return representation


class PendingOrderSerializer(serializers.ModelSerializer):
    """Serializer for orders pending collection or processing"""
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    provider_name = serializers.CharField(source='provider.user.get_full_name', read_only=True)
    test_names = serializers.SerializerMethodField()
    days_pending = serializers.SerializerMethodField()
    
    class Meta:
        model = LabOrder
        fields = [
            'id', 'order_number', 'patient_name', 'provider_name',
            'order_date', 'priority', 'status', 'test_names', 'days_pending'
        ]
    
    def get_test_names(self, obj):
        """Get list of test names in order"""
        return [item.test_type.name for item in obj.order_items.all()]
    
    def get_days_pending(self, obj):
        """Calculate days since order was placed"""
        from django.utils import timezone
        delta = timezone.now() - obj.order_date
        return delta.days
