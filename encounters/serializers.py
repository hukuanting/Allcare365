from rest_framework import serializers
from .models import Encounter, EncounterForm, EncounterDiagnosis
from patients.serializers import PatientSerializer


class EncounterDiagnosisSerializer(serializers.ModelSerializer):
    class Meta:
        model = EncounterDiagnosis
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'updated_by']


class EncounterFormSerializer(serializers.ModelSerializer):
    class Meta:
        model = EncounterForm
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'updated_by']


class EncounterSerializer(serializers.ModelSerializer):
    patient_info = PatientSerializer(source='patient', read_only=True)
    provider_name = serializers.CharField(source='provider.get_full_name', read_only=True)
    bmi = serializers.ReadOnlyField()
    blood_pressure = serializers.ReadOnlyField()
    diagnoses = EncounterDiagnosisSerializer(many=True, read_only=True)
    forms = EncounterFormSerializer(many=True, read_only=True)
    
    class Meta:
        model = Encounter
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'updated_by']
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        validated_data['updated_by'] = self.context['request'].user
        return super().update(instance, validated_data)


class EncounterListSerializer(serializers.ModelSerializer):
    """Simplified serializer for list views"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    provider_name = serializers.CharField(source='provider.get_full_name', read_only=True)
    
    class Meta:
        model = Encounter
        fields = [
            'id', 'patient', 'patient_name', 'provider', 'provider_name',
            'encounter_date', 'reason', 'status', 'chief_complaint'
        ]
