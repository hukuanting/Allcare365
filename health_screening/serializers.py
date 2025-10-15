from rest_framework import serializers
from .models import (
    HealthScreening, VitalSigns, LaboratoryResults, 
    CardiovascularRiskIndex, MedicalHistory, LifestyleQuestionnaire
)
from patients.models import Patient
from . import risk_calculators


class VitalSignsSerializer(serializers.ModelSerializer):
    class Meta:
        model = VitalSigns
        exclude = ['health_screening']


class LaboratoryResultsSerializer(serializers.ModelSerializer):
    class Meta:
        model = LaboratoryResults
        exclude = ['health_screening']


class CardiovascularRiskIndexSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardiovascularRiskIndex
        exclude = ['health_screening']


class MedicalHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalHistory
        exclude = ['health_screening']


class LifestyleQuestionnaireSerializer(serializers.ModelSerializer):
    class Meta:
        model = LifestyleQuestionnaire
        exclude = ['health_screening']


class HealthScreeningSerializer(serializers.ModelSerializer):
    vital_signs = VitalSignsSerializer(required=False)
    laboratory_results = LaboratoryResultsSerializer(required=False)
    cardiovascular_risk = CardiovascularRiskIndexSerializer(required=False)
    medical_history = MedicalHistorySerializer(required=False)
    lifestyle = LifestyleQuestionnaireSerializer(required=False)
    
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    provider_name = serializers.CharField(source='provider.get_full_name', read_only=True)
    patient_medical_record_number = serializers.CharField(source='patient.medical_record_number', read_only=True)
    
    class Meta:
        model = HealthScreening
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def to_representation(self, instance):
        """確保 age_at_screening 被正確計算和序列化"""
        representation = super().to_representation(instance)
        
        # 如果 age_at_screening 為空，嘗試計算
        if not representation.get('age_at_screening') and instance.patient and instance.patient.date_of_birth:
            screening_year = instance.screening_date.year
            birth_year = instance.patient.date_of_birth.year
            age = screening_year - birth_year
            
            # 檢查是否還沒過生日
            if (instance.screening_date.month, instance.screening_date.day) < (instance.patient.date_of_birth.month, instance.patient.date_of_birth.day):
                age -= 1
            
            representation['age_at_screening'] = age
            
            # 同時更新數據庫記錄
            if instance.age_at_screening != age:
                instance.age_at_screening = age
                instance.save(update_fields=['age_at_screening'])
        
        return representation
    
    def create(self, validated_data):
        # Extract nested data
        vital_signs_data = validated_data.pop('vital_signs', {})
        laboratory_data = validated_data.pop('laboratory_results', {})
        cardiovascular_data = validated_data.pop('cardiovascular_risk', {})
        medical_history_data = validated_data.pop('medical_history', {})
        lifestyle_data = validated_data.pop('lifestyle', {})
        
        # Create main screening record
        health_screening = HealthScreening.objects.create(**validated_data)
        
        # Create related records if data provided
        if vital_signs_data:
            VitalSigns.objects.create(health_screening=health_screening, **vital_signs_data)
        
        if laboratory_data:
            LaboratoryResults.objects.create(health_screening=health_screening, **laboratory_data)
        
        if cardiovascular_data:
            CardiovascularRiskIndex.objects.create(health_screening=health_screening, **cardiovascular_data)
        
        if medical_history_data:
            MedicalHistory.objects.create(health_screening=health_screening, **medical_history_data)
        
        if lifestyle_data:
            LifestyleQuestionnaire.objects.create(health_screening=health_screening, **lifestyle_data)

        # 計算並儲存心血管風險
        self._calculate_and_save_cardiovascular_risk(health_screening)
        
        return health_screening

    def _calculate_and_save_cardiovascular_risk(self, health_screening):
        patient = health_screening.patient
        vital_signs = getattr(health_screening, 'vital_signs', None)
        laboratory_results = getattr(health_screening, 'laboratory_results', None)
        medical_history = getattr(health_screening, 'medical_history', None)
        lifestyle = getattr(health_screening, 'lifestyle', None)

        # 提取計算所需的數據，安全處理 None 值
        age = patient.age if patient.age is not None else 50
        gender = patient.gender if patient.gender is not None else 'M'
        TC = laboratory_results.total_cholesterol_mgdl if laboratory_results and laboratory_results.total_cholesterol_mgdl is not None else 200.0
        HDL = laboratory_results.hdl_cholesterol_mgdl if laboratory_results and laboratory_results.hdl_cholesterol_mgdl is not None else 50.0
        SBP = vital_signs.systolic_bp_mmhg if vital_signs and vital_signs.systolic_bp_mmhg is not None else 120
        
        # 計算 eGFR 或使用預設值
        if laboratory_results and laboratory_results.urine_creatinine_mgdl is not None:
            creatinine = laboratory_results.urine_creatinine_mgdl
            eGFR = risk_calculators.calculate_egfr(creatinine, age, gender)
        else:
            eGFR = 90.0  # 預設正常 eGFR 值
            
        # 計算 BMI 或使用預設值
        if vital_signs and vital_signs.height_cm is not None and vital_signs.weight_kg is not None:
            height_m = vital_signs.height_cm / 100
            BMI = vital_signs.weight_kg / (height_m ** 2)
        elif vital_signs and vital_signs.bmi is not None:
            BMI = vital_signs.bmi
        else:
            BMI = 23.0  # 預設正常 BMI 值

        # 將布林值轉換為 0 或 1 - has_diabetes 在 lifestyle 中，不在 medical_history 中，安全處理 None 值
        diabetes = 1 if lifestyle and hasattr(lifestyle, 'has_diabetes') and lifestyle.has_diabetes is not None and lifestyle.has_diabetes else 0
        current_smoker = 1 if lifestyle and hasattr(lifestyle, 'is_current_smoker') and lifestyle.is_current_smoker is not None and lifestyle.is_current_smoker else 0
        anti_hyp_med = 1 if medical_history and hasattr(medical_history, 'hypertension_treated') and medical_history.hypertension_treated is not None and medical_history.hypertension_treated else 0
        statin = 0 # 假設沒有statin的數據，暫時設為0

        # 現在所有參數都有預設值，不需要檢查 None
        print(f"計算風險參數: age={age}, gender={gender}, TC={TC}, HDL={HDL}, SBP={SBP}, eGFR={eGFR}, BMI={BMI}")
        print(f"疾病史參數: diabetes={diabetes}, current_smoker={current_smoker}, anti_hyp_med={anti_hyp_med}, statin={statin}")

        # 根據性別呼叫不同的演算法
        cvd_10_year_risk = None
        ascvd_10_year_risk = None
        hf_10_year_risk = None

        if gender == 'F': # 女性
            cvd_10_year_risk = risk_calculators.women_cvd_10(age, TC, HDL, SBP, eGFR, diabetes, current_smoker, anti_hyp_med, statin)
            ascvd_10_year_risk = risk_calculators.women_ascvd_10(age, TC, HDL, SBP, eGFR, diabetes, current_smoker, anti_hyp_med, statin)
            hf_10_year_risk = risk_calculators.women_hf_10(age, SBP, BMI, eGFR, diabetes, current_smoker, anti_hyp_med)
        elif gender == 'M': # 男性
            cvd_10_year_risk = risk_calculators.man_cvd_10(age, TC, HDL, SBP, eGFR, diabetes, current_smoker, anti_hyp_med, statin)
            ascvd_10_year_risk = risk_calculators.man_ascvd_10(age, TC, HDL, SBP, eGFR, diabetes, current_smoker, anti_hyp_med, statin)
            hf_10_year_risk = risk_calculators.man_hf_10(age, SBP, BMI, eGFR, diabetes, current_smoker, anti_hyp_med)

        # 更新 CardiovascularRiskIndex 實例
        cardiovascular_risk, created = CardiovascularRiskIndex.objects.get_or_create(
            health_screening=health_screening,
            defaults={
                'cvd_10_year_risk_women': cvd_10_year_risk if gender == 'F' else None,
                'cvd_10_year_risk_men': cvd_10_year_risk if gender == 'M' else None,
                'ascvd_10_year_risk_women': ascvd_10_year_risk if gender == 'F' else None,
                'ascvd_10_year_risk_men': ascvd_10_year_risk if gender == 'M' else None,
                'hf_10_year_risk_women': hf_10_year_risk if gender == 'F' else None,
                'hf_10_year_risk_men': hf_10_year_risk if gender == 'M' else None,
            }
        )
        if not created:
            if gender == 'F':
                cardiovascular_risk.cvd_10_year_risk_women = cvd_10_year_risk
                cardiovascular_risk.ascvd_10_year_risk_women = ascvd_10_year_risk
                cardiovascular_risk.hf_10_year_risk_women = hf_10_year_risk
            elif gender == 'M':
                cardiovascular_risk.cvd_10_year_risk_men = cvd_10_year_risk
                cardiovascular_risk.ascvd_10_year_risk_men = ascvd_10_year_risk
                cardiovascular_risk.hf_10_year_risk_men = hf_10_year_risk
            cardiovascular_risk.save()

    def update(self, instance, validated_data):
        # Extract nested data
        vital_signs_data = validated_data.pop('vital_signs', None)
        laboratory_data = validated_data.pop('laboratory_results', None)
        cardiovascular_data = validated_data.pop('cardiovascular_risk', None)
        medical_history_data = validated_data.pop('medical_history', None)
        lifestyle_data = validated_data.pop('lifestyle', None)
        
        # Update main screening record
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update or create related records
        if vital_signs_data is not None:
            vital_signs, created = VitalSigns.objects.get_or_create(
                health_screening=instance,
                defaults=vital_signs_data
            )
            if not created:
                for attr, value in vital_signs_data.items():
                    setattr(vital_signs, attr, value)
                vital_signs.save()
        
        if laboratory_data is not None:
            laboratory, created = LaboratoryResults.objects.get_or_create(
                health_screening=instance,
                defaults=laboratory_data
            )
            if not created:
                for attr, value in laboratory_data.items():
                    setattr(laboratory, attr, value)
                laboratory.save()
        
        if cardiovascular_data is not None:
            cardiovascular, created = CardiovascularRiskIndex.objects.get_or_create(
                health_screening=instance,
                defaults=cardiovascular_data
            )
            if not created:
                for attr, value in cardiovascular_data.items():
                    setattr(cardiovascular, attr, value)
                cardiovascular.save()
        
        if medical_history_data is not None:
            medical_history, created = MedicalHistory.objects.get_or_create(
                health_screening=instance,
                defaults=medical_history_data
            )
            if not created:
                for attr, value in medical_history_data.items():
                    setattr(medical_history, attr, value)
                medical_history.save()
        
        if lifestyle_data is not None:
            lifestyle, created = LifestyleQuestionnaire.objects.get_or_create(
                health_screening=instance,
                defaults=lifestyle_data
            )
            if not created:
                for attr, value in lifestyle_data.items():
                    setattr(lifestyle, attr, value)
                lifestyle.save()
        
        # 計算並儲存心血管風險
        self._calculate_and_save_cardiovascular_risk(instance)
        
        return instance


class HealthScreeningListSerializer(serializers.ModelSerializer):
    """簡化的列表序列化器"""
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    provider_name = serializers.CharField(source='provider.get_full_name', read_only=True)
    
    class Meta:
        model = HealthScreening
        fields = ['id', 'patient', 'patient_name', 'provider', 'provider_name', 
                 'screening_date', 'screening_type', 'age_at_screening']


class BulkHealthScreeningSerializer(serializers.Serializer):
    """批量匯入序列化器"""
    screenings = HealthScreeningSerializer(many=True)
    
    def create(self, validated_data):
        screenings_data = validated_data['screenings']
        created_screenings = []
        
        for screening_data in screenings_data:
            serializer = HealthScreeningSerializer(data=screening_data)
            if serializer.is_valid():
                screening = serializer.save()
                created_screenings.append(screening)
            else:
                raise serializers.ValidationError(serializer.errors)
        
        return {'created_count': len(created_screenings), 'screenings': created_screenings}
