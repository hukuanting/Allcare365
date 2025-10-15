from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import auth_views

# 創建路由器
router = DefaultRouter()
router.register(r'providers', views.ProviderViewSet)
router.register(r'facilities', views.FacilityViewSet)
router.register(r'departments', views.DepartmentViewSet)
router.register(r'user-profiles', views.UserProfileViewSet)
router.register(r'users', views.UserViewSet)
router.register(r'audit-logs', views.AuditLogViewSet)
router.register(r'system-settings', views.SystemSettingViewSet)
router.register(r'system-stats', views.SystemStatsViewSet, basename='system-stats')

# 權限管理相關路由
router.register(r'roles', auth_views.RoleViewSet)
router.register(r'user-roles', auth_views.UserRoleViewSet)
router.register(r'session-logs', auth_views.SessionLogViewSet)
router.register(r'login-attempts', auth_views.LoginAttemptViewSet)
router.register(r'api-keys', auth_views.APIKeyViewSet)
router.register(r'two-factor-auth', auth_views.TwoFactorAuthViewSet)

app_name = 'administration'

urlpatterns = [
    path('', include(router.urls)),
    # 可以在這裡添加其他非 API 路由
]
