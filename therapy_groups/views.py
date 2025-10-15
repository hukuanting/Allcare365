"""
Therapy Groups Views
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count, Avg, F
from django.utils import timezone
from django.http import JsonResponse
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.core.paginator import Paginator
from datetime import datetime, timedelta
import logging

from .models import (
    TherapyGroup, TherapyGroupParticipant, TherapySession, 
    SessionAttendance, TherapyGroupNote
)
from .serializers import (
    TherapyGroupSerializer, TherapyGroupParticipantSerializer,
    TherapySessionSerializer, SessionAttendanceSerializer,
    TherapyGroupNoteSerializer, TherapyGroupListSerializer
)

logger = logging.getLogger(__name__)


# API ViewSets
class TherapyGroupViewSet(viewsets.ModelViewSet):
    """ViewSet for TherapyGroup model"""
    
    queryset = TherapyGroup.objects.all()
    serializer_class = TherapyGroupSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['therapy_type', 'status', 'primary_therapist', 'is_active']
    search_fields = ['name', 'description', 'location']
    ordering_fields = ['name', 'start_date', 'created_at']
    ordering = ['name']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return TherapyGroupListSerializer
        return TherapyGroupSerializer
    
    def get_queryset(self):
        """Filter queryset based on user permissions"""
        queryset = TherapyGroup.objects.all()
        
        # Filter by date range if provided
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(start_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(start_date__lte=end_date)
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def participants(self, request, pk=None):
        """Get participants for a specific therapy group"""
        group = self.get_object()
        participants = group.participants.all()
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            participants = participants.filter(status=status_filter)
        
        serializer = TherapyGroupParticipantSerializer(participants, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def sessions(self, request, pk=None):
        """Get sessions for a specific therapy group"""
        group = self.get_object()
        sessions = group.sessions.all()
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            sessions = sessions.filter(status=status_filter)
        
        serializer = TherapySessionSerializer(sessions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get statistics for a specific therapy group"""
        group = self.get_object()
        
        stats = {
            'total_participants': group.participants.count(),
            'active_participants': group.participants.filter(status='active').count(),
            'completed_participants': group.participants.filter(status='completed').count(),
            'total_sessions': group.sessions.count(),
            'completed_sessions': group.sessions.filter(status='completed').count(),
            'upcoming_sessions': group.sessions.filter(
                status='scheduled',
                scheduled_date__gte=timezone.now().date()
            ).count(),
            'average_attendance': group.sessions.aggregate(
                avg_attendance=Avg('attendance__id')
            )['avg_attendance'] or 0,
        }
        
        return Response(stats)


