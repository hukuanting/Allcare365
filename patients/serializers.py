from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Patient, PatientAllergy, PatientMedication, PatientVitals, PatientNote


class UserSerializer(serializers.ModelSerializer):
    """Simple user serializer for provider information"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'full_name']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()


class PatientSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    age = serializers.ReadOnlyField()
    
    class Meta:
        model = Patient
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate_date_of_birth(self, value):
        """Validate date of birth is not in the future"""
        from datetime import date
        if value > date.today():
            raise serializers.ValidationError("出生日期不能是未來日期")
        return value

    def validate_phone_mobile(self, value):
        """Validate phone number format"""
        if value and not value.replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '').isdigit():
            raise serializers.ValidationError("請輸入有效的電話號碼")
        return value

    def validate_medical_record_number(self, value):
        """Validate medical record number uniqueness"""
        if value:
            # 檢查是否與現有活躍患者重複（排除當前患者）
            existing_patient = Patient.objects.filter(
                medical_record_number=value,
                is_active=True  # 只檢查活躍患者
            )
            
            # 如果是更新操作，排除當前患者
            if self.instance:
                existing_patient = existing_patient.exclude(id=self.instance.id)
            
            if existing_patient.exists():
                # 不拋出錯誤，而是在 create/update 方法中處理
                pass
        return value

    def create(self, validated_data):
        """創建患者，自動處理病歷號重複問題"""
        # 讓模型的 save 方法處理病歷號重複問題
        patient = Patient(**validated_data)
        patient.save()
        return patient

    def update(self, instance, validated_data):
        """更新患者，自動處理病歷號重複問題"""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class PatientAllergySerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    
    class Meta:
        model = PatientAllergy
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate(self, data):
        """Validate that the allergy doesn't already exist for this patient"""
        if self.instance is None:  # Only check for new instances
            existing = PatientAllergy.objects.filter(
                patient=data['patient'],
                allergen__iexact=data['allergen'],
                is_active=True
            ).exists()
            if existing:
                raise serializers.ValidationError("This allergy already exists for this patient")
        return data


class PatientMedicationSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    prescribing_physician_name = serializers.CharField(source='prescribing_physician.user.get_full_name', read_only=True)
    
    class Meta:
        model = PatientMedication
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate(self, data):
        """Validate medication dates"""
        if data.get('end_date') and data.get('start_date'):
            if data['end_date'] < data['start_date']:
                raise serializers.ValidationError("End date cannot be before start date")
        return data


class PatientVitalsSerializer(serializers.ModelSerializer):
    bmi = serializers.ReadOnlyField()
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.get_full_name', read_only=True)
    
    class Meta:
        model = PatientVitals
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate(self, data):
        """Validate vital signs values"""
        if data.get('blood_pressure_systolic') and data.get('blood_pressure_diastolic'):
            if data['blood_pressure_systolic'] <= data['blood_pressure_diastolic']:
                raise serializers.ValidationError("Systolic BP must be higher than diastolic BP")
        
        if data.get('height') and data['height'] <= 0:
            raise serializers.ValidationError("Height must be positive")
        
        if data.get('weight') and data['weight'] <= 0:
            raise serializers.ValidationError("Weight must be positive")
            
        return data


class PatientNoteSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    
    class Meta:
        model = PatientNote
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at', 'date_created')


class PatientSummarySerializer(serializers.ModelSerializer):
    """Simplified patient serializer for lists"""
    full_name = serializers.ReadOnlyField()
    age = serializers.ReadOnlyField()
    primary_care_physician_name = serializers.CharField(source='primary_care_physician.user.get_full_name', read_only=True)
    
    class Meta:
        model = Patient
        fields = [
            'id', 'medical_record_number', 'full_name', 'age', 'gender', 
            'phone_mobile', 'email', 'primary_care_physician_name', 
            'date_of_birth', 'is_active'
        ]


class PatientDetailSerializer(PatientSerializer):
    """Detailed patient serializer with related data"""
    allergies = PatientAllergySerializer(many=True, read_only=True)
    current_medications = serializers.SerializerMethodField()
    recent_vitals = serializers.SerializerMethodField()
    recent_notes = serializers.SerializerMethodField()
    primary_care_physician_name = serializers.CharField(source='primary_care_physician.user.get_full_name', read_only=True)
    
    class Meta(PatientSerializer.Meta):
        fields = '__all__'
    
    def get_current_medications(self, obj):
        """Get current medications for patient"""
        current_meds = obj.medications.filter(is_current=True, is_active=True)
        return PatientMedicationSerializer(current_meds, many=True).data
    
    def get_recent_vitals(self, obj):
        """Get recent vitals for patient"""
        recent = obj.vitals.filter(is_active=True).order_by('-measurement_date')[:5]
        return PatientVitalsSerializer(recent, many=True).data
    
    def get_recent_notes(self, obj):
        """Get recent notes for patient"""
        recent = obj.notes.filter(is_active=True).order_by('-date_created')[:5]
        return PatientNoteSerializer(recent, many=True).data
