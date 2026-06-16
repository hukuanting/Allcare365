"""
Serializers for pharmacy models.
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from django.db.models import Q
from .models import (
    DrugCategory, Drug, DrugInteraction, DrugAllergy,
    DrugInventory, Prescription, PrescriptionRefill, InventoryTransaction
)


class DrugCategorySerializer(serializers.ModelSerializer):
    """Serializer for drug categories"""
    subcategories = serializers.StringRelatedField(many=True, read_only=True)
    
    class Meta:
        model = DrugCategory
        fields = [
            'id', 'name', 'code', 'description', 'parent_category',
            'subcategories', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'subcategories']


class DrugSerializer(serializers.ModelSerializer):
    """Serializer for drugs"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    dosage_form_display = serializers.CharField(source='get_dosage_form_display', read_only=True)
    controlled_substance_display = serializers.CharField(source='get_controlled_substance_display', read_only=True)
    total_inventory = serializers.SerializerMethodField()
    
    class Meta:
        model = Drug
        fields = [
            'id', 'name', 'generic_name', 'brand_name', 'ndc_number',
            'upc_code', 'manufacturer_code', 'category', 'category_name',
            'therapeutic_class', 'pharmacologic_class', 'dosage_form',
            'dosage_form_display', 'strength', 'unit', 'manufacturer',
            'supplier', 'controlled_substance', 'controlled_substance_display',
            'contraindications', 'warnings', 'side_effects', 'interactions',
            'reorder_level', 'max_level', 'unit_cost', 'unit_price',
            'average_wholesale_price', 'discontinued', 'discontinued_date',
            'total_inventory', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'category_name',
            'dosage_form_display', 'controlled_substance_display', 'total_inventory'
        ]
    
    def get_total_inventory(self, obj):
        """Get total inventory across all facilities"""
        return sum(inv.quantity_on_hand for inv in obj.inventory.filter(is_active=True))


