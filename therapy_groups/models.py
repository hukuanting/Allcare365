"""
Therapy Groups Models
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from patients.models import Patient
from medical_records.models import BaseModel
import uuid


class TherapyGroup(BaseModel):
    """Model for therapy groups"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    THERAPY_TYPE_CHOICES = [
        ('individual', 'Individual Therapy'),
        ('group', 'Group Therapy'),
        ('family', 'Family Therapy'),
        ('couples', 'Couples Therapy'),
        ('cognitive', 'Cognitive Behavioral Therapy'),
        ('psychodynamic', 'Psychodynamic Therapy'),
        ('humanistic', 'Humanistic Therapy'),
        ('behavioral', 'Behavioral Therapy'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=200, help_text="Name of the therapy group")
    description = models.TextField(blank=True, help_text="Description of the therapy group")
    therapy_type = models.CharField(max_length=20, choices=THERAPY_TYPE_CHOICES, default='group')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Schedule Information
    start_date = models.DateField(help_text="Start date of the therapy group")
    end_date = models.DateField(blank=True, null=True, help_text="End date of the therapy group")
    session_duration = models.IntegerField(
        validators=[MinValueValidator(15), MaxValueValidator(480)],
        help_text="Duration of each session in minutes"
    )
    max_participants = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(50)],
        default=10,
        help_text="Maximum number of participants"
    )
    
    # Staff Information
    primary_therapist = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='primary_therapy_groups',
        help_text="Primary therapist for this group"
    )
    co_therapists = models.ManyToManyField(
        User, blank=True, related_name='co_therapy_groups',
        help_text="Co-therapists for this group"
    )
    
    # Location and Contact
    location = models.CharField(max_length=200, blank=True, help_text="Location where therapy takes place")
    room_number = models.CharField(max_length=50, blank=True, help_text="Room number or identifier")
    contact_info = models.TextField(blank=True, help_text="Contact information for the group")
    
    # Clinical Information
    treatment_goals = models.TextField(blank=True, help_text="Treatment goals for the group")
    inclusion_criteria = models.TextField(blank=True, help_text="Criteria for group inclusion")
    exclusion_criteria = models.TextField(blank=True, help_text="Criteria for group exclusion")
    
    # Administrative
    admin_notes = models.TextField(blank=True, help_text="Administrative notes")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'therapy_groups'
        verbose_name = 'Therapy Group'
        verbose_name_plural = 'Therapy Groups'
        ordering = ['name', 'start_date']
        
    def __str__(self):
        return f"{self.name} ({self.get_therapy_type_display()})"
    
    @property
    def current_participants_count(self):
        """Get current number of active participants"""
        return self.participants.filter(status='active').count()
    
    @property
    def available_slots(self):
        """Get number of available slots"""
        return max(0, self.max_participants - self.current_participants_count)
    
    @property
    def is_full(self):
        """Check if group is full"""
        return self.current_participants_count >= self.max_participants
    
    @property
    def total_sessions(self):
        """Get total number of sessions"""
        return self.sessions.count()
    
    @property
    def completed_sessions(self):
        """Get number of completed sessions"""
        return self.sessions.filter(status='completed').count()


