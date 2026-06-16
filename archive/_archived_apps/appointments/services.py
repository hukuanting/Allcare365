"""
Advanced Appointment Management Services

This module provides advanced appointment management functionality including:
- Appointment scheduling with conflict detection
- Automatic reminders and notifications
- Waitlist management
- Schedule optimization
- Resource allocation
"""

from django.db.models import Q, Count, F, Sum, Avg
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime, timedelta, time
from typing import List, Dict, Tuple, Optional
import logging

from .models import Appointment, AppointmentType, AppointmentReminder, WaitlistEntry
from patients.models import Patient


logger = logging.getLogger(__name__)


class AppointmentSchedulingService:
    """
    Advanced appointment scheduling service with conflict detection and optimization
    """
    
    @staticmethod
    def check_scheduling_conflicts(
        provider_id: str,
        appointment_date: datetime.date,
        start_time: datetime.time,
        duration_minutes: int,
        exclude_appointment_id: str = None,
        facility_id: str = None
    ) -> List[Dict]:
        """
        Check for scheduling conflicts before booking an appointment
        
        Args:
            provider_id: Provider UUID
            appointment_date: Date of appointment
            start_time: Start time of appointment
            duration_minutes: Duration in minutes
            exclude_appointment_id: Appointment ID to exclude (for updates)
            facility_id: Optional facility constraint
            
        Returns:
            List of conflict details
        """
        from datetime import datetime, timedelta
        
        # Calculate end time
        start_datetime = datetime.combine(appointment_date, start_time)
        end_datetime = start_datetime + timedelta(minutes=duration_minutes)
        end_time = end_datetime.time()
        
        # Base query for existing appointments
        existing_appointments = Appointment.objects.filter(
            provider_id=provider_id,
            appointment_date=appointment_date,
            status__in=['scheduled', 'confirmed', 'in_progress']
        )
        
        if exclude_appointment_id:
            existing_appointments = existing_appointments.exclude(id=exclude_appointment_id)
        
        if facility_id:
            existing_appointments = existing_appointments.filter(facility_id=facility_id)
        
        conflicts = []
        
        for appointment in existing_appointments:
            # Calculate existing appointment end time
            existing_start = appointment.appointment_time
            existing_end = appointment.end_time
            
            if not existing_end:
                # Calculate end time if not set
                existing_start_datetime = datetime.combine(appointment_date, existing_start)
                existing_end_datetime = existing_start_datetime + timedelta(minutes=appointment.duration_minutes)
                existing_end = existing_end_datetime.time()
            
            # Check for time overlap
            if AppointmentSchedulingService._times_overlap(start_time, end_time, existing_start, existing_end):
                conflicts.append({
                    'appointment_id': appointment.id,
                    'patient_name': appointment.patient.get_full_name(),
                    'existing_start': existing_start,
                    'existing_end': existing_end,
                    'conflict_type': 'time_overlap',
                    'severity': 'high'
                })
        
        # Check provider availability/working hours
        availability_conflicts = AppointmentSchedulingService._check_provider_availability(
            provider_id, appointment_date, start_time, end_time
        )
        conflicts.extend(availability_conflicts)
        
        # Check facility capacity if specified
        if facility_id:
            capacity_conflicts = AppointmentSchedulingService._check_facility_capacity(
                facility_id, appointment_date, start_time, end_time
            )
            conflicts.extend(capacity_conflicts)
        
        return conflicts
    
    @staticmethod
    def _times_overlap(start1: time, end1: time, start2: time, end2: time) -> bool:
        """Check if two time ranges overlap"""
        return start1 < end2 and start2 < end1
    
    @staticmethod
    def _check_provider_availability(
        provider_id: str,
        appointment_date: datetime.date,
        start_time: time,
        end_time: time
    ) -> List[Dict]:
        """Check provider working hours and availability"""
        conflicts = []
        
        # This would integrate with provider schedule/availability system
        # For now, basic business hours check
        business_start = time(8, 0)  # 8:00 AM
        business_end = time(18, 0)   # 6:00 PM
        
        if start_time < business_start or end_time > business_end:
            conflicts.append({
                'conflict_type': 'outside_business_hours',
                'severity': 'medium',
                'message': f'Appointment time ({start_time}-{end_time}) is outside business hours ({business_start}-{business_end})'
            })
        
        # Check for provider vacation/time-off
        # This would query a provider availability/time-off system
        
        return conflicts
    
    @staticmethod
    def _check_facility_capacity(
        facility_id: str,
        appointment_date: datetime.date,
        start_time: time,
        end_time: time
    ) -> List[Dict]:
        """Check facility capacity and resource availability"""
        conflicts = []
        
        # Count concurrent appointments at the facility
        concurrent_appointments = Appointment.objects.filter(
            facility_id=facility_id,
            appointment_date=appointment_date,
            status__in=['scheduled', 'confirmed', 'in_progress']
        )
        
        # This would need facility capacity information
        # For now, assume max 10 concurrent appointments
        max_capacity = 10
        concurrent_count = 0
        
        for apt in concurrent_appointments:
            apt_start = apt.appointment_time
            apt_end = apt.end_time or (datetime.combine(appointment_date, apt_start) + 
                                     timedelta(minutes=apt.duration_minutes)).time()
            
            if AppointmentSchedulingService._times_overlap(start_time, end_time, apt_start, apt_end):
                concurrent_count += 1
        
        if concurrent_count >= max_capacity:
            conflicts.append({
                'conflict_type': 'facility_capacity',
                'severity': 'high',
                'message': f'Facility at capacity ({concurrent_count}/{max_capacity}) for requested time'
            })
        
        return conflicts
    
    @staticmethod
    def suggest_alternative_times(
        provider_id: str,
        appointment_date: datetime.date,
        duration_minutes: int,
        preferred_time: time = None,
        max_suggestions: int = 5
    ) -> List[Dict]:
        """
        Suggest alternative appointment times if conflicts exist
        
        Args:
            provider_id: Provider UUID
            appointment_date: Preferred date
            duration_minutes: Required duration
            preferred_time: Preferred start time
            max_suggestions: Maximum number of suggestions
            
        Returns:
            List of suggested time slots
        """
        suggestions = []
        
        # Define search parameters
        business_start = time(8, 0)
        business_end = time(18, 0)
        slot_interval = 15  # 15-minute intervals
        
        # Get existing appointments for the day
        existing_appointments = Appointment.objects.filter(
            provider_id=provider_id,
            appointment_date=appointment_date,
            status__in=['scheduled', 'confirmed', 'in_progress']
        ).order_by('appointment_time')
        
        # Generate time slots
        current_time = business_start
        
        while current_time < business_end and len(suggestions) < max_suggestions:
            # Calculate end time for this slot
            start_datetime = datetime.combine(appointment_date, current_time)
            end_datetime = start_datetime + timedelta(minutes=duration_minutes)
            
            if end_datetime.time() > business_end:
                break
            
            # Check if this slot is available
            conflicts = AppointmentSchedulingService.check_scheduling_conflicts(
                provider_id, appointment_date, current_time, duration_minutes
            )
            
            if not conflicts:
                # Calculate preference score if preferred time is given
                preference_score = 100
                if preferred_time:
                    time_diff = abs((datetime.combine(appointment_date, current_time) - 
                                   datetime.combine(appointment_date, preferred_time)).total_seconds() / 60)
                    preference_score = max(0, 100 - time_diff)  # Closer = higher score
                
                suggestions.append({
                    'start_time': current_time,
                    'end_time': end_datetime.time(),
                    'duration_minutes': duration_minutes,
                    'preference_score': preference_score,
                    'availability': 'available'
                })
            
            # Move to next time slot
            current_time = (datetime.combine(appointment_date, current_time) + 
                          timedelta(minutes=slot_interval)).time()
        
        # Sort by preference score
        suggestions.sort(key=lambda x: x['preference_score'], reverse=True)
        
        return suggestions[:max_suggestions]


