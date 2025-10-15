from rest_framework import serializers
from .models import (
    VaccineManufacturer, Vaccine, VaccineLot, ImmunizationSchedule,
    ScheduledVaccination, Immunization, ImmunizationObservation,
    ImmunizationContraindication, PatientImmunizationAlert
)
from patients.models import Patient
from django.contrib.auth.models import User


class VaccineManufacturerSerializer(serializers.ModelSerializer):
    """Vaccine manufacturer serializer"""
    
    class Meta:
        model = VaccineManufacturer
        fields = ['id', 'uuid', 'name', 'code', 'is_active', 'create_date', 'update_date']
        read_only_fields = ['uuid', 'create_date', 'update_date']


class VaccineSerializer(serializers.ModelSerializer):
    """Vaccine serializer"""
    manufacturer_name = serializers.CharField(source='manufacturer.name', read_only=True)
    
    class Meta:
        model = Vaccine
        fields = [
            'id', 'uuid', 'cvx_code', 'name', 'short_name', 'manufacturer', 
            'manufacturer_name', 'vaccine_type', 'is_active', 'min_age_days',
            'max_age_days', 'doses_required', 'interval_days', 'storage_temp_min',
            'storage_temp_max', 'create_date', 'update_date'
        ]
        read_only_fields = ['uuid', 'create_date', 'update_date']


class VaccineLotSerializer(serializers.ModelSerializer):
    """Vaccine lot serializer"""
    vaccine_name = serializers.CharField(source='vaccine.name', read_only=True)
    manufacturer_name = serializers.CharField(source='manufacturer.name', read_only=True)
    quantity_available = serializers.IntegerField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = VaccineLot
        fields = [
            'id', 'uuid', 'vaccine', 'vaccine_name', 'lot_number', 
            'manufacturer', 'manufacturer_name', 'expiration_date',
            'quantity_received', 'quantity_used', 'quantity_wasted',
            'quantity_available', 'is_expired', 'storage_location',
            'create_date', 'update_date'
        ]
        read_only_fields = ['uuid', 'create_date', 'update_date']


class ScheduledVaccinationSerializer(serializers.ModelSerializer):
    """Scheduled vaccination serializer"""
    vaccine_name = serializers.CharField(source='vaccine.name', read_only=True)
    
    class Meta:
        model = ScheduledVaccination
        fields = [
            'id', 'uuid', 'schedule', 'vaccine', 'vaccine_name', 
            'dose_number', 'recommended_age_days', 'earliest_age_days',
            'latest_age_days', 'create_date', 'update_date'
        ]
        read_only_fields = ['uuid', 'create_date', 'update_date']


class ImmunizationScheduleSerializer(serializers.ModelSerializer):
    """Immunization schedule serializer"""
    vaccinations = ScheduledVaccinationSerializer(many=True, read_only=True)
    
    class Meta:
        model = ImmunizationSchedule
        fields = [
            'id', 'uuid', 'name', 'description', 'age_group', 
            'is_active', 'vaccinations', 'create_date', 'update_date'
        ]
        read_only_fields = ['uuid', 'create_date', 'update_date']


class ImmunizationObservationSerializer(serializers.ModelSerializer):
    """Immunization observation serializer"""
    
    class Meta:
        model = ImmunizationObservation
        fields = [
            'id', 'uuid', 'immunization', 'observation_type', 
            'observation_date', 'severity', 'description', 'action_taken',
            'outcome', 'reported_to_vaers', 'vaers_id', 'create_date', 'update_date'
        ]
        read_only_fields = ['uuid', 'create_date', 'update_date']