class TherapyGroupParticipant(BaseModel):
    """Model for therapy group participants"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('completed', 'Completed'),
        ('dropped', 'Dropped'),
        ('transferred', 'Transferred'),
    ]
    
    group = models.ForeignKey(TherapyGroup, on_delete=models.CASCADE, related_name='participants')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='therapy_groups')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Enrollment Information
    enrollment_date = models.DateField(default=timezone.now)
    completion_date = models.DateField(blank=True, null=True)
    
    # Clinical Information
    presenting_concerns = models.TextField(blank=True, help_text="Patient's presenting concerns")
    treatment_goals = models.TextField(blank=True, help_text="Individual treatment goals")
    progress_notes = models.TextField(blank=True, help_text="Progress notes")
    
    # Administrative
    emergency_contact = models.CharField(max_length=200, blank=True)
    emergency_phone = models.CharField(max_length=20, blank=True)
    referral_source = models.CharField(max_length=200, blank=True)
    
    # Attendance tracking
    sessions_attended = models.IntegerField(default=0)
    sessions_missed = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'therapy_group_participants'
        verbose_name = 'Therapy Group Participant'
        verbose_name_plural = 'Therapy Group Participants'
        unique_together = ['group', 'patient']
        ordering = ['enrollment_date']
        
    def __str__(self):
        return f"{self.patient} in {self.group.name}"
    
    @property
    def attendance_rate(self):
        """Calculate attendance rate"""
        total_sessions = self.sessions_attended + self.sessions_missed
        if total_sessions == 0:
            return 0
        return (self.sessions_attended / total_sessions) * 100


class TherapySession(BaseModel):
    """Model for individual therapy sessions"""
    
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]
    
    group = models.ForeignKey(TherapyGroup, on_delete=models.CASCADE, related_name='sessions')
    session_number = models.IntegerField(help_text="Session number in the series")
    
    # Schedule Information
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField()
    duration = models.IntegerField(help_text="Duration in minutes")
    
    # Session Details
    topic = models.CharField(max_length=200, blank=True, help_text="Session topic or theme")
    objectives = models.TextField(blank=True, help_text="Session objectives")
    activities = models.TextField(blank=True, help_text="Activities and interventions used")
    
    # Clinical Notes
    session_notes = models.TextField(blank=True, help_text="Clinical notes from the session")
    homework_assigned = models.TextField(blank=True, help_text="Homework or tasks assigned")
    
    # Status and Outcomes
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    outcomes = models.TextField(blank=True, help_text="Session outcomes and observations")
    
    # Staff
    therapist = models.ForeignKey(User, on_delete=models.CASCADE, related_name='therapy_sessions')
    co_therapists = models.ManyToManyField(User, blank=True, related_name='co_therapy_sessions')
    
    class Meta:
        db_table = 'therapy_sessions'
        verbose_name = 'Therapy Session'
        verbose_name_plural = 'Therapy Sessions'
        unique_together = ['group', 'session_number']
        ordering = ['scheduled_date', 'scheduled_time']
        
    def __str__(self):
        return f"{self.group.name} - Session {self.session_number}"


class SessionAttendance(BaseModel):
    """Model for tracking attendance at therapy sessions"""
    
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('left_early', 'Left Early'),
    ]
    
    session = models.ForeignKey(TherapySession, on_delete=models.CASCADE, related_name='attendance')
    participant = models.ForeignKey(TherapyGroupParticipant, on_delete=models.CASCADE, related_name='attendance')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present')
    
    # Attendance Details
    arrival_time = models.TimeField(blank=True, null=True)
    departure_time = models.TimeField(blank=True, null=True)
    notes = models.TextField(blank=True, help_text="Notes about attendance")
    
    class Meta:
        db_table = 'session_attendance'
        verbose_name = 'Session Attendance'
        verbose_name_plural = 'Session Attendance'
        unique_together = ['session', 'participant']
        ordering = ['session__scheduled_date', 'participant__patient__last_name']
        
    def __str__(self):
        return f"{self.participant.patient} - {self.session} ({self.status})"


class TherapyGroupNote(BaseModel):
    """Model for therapy group notes and documentation"""
    
    NOTE_TYPE_CHOICES = [
        ('progress', 'Progress Note'),
        ('incident', 'Incident Report'),
        ('assessment', 'Assessment'),
        ('treatment_plan', 'Treatment Plan'),
        ('discharge', 'Discharge Summary'),
        ('other', 'Other'),
    ]
    
    group = models.ForeignKey(TherapyGroup, on_delete=models.CASCADE, related_name='notes')
    participant = models.ForeignKey(
        TherapyGroupParticipant, on_delete=models.CASCADE, 
        related_name='notes', blank=True, null=True
    )
    session = models.ForeignKey(
        TherapySession, on_delete=models.CASCADE, 
        related_name='notes', blank=True, null=True
    )
    
    note_type = models.CharField(max_length=20, choices=NOTE_TYPE_CHOICES, default='progress')
    title = models.CharField(max_length=200)
    content = models.TextField()
    
    # Clinical Information
    observations = models.TextField(blank=True, help_text="Clinical observations")
    interventions = models.TextField(blank=True, help_text="Interventions used")
    response = models.TextField(blank=True, help_text="Patient response to interventions")
    plan = models.TextField(blank=True, help_text="Treatment plan or next steps")
    
    # Administrative
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='therapy_notes')
    is_confidential = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'therapy_group_notes'
        verbose_name = 'Therapy Group Note'
        verbose_name_plural = 'Therapy Group Notes'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.title} - {self.group.name}"
