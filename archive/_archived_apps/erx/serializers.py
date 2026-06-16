"""
Electronic Prescription (eRx) Serializers

This module provides serializers for the eRx system including
prescriptions, drug interactions, formulary information, and
pharmacy directory.
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from django.db import models
from patients.models import Patient
from .models import (
    ElectronicPrescription,
    PrescriptionRefill,
    PrescriptionHistory,
    DrugFormulary,
    DrugInteraction,
    PharmacyDirectory
)


class DrugFormularySerializer(serializers.ModelSerializer):
    """Serializer for drug formulary information"""
    
    class Meta:
        model = DrugFormulary
        fields = [
            'id', 'drug_name', 'generic_name', 'ndc_number', 'rxnorm_code',
            'formulary_status', 'tier_level', 'copay_amount', 'prior_auth_required',
            'quantity_limit', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DrugInteractionSerializer(serializers.ModelSerializer):
    """Serializer for drug interaction information"""
    
    class Meta:
        model = DrugInteraction
        fields = [
            'id', 'drug1_name', 'drug2_name', 'interaction_severity',
            'interaction_description', 'clinical_management', 'reference_source',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PharmacyDirectorySerializer(serializers.ModelSerializer):
    """Serializer for pharmacy directory"""
    
    full_address = serializers.ReadOnlyField()
    
    class Meta:
        model = PharmacyDirectory
        fields = [
            'id', 'ncpdp_id', 'name', 'address_line1', 'address_line2',
            'city', 'state', 'zip_code', 'phone', 'fax', 'email',
            'accepts_erx', 'accepts_controlled_substances', 'hours_operation',
            'is_active', 'full_address', 'last_updated'
        ]
        read_only_fields = ['id', 'last_updated', 'full_address']


class PrescriptionRefillSerializer(serializers.ModelSerializer):
    """Serializer for prescription refills"""
    
    class Meta:
        model = PrescriptionRefill
        fields = [
            'id', 'prescription', 'refill_number', 'date_filled',
            'quantity_dispensed', 'days_supply', 'pharmacy_ncpdp',
            'pharmacist', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PrescriptionHistorySerializer(serializers.ModelSerializer):
    """Serializer for prescription history"""
    
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = PrescriptionHistory
        fields = [
            'id', 'prescription', 'action', 'user', 'user_name',
            'timestamp', 'notes', 'old_values', 'new_values'
        ]
        read_only_fields = ['id', 'timestamp', 'user_name']


class ElectronicPrescriptionSerializer(serializers.ModelSerializer):
    """Serializer for electronic prescriptions"""
    
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    prescriber_name = serializers.CharField(source='prescriber.get_full_name', read_only=True)
    is_expired = serializers.ReadOnlyField()
    refills_remaining = serializers.ReadOnlyField()
    
    # Nested serializers for related data
    prescription_refills = PrescriptionRefillSerializer(many=True, read_only=True)
    history = PrescriptionHistorySerializer(many=True, read_only=True)
    
    class Meta:
        model = ElectronicPrescription
        fields = [
            'id', 'prescription_id', 'patient', 'patient_name',
            'prescriber', 'prescriber_name', 'prescription_type', 'status',
            'drug_name', 'generic_name', 'strength', 'dosage_form',
            'ndc_number', 'rxnorm_code', 'quantity', 'quantity_unit',
            'days_supply', 'refills', 'sig_code', 'directions',
            'date_prescribed', 'date_sent', 'effective_date', 'expiration_date',
            'pharmacy_ncpdp', 'pharmacy_name', 'pharmacy_address', 'pharmacy_phone',
            'diagnosis_code', 'clinical_notes', 'dispense_as_written',
            'controlled_substance', 'external_prescription_id', 'transmission_method',
            'response_message', 'response_code', 'is_expired', 'refills_remaining',
            'prescription_refills', 'history', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'prescription_id', 'is_expired', 'refills_remaining',
            'patient_name', 'prescriber_name', 'prescription_refills',
            'history', 'created_at', 'updated_at'
        ]
    
    def validate_patient(self, value):
        """Validate patient exists and is active"""
        if not value.is_active:
            raise serializers.ValidationError("Cannot prescribe for inactive patient")
        return value
    
    def validate_quantity(self, value):
        """Validate quantity is positive"""
        if value <= 0:
            raise serializers.ValidationError("Quantity must be positive")
        return value
    
    def validate_days_supply(self, value):
        """Validate days supply"""
        if value <= 0:
            raise serializers.ValidationError("Days supply must be positive")
        if value > 90:
            raise serializers.ValidationError("Days supply cannot exceed 90 days")
        return value
    
    def validate_refills(self, value):
        """Validate refills count"""
        if value < 0:
            raise serializers.ValidationError("Refills cannot be negative")
        if value > 11:
            raise serializers.ValidationError("Refills cannot exceed 11")
        return value


class ElectronicPrescriptionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating electronic prescriptions"""
    
    class Meta:
        model = ElectronicPrescription
        fields = [
            'id', 'prescription_id', 'patient', 'prescription_type', 'drug_name', 'generic_name',
            'strength', 'dosage_form', 'ndc_number', 'rxnorm_code',
            'quantity', 'quantity_unit', 'days_supply', 'refills',
            'sig_code', 'directions', 'effective_date', 'expiration_date',
            'pharmacy_ncpdp', 'pharmacy_name', 'pharmacy_address',
            'pharmacy_phone', 'diagnosis_code', 'clinical_notes',
            'dispense_as_written', 'controlled_substance'
        ]
        read_only_fields = ['id', 'prescription_id']
    
    def validate(self, data):
        """Validate prescription data"""
        # Check for drug interactions
        if 'drug_name' in data:
            self._check_drug_interactions(data['drug_name'])
        
        # Validate controlled substance requirements
        if data.get('controlled_substance', False):
            if not data.get('diagnosis_code'):
                raise serializers.ValidationError(
                    "Diagnosis code required for controlled substances"
                )
        
        return data
    
    def _check_drug_interactions(self, drug_name):
        """Check for drug interactions"""
        # This would integrate with a drug interaction database
        # For now, we'll just check against our local database
        interactions = DrugInteraction.objects.filter(
            models.Q(drug1_name__icontains=drug_name) | 
            models.Q(drug2_name__icontains=drug_name)
        )
        
        if interactions.exists():
            # Log warning but don't block prescription
            # In a real system, this would trigger alerts
            pass
    
    def create(self, validated_data):
        """Create prescription with prescriber from request"""
        validated_data['prescriber'] = self.context['request'].user
        return super().create(validated_data)


class PrescriptionStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating prescription status"""
    
    class Meta:
        model = ElectronicPrescription
        fields = ['status', 'response_message', 'response_code']
    
    def update(self, instance, validated_data):
        """Update prescription status and log history"""
        old_status = instance.status
        instance = super().update(instance, validated_data)
        
        # Log status change
        PrescriptionHistory.objects.create(
            prescription=instance,
            action='modified',
            user=self.context['request'].user,
            notes=f"Status changed from {old_status} to {instance.status}",
            old_values={'status': old_status},
            new_values={'status': instance.status}
        )
        
        return instance


class DrugInteractionCheckSerializer(serializers.Serializer):
    """Serializer for drug interaction checks"""
    
    drugs = serializers.ListField(
        child=serializers.CharField(max_length=255),
        min_length=2,
        help_text="List of drug names to check for interactions"
    )
    
    def validate_drugs(self, value):
        """Validate drug names"""
        if len(value) < 2:
            raise serializers.ValidationError("At least 2 drugs required for interaction check")
        return value


class FormularyCheckSerializer(serializers.Serializer):
    """Serializer for formulary checks"""
    
    drug_name = serializers.CharField(max_length=255)
    patient_id = serializers.IntegerField()
    
    def validate_patient_id(self, value):
        """Validate patient exists"""
        try:
            Patient.objects.get(id=value)
        except Patient.DoesNotExist:
            raise serializers.ValidationError("Patient not found")
        return value


class PharmacySearchSerializer(serializers.Serializer):
    """Serializer for pharmacy search"""
    
    search_term = serializers.CharField(max_length=255, required=False)
    city = serializers.CharField(max_length=100, required=False)
    state = serializers.CharField(max_length=2, required=False)
    zip_code = serializers.CharField(max_length=10, required=False)
    accepts_erx = serializers.BooleanField(default=True)
    accepts_controlled_substances = serializers.BooleanField(required=False)
    
    def validate(self, data):
        """Validate search parameters"""
        if not any([
            data.get('search_term'),
            data.get('city'),
            data.get('state'),
            data.get('zip_code')
        ]):
            raise serializers.ValidationError(
                "At least one search parameter is required"
            )
        return data
