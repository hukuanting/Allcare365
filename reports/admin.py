from django.contrib import admin
from .models import ReportTemplate, ReportExecution, ScheduledReport, ReportFavorite


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'report_type', 'is_public', 'is_active', 'created_at', 'created_by']
    list_filter = ['report_type', 'is_public', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['name', 'description', 'report_type']
        }),
        ('Configuration', {
            'fields': ['sql_query', 'filters_config', 'columns_config']
        }),
        ('Output Options', {
            'fields': ['supports_pdf', 'supports_excel', 'supports_csv']
        }),
        ('Access Control', {
            'fields': ['is_public', 'is_active', 'allowed_users']
        }),
        ('Metadata', {
            'fields': ['id', 'created_at', 'updated_at', 'created_by'],
            'classes': ['collapse']
        })
    ]


@admin.register(ReportExecution)
class ReportExecutionAdmin(admin.ModelAdmin):
    list_display = ['template', 'executed_by', 'status', 'output_format', 'result_count', 'created_at']
    list_filter = ['status', 'output_format', 'created_at', 'template__report_type']
    search_fields = ['template__name', 'executed_by__username']
    readonly_fields = ['id', 'created_at', 'updated_at', 'execution_time', 'file_size']
    
    fieldsets = [
        ('Execution Details', {
            'fields': ['template', 'executed_by', 'parameters', 'output_format']
        }),
        ('Status', {
            'fields': ['status', 'started_at', 'completed_at', 'execution_time']
        }),
        ('Results', {
            'fields': ['result_count', 'error_message', 'file_path', 'file_size']
        }),
        ('Metadata', {
            'fields': ['id', 'created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]


@admin.register(ScheduledReport)
class ScheduledReportAdmin(admin.ModelAdmin):
    list_display = ['name', 'template', 'frequency', 'is_enabled', 'last_execution', 'next_execution']
    list_filter = ['frequency', 'is_enabled', 'template__report_type']
    search_fields = ['name', 'template__name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_execution']
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['name', 'description', 'template', 'scheduled_by']
        }),
        ('Schedule Configuration', {
            'fields': ['frequency', 'schedule_time', 'day_of_week', 'day_of_month']
        }),
        ('Parameters', {
            'fields': ['parameters', 'output_format']
        }),
        ('Email Configuration', {
            'fields': ['email_recipients', 'email_subject', 'email_body']
        }),
        ('Status', {
            'fields': ['is_enabled', 'last_execution', 'next_execution']
        }),
        ('Metadata', {
            'fields': ['id', 'created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]


@admin.register(ReportFavorite)
class ReportFavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'template', 'custom_name', 'created_at']
    list_filter = ['template__report_type', 'created_at']
    search_fields = ['user__username', 'template__name', 'custom_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
