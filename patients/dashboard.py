from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from patients.models import Patient, PatientVitals
from appointments.models import Appointment
from medical_records.models import MedicalRecord, Prescription
from billing.models import Invoice, Payment


class DashboardStatsView(APIView):
    """Dashboard statistics API"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get dashboard statistics"""
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Patient statistics
        total_patients = Patient.objects.filter(is_active=True).count()
        new_patients_this_week = Patient.objects.filter(
            created_at__date__gte=week_ago,
            is_active=True
        ).count()
        
        # Appointment statistics (using placeholder data since appointments model needs completion)
        appointments_today = 0  # Will be implemented when appointments are completed
        appointments_this_week = 0
        
        # Vital signs statistics
        recent_vitals = PatientVitals.objects.filter(
            measurement_date__date__gte=week_ago,
            is_active=True
        ).count()
        
        # Medical records statistics (placeholder)
        new_records_this_week = 0  # Will be implemented
        
        # Billing statistics (placeholder)
        revenue_this_month = 0  # Will be implemented
        outstanding_invoices = 0
        
        # Patient demographics
        gender_distribution = Patient.objects.filter(is_active=True).values('gender').annotate(
            count=Count('gender')
        )
        
        # Age group distribution
        age_groups = self._calculate_age_groups()
        
        # Recent activity
        recent_patients = Patient.objects.filter(is_active=True).order_by('-created_at')[:5]
        recent_vitals_list = PatientVitals.objects.filter(is_active=True).order_by('-measurement_date')[:5]
        
        data = {
            'overview': {
                'total_patients': total_patients,
                'new_patients_this_week': new_patients_this_week,
                'appointments_today': appointments_today,
                'appointments_this_week': appointments_this_week,
                'recent_vitals': recent_vitals,
                'new_records_this_week': new_records_this_week,
                'revenue_this_month': revenue_this_month,
                'outstanding_invoices': outstanding_invoices,
            },
            'demographics': {
                'gender_distribution': list(gender_distribution),
                'age_groups': age_groups,
            },
            'recent_activity': {
                'recent_patients': [
                    {
                        'id': p.id,
                        'name': p.full_name,
                        'mrn': p.medical_record_number,
                        'created_at': p.created_at,
                    } for p in recent_patients
                ],
                'recent_vitals': [
                    {
                        'id': v.id,
                        'patient_name': v.patient.full_name,
                        'measurement_date': v.measurement_date,
                        'recorded_by': v.recorded_by.get_full_name() if v.recorded_by else None,
                    } for v in recent_vitals_list
                ],
            }
        }
        
        return Response(data)
    
    def _calculate_age_groups(self):
        """Calculate age group distribution"""
        today = timezone.now().date()
        
        pediatric = Patient.objects.filter(
            date_of_birth__gt=today - timedelta(days=18*365),
            is_active=True
        ).count()
        
        adult = Patient.objects.filter(
            date_of_birth__lte=today - timedelta(days=18*365),
            date_of_birth__gt=today - timedelta(days=65*365),
            is_active=True
        ).count()
        
        senior = Patient.objects.filter(
            date_of_birth__lte=today - timedelta(days=65*365),
            is_active=True
        ).count()
        
        return {
            'pediatric': pediatric,
            'adult': adult,
            'senior': senior,
        }


class PatientChartsView(APIView):
    """Patient charts and analytics"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get patient charts data"""
        # Patient registration trend (last 30 days)
        registration_trend = self._get_registration_trend()
        
        # Vital signs trends
        vitals_trend = self._get_vitals_trend()
        
        # Most common allergies
        common_allergies = self._get_common_allergies()
        
        # Most prescribed medications
        common_medications = self._get_common_medications()
        
        data = {
            'registration_trend': registration_trend,
            'vitals_trend': vitals_trend,
            'common_allergies': common_allergies,
            'common_medications': common_medications,
        }
        
        return Response(data)
    
    def _get_registration_trend(self):
        """Get patient registration trend for last 30 days"""
        from django.db.models import Count
        from django.db.models.functions import TruncDate
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        trend = Patient.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            is_active=True
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        return list(trend)
    
    def _get_vitals_trend(self):
        """Get vitals measurement trend"""
        from django.db.models import Avg
        from django.db.models.functions import TruncDate
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        trend = PatientVitals.objects.filter(
            measurement_date__date__gte=start_date,
            measurement_date__date__lte=end_date,
            is_active=True
        ).annotate(
            date=TruncDate('measurement_date')
        ).values('date').annotate(
            avg_systolic=Avg('blood_pressure_systolic'),
            avg_diastolic=Avg('blood_pressure_diastolic'),
            avg_heart_rate=Avg('heart_rate'),
            count=Count('id')
        ).order_by('date')
        
        return list(trend)
    
    def _get_common_allergies(self):
        """Get most common allergies"""
        from patients.models import PatientAllergy
        
        allergies = PatientAllergy.objects.filter(is_active=True).values(
            'allergen'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        return list(allergies)
    
    def _get_common_medications(self):
        """Get most prescribed medications"""
        from patients.models import PatientMedication
        
        medications = PatientMedication.objects.filter(
            is_current=True, 
            is_active=True
        ).values(
            'medication_name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        return list(medications)