class AppointmentReminderService:
    """
    Service for managing appointment reminders and notifications
    """
    
    @staticmethod
    def schedule_reminders(appointment_id: str) -> Dict:
        """
        Schedule automatic reminders for an appointment
        
        Args:
            appointment_id: Appointment UUID
            
        Returns:
            Dictionary with scheduled reminder details
        """
        try:
            appointment = Appointment.objects.get(id=appointment_id)
        except Appointment.DoesNotExist:
            return {'error': 'Appointment not found'}
        
        reminder_schedule = [
            {'days_before': 7, 'type': 'email'},
            {'days_before': 1, 'type': 'sms'},
            {'hours_before': 2, 'type': 'email'}
        ]
        
        scheduled_reminders = []
        
        for reminder_config in reminder_schedule:
            # Calculate reminder datetime
            appointment_datetime = datetime.combine(
                appointment.appointment_date,
                appointment.appointment_time
            )
            
            if 'days_before' in reminder_config:
                reminder_datetime = appointment_datetime - timedelta(days=reminder_config['days_before'])
            elif 'hours_before' in reminder_config:
                reminder_datetime = appointment_datetime - timedelta(hours=reminder_config['hours_before'])
            else:
                continue
            
            # Only schedule future reminders
            if reminder_datetime > timezone.now():
                reminder = AppointmentReminder.objects.create(
                    appointment=appointment,
                    reminder_type=reminder_config['type'],
                    scheduled_datetime=reminder_datetime,
                    status='scheduled'
                )
                
                scheduled_reminders.append({
                    'id': reminder.id,
                    'type': reminder.reminder_type,
                    'scheduled_for': reminder.scheduled_datetime,
                    'status': reminder.status
                })
        
        return {
            'appointment_id': appointment_id,
            'scheduled_reminders': scheduled_reminders
        }
    
    @staticmethod
    def send_reminder(reminder_id: str) -> Dict:
        """
        Send a specific reminder
        
        Args:
            reminder_id: Reminder UUID
            
        Returns:
            Dictionary with send result
        """
        try:
            reminder = AppointmentReminder.objects.get(id=reminder_id, status='scheduled')
        except AppointmentReminder.DoesNotExist:
            return {'error': 'Reminder not found or already sent'}
        
        appointment = reminder.appointment
        patient = appointment.patient
        
        try:
            if reminder.reminder_type == 'email':
                result = AppointmentReminderService._send_email_reminder(appointment, patient)
            elif reminder.reminder_type == 'sms':
                result = AppointmentReminderService._send_sms_reminder(appointment, patient)
            else:
                return {'error': 'Unknown reminder type'}
            
            if result['success']:
                reminder.status = 'sent'
                reminder.sent_datetime = timezone.now()
                reminder.delivery_status = 'delivered'
            else:
                reminder.status = 'failed'
                reminder.delivery_status = 'failed'
                reminder.error_message = result.get('error', 'Unknown error')
            
            reminder.save()
            
            return {
                'reminder_id': reminder_id,
                'status': reminder.status,
                'sent_at': reminder.sent_datetime
            }
            
        except Exception as e:
            reminder.status = 'failed'
            reminder.error_message = str(e)
            reminder.save()
            
            logger.error(f'Failed to send reminder {reminder_id}: {str(e)}')
            
            return {
                'error': f'Failed to send reminder: {str(e)}'
            }
    
    @staticmethod
    def _send_email_reminder(appointment: Appointment, patient: Patient) -> Dict:
        """Send email reminder"""
        if not patient.email:
            return {'success': False, 'error': 'Patient has no email address'}
        
        subject = f'Appointment Reminder - {appointment.appointment_date}'
        message = f"""
        Dear {patient.get_full_name()},
        
        This is a reminder of your upcoming appointment:
        
        Date: {appointment.appointment_date}
        Time: {appointment.appointment_time}
        Provider: {appointment.provider.get_full_name() if appointment.provider else 'TBD'}
        Type: {appointment.appointment_type.name if appointment.appointment_type else 'General'}
        
        Please arrive 15 minutes before your scheduled time.
        
        If you need to reschedule or cancel, please contact us at least 24 hours in advance.
        
        Thank you,
        Healthcare Team
        """
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[patient.email],
                fail_silently=False
            )
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def _send_sms_reminder(appointment: Appointment, patient: Patient) -> Dict:
        """Send SMS reminder"""
        if not patient.phone_mobile:
            return {'success': False, 'error': 'Patient has no mobile phone number'}
        
        message = f"Reminder: Appointment on {appointment.appointment_date} at {appointment.appointment_time}. Reply CANCEL to cancel."
        
        # This would integrate with SMS service (Twilio, etc.)
        # For now, just log the message
        logger.info(f'SMS reminder to {patient.phone_mobile}: {message}')
        
        return {'success': True, 'message': 'SMS sent (simulated)'}
    
    @staticmethod
    def process_pending_reminders() -> Dict:
        """
        Process all pending reminders
        
        Returns:
            Dictionary with processing results
        """
        current_time = timezone.now()
        
        pending_reminders = AppointmentReminder.objects.filter(
            status='scheduled',
            scheduled_datetime__lte=current_time
        )
        
        results = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        for reminder in pending_reminders:
            result = AppointmentReminderService.send_reminder(str(reminder.id))
            results['processed'] += 1
            
            if 'error' in result:
                results['failed'] += 1
                results['errors'].append({
                    'reminder_id': str(reminder.id),
                    'error': result['error']
                })
            else:
                results['successful'] += 1
        
        return results


