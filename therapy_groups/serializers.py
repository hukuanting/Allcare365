"""
Therapy Groups Serializers
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from patients.models import Patient
from .models import (
    TherapyGroup, TherapyGroupParticipant, TherapySession, 
    SessionAttendance, TherapyGroupNote
)


class TherapyGroupSerializer(serializers.ModelSerializer):
    """Serializer for TherapyGroup model"""
    
    primary_therapist_name = serializers.CharField(source='primary_therapist.get_full_name', read_only=True)
    co_therapists_names = serializers.SerializerMethodField()
    current_participants_count = serializers.ReadOnlyField()
    available_slots = serializers.ReadOnlyField()
    is_full = serializers.ReadOnlyField()
    total_sessions = serializers.ReadOnlyField()
    completed_sessions = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    therapy_type_display = serializers.CharField(source='get_therapy_type_display', read_only=True)
    
    class Meta:
        model = TherapyGroup
        fields = [
            'id', 'name', 'description', 'therapy_type', 'therapy_type_display',
            'status', 'status_display', 'start_date', 'end_date', 'session_duration',
            'max_participants', 'primary_therapist', 'primary_therapist_name',
            'co_therapists', 'co_therapists_names', 'location', 'room_number',
            'contact_info', 'treatment_goals', 'inclusion_criteria', 'exclusion_criteria',
            'admin_notes', 'is_active', 'current_participants_count', 'available_slots',
            'is_full', 'total_sessions', 'completed_sessions', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_co_therapists_names(self, obj):
        """Get names of co-therapists"""
        return [user.get_full_name() or user.username for user in obj.co_therapists.all()]
    
    def validate(self, data):
        """Validate therapy group data"""
        if data.get('end_date') and data.get('start_date'):
            if data['end_date'] < data['start_date']:
                raise serializers.ValidationError("End date cannot be before start date")
        
        if data.get('max_participants', 0) < 1:
            raise serializers.ValidationError("Maximum participants must be at least 1")
        
        return data


class TherapyGroupParticipantSerializer(serializers.ModelSerializer):
    """Serializer for TherapyGroupParticipant model"""
    
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    attendance_rate = serializers.ReadOnlyField()
    
    class Meta:
        model = TherapyGroupParticipant
        fields = [
            'id', 'group', 'group_name', 'patient', 'patient_name', 'status', 'status_display',
            'enrollment_date', 'completion_date', 'presenting_concerns', 'treatment_goals',
            'progress_notes', 'emergency_contact', 'emergency_phone', 'referral_source',
            'sessions_attended', 'sessions_missed', 'attendance_rate',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validate participant data"""
        if data.get('completion_date') and data.get('enrollment_date'):
            if data['completion_date'] < data['enrollment_date']:
                raise serializers.ValidationError("Completion date cannot be before enrollment date")
        
        # Check if group is full when adding new participant
        if not self.instance and data.get('group'):
            if data['group'].is_full:
                raise serializers.ValidationError("This therapy group is full")
        
        return data


class TherapySessionSerializer(serializers.ModelSerializer):
    """Serializer for TherapySession model"""
    
    group_name = serializers.CharField(source='group.name', read_only=True)
    therapist_name = serializers.CharField(source='therapist.get_full_name', read_only=True)
    co_therapists_names = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    attendance_count = serializers.SerializerMethodField()
    
    class Meta:
        model = TherapySession
        fields = [
            'id', 'group', 'group_name', 'session_number', 'scheduled_date', 'scheduled_time',
            'duration', 'topic', 'objectives', 'activities', 'session_notes',
            'homework_assigned', 'status', 'status_display', 'outcomes',
            'therapist', 'therapist_name', 'co_therapists', 'co_therapists_names',
            'attendance_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_co_therapists_names(self, obj):
        """Get names of co-therapists"""
        return [user.get_full_name() or user.username for user in obj.co_therapists.all()]
    
    def get_attendance_count(self, obj):
        """Get attendance count for this session"""
        return {
            'present': obj.attendance.filter(status='present').count(),
            'absent': obj.attendance.filter(status='absent').count(),
            'late': obj.attendance.filter(status='late').count(),
            'left_early': obj.attendance.filter(status='left_early').count(),
        }


class SessionAttendanceSerializer(serializers.ModelSerializer):
    """Serializer for SessionAttendance model"""
    
    participant_name = serializers.CharField(source='participant.patient.get_full_name', read_only=True)
    session_info = serializers.CharField(source='session.__str__', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = SessionAttendance
        fields = [
            'id', 'session', 'session_info', 'participant', 'participant_name',
            'status', 'status_display', 'arrival_time', 'departure_time', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validate attendance data"""
        if data.get('departure_time') and data.get('arrival_time'):
            if data['departure_time'] < data['arrival_time']:
                raise serializers.ValidationError("Departure time cannot be before arrival time")
        
        return data


class TherapyGroupNoteSerializer(serializers.ModelSerializer):
    """Serializer for TherapyGroupNote model"""
    
    group_name = serializers.CharField(source='group.name', read_only=True)
    participant_name = serializers.CharField(source='participant.patient.get_full_name', read_only=True)
    session_info = serializers.CharField(source='session.__str__', read_only=True)
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    note_type_display = serializers.CharField(source='get_note_type_display', read_only=True)
    
    class Meta:
        model = TherapyGroupNote
        fields = [
            'id', 'group', 'group_name', 'participant', 'participant_name',
            'session', 'session_info', 'note_type', 'note_type_display',
            'title', 'content', 'observations', 'interventions', 'response',
            'plan', 'author', 'author_name', 'is_confidential',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        """Create note with current user as author"""
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)


class TherapyGroupListSerializer(serializers.ModelSerializer):
    """Simplified serializer for therapy group lists"""
    
    primary_therapist_name = serializers.CharField(source='primary_therapist.get_full_name', read_only=True)
    current_participants_count = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    therapy_type_display = serializers.CharField(source='get_therapy_type_display', read_only=True)
    
    class Meta:
        model = TherapyGroup
        fields = [
            'id', 'name', 'therapy_type', 'therapy_type_display',
            'status', 'status_display', 'start_date', 'end_date',
            'primary_therapist_name', 'current_participants_count',
            'max_participants', 'location'
        ]
