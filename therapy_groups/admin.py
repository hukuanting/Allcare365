"""
Therapy Groups Admin Configuration
"""
from django.contrib import admin
from .models import (
    TherapyGroup, TherapyGroupParticipant, TherapySession, 
    SessionAttendance, TherapyGroupNote
)


@admin.register(TherapyGroup)
class TherapyGroupAdmin(admin.ModelAdmin):
    """Admin configuration for TherapyGroup model"""
    
    list_display = ['name', 'therapy_type', 'status', 'primary_therapist', 'start_date', 'current_participants_count', 'max_participants']
    list_filter = ['therapy_type', 'status', 'start_date', 'is_active']
    search_fields = ['name', 'description', 'location']
    readonly_fields = ['id', 'created_at', 'updated_at', 'current_participants_count', 'available_slots', 'is_full']
    filter_horizontal = ['co_therapists']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'description', 'therapy_type', 'status', 'is_active')
        }),
        ('Schedule', {
            'fields': ('start_date', 'end_date', 'session_duration', 'max_participants')
        }),
        ('Staff', {
            'fields': ('primary_therapist', 'co_therapists')
        }),
        ('Location', {
            'fields': ('location', 'room_number', 'contact_info')
        }),
        ('Clinical Information', {
            'fields': ('treatment_goals', 'inclusion_criteria', 'exclusion_criteria')
        }),
        ('Administrative', {
            'fields': ('admin_notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('current_participants_count', 'available_slots', 'is_full'),
            'classes': ('collapse',)
        })
    )


@admin.register(TherapyGroupParticipant)
class TherapyGroupParticipantAdmin(admin.ModelAdmin):
    """Admin configuration for TherapyGroupParticipant model"""
    
    list_display = ['patient', 'group', 'status', 'enrollment_date', 'sessions_attended', 'sessions_missed', 'attendance_rate']
    list_filter = ['status', 'enrollment_date', 'group__therapy_type']
    search_fields = ['patient__first_name', 'patient__last_name', 'group__name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'attendance_rate']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'group', 'patient', 'status')
        }),
        ('Enrollment', {
            'fields': ('enrollment_date', 'completion_date')
        }),
        ('Clinical Information', {
            'fields': ('presenting_concerns', 'treatment_goals', 'progress_notes')
        }),
        ('Emergency Contact', {
            'fields': ('emergency_contact', 'emergency_phone', 'referral_source')
        }),
        ('Attendance', {
            'fields': ('sessions_attended', 'sessions_missed', 'attendance_rate')
        }),
        ('Administrative', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(TherapySession)
class TherapySessionAdmin(admin.ModelAdmin):
    """Admin configuration for TherapySession model"""
    
    list_display = ['__str__', 'group', 'scheduled_date', 'scheduled_time', 'status', 'therapist']
    list_filter = ['status', 'scheduled_date', 'group__therapy_type']
    search_fields = ['group__name', 'topic', 'therapist__first_name', 'therapist__last_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    filter_horizontal = ['co_therapists']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'group', 'session_number', 'status')
        }),
        ('Schedule', {
            'fields': ('scheduled_date', 'scheduled_time', 'duration')
        }),
        ('Session Content', {
            'fields': ('topic', 'objectives', 'activities', 'homework_assigned')
        }),
        ('Clinical Notes', {
            'fields': ('session_notes', 'outcomes')
        }),
        ('Staff', {
            'fields': ('therapist', 'co_therapists')
        }),
        ('Administrative', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(SessionAttendance)
class SessionAttendanceAdmin(admin.ModelAdmin):
    """Admin configuration for SessionAttendance model"""
    
    list_display = ['participant', 'session', 'status', 'arrival_time', 'departure_time']
    list_filter = ['status', 'session__scheduled_date', 'session__group']
    search_fields = ['participant__patient__first_name', 'participant__patient__last_name', 'session__group__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'session', 'participant', 'status')
        }),
        ('Attendance Details', {
            'fields': ('arrival_time', 'departure_time', 'notes')
        }),
        ('Administrative', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(TherapyGroupNote)
class TherapyGroupNoteAdmin(admin.ModelAdmin):
    """Admin configuration for TherapyGroupNote model"""
    
    list_display = ['title', 'group', 'participant', 'note_type', 'author', 'created_at', 'is_confidential']
    list_filter = ['note_type', 'is_confidential', 'created_at', 'group__therapy_type']
    search_fields = ['title', 'content', 'group__name', 'participant__patient__first_name', 'participant__patient__last_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'group', 'participant', 'session', 'note_type', 'title', 'is_confidential')
        }),
        ('Content', {
            'fields': ('content', 'observations', 'interventions', 'response', 'plan')
        }),
        ('Administrative', {
            'fields': ('author', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
