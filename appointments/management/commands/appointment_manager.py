"""
Advanced Appointment Management Commands

This command provides comprehensive appointment management functionality including:
- Conflict detection and scheduling optimization
- Automatic reminder processing
- Waitlist management
- Schedule analytics and reporting
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from django.db.models import Count, Q, Avg
from datetime import datetime, timedelta, time
from appointments.models import Appointment, AppointmentType, AppointmentReminder, WaitlistEntry
from appointments.services import (
    AppointmentSchedulingService, AppointmentReminderService,
    WaitlistService, AppointmentAnalyticsService
)
import json


class Command(BaseCommand):
    help = 'Advanced appointment management operations'
    
    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='action', help='Available actions')
        
        # Check conflicts
        conflict_parser = subparsers.add_parser('check-conflicts', help='Check scheduling conflicts')
        conflict_parser.add_argument('--provider-id', type=str, required=True, help='Provider UUID')
        conflict_parser.add_argument('--date', type=str, required=True, help='Appointment date (YYYY-MM-DD)')
        conflict_parser.add_argument('--time', type=str, required=True, help='Appointment time (HH:MM)')
        conflict_parser.add_argument('--duration', type=int, default=30, help='Duration in minutes')
        conflict_parser.add_argument('--exclude', type=str, help='Appointment ID to exclude')
        
        # Process reminders
        reminder_parser = subparsers.add_parser('process-reminders', help='Process pending reminders')
        reminder_parser.add_argument('--dry-run', action='store_true', help='Show what would be sent without sending')
        
        # Schedule reminders
        schedule_parser = subparsers.add_parser('schedule-reminders', help='Schedule reminders for appointment')
        schedule_parser.add_argument('appointment_id', type=str, help='Appointment UUID')
        
        # Waitlist management
        waitlist_parser = subparsers.add_parser('waitlist', help='Manage waitlist')
        waitlist_parser.add_argument('--check-opportunities', action='store_true', help='Check for waitlist opportunities')
        waitlist_parser.add_argument('--add-patient', type=str, help='Add patient to waitlist (patient UUID)')
        waitlist_parser.add_argument('--provider-id', type=str, help='Provider UUID for waitlist')
        waitlist_parser.add_argument('--priority', choices=['urgent', 'high', 'normal', 'low'], default='normal')
        
        # Analytics
        analytics_parser = subparsers.add_parser('analytics', help='Generate appointment analytics')
        analytics_parser.add_argument('--provider-id', type=str, help='Provider UUID filter')
        analytics_parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)')
        analytics_parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD)')
        analytics_parser.add_argument('--output', type=str, help='Output file for results')
        
        # Suggest times
        suggest_parser = subparsers.add_parser('suggest-times', help='Suggest alternative appointment times')
        suggest_parser.add_argument('--provider-id', type=str, required=True, help='Provider UUID')
        suggest_parser.add_argument('--date', type=str, required=True, help='Preferred date (YYYY-MM-DD)')
        suggest_parser.add_argument('--duration', type=int, default=30, help='Duration in minutes')
        suggest_parser.add_argument('--preferred-time', type=str, help='Preferred time (HH:MM)')
        suggest_parser.add_argument('--max-suggestions', type=int, default=5, help='Maximum suggestions')
    
    def handle(self, *args, **options):
        """Execute the command based on action"""
        action = options.get('action')
        
        if not action:
            self.print_help('manage.py', 'appointment_manager')
            return
        
        try:
            if action == 'check-conflicts':
                self.check_conflicts(options)
            elif action == 'process-reminders':
                self.process_reminders(options)
            elif action == 'schedule-reminders':
                self.schedule_reminders(options)
            elif action == 'waitlist':
                self.manage_waitlist(options)
            elif action == 'analytics':
                self.generate_analytics(options)
            elif action == 'suggest-times':
                self.suggest_times(options)
            else:
                raise CommandError(f'Unknown action: {action}')
                
        except Exception as e:
            raise CommandError(f'❌ Command failed: {str(e)}')
    
    def check_conflicts(self, options):
        """Check scheduling conflicts"""
        self.stdout.write(
            self.style.SUCCESS('🔍 Checking scheduling conflicts...')
        )
        
        provider_id = options['provider_id']
        date_str = options['date']
        time_str = options['time']
        duration = options['duration']
        exclude_id = options.get('exclude')
        
        try:
            appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            appointment_time = datetime.strptime(time_str, '%H:%M').time()
        except ValueError as e:
            raise CommandError(f'Invalid date/time format: {str(e)}')
        
        conflicts = AppointmentSchedulingService.check_scheduling_conflicts(
            provider_id=provider_id,
            appointment_date=appointment_date,
            start_time=appointment_time,
            duration_minutes=duration,
            exclude_appointment_id=exclude_id
        )
        
        if not conflicts:
            self.stdout.write(
                self.style.SUCCESS('✅ No conflicts found - time slot is available')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'⚠️  Found {len(conflicts)} conflict(s):')
            )
            
            for i, conflict in enumerate(conflicts, 1):
                self.stdout.write(f"\n{i}. {conflict.get('conflict_type', 'Unknown conflict')}")
                
                if 'patient_name' in conflict:
                    self.stdout.write(f"   Patient: {conflict['patient_name']}")
                    self.stdout.write(f"   Existing time: {conflict['existing_start']} - {conflict['existing_end']}")
                
                if 'message' in conflict:
                    self.stdout.write(f"   Details: {conflict['message']}")
                
                severity = conflict.get('severity', 'medium')
                if severity == 'high':
                    self.stdout.write(
                        self.style.ERROR(f"   Severity: {severity.upper()}")
                    )
                else:
                    self.stdout.write(f"   Severity: {severity}")
    
    def process_reminders(self, options):
        """Process pending reminders"""
        self.stdout.write(
            self.style.SUCCESS('📨 Processing pending reminders...')
        )
        
        dry_run = options.get('dry_run', False)
        
        if dry_run:
            self.stdout.write('🔍 DRY RUN MODE - No reminders will be sent')
        
        current_time = timezone.now()
        pending_reminders = AppointmentReminder.objects.filter(
            status='scheduled',
            scheduled_datetime__lte=current_time
        )
        
        self.stdout.write(f'📊 Found {pending_reminders.count()} pending reminders')
        
        if dry_run:
            for reminder in pending_reminders[:10]:  # Show first 10
                self.stdout.write(
                    f"   Would send {reminder.reminder_type} to {reminder.appointment.patient.get_full_name()}"
                )
                self.stdout.write(
                    f"   Scheduled for: {reminder.scheduled_datetime}"
                )
            
            if pending_reminders.count() > 10:
                self.stdout.write(f"   ... and {pending_reminders.count() - 10} more")
        
        else:
            results = AppointmentReminderService.process_pending_reminders()
            
            self.stdout.write(f"\n📈 Processing Results:")
            self.stdout.write(f"   Total processed: {results['processed']}")
            self.stdout.write(f"   Successful: {results['successful']}")
            self.stdout.write(f"   Failed: {results['failed']}")
            
            if results['errors']:
                self.stdout.write(f"\n❌ Errors:")
                for error in results['errors'][:5]:  # Show first 5 errors
                    self.stdout.write(f"   {error['reminder_id']}: {error['error']}")
    
    def schedule_reminders(self, options):
        """Schedule reminders for an appointment"""
        self.stdout.write(
            self.style.SUCCESS('⏰ Scheduling appointment reminders...')
        )
        
        appointment_id = options['appointment_id']
        
        try:
            appointment = Appointment.objects.get(id=appointment_id)
            self.stdout.write(
                f"📅 Appointment: {appointment.patient.get_full_name()} on {appointment.appointment_date} at {appointment.appointment_time}"
            )
        except Appointment.DoesNotExist:
            raise CommandError(f'Appointment not found: {appointment_id}')
        
        result = AppointmentReminderService.schedule_reminders(appointment_id)
        
        if 'error' in result:
            raise CommandError(result['error'])
        
        scheduled_reminders = result['scheduled_reminders']
        
        self.stdout.write(f"✅ Scheduled {len(scheduled_reminders)} reminders:")
        
        for reminder in scheduled_reminders:
            self.stdout.write(
                f"   {reminder['type'].upper()}: {reminder['scheduled_for']}"
            )
    
    def manage_waitlist(self, options):
        """Manage waitlist operations"""
        self.stdout.write(
            self.style.SUCCESS('📋 Managing waitlist...')
        )
        
        if options.get('check_opportunities'):
            self.stdout.write('🔍 Checking waitlist opportunities...')
            
            opportunities = WaitlistService.check_waitlist_opportunities()
            
            if not opportunities:
                self.stdout.write('📭 No waitlist opportunities found')
            else:
                self.stdout.write(f'🎯 Found {len(opportunities)} opportunities:')
                
                for i, opp in enumerate(opportunities[:10], 1):  # Show first 10
                    self.stdout.write(f"\n{i}. {opp['patient_name']} ({opp['priority']})")
                    slot = opp['available_slot']
                    self.stdout.write(f"   Available: {slot['date']} at {slot['time']} ({slot['duration']} min)")
                    self.stdout.write(f"   Type: {opp['opportunity_type']}")
        
        elif options.get('add_patient'):
            patient_id = options['add_patient']
            provider_id = options.get('provider_id')
            priority = options.get('priority', 'normal')
            
            if not provider_id:
                raise CommandError('Provider ID required when adding to waitlist')
            
            try:
                from patients.models import Patient
                patient = Patient.objects.get(id=patient_id)
                self.stdout.write(f"👤 Adding patient: {patient.get_full_name()}")
            except Patient.DoesNotExist:
                raise CommandError(f'Patient not found: {patient_id}')
            
            result = WaitlistService.add_to_waitlist(
                patient_id=patient_id,
                provider_id=provider_id,
                priority=priority
            )
            
            if 'error' in result:
                raise CommandError(result['error'])
            
            self.stdout.write(f"✅ Added to waitlist:")
            self.stdout.write(f"   Entry ID: {result['waitlist_entry_id']}")
            self.stdout.write(f"   Position: {result['position']}")
            
            wait_time = result['estimated_wait_time']
            self.stdout.write(f"   Estimated wait: {wait_time['estimated_days']} days")
        
        else:
            # Show current waitlist status
            total_entries = WaitlistEntry.objects.filter(status='active').count()
            self.stdout.write(f"📊 Current waitlist status: {total_entries} active entries")
            
            # Show by priority
            priorities = WaitlistEntry.objects.filter(status='active').values('priority').annotate(
                count=Count('id')
            )
            
            for priority_data in priorities:
                priority = priority_data['priority']
                count = priority_data['count']
                self.stdout.write(f"   {priority.title()}: {count}")
    
    def generate_analytics(self, options):
        """Generate appointment analytics"""
        self.stdout.write(
            self.style.SUCCESS('📊 Generating appointment analytics...')
        )
        
        provider_id = options.get('provider_id')
        start_date_str = options.get('start_date')
        end_date_str = options.get('end_date')
        output_file = options.get('output')
        
        # Parse dates
        start_date = None
        end_date = None
        
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                raise CommandError(f'Invalid start date format: {start_date_str}')
        
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                raise CommandError(f'Invalid end date format: {end_date_str}')
        
        # Generate statistics
        stats = AppointmentAnalyticsService.get_appointment_statistics(
            provider_id=provider_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Display results
        period = stats['period']
        self.stdout.write(f"\n📅 Analysis Period: {period['start_date']} to {period['end_date']}")
        
        totals = stats['totals']
        self.stdout.write(f"\n📈 Totals:")
        self.stdout.write(f"   Total appointments: {totals['total_appointments']}")
        self.stdout.write(f"   Completed: {totals['completed']}")
        self.stdout.write(f"   No-shows: {totals['no_shows']}")
        self.stdout.write(f"   Cancellations: {totals['cancellations']}")
        
        rates = stats['rates']
        self.stdout.write(f"\n📊 Rates:")
        self.stdout.write(f"   Completion rate: {rates['completion_rate']}%")
        self.stdout.write(f"   No-show rate: {rates['no_show_rate']}%")
        self.stdout.write(f"   Cancellation rate: {rates['cancellation_rate']}%")
        
        metrics = stats['metrics']
        self.stdout.write(f"\n⏱️  Metrics:")
        self.stdout.write(f"   Average duration: {metrics['average_duration_minutes']} minutes")
        self.stdout.write(f"   Total time: {metrics['total_duration_hours']} hours")
        
        # Appointment types
        by_type = stats['breakdowns']['by_type']
        if by_type:
            self.stdout.write(f"\n🏷️  By Type:")
            for apt_type, count in list(by_type.items())[:5]:  # Top 5
                self.stdout.write(f"   {apt_type or 'Unspecified'}: {count}")
        
        # Save to file if requested
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    json.dump({
                        'generated_at': timezone.now().isoformat(),
                        'analytics': stats
                    }, f, indent=2, default=str)
                
                self.stdout.write(f'\n💾 Analytics saved to {output_file}')
                
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Failed to save analytics: {str(e)}')
                )
    
    def suggest_times(self, options):
        """Suggest alternative appointment times"""
        self.stdout.write(
            self.style.SUCCESS('💡 Suggesting alternative appointment times...')
        )
        
        provider_id = options['provider_id']
        date_str = options['date']
        duration = options['duration']
        preferred_time_str = options.get('preferred_time')
        max_suggestions = options['max_suggestions']
        
        try:
            appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            raise CommandError(f'Invalid date format: {date_str}')
        
        preferred_time = None
        if preferred_time_str:
            try:
                preferred_time = datetime.strptime(preferred_time_str, '%H:%M').time()
            except ValueError:
                raise CommandError(f'Invalid time format: {preferred_time_str}')
        
        suggestions = AppointmentSchedulingService.suggest_alternative_times(
            provider_id=provider_id,
            appointment_date=appointment_date,
            duration_minutes=duration,
            preferred_time=preferred_time,
            max_suggestions=max_suggestions
        )
        
        if not suggestions:
            self.stdout.write(
                self.style.WARNING('😞 No available time slots found for the requested date')
            )
        else:
            self.stdout.write(f'🎯 Found {len(suggestions)} available time slots:')
            
            for i, suggestion in enumerate(suggestions, 1):
                score = suggestion['preference_score']
                
                self.stdout.write(f"\n{i}. {suggestion['start_time']} - {suggestion['end_time']}")
                self.stdout.write(f"   Duration: {suggestion['duration_minutes']} minutes")
                
                if preferred_time:
                    self.stdout.write(f"   Match score: {score:.1f}/100")
                
                if score >= 90:
                    self.stdout.write(
                        self.style.SUCCESS("   ⭐ Excellent match!")
                    )
                elif score >= 70:
                    self.stdout.write("   ✨ Good match")
                else:
                    self.stdout.write("   📝 Available")
