"""
Therapy Groups URL Configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# API router setup
router = DefaultRouter()
router.register(r'groups', views.TherapyGroupViewSet, basename='therapygroup')
router.register(r'participants', views.TherapyGroupParticipantViewSet, basename='therapygroupparticipant')
router.register(r'sessions', views.TherapySessionViewSet, basename='therapysession')
router.register(r'attendance', views.SessionAttendanceViewSet, basename='sessionattendance')
router.register(r'notes', views.TherapyGroupNoteViewSet, basename='therapygroupnote')

app_name = 'therapy_groups'

urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
    
    # Web views
    path('', views.therapy_groups_dashboard, name='dashboard'),
    path('groups/', views.therapy_group_list, name='group_list'),
    path('groups/<uuid:group_id>/', views.therapy_group_detail, name='group_detail'),
    path('sessions/', views.session_list, name='session_list'),
    path('sessions/<uuid:session_id>/', views.session_detail, name='session_detail'),
]
