from django.contrib import admin
from .models import Provider, Facility, Department, UserProfile, AuditLog, SystemSetting


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ['user', 'provider_type', 'license_number', 'primary_specialty', 'is_accepting_patients', 'is_active']
    list_filter = ['provider_type', 'is_accepting_patients', 'is_active']
    search_fields = ['user__first_name', 'user__last_name', 'license_number', 'primary_specialty']
    ordering = ['user__last_name', 'user__first_name']


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ['name', 'facility_type', 'city', 'state', 'administrator', 'is_active']
    list_filter = ['facility_type', 'state', 'is_active']
    search_fields = ['name', 'city', 'state']
    ordering = ['name']


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'facility', 'head_of_department', 'is_active']
    list_filter = ['facility', 'is_active']
    search_fields = ['name', 'facility__name']
    ordering = ['facility', 'name']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'employee_id', 'department', 'job_title', 'hire_date', 'is_active']
    list_filter = ['department', 'is_active']
    search_fields = ['user__first_name', 'user__last_name', 'employee_id', 'job_title']
    ordering = ['user__last_name', 'user__first_name']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'table_name', 'timestamp', 'ip_address']
    list_filter = ['action', 'table_name', 'timestamp']
    search_fields = ['user__username', 'action', 'table_name']
    ordering = ['-timestamp']
    readonly_fields = ['user', 'action', 'table_name', 'record_id', 'old_values', 'new_values', 'ip_address', 'user_agent', 'timestamp']


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ['category', 'key', 'value', 'data_type', 'is_active']
    list_filter = ['category', 'data_type', 'is_active']
    search_fields = ['category', 'key', 'description']
    ordering = ['category', 'key']