class ImmunizationSerializer(serializers.ModelSerializer):
    """Immunization serializer"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    vaccine_name = serializers.CharField(source='vaccine.name', read_only=True)
    vaccine_cvx_code = serializers.CharField(source='vaccine.cvx_code', read_only=True)
    lot_number = serializers.CharField(source='vaccine_lot.lot_number', read_only=True)
    administered_by_name = serializers.CharField(source='administered_by.get_full_name', read_only=True)
    ordering_provider_name = serializers.CharField(source='ordering_provider.get_full_name', read_only=True)
    observations = ImmunizationObservationSerializer(many=True, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Immunization
        fields = [
            'id', 'uuid', 'patient', 'patient_name', 'vaccine', 'vaccine_name',
            'vaccine_cvx_code', 'vaccine_lot', 'lot_number', 'administered_date',
            'administered_by', 'administered_by_name', 'amount_administered',
            'amount_administered_unit', 'dose_number', 'route', 'administration_site',
            'vis_date', 'education_date', 'note', 'completion_status',
            'information_source', 'refusal_reason', 'ordering_provider',
            'ordering_provider_name', 'reason_code', 'reason_description',
            'added_erroneously', 'external_id', 'observations', 'is_overdue',
            'create_date', 'update_date'
        ]
        read_only_fields = ['uuid', 'create_date', 'update_date']
    
    def validate(self, data):
        """Validate immunization data"""
        # Check if vaccine lot is expired
        if data.get('vaccine_lot') and data['vaccine_lot'].is_expired:
            raise serializers.ValidationError("Cannot administer expired vaccine lot")
        
        # Check if completion status is refused but no refusal reason
        if data.get('completion_status') == 'refused' and not data.get('refusal_reason'):
            raise serializers.ValidationError("Refusal reason is required when completion status is refused")
        
        return data


class ImmunizationCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for creating immunizations"""
    
    class Meta:
        model = Immunization
        fields = [
            'patient', 'vaccine', 'vaccine_lot', 'administered_date',
            'administered_by', 'amount_administered', 'amount_administered_unit',
            'dose_number', 'route', 'administration_site', 'vis_date',
            'education_date', 'note', 'completion_status', 'information_source',
            'refusal_reason', 'ordering_provider', 'reason_code', 'reason_description'
        ]


class ImmunizationContraindicationSerializer(serializers.ModelSerializer):
    """Immunization contraindication serializer"""
    vaccine_name = serializers.CharField(source='vaccine.name', read_only=True)
    
    class Meta:
        model = ImmunizationContraindication
        fields = [
            'id', 'uuid', 'vaccine', 'vaccine_name', 'contraindication_type',
            'description', 'is_permanent', 'severity', 'create_date', 'update_date'
        ]
        read_only_fields = ['uuid', 'create_date', 'update_date']


class PatientImmunizationAlertSerializer(serializers.ModelSerializer):
    """Patient immunization alert serializer"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    vaccine_name = serializers.CharField(source='vaccine.name', read_only=True)
    acknowledged_by_name = serializers.CharField(source='acknowledged_by.get_full_name', read_only=True)
    
    class Meta:
        model = PatientImmunizationAlert
        fields = [
            'id', 'uuid', 'patient', 'patient_name', 'vaccine', 'vaccine_name',
            'alert_type', 'alert_date', 'due_date', 'message', 'is_active',
            'acknowledged_by', 'acknowledged_by_name', 'acknowledged_date',
            'create_date', 'update_date'
        ]
        read_only_fields = ['uuid', 'create_date', 'update_date']


class PatientImmunizationHistorySerializer(serializers.ModelSerializer):
    """Patient immunization history serializer"""
    immunizations = ImmunizationSerializer(many=True, read_only=True)
    alerts = PatientImmunizationAlertSerializer(source='immunization_alerts', many=True, read_only=True)
    
    class Meta:
        model = Patient
        fields = ['id', 'first_name', 'last_name', 'date_of_birth', 'immunizations', 'alerts']


class ImmunizationDashboardSerializer(serializers.Serializer):
    """Dashboard summary serializer"""
    total_immunizations = serializers.IntegerField()
    immunizations_today = serializers.IntegerField()
    immunizations_this_week = serializers.IntegerField()
    immunizations_this_month = serializers.IntegerField()
    pending_alerts = serializers.IntegerField()
    expired_lots = serializers.IntegerField()
    low_stock_vaccines = serializers.IntegerField()
    
    # Recent immunizations
    recent_immunizations = ImmunizationSerializer(many=True)
    
    # Upcoming due immunizations
    upcoming_due = PatientImmunizationAlertSerializer(many=True)
    
    # Vaccine usage statistics
    vaccine_usage_stats = serializers.ListField(
        child=serializers.DictField()
    )
