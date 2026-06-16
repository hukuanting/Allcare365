from rest_framework import serializers
from django.utils import timezone
from datetime import datetime, timedelta
from .models import (
    AppointmentType, Appointment, WaitingList, 
    RecurringAppointment, AppointmentNote
)
from patients.models import Patient
from administration.models import Provider, Facility


class AppointmentTypeSerializer(serializers.ModelSerializer):
    """預約類型序列化器"""
    
    class Meta:
        model = AppointmentType
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class AppointmentSerializer(serializers.ModelSerializer):
    """預約序列化器"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    provider_name = serializers.CharField(source='provider.full_name', read_only=True)
    facility_name = serializers.CharField(source='facility.name', read_only=True)
    appointment_type_name = serializers.CharField(source='appointment_type.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Appointment
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def validate(self, data):
        """驗證預約資料"""
        # 檢查預約時間是否在未來
        if data.get('appointment_date') and data['appointment_date'] < timezone.now().date():
            raise serializers.ValidationError("預約時間不能在過去")
        
        # 檢查預約衝突
        if self.instance:
            # 更新時排除自己
            conflicting_appointments = Appointment.objects.filter(
                provider=data.get('provider', self.instance.provider),
                appointment_date=data.get('appointment_date', self.instance.appointment_date),
                status__in=['scheduled', 'confirmed']
            ).exclude(id=self.instance.id)
        else:
            # 新建時檢查
            conflicting_appointments = Appointment.objects.filter(
                provider=data.get('provider'),
                appointment_date=data.get('appointment_date'),
                status__in=['scheduled', 'confirmed']
            )
        
        if conflicting_appointments.exists():
            raise serializers.ValidationError("該時間段已有預約")
        
        return data


class AppointmentSummarySerializer(serializers.ModelSerializer):
    """預約摘要序列化器"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    provider_name = serializers.CharField(source='provider.full_name', read_only=True)
    appointment_type_name = serializers.CharField(source='appointment_type.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'patient_name', 'provider_name', 'appointment_type_name',
            'appointment_date', 'duration_minutes', 'status', 'status_display',
            'patient', 'provider', 'appointment_type'
        ]


class AppointmentWaitingListSerializer(serializers.ModelSerializer):
    """候補名單序列化器"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    provider_name = serializers.CharField(source='provider.full_name', read_only=True)
    appointment_type_name = serializers.CharField(source='appointment_type.name', read_only=True)
    
    class Meta:
        model = WaitingList
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class RecurringAppointmentSerializer(serializers.ModelSerializer):
    """重複預約序列化器"""
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    provider_name = serializers.CharField(source='provider.full_name', read_only=True)
    appointment_type_name = serializers.CharField(source='appointment_type.name', read_only=True)
    
    class Meta:
        model = RecurringAppointment
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def validate(self, data):
        """驗證重複預約資料"""
        if data.get('end_date') and data.get('start_date'):
            if data['end_date'] <= data['start_date']:
                raise serializers.ValidationError("結束日期必須晚於開始日期")
        
        if data.get('occurrences') and data['occurrences'] <= 0:
            raise serializers.ValidationError("重複次數必須大於0")
        
        return data


class AppointmentNoteSerializer(serializers.ModelSerializer):
    """預約筆記序列化器"""
    author_name = serializers.SerializerMethodField()
    
    class Meta:
        model = AppointmentNote
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'author')
    
    def get_author_name(self, obj):
        if obj.author:
            return f"{obj.author.first_name} {obj.author.last_name}".strip()
        return "Unknown"


class AppointmentDetailSerializer(serializers.ModelSerializer):
    """預約詳細序列化器"""
    patient = serializers.StringRelatedField(read_only=True)
    provider = serializers.StringRelatedField(read_only=True)
    facility = serializers.StringRelatedField(read_only=True)
    appointment_type = AppointmentTypeSerializer(read_only=True)
    notes = AppointmentNoteSerializer(many=True, read_only=True)
    
    class Meta:
        model = Appointment
        fields = '__all__'


class AppointmentCalendarSerializer(serializers.ModelSerializer):
    """預約日曆序列化器"""
    title = serializers.SerializerMethodField()
    start = serializers.DateTimeField(source='appointment_date')
    end = serializers.SerializerMethodField()
    color = serializers.SerializerMethodField()
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'title', 'start', 'end', 'color',
            'status', 'patient', 'provider'
        ]
    
    def get_title(self, obj):
        return f"{obj.patient.get_full_name()} - {obj.appointment_type.name}"
    
    def get_end(self, obj):
        return obj.appointment_date + timedelta(minutes=obj.duration)
    
    def get_color(self, obj):
        color_map = {
            'scheduled': '#007bff',
            'confirmed': '#28a745',
            'checked_in': '#ffc107',
            'in_progress': '#17a2b8',
            'completed': '#6c757d',
            'cancelled': '#dc3545',
            'no_show': '#fd7e14'
        }
        return color_map.get(obj.status, '#007bff')


class AppointmentStatisticsSerializer(serializers.Serializer):
    """預約統計序列化器"""
    total_appointments = serializers.IntegerField()
    scheduled_appointments = serializers.IntegerField()
    confirmed_appointments = serializers.IntegerField()
    completed_appointments = serializers.IntegerField()
    cancelled_appointments = serializers.IntegerField()
    no_show_appointments = serializers.IntegerField()
    appointment_types = serializers.ListField()
    providers = serializers.ListField()
    daily_stats = serializers.ListField()
    monthly_stats = serializers.ListField()
