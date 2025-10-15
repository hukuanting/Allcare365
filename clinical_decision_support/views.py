"""
Clinical Decision Support Views

This module provides both API and web views for the clinical decision support system.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.template.loader import render_to_string
import json
import logging

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import (
    RuleCategory, ClinicalRule, ClinicalAlert, DrugInteraction,
    PreventiveCareReminder, PatientReminder, RuleExecution,
    ClinicalProtocol, ProtocolExecution
)
from .serializers import (
    RuleCategorySerializer, ClinicalRuleSerializer, ClinicalAlertSerializer,
    DrugInteractionSerializer, PreventiveCareReminderSerializer,
    PatientReminderSerializer, RuleExecutionSerializer,
    ClinicalProtocolSerializer, ProtocolExecutionSerializer
)
from patients.models import Patient
from medical_records.models import MedicalRecord

logger = logging.getLogger(__name__)


# API ViewSets
class RuleCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing rule categories"""
    queryset = RuleCategory.objects.all()
    serializer_class = RuleCategorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return RuleCategory.objects.filter(is_active=True).order_by('display_order', 'name')


class ClinicalRuleViewSet(viewsets.ModelViewSet):
    """ViewSet for managing clinical rules"""
    queryset = ClinicalRule.objects.all()
    serializer_class = ClinicalRuleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = ClinicalRule.objects.filter(is_active=True)
        category = self.request.query_params.get('category', None)
        rule_type = self.request.query_params.get('type', None)
        
        if category:
            queryset = queryset.filter(category__name=category)
        if rule_type:
            queryset = queryset.filter(rule_type=rule_type)
            
        return queryset.order_by('-priority', 'name')
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """Execute a clinical rule for a specific patient"""
        rule = self.get_object()
        patient_id = request.data.get('patient_id')
        
        if not patient_id:
            return Response({'error': 'Patient ID required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            patient = Patient.objects.get(id=patient_id)
            result = self._execute_rule(rule, patient, request.user)
            return Response(result)
        except Patient.DoesNotExist:
            return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error executing rule {rule.name}: {str(e)}")
            return Response({'error': 'Rule execution failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _execute_rule(self, rule, patient, user):
        """Execute a clinical rule and return results"""
        # Create rule execution record
        execution = RuleExecution.objects.create(
            rule=rule,
            patient=patient,
            execution_time_ms=100,  # Placeholder
            status='success',
            input_data={'patient_id': str(patient.id)},
            output_data={},
            condition_met=False,
            alert_generated=False,
            created_by=user
        )
        
        # Basic rule execution logic (would be expanded based on rule type)
        alerts_triggered = []
        
        if rule.rule_type == 'medication_alert':
            alerts_triggered = self._check_medication_alerts(rule, patient)
        elif rule.rule_type == 'allergy_check':
            alerts_triggered = self._check_allergy_alerts(rule, patient)
        elif rule.rule_type == 'lab_value_check':
            alerts_triggered = self._check_lab_values(rule, patient)
        
        # Update execution with results
        execution.output_data = {
            'alerts_triggered': len(alerts_triggered),
            'alerts': alerts_triggered,
            'status': 'completed'
        }
        execution.condition_met = len(alerts_triggered) > 0
        execution.alert_generated = len(alerts_triggered) > 0
        execution.save()
        
        return {
            'execution_id': execution.id,
            'alerts_triggered': len(alerts_triggered),
            'alerts': alerts_triggered,
            'status': 'completed'
        }
    
    def _check_medication_alerts(self, rule, patient):
        """Check for medication-related alerts"""
        alerts = []
        # Implementation would check patient's medications against rule criteria
        return alerts
    
    def _check_allergy_alerts(self, rule, patient):
        """Check for allergy-related alerts"""
        alerts = []
        # Implementation would check patient's allergies against rule criteria
        return alerts
    
    def _check_lab_values(self, rule, patient):
        """Check lab values against rule criteria"""
        alerts = []
        # Implementation would check patient's lab results against rule criteria
        return alerts


class ClinicalAlertViewSet(viewsets.ModelViewSet):
    """ViewSet for managing clinical alerts"""
    queryset = ClinicalAlert.objects.all()
    serializer_class = ClinicalAlertSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = ClinicalAlert.objects.filter(is_active=True)
        severity = self.request.query_params.get('severity', None)
        patient_id = self.request.query_params.get('patient_id', None)
        
        if severity:
            queryset = queryset.filter(severity=severity)
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
            
        return queryset.order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Acknowledge an alert"""
        alert = self.get_object()
        alert.acknowledged_by = request.user
        alert.acknowledged_at = timezone.now()
        alert.save()
        return Response({'status': 'acknowledged'})


class DrugInteractionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing drug interactions"""
    queryset = DrugInteraction.objects.all()
    serializer_class = DrugInteractionSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def check_interactions(self, request):
        """Check for drug interactions"""
        medications = request.data.get('medications', [])
        
        if not medications:
            return Response({'error': 'Medications list required'}, status=status.HTTP_400_BAD_REQUEST)
        
        interactions = []
        for i, med1 in enumerate(medications):
            for med2 in medications[i+1:]:
                interaction = DrugInteraction.objects.filter(
                    Q(drug_1=med1, drug_2=med2) | Q(drug_1=med2, drug_2=med1),
                    is_active=True
                ).first()
                
                if interaction:
                    interactions.append({
                        'drug_1': med1,
                        'drug_2': med2,
                        'severity': interaction.severity,
                        'mechanism': interaction.mechanism,
                        'clinical_effect': interaction.clinical_effect,
                        'management': interaction.management
                    })
        
        return Response({'interactions': interactions})


class PreventiveCareReminderViewSet(viewsets.ModelViewSet):
    """ViewSet for managing preventive care reminders"""
    queryset = PreventiveCareReminder.objects.all()
    serializer_class = PreventiveCareReminderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = PreventiveCareReminder.objects.filter(is_active=True)
        care_type = self.request.query_params.get('care_type', None)
        
        if care_type:
            queryset = queryset.filter(care_type=care_type)
            
        return queryset.order_by('name')


class PatientReminderViewSet(viewsets.ModelViewSet):
    """ViewSet for managing patient reminders"""
    queryset = PatientReminder.objects.all()
    serializer_class = PatientReminderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = PatientReminder.objects.filter(is_active=True)
        patient_id = self.request.query_params.get('patient_id', None)
        status_filter = self.request.query_params.get('status', None)
        
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            
        return queryset.order_by('-due_date')


class ClinicalProtocolViewSet(viewsets.ModelViewSet):
    """ViewSet for managing clinical protocols"""
    queryset = ClinicalProtocol.objects.all()
    serializer_class = ClinicalProtocolSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = ClinicalProtocol.objects.filter(is_active=True)
        specialty = self.request.query_params.get('specialty', None)
        
        if specialty:
            queryset = queryset.filter(specialty=specialty)
            
        return queryset.order_by('name')
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """Execute a clinical protocol for a patient"""
        protocol = self.get_object()
        patient_id = request.data.get('patient_id')
        
        if not patient_id:
            return Response({'error': 'Patient ID required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            patient = Patient.objects.get(id=patient_id)
            execution = ProtocolExecution.objects.create(
                protocol=protocol,
                patient=patient,
                started_by=request.user,
                status='active'
            )
            
            return Response({
                'execution_id': execution.id,
                'protocol': protocol.name,
                'status': 'started'
            })
        except Patient.DoesNotExist:
            return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)


# Web Views
@login_required
def dashboard(request):
    """Clinical Decision Support dashboard"""
    # Get recent alerts
    recent_alerts = ClinicalAlert.objects.filter(
        is_active=True,
        acknowledged_at__isnull=True
    ).order_by('-created_at')[:10]
    
    # Get alert statistics
    alert_stats = ClinicalAlert.objects.filter(is_active=True).aggregate(
        total=Count('id'),
        critical=Count('id', filter=Q(alert_level='critical')),
        warning=Count('id', filter=Q(alert_level='high')),
        info=Count('id', filter=Q(alert_level='medium'))
    )
    
    # Get active rules count
    active_rules = ClinicalRule.objects.filter(is_active=True).count()
    
    # Get recent rule executions
    recent_executions = RuleExecution.objects.select_related('rule', 'patient').order_by('-created_at')[:5]
    
    context = {
        'recent_alerts': recent_alerts,
        'alert_stats': alert_stats,
        'active_rules': active_rules,
        'recent_executions': recent_executions,
        'page_title': 'Clinical Decision Support Dashboard'
    }
    
    return render(request, 'clinical_decision_support/dashboard.html', context)


@login_required
def rules_list(request):
    """List clinical rules"""
    rules = ClinicalRule.objects.filter(is_active=True).select_related('category')
    
    # Search and filter
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    type_filter = request.GET.get('type', '')
    
    if search_query:
        rules = rules.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    if category_filter:
        rules = rules.filter(category__name=category_filter)
    
    if type_filter:
        rules = rules.filter(rule_type=type_filter)
    
    # Pagination
    paginator = Paginator(rules, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get categories for filter dropdown
    categories = RuleCategory.objects.filter(is_active=True).order_by('name')
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'search_query': search_query,
        'category_filter': category_filter,
        'type_filter': type_filter,
        'rule_types': ClinicalRule.RULE_TYPES,
        'page_title': 'Clinical Rules'
    }
    
    return render(request, 'clinical_decision_support/rules_list.html', context)


@login_required
def rule_detail(request, rule_id):
    """View rule details"""
    rule = get_object_or_404(ClinicalRule, id=rule_id, is_active=True)
    
    # Get recent executions
    recent_executions = RuleExecution.objects.filter(rule=rule).select_related('patient').order_by('-created_at')[:10]
    
    context = {
        'rule': rule,
        'recent_executions': recent_executions,
        'page_title': f'Rule: {rule.name}'
    }
    
    return render(request, 'clinical_decision_support/rule_detail.html', context)


@login_required
def alerts_list(request):
    """List clinical alerts"""
    alerts = ClinicalAlert.objects.filter(is_active=True).select_related('patient', 'rule')
    
    # Filter by severity
    severity_filter = request.GET.get('severity', '')
    if severity_filter:
        alerts = alerts.filter(alert_level=severity_filter)
    
    # Filter by acknowledgment status
    ack_filter = request.GET.get('acknowledged', '')
    if ack_filter == 'yes':
        alerts = alerts.filter(acknowledged_at__isnull=False)
    elif ack_filter == 'no':
        alerts = alerts.filter(acknowledged_at__isnull=True)
    
    # Pagination
    paginator = Paginator(alerts.order_by('-created_at'), 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'severity_filter': severity_filter,
        'ack_filter': ack_filter,
        'severities': ClinicalRule.SEVERITY_LEVELS,
        'page_title': 'Clinical Alerts'
    }
    
    return render(request, 'clinical_decision_support/alerts_list.html', context)


@login_required
@require_http_methods(["POST"])
def acknowledge_alert(request, alert_id):
    """Acknowledge an alert"""
    alert = get_object_or_404(ClinicalAlert, id=alert_id, is_active=True)
    
    if not alert.acknowledged_at:
        alert.acknowledged_by = request.user
        alert.acknowledged_at = timezone.now()
        alert.save()
        messages.success(request, 'Alert acknowledged successfully.')
    else:
        messages.info(request, 'Alert was already acknowledged.')
    
    return redirect('clinical_decision_support:alerts_list')


@login_required
def drug_interactions(request):
    """Drug interactions management"""
    interactions = DrugInteraction.objects.filter(is_active=True).order_by('-severity', 'drug_1')
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        interactions = interactions.filter(
            Q(drug1__icontains=search_query) |
            Q(drug2__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Filter by severity
    severity_filter = request.GET.get('severity', '')
    if severity_filter:
        interactions = interactions.filter(severity=severity_filter)
    
    # Pagination
    paginator = Paginator(interactions, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'severity_filter': severity_filter,
        'severities': DrugInteraction.INTERACTION_SEVERITY,
        'page_title': 'Drug Interactions'
    }
    
    return render(request, 'clinical_decision_support/drug_interactions.html', context)


@login_required
def preventive_care(request):
    """Preventive care reminders"""
    reminders = PreventiveCareReminder.objects.filter(is_active=True).order_by('name')
    
    # Filter by care type
    care_type_filter = request.GET.get('care_type', '')
    if care_type_filter:
        reminders = reminders.filter(care_type=care_type_filter)
    
    context = {
        'reminders': reminders,
        'care_type_filter': care_type_filter,
        'care_types': PreventiveCareReminder.REMINDER_TYPES,
        'page_title': 'Preventive Care Reminders'
    }
    
    return render(request, 'clinical_decision_support/preventive_care.html', context)


@login_required
def protocols_list(request):
    """List clinical protocols"""
    protocols = ClinicalProtocol.objects.filter(is_active=True).order_by('name')
    
    # Filter by specialty
    specialty_filter = request.GET.get('specialty', '')
    if specialty_filter:
        protocols = protocols.filter(specialty=specialty_filter)
    
    context = {
        'protocols': protocols,
        'specialty_filter': specialty_filter,
        'specialties': ClinicalProtocol.PROTOCOL_TYPES,
        'page_title': 'Clinical Protocols'
    }
    
    return render(request, 'clinical_decision_support/protocols_list.html', context)


@login_required
def protocol_detail(request, protocol_id):
    """View protocol details"""
    protocol = get_object_or_404(ClinicalProtocol, id=protocol_id, is_active=True)
    
    # Get recent executions
    recent_executions = ProtocolExecution.objects.filter(protocol=protocol).select_related('patient').order_by('-created_at')[:10]
    
    context = {
        'protocol': protocol,
        'recent_executions': recent_executions,
        'page_title': f'Protocol: {protocol.name}'
    }
    
    return render(request, 'clinical_decision_support/protocol_detail.html', context)


# AJAX Views
@login_required
@csrf_exempt
def check_patient_alerts(request):
    """Check alerts for a specific patient"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        data = json.loads(request.body)
        patient_id = data.get('patient_id')
        
        if not patient_id:
            return JsonResponse({'error': 'Patient ID required'}, status=400)
        
        # Get active alerts for the patient
        alerts = ClinicalAlert.objects.filter(
            patient_id=patient_id,
            is_active=True,
            acknowledged_at__isnull=True
        ).order_by('-severity', '-created_at')
        
        alerts_data = []
        for alert in alerts:
            alerts_data.append({
                'id': str(alert.id),
                'severity': alert.severity,
                'title': alert.title,
                'message': alert.message,
                'created_at': alert.created_at.isoformat(),
                'rule_name': alert.rule.name if alert.rule else None
            })
        
        return JsonResponse({
            'alerts': alerts_data,
            'count': len(alerts_data)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error checking patient alerts: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
@csrf_exempt
def execute_rule_for_patient(request):
    """Execute a rule for a specific patient"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        data = json.loads(request.body)
        rule_id = data.get('rule_id')
        patient_id = data.get('patient_id')
        
        if not rule_id or not patient_id:
            return JsonResponse({'error': 'Rule ID and Patient ID required'}, status=400)
        
        rule = ClinicalRule.objects.get(id=rule_id, is_active=True)
        patient = Patient.objects.get(id=patient_id)
        
        # Execute the rule (simplified version)
        execution = RuleExecution.objects.create(
            rule=rule,
            patient=patient,
            executed_by=request.user,
            execution_context={'patient_id': patient_id}
        )
        
        # Basic execution logic would go here
        execution.result = {'status': 'completed', 'alerts_triggered': 0}
        execution.save()
        
        return JsonResponse({
            'execution_id': str(execution.id),
            'status': 'completed',
            'message': f'Rule "{rule.name}" executed successfully for patient {patient.first_name} {patient.last_name}'
        })
        
    except ClinicalRule.DoesNotExist:
        return JsonResponse({'error': 'Rule not found'}, status=404)
    except Patient.DoesNotExist:
        return JsonResponse({'error': 'Patient not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error executing rule: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def check_drug_interactions(request):
    """AJAX endpoint for checking drug interactions"""
    try:
        data = json.loads(request.body)
        medications = data.get('medications', [])
        
        if not medications:
            return JsonResponse({'error': 'Medications list required'}, status=400)
        
        interactions = []
        for i, med1 in enumerate(medications):
            for med2 in medications[i+1:]:
                interaction = DrugInteraction.objects.filter(
                    Q(drug_1=med1, drug_2=med2) | Q(drug_1=med2, drug_2=med1),
                    is_active=True
                ).first()
                
                if interaction:
                    interactions.append({
                        'drug_1': med1,
                        'drug_2': med2,
                        'severity': interaction.severity,
                        'mechanism': interaction.mechanism,
                        'clinical_effect': interaction.clinical_effect,
                        'management': interaction.management
                    })
        
        return JsonResponse({'interactions': interactions})
    
    except Exception as e:
        logger.error(f"Error checking drug interactions: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)
