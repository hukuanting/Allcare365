from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'reports'

router = DefaultRouter()
router.register('templates', views.ReportTemplateViewSet)
router.register('executions', views.ReportExecutionViewSet)
router.register('favorites', views.ReportFavoriteViewSet)
router.register('analytics', views.ReportAnalyticsViewSet, basename='report-analytics')
router.register('builtin', views.BuiltInReportsViewSet, basename='builtin-reports')

urlpatterns = [
    path('', include(router.urls)),
]