class WaitlistService:
    """
    Service for managing appointment waitlists
    """
    
    @staticmethod
    def add_to_waitlist(
        patient_id: str,
        provider_id: str,
        preferred_date: datetime.date = None,
        appointment_type_id: str = None,
        priority: str = 'normal'
    ) -> Dict:
        """
        Add patient to waitlist for earlier appointment
        
        Args:
            patient_id: Patient UUID
            provider_id: Provider UUID
            preferred_date: Preferred appointment date
            appointment_type_id: Appointment type UUID
            priority: Priority level (urgent, high, normal, low)
            
        Returns:
            Dictionary with waitlist entry details
        """
        try:
            patient = Patient.objects.get(id=patient_id)
            
            # Check if already on waitlist
            existing_entry = WaitlistEntry.objects.filter(
                patient=patient,
                provider_id=provider_id,
                status='active'
            ).first()
            
            if existing_entry:
                return {
                    'error': 'Patient already on waitlist for this provider',
                    'existing_entry_id': str(existing_entry.id)
                }
            
            # Create waitlist entry
            entry = WaitlistEntry.objects.create(
                patient=patient,
                provider_id=provider_id,
                appointment_type_id=appointment_type_id,
                preferred_date=preferred_date,
                priority=priority,
                status='active'
            )
            
            return {
                'waitlist_entry_id': str(entry.id),
                'position': WaitlistService.get_waitlist_position(str(entry.id)),
                'estimated_wait_time': WaitlistService.estimate_wait_time(str(entry.id))
            }
            
        except Patient.DoesNotExist:
            return {'error': 'Patient not found'}
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def get_waitlist_position(entry_id: str) -> int:
        """Get position of entry in waitlist"""
        try:
            entry = WaitlistEntry.objects.get(id=entry_id)
            
            # Count entries with higher priority or earlier creation date
            earlier_entries = WaitlistEntry.objects.filter(
                provider_id=entry.provider_id,
                status='active'
            ).filter(
                Q(priority__in=['urgent', 'high']) & Q(priority__gt=entry.priority) |
                Q(priority=entry.priority, created_at__lt=entry.created_at)
            ).count()
            
            return earlier_entries + 1
            
        except WaitlistEntry.DoesNotExist:
            return 0
    
    @staticmethod
    def estimate_wait_time(entry_id: str) -> Dict:
        """Estimate wait time for waitlist entry"""
        try:
            entry = WaitlistEntry.objects.get(id=entry_id)
            position = WaitlistService.get_waitlist_position(entry_id)
            
            # Calculate average appointment duration for provider
            avg_duration = Appointment.objects.filter(
                provider_id=entry.provider_id,
                status='completed'
            ).aggregate(avg_duration=Avg('duration_minutes'))['avg_duration'] or 30
            
            # Estimate based on position and average appointment slots per day
            appointments_per_day = 8  # Assume 8 appointments per day
            estimated_days = max(1, position // appointments_per_day)
            
            return {
                'estimated_days': estimated_days,
                'estimated_date': (timezone.now().date() + timedelta(days=estimated_days)),
                'position': position,
                'confidence': 'medium'  # Could be calculated based on historical data
            }
            
        except WaitlistEntry.DoesNotExist:
            return {'error': 'Waitlist entry not found'}
    
    @staticmethod
    def check_waitlist_opportunities() -> List[Dict]:
        """
        Check for appointment opportunities for waitlist patients
        
        Returns:
            List of opportunities found
        """
        opportunities = []
        
        # Look for cancellations or gaps in schedule
        recent_cancellations = Appointment.objects.filter(
            status='cancelled',
            appointment_date__gte=timezone.now().date(),
            updated_at__gte=timezone.now() - timedelta(hours=24)
        )
        
        for cancelled_appointment in recent_cancellations:
            # Find waitlist entries that could fill this slot
            suitable_entries = WaitlistEntry.objects.filter(
                provider_id=cancelled_appointment.provider_id,
                status='active'
            ).filter(
                Q(preferred_date__isnull=True) |
                Q(preferred_date__lte=cancelled_appointment.appointment_date)
            ).order_by('priority', 'created_at')[:5]
            
            for entry in suitable_entries:
                opportunities.append({
                    'waitlist_entry_id': str(entry.id),
                    'patient_name': entry.patient.get_full_name(),
                    'available_slot': {
                        'date': cancelled_appointment.appointment_date,
                        'time': cancelled_appointment.appointment_time,
                        'duration': cancelled_appointment.duration_minutes
                    },
                    'opportunity_type': 'cancellation',
                    'priority': entry.priority
                })
        
        return opportunities


class AppointmentAnalyticsService:
    """
    Service for appointment analytics and reporting
    """
    
    @staticmethod
    def get_appointment_statistics(
        provider_id: str = None,
        start_date: datetime.date = None,
        end_date: datetime.date = None
    ) -> Dict:
        """
        Get comprehensive appointment statistics
        
        Args:
            provider_id: Optional provider filter
            start_date: Start date for analysis
            end_date: End date for analysis
            
        Returns:
            Dictionary with statistics
        """
        # Default to last 30 days if no dates provided
        if not end_date:
            end_date = timezone.now().date()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Base queryset
        appointments = Appointment.objects.filter(
            appointment_date__range=(start_date, end_date)
        )
        
        if provider_id:
            appointments = appointments.filter(provider_id=provider_id)
        
        # Basic counts
        total_appointments = appointments.count()
        appointments_by_status = appointments.values('status').annotate(count=Count('id'))
        
        # No-show rate
        no_shows = appointments.filter(status='no_show').count()
        no_show_rate = (no_shows / total_appointments * 100) if total_appointments > 0 else 0
        
        # Cancellation rate
        cancellations = appointments.filter(status='cancelled').count()
        cancellation_rate = (cancellations / total_appointments * 100) if total_appointments > 0 else 0
        
        # Average duration
        avg_duration = appointments.aggregate(avg_duration=Avg('duration_minutes'))['avg_duration'] or 0
        
        # Appointments by type
        appointments_by_type = appointments.values('appointment_type__name').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Daily appointment counts
        daily_counts = appointments.values('appointment_date').annotate(
            count=Count('id')
        ).order_by('appointment_date')
        
        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'totals': {
                'total_appointments': total_appointments,
                'no_shows': no_shows,
                'cancellations': cancellations,
                'completed': appointments.filter(status='completed').count()
            },
            'rates': {
                'no_show_rate': round(no_show_rate, 2),
                'cancellation_rate': round(cancellation_rate, 2),
                'completion_rate': round((total_appointments - no_shows - cancellations) / total_appointments * 100, 2) if total_appointments > 0 else 0
            },
            'metrics': {
                'average_duration_minutes': round(avg_duration, 1),
                'total_duration_hours': round(appointments.aggregate(total=Sum('duration_minutes'))['total'] / 60, 1) if appointments.exists() else 0
            },
            'breakdowns': {
                'by_status': {item['status']: item['count'] for item in appointments_by_status},
                'by_type': {item['appointment_type__name']: item['count'] for item in appointments_by_type},
                'daily_counts': list(daily_counts)
            }
        }
