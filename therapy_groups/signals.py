"""
Therapy Groups Signals
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import TherapyGroupParticipant, SessionAttendance, TherapySession
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=SessionAttendance)
def update_participant_attendance(sender, instance, created, **kwargs):
    """Update participant attendance counters when attendance is marked"""
    if created:
        participant = instance.participant
        
        # Update attendance counters
        if instance.status == 'present':
            participant.sessions_attended += 1
        else:
            participant.sessions_missed += 1
        
        participant.save(update_fields=['sessions_attended', 'sessions_missed'])
        
        logger.info(f"Updated attendance for participant {participant.id}: "
                   f"attended={participant.sessions_attended}, missed={participant.sessions_missed}")


@receiver(post_delete, sender=SessionAttendance)
def revert_participant_attendance(sender, instance, **kwargs):
    """Revert participant attendance counters when attendance is deleted"""
    participant = instance.participant
    
    # Revert attendance counters
    if instance.status == 'present':
        participant.sessions_attended = max(0, participant.sessions_attended - 1)
    else:
        participant.sessions_missed = max(0, participant.sessions_missed - 1)
    
    participant.save(update_fields=['sessions_attended', 'sessions_missed'])
    
    logger.info(f"Reverted attendance for participant {participant.id}: "
               f"attended={participant.sessions_attended}, missed={participant.sessions_missed}")


@receiver(post_save, sender=TherapySession)
def create_attendance_records(sender, instance, created, **kwargs):
    """Create attendance records for all active participants when a session is created"""
    if created and instance.status == 'scheduled':
        # Get all active participants in the group
        participants = instance.group.participants.filter(status='active')
        
        # Create attendance records for each participant
        attendance_records = []
        for participant in participants:
            attendance_records.append(
                SessionAttendance(
                    session=instance,
                    participant=participant,
                    status='present'  # Default to present, can be changed later
                )
            )
        
        # Bulk create attendance records
        if attendance_records:
            SessionAttendance.objects.bulk_create(attendance_records)
            logger.info(f"Created {len(attendance_records)} attendance records for session {instance.id}")


@receiver(post_save, sender=TherapyGroupParticipant)
def handle_participant_status_change(sender, instance, created, **kwargs):
    """Handle participant status changes"""
    if not created:
        # If participant status changed to completed, set completion date
        if instance.status == 'completed' and not instance.completion_date:
            from django.utils import timezone
            instance.completion_date = timezone.now().date()
            instance.save(update_fields=['completion_date'])
            
            logger.info(f"Set completion date for participant {instance.id}")
        
        # If participant status changed from active to inactive,
        # remove them from future scheduled sessions
        if instance.status in ['inactive', 'dropped', 'completed']:
            future_sessions = TherapySession.objects.filter(
                group=instance.group,
                status='scheduled',
                scheduled_date__gt=timezone.now().date()
            )
            
            # Remove attendance records for future sessions
            deleted_count = SessionAttendance.objects.filter(
                session__in=future_sessions,
                participant=instance
            ).delete()[0]
            
            if deleted_count > 0:
                logger.info(f"Removed {deleted_count} future attendance records for participant {instance.id}")
