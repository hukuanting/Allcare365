"""
Clinical Decision Support Serializers

Provides API serialization for clinical decision support models.
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    RuleCategory, ClinicalRule, ClinicalAlert, DrugInteraction,
    PreventiveCareReminder, PatientReminder, RuleExecution,
    ClinicalProtocol, ProtocolExecution
)
from patients.models import Patient


class RuleCategorySerializer(serializers.ModelSerializer):
    """Serializer for rule categories"""
    rules_count = serializers.SerializerMethodField()
    
    class Meta:
        model = RuleCategory
        fields = [
            'id', 'name', 'description', 'color', 'icon', 'display_order',
            'is_active', 'created_at', 'updated_at', 'rules_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_rules_count(self, obj):
        return obj.rules.filter(is_active=True).count()


class ClinicalRuleSerializer(serializers.ModelSerializer):
    """Serializer for clinical rules"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    rule_type_display = serializers.CharField(source='get_rule_type_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)
    is_rule_active = serializers.BooleanField(read_only=True)
    alerts_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ClinicalRule
        fields = [
            'id', 'name', 'code', 'category', 'category_name', 'rule_type', 'rule_type_display',
            'description', 'condition_logic', 'action_type', 'action_type_display', 'action_config',
            'severity', 'severity_display', 'priority', 'is_real_time', 'check_frequency_hours',
            'effective_date', 'expiry_date', 'evidence_level', 'reference_url', 'version',
            'is_active', 'is_rule_active', 'created_at', 'updated_at', 'alerts_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_rule_active']
    
    def get_alerts_count(self, obj):
        return obj.alerts.filter(status='active').count()


class ClinicalAlertSerializer(serializers.ModelSerializer):
    """Serializer for clinical alerts"""
    rule_name = serializers.CharField(source='rule.name', read_only=True)
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    alert_level_display = serializers.CharField(source='get_alert_level_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    acknowledged_by_name = serializers.CharField(source='acknowledged_by.get_full_name', read_only=True)
    days_since_triggered = serializers.SerializerMethodField()
    
    class Meta:
        model = ClinicalAlert
        fields = [
            'id', 'rule', 'rule_name', 'patient', 'patient_name', 'encounter',
            'title', 'message', 'alert_level', 'alert_level_display',
            'trigger_data', 'recommended_actions', 'status', 'status_display',
            'acknowledged_by', 'acknowledged_by_name', 'acknowledged_at', 'acknowledgment_note',
            'triggered_at', 'expires_at', 'resolved_at', 'days_since_triggered'
        ]
        read_only_fields = [
            'id', 'triggered_at', 'rule_name', 'patient_name', 'alert_level_display',
            'status_display', 'acknowledged_by_name', 'days_since_triggered'
        ]
    
    def get_days_since_triggered(self, obj):
        from django.utils import timezone
        delta = timezone.now() - obj.triggered_at
        return delta.days


class ClinicalAlertActionSerializer(serializers.Serializer):
    """Serializer for alert actions"""
    action = serializers.ChoiceField(choices=['acknowledge', 'dismiss', 'resolve'])
    note = serializers.CharField(required=False, allow_blank=True)


class DrugInteractionSerializer(serializers.ModelSerializer):
    """Serializer for drug interactions"""
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    
    class Meta:
        model = DrugInteraction
        fields = [
            'id', 'drug_1', 'drug_2', 'interaction_type', 'severity', 'severity_display',
            'mechanism', 'clinical_effect', 'management', 'evidence_level',
            'reference_source', 'reference_url', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'severity_display']


class DrugInteractionCheckSerializer(serializers.Serializer):
    """Serializer for drug interaction checking"""
    medications = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of medication names or codes to check"
    )
    patient_id = serializers.UUIDField(required=False, help_text="Patient ID for context")


