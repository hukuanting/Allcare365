from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# API Router
router = DefaultRouter()
router.register(r'channels', views.MessageChannelViewSet, basename='channel')
router.register(r'threads', views.MessageThreadViewSet, basename='thread')
router.register(r'messages', views.MessageViewSet, basename='message')
router.register(r'notifications', views.NotificationViewSet, basename='notification')
router.register(r'bulk-messages', views.BulkMessageViewSet, basename='bulk-message')
router.register(r'templates', views.MessageTemplateViewSet, basename='template')

app_name = 'communications'

urlpatterns = [
    # Web Views
    path('', views.CommunicationsDashboardView.as_view(), name='dashboard'),
    path('channels/', views.ChannelListView.as_view(), name='channel_list'),
    path('channels/<uuid:pk>/', views.ChannelDetailView.as_view(), name='channel_detail'),
    path('threads/<uuid:pk>/', views.ThreadDetailView.as_view(), name='thread_detail'),
    path('notifications/', views.notifications_view, name='notifications'),
    
    # AJAX Views
    path('ajax/send-message/', views.send_message_ajax, name='send_message_ajax'),
    path('ajax/notifications/<uuid:notification_id>/read/', 
         views.mark_notification_read_ajax, name='mark_notification_read_ajax'),
    
    # API Endpoints
    path('api/', include(router.urls)),
    path('api/user-channels/', views.get_user_channels, name='api_user_channels'),
    path('api/unread-counts/', views.get_unread_counts, name='api_unread_counts'),
]
