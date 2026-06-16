from rest_framework import serializers
from .models import (
    Patient, FamilyHealthHistory, MedicalDevice, CareTeamMember,
    PatientAllergy, CarePlan, PatientMedication, MedicalOrder,
    InsuranceData, AdvanceDirective, PatientDocument
)

class FamilyHealthHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FamilyHealthHistory
        fields = '__all__'

class MedicalDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalDevice
        fields = '__all__'

class CareTeamMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareTeamMember
        fields = '__all__'

class PatientAllergySerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientAllergy
        fields = '__all__'

class CarePlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarePlan
        fields = '__all__'

class PatientMedicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientMedication
        fields = '__all__'

class MedicalOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalOrder
        fields = '__all__'

class InsuranceDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = InsuranceData
        fields = '__all__'

class AdvanceDirectiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdvanceDirective
        fields = '__all__'

class PatientDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientDocument
        fields = '__all__'

class PatientSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    
    # Nested serializers for read operations (optional, can be heavy)
    care_team = CareTeamMemberSerializer(many=True, read_only=True)
    allergies = PatientAllergySerializer(many=True, read_only=True)
    care_plans = CarePlanSerializer(many=True, read_only=True)
    medications = PatientMedicationSerializer(many=True, read_only=True)
    medical_orders = MedicalOrderSerializer(many=True, read_only=True)
    insurance_info = InsuranceDataSerializer(many=True, read_only=True)
    advance_directives = AdvanceDirectiveSerializer(many=True, read_only=True)
    family_history = FamilyHealthHistorySerializer(many=True, read_only=True)
    medical_devices = MedicalDeviceSerializer(many=True, read_only=True)
    clinical_notes = PatientDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Patient
        fields = [
            'id', 'medical_record_number', 'first_name', 'last_name', 'middle_name',
            'full_name', 'date_of_birth', 'age', 'sex', 'status', 
            'current_address_line1', 'city', 'state', 'phone_number', 'email_address',
            'care_team', 'allergies', 'care_plans', 'medications', 'medical_orders',
            'insurance_info', 'advance_directives', 'family_history', 'medical_devices',
            'clinical_notes'
        ]

    def get_full_name(self, obj):
        return f"{obj.last_name}{obj.first_name}"

    def get_age(self, obj):
        if obj.date_of_birth:
            from django.utils import timezone
            today = timezone.now().date()
            return today.year - obj.date_of_birth.year - ((today.month, today.day) < (obj.date_of_birth.month, obj.date_of_birth.day))
        return None