class TherapyGroupParticipantViewSet(viewsets.ModelViewSet):
    """ViewSet for TherapyGroupParticipant model"""
    
    queryset = TherapyGroupParticipant.objects.all()
    serializer_class = TherapyGroupParticipantSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['group', 'status', 'enrollment_date']
    search_fields = ['patient__first_name', 'patient__last_name', 'presenting_concerns']
    ordering_fields = ['enrollment_date', 'patient__last_name']
    ordering = ['enrollment_date']
    
    @action(detail=True, methods=['get'])
    def attendance_history(self, request, pk=None):
        """Get attendance history for a participant"""
        participant = self.get_object()
        attendance = participant.attendance.all()
        serializer = SessionAttendanceSerializer(attendance, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def notes(self, request, pk=None):
        """Get notes for a participant"""
        participant = self.get_object()
        notes = participant.notes.all()
        serializer = TherapyGroupNoteSerializer(notes, many=True)
        return Response(serializer.data)


class TherapySessionViewSet(viewsets.ModelViewSet):
    """ViewSet for TherapySession model"""
    
    queryset = TherapySession.objects.all()
    serializer_class = TherapySessionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['group', 'status', 'therapist', 'scheduled_date']
    search_fields = ['topic', 'objectives', 'session_notes']
    ordering_fields = ['scheduled_date', 'scheduled_time', 'session_number']
    ordering = ['scheduled_date', 'scheduled_time']
    
    @action(detail=True, methods=['get'])
    def attendance(self, request, pk=None):
        """Get attendance for a specific session"""
        session = self.get_object()
        attendance = session.attendance.all()
        serializer = SessionAttendanceSerializer(attendance, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_attendance(self, request, pk=None):
        """Mark attendance for a session"""
        session = self.get_object()
        participant_id = request.data.get('participant_id')
        attendance_status = request.data.get('status', 'present')
        
        if not participant_id:
            return Response(
                {'error': 'participant_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            participant = TherapyGroupParticipant.objects.get(
                id=participant_id, group=session.group
            )
            
            attendance, created = SessionAttendance.objects.get_or_create(
                session=session,
                participant=participant,
                defaults={'status': attendance_status}
            )
            
            if not created:
                attendance.status = attendance_status
                attendance.save()
            
            # Update participant attendance counters
            if attendance_status == 'present':
                participant.sessions_attended = F('sessions_attended') + 1
            else:
                participant.sessions_missed = F('sessions_missed') + 1
            participant.save()
            
            serializer = SessionAttendanceSerializer(attendance)
            return Response(serializer.data)
            
        except TherapyGroupParticipant.DoesNotExist:
            return Response(
                {'error': 'Participant not found in this group'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class SessionAttendanceViewSet(viewsets.ModelViewSet):
    """ViewSet for SessionAttendance model"""
    
    queryset = SessionAttendance.objects.all()
    serializer_class = SessionAttendanceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['session', 'participant', 'status']
    ordering_fields = ['session__scheduled_date', 'participant__patient__last_name']
    ordering = ['session__scheduled_date']


class TherapyGroupNoteViewSet(viewsets.ModelViewSet):
    """ViewSet for TherapyGroupNote model"""
    
    queryset = TherapyGroupNote.objects.all()
    serializer_class = TherapyGroupNoteSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['group', 'participant', 'session', 'note_type', 'author']
    search_fields = ['title', 'content', 'observations']
    ordering_fields = ['created_at', 'title']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter notes based on confidentiality and user permissions"""
        queryset = TherapyGroupNote.objects.all()
        
        # If user is not staff, exclude confidential notes from other authors
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(is_confidential=False) | Q(author=self.request.user)
            )
        
        return queryset


# Web Views
@login_required
def therapy_groups_dashboard(request):
    """Therapy groups dashboard view"""
    
    # Get summary statistics
    total_groups = TherapyGroup.objects.filter(is_active=True).count()
    active_groups = TherapyGroup.objects.filter(status='active').count()
    total_participants = TherapyGroupParticipant.objects.filter(status='active').count()
    
    # Get recent groups
    recent_groups = TherapyGroup.objects.filter(is_active=True).order_by('-created_at')[:5]
    
    # Get upcoming sessions
    upcoming_sessions = TherapySession.objects.filter(
        status='scheduled',
        scheduled_date__gte=timezone.now().date()
    ).order_by('scheduled_date', 'scheduled_time')[:10]
    
    context = {
        'total_groups': total_groups,
        'active_groups': active_groups,
        'total_participants': total_participants,
        'recent_groups': recent_groups,
        'upcoming_sessions': upcoming_sessions,
        'title': 'Therapy Groups Dashboard'
    }
    
    return render(request, 'therapy_groups/dashboard.html', context)


@login_required
def therapy_group_list(request):
    """List all therapy groups"""
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    therapy_type_filter = request.GET.get('therapy_type', '')
    search_query = request.GET.get('search', '')
    
    # Build queryset
    groups = TherapyGroup.objects.filter(is_active=True)
    
    if status_filter:
        groups = groups.filter(status=status_filter)
    
    if therapy_type_filter:
        groups = groups.filter(therapy_type=therapy_type_filter)
    
    if search_query:
        groups = groups.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(location__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(groups, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'therapy_type_filter': therapy_type_filter,
        'search_query': search_query,
        'status_choices': TherapyGroup.STATUS_CHOICES,
        'therapy_type_choices': TherapyGroup.THERAPY_TYPE_CHOICES,
        'title': 'Therapy Groups'
    }
    
    return render(request, 'therapy_groups/group_list.html', context)


@login_required
def therapy_group_detail(request, group_id):
    """View therapy group details"""
    
    group = get_object_or_404(TherapyGroup, id=group_id)
    
    # Get participants
    participants = group.participants.filter(status='active')
    
    # Get recent sessions
    recent_sessions = group.sessions.order_by('-scheduled_date', '-scheduled_time')[:10]
    
    # Get upcoming sessions
    upcoming_sessions = group.sessions.filter(
        status='scheduled',
        scheduled_date__gte=timezone.now().date()
    ).order_by('scheduled_date', 'scheduled_time')[:5]
    
    # Get recent notes
    recent_notes = group.notes.order_by('-created_at')[:10]
    
    context = {
        'group': group,
        'participants': participants,
        'recent_sessions': recent_sessions,
        'upcoming_sessions': upcoming_sessions,
        'recent_notes': recent_notes,
        'title': f'Therapy Group - {group.name}'
    }
    
    return render(request, 'therapy_groups/group_detail.html', context)


@login_required
def session_list(request):
    """List therapy sessions"""
    
    # Get filter parameters
    group_filter = request.GET.get('group', '')
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Build queryset
    sessions = TherapySession.objects.all()
    
    if group_filter:
        sessions = sessions.filter(group_id=group_filter)
    
    if status_filter:
        sessions = sessions.filter(status=status_filter)
    
    if date_from:
        sessions = sessions.filter(scheduled_date__gte=date_from)
    
    if date_to:
        sessions = sessions.filter(scheduled_date__lte=date_to)
    
    sessions = sessions.order_by('-scheduled_date', '-scheduled_time')
    
    # Pagination
    paginator = Paginator(sessions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get groups for filter dropdown
    groups = TherapyGroup.objects.filter(is_active=True).order_by('name')
    
    context = {
        'page_obj': page_obj,
        'groups': groups,
        'group_filter': group_filter,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'status_choices': TherapySession.STATUS_CHOICES,
        'title': 'Therapy Sessions'
    }
    
    return render(request, 'therapy_groups/session_list.html', context)


@login_required
def session_detail(request, session_id):
    """View session details"""
    
    session = get_object_or_404(TherapySession, id=session_id)
    
    # Get attendance
    attendance = session.attendance.all()
    
    # Get session notes
    notes = session.notes.order_by('-created_at')
    
    context = {
        'session': session,
        'attendance': attendance,
        'notes': notes,
        'title': f'Session - {session}'
    }
    
    return render(request, 'therapy_groups/session_detail.html', context)
