from rest_framework import serializers
from .models import ReportTemplate, ReportExecution, ScheduledReport, ReportFavorite
from django.contrib.auth.models import User


class ReportTemplateSerializer(serializers.ModelSerializer):
    """Report template serializer"""
    executions_count = serializers.SerializerMethodField()
    last_execution = serializers.SerializerMethodField()
    
    class Meta:
        model = ReportTemplate
        fields = [
            'id', 'name', 'description', 'report_type',
            'supports_pdf', 'supports_excel', 'supports_csv',
            'is_public', 'is_active', 'created_at', 'updated_at',
            'executions_count', 'last_execution'
        ]
    
    def get_executions_count(self, obj):
        return obj.executions.count()
    
    def get_last_execution(self, obj):
        last_exec = obj.executions.order_by('-created_at').first()
        if last_exec:
            return last_exec.created_at
        return None


class ReportTemplateDetailSerializer(serializers.ModelSerializer):
    """Detailed report template serializer"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    recent_executions = serializers.SerializerMethodField()
    
    class Meta:
        model = ReportTemplate
        fields = [
            'id', 'name', 'description', 'report_type',
            'sql_query', 'filters_config', 'columns_config',
            'supports_pdf', 'supports_excel', 'supports_csv',
            'is_public', 'is_active', 'created_at', 'updated_at',
            'created_by_name', 'recent_executions'
        ]
    
    def get_recent_executions(self, obj):
        recent = obj.executions.order_by('-created_at')[:5]
        return ReportExecutionSerializer(recent, many=True).data


class ReportExecutionSerializer(serializers.ModelSerializer):
    """Report execution serializer"""
    template_name = serializers.CharField(source='template.name', read_only=True)
    executed_by_name = serializers.CharField(source='executed_by.get_full_name', read_only=True)
    duration_seconds = serializers.SerializerMethodField()
    
    class Meta:
        model = ReportExecution
        fields = [
            'id', 'template', 'template_name', 'executed_by', 'executed_by_name',
            'parameters', 'status', 'started_at', 'completed_at',
            'execution_time', 'duration_seconds', 'result_count',
            'error_message', 'output_format', 'file_size', 'created_at'
        ]
    
    def get_duration_seconds(self, obj):
        if obj.execution_time:
            return obj.execution_time.total_seconds()
        return None


class ReportExecutionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating report executions"""
    
    class Meta:
        model = ReportExecution
        fields = [
            'template', 'parameters', 'output_format'
        ]


class ScheduledReportSerializer(serializers.ModelSerializer):
    """Scheduled report serializer"""
    template_name = serializers.CharField(source='template.name', read_only=True)
    scheduled_by_name = serializers.CharField(source='scheduled_by.get_full_name', read_only=True)
    
    class Meta:
        model = ScheduledReport
        fields = [
            'id', 'template', 'template_name', 'scheduled_by', 'scheduled_by_name',
            'name', 'description', 'frequency', 'schedule_time',
            'day_of_week', 'day_of_month', 'parameters', 'output_format',
            'email_recipients', 'email_subject', 'is_enabled',
            'last_execution', 'next_execution', 'created_at'
        ]


class ReportFavoriteSerializer(serializers.ModelSerializer):
    """Report favorite serializer"""
    template_name = serializers.CharField(source='template.name', read_only=True)
    template_type = serializers.CharField(source='template.report_type', read_only=True)
    
    class Meta:
        model = ReportFavorite
        fields = [
            'id', 'template', 'template_name', 'template_type',
            'custom_name', 'saved_parameters', 'created_at'
        ]


class ReportStatsSerializer(serializers.Serializer):
    """Report statistics serializer"""
    total_templates = serializers.IntegerField()
    total_executions = serializers.IntegerField()
    executions_today = serializers.IntegerField()
    executions_this_week = serializers.IntegerField()
    executions_this_month = serializers.IntegerField()
    
    popular_reports = serializers.ListField(
        child=serializers.DictField(), 
        read_only=True
    )
    recent_executions = serializers.ListField(
        child=serializers.DictField(), 
        read_only=True
    )
    execution_status_summary = serializers.ListField(
        child=serializers.DictField(), 
        read_only=True
    )


class PatientListReportSerializer(serializers.Serializer):
    """Patient list report parameters"""
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    provider_id = serializers.UUIDField(required=False)
    facility_id = serializers.UUIDField(required=False)
    insurance_provider_id = serializers.UUIDField(required=False)
    age_range_min = serializers.IntegerField(required=False, min_value=0)
    age_range_max = serializers.IntegerField(required=False, min_value=0)
    gender = serializers.ChoiceField(choices=[('M', 'Male'), ('F', 'Female')], required=False)
    include_inactive = serializers.BooleanField(default=False)


class AppointmentReportSerializer(serializers.Serializer):
    """Appointment report parameters"""
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    provider_id = serializers.UUIDField(required=False)
    facility_id = serializers.UUIDField(required=False)
    appointment_type = serializers.CharField(required=False)
    status = serializers.CharField(required=False)
    include_cancelled = serializers.BooleanField(default=False)


class FinancialReportSerializer(serializers.Serializer):
    """Financial report parameters"""
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    provider_id = serializers.UUIDField(required=False)
    facility_id = serializers.UUIDField(required=False)
    payment_method = serializers.CharField(required=False)
    insurance_provider_id = serializers.UUIDField(required=False)
    include_adjustments = serializers.BooleanField(default=True)
    group_by = serializers.ChoiceField(
        choices=[
            ('day', 'Daily'),
            ('week', 'Weekly'),
            ('month', 'Monthly'),
            ('provider', 'By Provider'),
            ('facility', 'By Facility')
        ],
        default='month'
    )