class DrugInteractionSerializer(serializers.ModelSerializer):
    """Serializer for drug interactions"""
    drug1_name = serializers.CharField(source='drug1.name', read_only=True)
    drug2_name = serializers.CharField(source='drug2.name', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    
    class Meta:
        model = DrugInteraction
        fields = [
            'id', 'drug1', 'drug1_name', 'drug2', 'drug2_name',
            'severity', 'severity_display', 'description',
            'clinical_management', 'mechanism', 'reference_source',
            'reference_date', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'drug1_name',
            'drug2_name', 'severity_display'
        ]


class DrugAllergySerializer(serializers.ModelSerializer):
    """Serializer for drug allergies"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    drug_name = serializers.CharField(source='drug.name', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    verified_by_name = serializers.CharField(source='verified_by.get_full_name', read_only=True)
    
    class Meta:
        model = DrugAllergy
        fields = [
            'id', 'patient', 'patient_name', 'drug', 'drug_name',
            'allergen', 'severity', 'severity_display', 'reaction_description',
            'onset_date', 'verified', 'verified_by', 'verified_by_name',
            'verified_date', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'patient_name',
            'drug_name', 'severity_display', 'verified_by_name'
        ]


class DrugInventorySerializer(serializers.ModelSerializer):
    """Serializer for drug inventory"""
    drug_name = serializers.CharField(source='drug.name', read_only=True)
    drug_strength = serializers.CharField(source='drug.strength', read_only=True)
    facility_name = serializers.CharField(source='facility.name', read_only=True)
    quantity_available = serializers.ReadOnlyField()
    total_cost = serializers.ReadOnlyField()
    days_until_expiry = serializers.SerializerMethodField()
    
    class Meta:
        model = DrugInventory
        fields = [
            'id', 'drug', 'drug_name', 'drug_strength', 'facility',
            'facility_name', 'warehouse', 'lot_number', 'expiration_date',
            'quantity_on_hand', 'quantity_allocated', 'quantity_available',
            'unit_cost', 'total_cost', 'days_until_expiry',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'drug_name',
            'drug_strength', 'facility_name', 'quantity_available',
            'total_cost', 'days_until_expiry'
        ]
    
    def get_days_until_expiry(self, obj):
        """Calculate days until expiry"""
        from django.utils import timezone
        if obj.expiration_date:
            delta = obj.expiration_date - timezone.now().date()
            return delta.days
        return None


class PrescriptionSerializer(serializers.ModelSerializer):
    """Serializer for prescriptions"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    provider_name = serializers.CharField(source='provider.get_full_name', read_only=True)
    drug_name = serializers.CharField(source='drug.name', read_only=True)
    drug_strength = serializers.CharField(source='drug.strength', read_only=True)
    route_display = serializers.CharField(source='get_route_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    dispensed_by_name = serializers.CharField(source='dispensed_by.get_full_name', read_only=True)
    
    class Meta:
        model = Prescription
        fields = [
            'id', 'patient', 'patient_name', 'provider', 'provider_name',
            'encounter', 'drug', 'drug_name', 'drug_strength',
            'prescribed_date', 'start_date', 'end_date', 'quantity',
            'quantity_dispensed', 'unit', 'refills', 'refills_remaining',
            'dosage_instructions', 'sig_code', 'frequency', 'duration',
            'route', 'route_display', 'status', 'status_display',
            'pharmacy', 'pharmacy_phone', 'dispensed_date', 'dispensed_by',
            'dispensed_by_name', 'indication', 'notes', 'e_prescribed',
            'dea_number', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'patient_name',
            'provider_name', 'drug_name', 'drug_strength', 'route_display',
            'status_display', 'dispensed_by_name'
        ]


class PrescriptionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating prescriptions with validation"""
    
    class Meta:
        model = Prescription
        fields = [
            'patient', 'provider', 'encounter', 'drug', 'prescribed_date',
            'start_date', 'end_date', 'quantity', 'unit', 'refills',
            'dosage_instructions', 'sig_code', 'frequency', 'duration',
            'route', 'indication', 'notes', 'e_prescribed', 'dea_number'
        ]
    
    def validate(self, data):
        """Validate prescription data"""
        # Check for drug allergies
        patient = data['patient']
        drug = data['drug']
        
        # Check if patient has allergies to this drug
        allergies = patient.drug_allergies.filter(
            drug=drug,
            is_active=True
        )
        if allergies.exists():
            allergy = allergies.first()
            raise serializers.ValidationError(
                f"Patient has a {allergy.severity} allergy to {drug.name}: {allergy.reaction_description}"
            )
        
        # Check for drug interactions with active prescriptions
        active_prescriptions = patient.pharmacy_prescriptions.filter(
            status='active',
            is_active=True
        ).exclude(drug=drug)
        
        for prescription in active_prescriptions:
            interactions = DrugInteraction.objects.filter(
                Q(drug1=drug, drug2=prescription.drug) |
                Q(drug1=prescription.drug, drug2=drug),
                is_active=True
            )
            
            for interaction in interactions:
                if interaction.severity in ['major', 'contraindicated']:
                    raise serializers.ValidationError(
                        f"Major drug interaction detected: {interaction.description}"
                    )
        
        # Validate controlled substance requirements
        if drug.controlled_substance and not data.get('dea_number'):
            raise serializers.ValidationError(
                "DEA number is required for controlled substances"
            )
        
        return data
    
    def create(self, validated_data):
        """Create prescription with proper initialization"""
        prescription = super().create(validated_data)
        prescription.refills_remaining = prescription.refills
        prescription.save()
        return prescription


class PrescriptionRefillSerializer(serializers.ModelSerializer):
    """Serializer for prescription refills"""
    prescription_drug = serializers.CharField(source='prescription.drug.name', read_only=True)
    patient_name = serializers.CharField(source='prescription.patient.get_full_name', read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    dispensed_by_name = serializers.CharField(source='dispensed_by.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = PrescriptionRefill
        fields = [
            'id', 'prescription', 'prescription_drug', 'patient_name',
            'refill_number', 'requested_date', 'approved_date',
            'dispensed_date', 'quantity_dispensed', 'days_supply',
            'requested_by', 'requested_by_name', 'approved_by',
            'approved_by_name', 'dispensed_by', 'dispensed_by_name',
            'status', 'status_display', 'notes',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'prescription_drug',
            'patient_name', 'requested_by_name', 'approved_by_name',
            'dispensed_by_name', 'status_display'
        ]


class InventoryTransactionSerializer(serializers.ModelSerializer):
    """Serializer for inventory transactions"""
    drug_name = serializers.CharField(source='drug_inventory.drug.name', read_only=True)
    facility_name = serializers.CharField(source='drug_inventory.facility.name', read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = InventoryTransaction
        fields = [
            'id', 'drug_inventory', 'drug_name', 'facility_name',
            'transaction_type', 'transaction_type_display', 'quantity_before',
            'quantity_change', 'quantity_after', 'reference_number',
            'prescription', 'unit_cost', 'total_cost', 'reason',
            'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'drug_name',
            'facility_name', 'transaction_type_display', 'created_by_name'
        ]


# Summary serializers for dashboard/reporting
class DrugSummarySerializer(serializers.ModelSerializer):
    """Summary serializer for drug dashboard"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    total_inventory = serializers.SerializerMethodField()
    low_stock_items = serializers.SerializerMethodField()
    expired_items = serializers.SerializerMethodField()
    
    class Meta:
        model = Drug
        fields = [
            'id', 'name', 'generic_name', 'strength', 'category_name',
            'total_inventory', 'low_stock_items', 'expired_items'
        ]
    
    def get_total_inventory(self, obj):
        return sum(inv.quantity_on_hand for inv in obj.inventory.filter(is_active=True))
    
    def get_low_stock_items(self, obj):
        return obj.inventory.filter(
            quantity_on_hand__lte=obj.reorder_level,
            is_active=True
        ).count()
    
    def get_expired_items(self, obj):
        from django.utils import timezone
        return obj.inventory.filter(
            expiration_date__lt=timezone.now().date(),
            is_active=True
        ).count()


class PrescriptionSummarySerializer(serializers.ModelSerializer):
    """Summary serializer for prescription dashboard"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    provider_name = serializers.CharField(source='provider.get_full_name', read_only=True)
    drug_name = serializers.CharField(source='drug.name', read_only=True)
    
    class Meta:
        model = Prescription
        fields = [
            'id', 'patient_name', 'provider_name', 'drug_name',
            'prescribed_date', 'status', 'refills_remaining'
        ]