class PreventiveCareReminderSerializer(serializers.ModelSerializer):
    """Serializer for preventive care reminders"""
    reminder_type_display = serializers.CharField(source='get_reminder_type_display', read_only=True)
    applicable_patients_count = serializers.SerializerMethodField()
    
    class Meta:
        model = PreventiveCareReminder
        fields = [
            'id', 'name', 'reminder_type', 'reminder_type_display', 'description',
            'target_age_min', 'target_age_max', 'target_gender', 'target_conditions',
            'interval_months', 'lead_time_days', 'guideline_source', 'evidence_grade',
            'is_active', 'created_at', 'updated_at', 'applicable_patients_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'reminder_type_display']
    
    def get_applicable_patients_count(self, obj):
        # This would require complex query logic
        # For now, return 0 as placeholder
        return 0


class PatientReminderSerializer(serializers.ModelSerializer):
    """Serializer for patient reminders"""
    preventive_care_name = serializers.CharField(source='preventive_care.name', read_only=True)
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    completed_by_name = serializers.CharField(source='completed_by.get_full_name', read_only=True)
    days_until_due = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    
    class Meta:
        model = PatientReminder
        fields = [
            'id', 'patient', 'patient_name', 'preventive_care', 'preventive_care_name',
            'due_date', 'last_completed_date', 'next_due_date', 'status', 'status_display',
            'priority', 'completed_by', 'completed_by_name', 'completed_at', 'completion_notes',
            'days_until_due', 'is_overdue', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'preventive_care_name', 'patient_name', 'status_display',
            'completed_by_name', 'days_until_due', 'is_overdue', 'created_at', 'updated_at'
        ]
    
    def get_days_until_due(self, obj):
        from django.utils import timezone
        today = timezone.now().date()
        delta = obj.due_date - today
        return delta.days
    
    def get_is_overdue(self, obj):
        from django.utils import timezone
        return obj.due_date < timezone.now().date() and obj.status in ['pending', 'due']


class PatientReminderActionSerializer(serializers.Serializer):
    """Serializer for patient reminder actions"""
    action = serializers.ChoiceField(choices=['complete', 'dismiss', 'reschedule'])
    notes = serializers.CharField(required=False, allow_blank=True)
    reschedule_date = serializers.DateField(required=False)


class RuleExecutionSerializer(serializers.ModelSerializer):
    """Serializer for rule executions"""
    rule_name = serializers.CharField(source='rule.name', read_only=True)
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = RuleExecution
        fields = [
            'id', 'rule', 'rule_name', 'patient', 'patient_name',
            'executed_at', 'execution_time_ms', 'status', 'status_display',
            'input_data', 'output_data', 'error_message',
            'condition_met', 'alert_generated', 'alert'
        ]
        read_only_fields = [
            'id', 'rule_name', 'patient_name', 'status_display', 'executed_at'
        ]


class ClinicalProtocolSerializer(serializers.ModelSerializer):
    """Serializer for clinical protocols"""
    protocol_type_display = serializers.CharField(source='get_protocol_type_display', read_only=True)
    active_executions_count = serializers.SerializerMethodField()
    total_executions_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ClinicalProtocol
        fields = [
            'id', 'name', 'code', 'protocol_type', 'protocol_type_display', 'description',
            'steps', 'conditions', 'guideline_source', 'evidence_level', 'version',
            'is_active', 'created_at', 'updated_at',
            'active_executions_count', 'total_executions_count'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'protocol_type_display',
            'active_executions_count', 'total_executions_count'
        ]
    
    def get_active_executions_count(self, obj):
        return obj.executions.filter(status='active').count()
    
    def get_total_executions_count(self, obj):
        return obj.executions.count()


class ProtocolExecutionSerializer(serializers.ModelSerializer):
    """Serializer for protocol executions"""
    protocol_name = serializers.CharField(source='protocol.name', read_only=True)
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    started_by_name = serializers.CharField(source='started_by.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    current_step_name = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = ProtocolExecution
        fields = [
            'id', 'protocol', 'protocol_name', 'patient', 'patient_name', 'encounter',
            'started_by', 'started_by_name', 'started_at', 'completed_at',
            'status', 'status_display', 'current_step', 'current_step_name',
            'step_results', 'notes', 'progress_percentage'
        ]
        read_only_fields = [
            'id', 'protocol_name', 'patient_name', 'started_by_name',
            'status_display', 'current_step_name', 'progress_percentage', 'started_at'
        ]
    
    def get_current_step_name(self, obj):
        if obj.protocol.steps and len(obj.protocol.steps) > obj.current_step:
            step = obj.protocol.steps[obj.current_step]
            return step.get('name', f'Step {obj.current_step + 1}')
        return 'Completed'
    
    def get_progress_percentage(self, obj):
        if not obj.protocol.steps:
            return 0
        total_steps = len(obj.protocol.steps)
        if total_steps == 0:
            return 100
        return int((obj.current_step / total_steps) * 100)


class ProtocolExecutionActionSerializer(serializers.Serializer):
    """Serializer for protocol execution actions"""
    action = serializers.ChoiceField(choices=['advance', 'complete', 'cancel', 'suspend'])
    step_result = serializers.JSONField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)


class ClinicalAlertSummarySerializer(serializers.Serializer):
    """Serializer for clinical alert summaries"""
    total_alerts = serializers.IntegerField()
    active_alerts = serializers.IntegerField()
    critical_alerts = serializers.IntegerField()
    high_priority_alerts = serializers.IntegerField()
    acknowledged_alerts = serializers.IntegerField()
    dismissed_alerts = serializers.IntegerField()
    alerts_by_category = serializers.DictField()
    alerts_by_severity = serializers.DictField()
    recent_alerts = ClinicalAlertSerializer(many=True)


class PatientReminderSummarySerializer(serializers.Serializer):
    """Serializer for patient reminder summaries"""
    total_reminders = serializers.IntegerField()
    due_reminders = serializers.IntegerField()
    overdue_reminders = serializers.IntegerField()
    completed_reminders = serializers.IntegerField()
    upcoming_reminders = serializers.IntegerField()
    reminders_by_type = serializers.DictField()
    recent_reminders = PatientReminderSerializer(many=True)


class ClinicalDecisionSupportDashboardSerializer(serializers.Serializer):
    """Serializer for CDS dashboard data"""
    alert_summary = ClinicalAlertSummarySerializer()
    reminder_summary = PatientReminderSummarySerializer()
    active_rules_count = serializers.IntegerField()
    total_patients_monitored = serializers.IntegerField()
    recent_rule_executions = RuleExecutionSerializer(many=True)
    top_triggered_rules = ClinicalRuleSerializer(many=True)


class DrugInteractionCheckResultSerializer(serializers.Serializer):
    """Serializer for drug interaction check results"""
    interactions_found = serializers.IntegerField()
    interactions = DrugInteractionSerializer(many=True)
    severity_summary = serializers.DictField()
    recommendations = serializers.ListField(child=serializers.CharField())


class PatientClinicalSummarySerializer(serializers.Serializer):
    """Serializer for patient clinical summary"""
    patient_id = serializers.UUIDField()
    patient_name = serializers.CharField()
    active_alerts = ClinicalAlertSerializer(many=True)
    pending_reminders = PatientReminderSerializer(many=True)
    recent_executions = RuleExecutionSerializer(many=True)
    active_protocols = ProtocolExecutionSerializer(many=True)
    risk_factors = serializers.ListField(child=serializers.CharField())
    recommendations = serializers.ListField(child=serializers.CharField())
