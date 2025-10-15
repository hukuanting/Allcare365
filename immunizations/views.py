from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Q, F
from django.utils import timezone
from datetime import datetime, timedelta
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Prefetch
from django.core.paginator import Paginator
import json

from .models import (
    VaccineManufacturer, Vaccine, VaccineLot, ImmunizationSchedule,
    ScheduledVaccination, Immunization, ImmunizationObservation,
    ImmunizationContraindication, PatientImmunizationAlert
)
from .serializers import (
    VaccineManufacturerSerializer, VaccineSerializer, VaccineLotSerializer,
    ImmunizationScheduleSerializer, ImmunizationSerializer, ImmunizationCreateSerializer,
    ImmunizationObservationSerializer, ImmunizationContraindicationSerializer,
    PatientImmunizationAlertSerializer, PatientImmunizationHistorySerializer,
    ImmunizationDashboardSerializer
)
from patients.models import Patient


class VaccineManufacturerViewSet(viewsets.ModelViewSet):
    """Vaccine manufacturer management"""
    queryset = VaccineManufacturer.objects.all()
    serializer_class = VaccineManufacturerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active']
    search_fields = ['name', 'code']
    ordering_fields = ['name', 'create_date']
    ordering = ['name']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class VaccineViewSet(viewsets.ModelViewSet):
    """Vaccine management"""
    queryset = Vaccine.objects.select_related('manufacturer').all()
    serializer_class = VaccineSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'manufacturer', 'vaccine_type']
    search_fields = ['name', 'cvx_code', 'short_name']
    ordering_fields = ['name', 'cvx_code', 'create_date']
    ordering = ['name']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def contraindications(self, request, pk=None):
        """Get contraindications for a specific vaccine"""
        vaccine = self.get_object()
        contraindications = vaccine.contraindications.all()
        serializer = ImmunizationContraindicationSerializer(contraindications, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def lots(self, request, pk=None):
        """Get vaccine lots for a specific vaccine"""
        vaccine = self.get_object()
        lots = vaccine.lots.select_related('manufacturer').all()
        serializer = VaccineLotSerializer(lots, many=True)
        return Response(serializer.data)


class VaccineLotViewSet(viewsets.ModelViewSet):
    """Vaccine lot management"""
    queryset = VaccineLot.objects.select_related('vaccine', 'manufacturer').all()
    serializer_class = VaccineLotSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['vaccine', 'manufacturer']
    search_fields = ['lot_number', 'vaccine__name']
    ordering_fields = ['expiration_date', 'create_date']
    ordering = ['expiration_date']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def expired(self, request):
        """Get expired vaccine lots"""
        expired_lots = self.get_queryset().filter(expiration_date__lt=timezone.now().date())
        serializer = self.get_serializer(expired_lots, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get low stock vaccine lots"""
        # Define low stock as less than 10 units available
        low_stock_lots = self.get_queryset().filter(
            quantity_received__lt=10 + F('quantity_used') + F('quantity_wasted')
        )
        serializer = self.get_serializer(low_stock_lots, many=True)
        return Response(serializer.data)


class ImmunizationScheduleViewSet(viewsets.ModelViewSet):
    """Immunization schedule management"""
    queryset = ImmunizationSchedule.objects.prefetch_related(
        Prefetch('vaccinations', queryset=ScheduledVaccination.objects.select_related('vaccine'))
    ).all()
    serializer_class = ImmunizationScheduleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['age_group', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'create_date']
    ordering = ['name']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class ImmunizationViewSet(viewsets.ModelViewSet):
    """Immunization management"""
    queryset = Immunization.objects.select_related(
        'patient', 'vaccine', 'vaccine_lot', 'administered_by', 'ordering_provider'
    ).prefetch_related('observations').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['patient', 'vaccine', 'completion_status', 'administered_by']
    search_fields = ['patient__first_name', 'patient__last_name', 'vaccine__name']
    ordering_fields = ['administered_date', 'create_date']
    ordering = ['-administered_date']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ImmunizationCreateSerializer
        return ImmunizationSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def add_observation(self, request, pk=None):
        """Add an observation to an immunization"""
        immunization = self.get_object()
        data = request.data.copy()
        data['immunization'] = immunization.id
        
        serializer = ImmunizationObservationSerializer(data=data)
        if serializer.is_valid():
            serializer.save(created_by=request.user, updated_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def patient_history(self, request):
        """Get immunization history for a patient"""
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response({'error': 'patient_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            patient = Patient.objects.get(id=patient_id)
            serializer = PatientImmunizationHistorySerializer(patient)
            return Response(serializer.data)
        except Patient.DoesNotExist:
            return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get dashboard statistics"""
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Basic statistics
        total_immunizations = Immunization.objects.count()
        immunizations_today = Immunization.objects.filter(administered_date__date=today).count()
        immunizations_this_week = Immunization.objects.filter(administered_date__date__gte=week_ago).count()
        immunizations_this_month = Immunization.objects.filter(administered_date__date__gte=month_ago).count()
        
        # Alerts and inventory
        pending_alerts = PatientImmunizationAlert.objects.filter(is_active=True).count()
        expired_lots = VaccineLot.objects.filter(expiration_date__lt=today).count()
        low_stock_vaccines = VaccineLot.objects.filter(
            quantity_received__lt=10 + F('quantity_used') + F('quantity_wasted')
        ).count()
        
        # Recent immunizations
        recent_immunizations = Immunization.objects.select_related(
            'patient', 'vaccine', 'administered_by'
        ).order_by('-administered_date')[:10]
        
        # Upcoming due immunizations
        upcoming_due = PatientImmunizationAlert.objects.filter(
            alert_type='due', is_active=True
        ).select_related('patient', 'vaccine').order_by('due_date')[:10]
        
        # Vaccine usage statistics
        vaccine_usage_stats = list(Immunization.objects.values('vaccine__name').annotate(
            count=Count('id')
        ).order_by('-count')[:10])
        
        dashboard_data = {
            'total_immunizations': total_immunizations,
            'immunizations_today': immunizations_today,
            'immunizations_this_week': immunizations_this_week,
            'immunizations_this_month': immunizations_this_month,
            'pending_alerts': pending_alerts,
            'expired_lots': expired_lots,
            'low_stock_vaccines': low_stock_vaccines,
            'recent_immunizations': ImmunizationSerializer(recent_immunizations, many=True).data,
            'upcoming_due': PatientImmunizationAlertSerializer(upcoming_due, many=True).data,
            'vaccine_usage_stats': vaccine_usage_stats
        }
        
        return Response(dashboard_data)


class ImmunizationObservationViewSet(viewsets.ModelViewSet):
    """Immunization observation management"""
    queryset = ImmunizationObservation.objects.select_related('immunization').all()
    serializer_class = ImmunizationObservationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['observation_type', 'severity', 'reported_to_vaers']
    search_fields = ['description', 'immunization__patient__first_name', 'immunization__patient__last_name']
    ordering_fields = ['observation_date', 'create_date']
    ordering = ['-observation_date']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class ImmunizationContraindicationViewSet(viewsets.ModelViewSet):
    """Immunization contraindication management"""
    queryset = ImmunizationContraindication.objects.select_related('vaccine').all()
    serializer_class = ImmunizationContraindicationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['vaccine', 'contraindication_type', 'severity', 'is_permanent']
    search_fields = ['description', 'vaccine__name']
    ordering_fields = ['vaccine', 'contraindication_type', 'create_date']
    ordering = ['vaccine']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class PatientImmunizationAlertViewSet(viewsets.ModelViewSet):
    """Patient immunization alert management"""
    queryset = PatientImmunizationAlert.objects.select_related('patient', 'vaccine', 'acknowledged_by').all()
    serializer_class = PatientImmunizationAlertSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['patient', 'vaccine', 'alert_type', 'is_active']
    search_fields = ['patient__first_name', 'patient__last_name', 'vaccine__name']
    ordering_fields = ['alert_date', 'due_date', 'create_date']
    ordering = ['-alert_date']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Acknowledge an alert"""
        alert = self.get_object()
        alert.acknowledged_by = request.user
        alert.acknowledged_date = timezone.now()
        alert.is_active = False
        alert.save()
        
        serializer = self.get_serializer(alert)
        return Response(serializer.data)


# Template views
@login_required
def immunization_dashboard(request):
    """Immunization dashboard view"""
    context = {
        'title': 'Immunization Dashboard',
        'active_menu': 'immunizations'
    }
    return render(request, 'immunizations/dashboard.html', context)


@login_required
def immunization_list(request):
    """Immunization list view"""
    immunizations = Immunization.objects.select_related(
        'patient', 'vaccine', 'administered_by'
    ).order_by('-administered_date')
    
    # Pagination
    paginator = Paginator(immunizations, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'title': 'Immunization Records',
        'active_menu': 'immunizations',
        'page_obj': page_obj
    }
    return render(request, 'immunizations/list.html', context)


@login_required
def immunization_detail(request, pk):
    """Immunization detail view"""
    immunization = get_object_or_404(
        Immunization.objects.select_related(
            'patient', 'vaccine', 'vaccine_lot', 'administered_by', 'ordering_provider'
        ).prefetch_related('observations'),
        pk=pk
    )
    
    context = {
        'title': f'Immunization - {immunization.patient.get_full_name()}',
        'active_menu': 'immunizations',
        'immunization': immunization
    }
    return render(request, 'immunizations/detail.html', context)


@login_required
def patient_immunization_history(request, patient_id):
    """Patient immunization history view"""
    patient = get_object_or_404(Patient, id=patient_id)
    immunizations = patient.immunizations.select_related(
        'vaccine', 'administered_by'
    ).order_by('-administered_date')
    
    alerts = patient.immunization_alerts.filter(is_active=True).select_related('vaccine')
    
    context = {
        'title': f'Immunization History - {patient.get_full_name()}',
        'active_menu': 'immunizations',
        'patient': patient,
        'immunizations': immunizations,
        'alerts': alerts
    }
    return render(request, 'immunizations/patient_history.html', context)


@login_required
def vaccine_inventory(request):
    """Vaccine inventory view"""
    lots = VaccineLot.objects.select_related('vaccine', 'manufacturer').order_by('expiration_date')
    
    context = {
        'title': 'Vaccine Inventory',
        'active_menu': 'immunizations',
        'lots': lots
    }
    return render(request, 'immunizations/inventory.html', context)


@staff_member_required
def immunization_reports(request):
    """Immunization reports view"""
    context = {
        'title': 'Immunization Reports',
        'active_menu': 'immunizations'
    }
    return render(request, 'immunizations/reports.html', context)
