from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# 創建API路由器
router = DefaultRouter()
router.register(r'appointment-types', views.AppointmentTypeViewSet)
router.register(r'appointments', views.AppointmentViewSet)
router.register(r'waiting-list', views.WaitingListViewSet, basename='waitinglist')
router.register(r'recurring-appointments', views.RecurringAppointmentViewSet)
router.register(r'appointment-notes', views.AppointmentNoteViewSet)
router.register(r'schedules', views.ScheduleViewSet, basename='schedule')

app_name = 'appointments'

# 組合API和模板路由
urlpatterns = [
    # 前端頁面URL
    path('', views.appointment_list_view, name='appointment_list'),
    
    # API路由 (for /api/v1/appointments/)
    path('api/', include(router.urls)),
    
    # Template views (for /appointments/ when namespace is different)
    path('web/', views.appointment_management_view, name='appointment_management'),
    path('web/modern/', views.modern_appointment_management_view, name='modern_appointment_management'),
    path('web/management/', views.appointment_management_view, name='appointment_management_detail'),
    path('web/calendar/', views.appointment_calendar_view, name='appointment_calendar'),
    path('web/schedule/', views.appointment_schedule_view, name='appointment_schedule'),
    path('web/reports/', views.appointment_reports_view, name='appointment_reports'),
    
    # Legacy API URLs for backward compatibility
    path('api/', include(router.urls)),
]
