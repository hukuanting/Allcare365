from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    MessageChannel, MessageThread, Message, MessageAttachment,
    MessageParticipant, MessageReaction, MessageReadReceipt,
    Notification, BulkMessage, BulkMessageRecipient, MessageTemplate
)


@admin.register(MessageChannel)
class MessageChannelAdmin(admin.ModelAdmin):
    list_display = ['name', 'channel_type', 'created_by', 'participant_count', 'is_active', 'created_at']
    list_filter = ['channel_type', 'is_active', 'is_archived', 'created_at']
    search_fields = ['name', 'description', 'created_by__username']
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_activity']
    filter_horizontal = []
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('name', 'description', 'channel_type', 'created_by')
        }),
        ('狀態設定', {
            'fields': ('is_active', 'is_archived')
        }),
        ('安全設定', {
            'fields': ('is_encrypted', 'require_approval', 'max_participants')
        }),
        ('時間資訊', {
            'fields': ('created_at', 'updated_at', 'last_activity'),
            'classes': ('collapse',)
        }),
        ('系統資訊', {
            'fields': ('id',),
            'classes': ('collapse',)
        })
    )
    
    def participant_count(self, obj):
        count = obj.participants.filter(status='ACTIVE').count()
        return format_html(
            '<span style="color: {};">{}</span>',
            'green' if count > 0 else 'gray',
            count
        )
    participant_count.short_description = '參與者數量'
    participant_count.admin_order_field = 'participants__count'


class MessageInline(admin.TabularInline):
    model = Message
    fields = ['sender', 'message_type', 'content_preview', 'sent_at', 'is_urgent']
    readonly_fields = ['content_preview', 'sent_at']
    extra = 0
    max_num = 5
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = '內容預覽'


@admin.register(MessageThread)
class MessageThreadAdmin(admin.ModelAdmin):
    list_display = ['subject', 'channel', 'started_by', 'priority', 'status', 'message_count', 'started_at']
    list_filter = ['priority', 'status', 'is_pinned', 'started_at', 'channel__channel_type']
    search_fields = ['subject', 'started_by__username', 'channel__name']
    readonly_fields = ['id', 'started_at', 'last_reply_at', 'message_count', 'participant_count']
    raw_id_fields = ['patient', 'appointment', 'medical_record']
    inlines = [MessageInline]
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('channel', 'subject', 'started_by', 'priority', 'status', 'is_pinned')
        }),
        ('醫療關聯', {
            'fields': ('patient', 'appointment', 'medical_record'),
            'classes': ('collapse',)
        }),
        ('統計資訊', {
            'fields': ('message_count', 'participant_count'),
            'classes': ('collapse',)
        }),
        ('時間資訊', {
            'fields': ('started_at', 'last_reply_at'),
            'classes': ('collapse',)
        }),
        ('系統資訊', {
            'fields': ('id',),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('channel', 'started_by')


class MessageAttachmentInline(admin.TabularInline):
    model = MessageAttachment
    fields = ['file', 'original_filename', 'file_size_display', 'attachment_type', 'is_safe']
    readonly_fields = ['file_size_display', 'original_filename']
    extra = 0
    
    def file_size_display(self, obj):
        if obj.file_size:
            if obj.file_size < 1024:
                return f"{obj.file_size} B"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size / 1024:.1f} KB"
            else:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
        return "-"
    file_size_display.short_description = '檔案大小'


class MessageReactionInline(admin.TabularInline):
    model = MessageReaction
    fields = ['user', 'reaction_type', 'created_at']
    readonly_fields = ['created_at']
    extra = 0


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['content_preview', 'sender', 'thread', 'message_type', 'sent_at', 'is_urgent', 'is_important']
    list_filter = ['message_type', 'is_urgent', 'is_important', 'is_deleted', 'sent_at']
    search_fields = ['content', 'sender__username', 'thread__subject']
    readonly_fields = ['id', 'sent_at', 'edited_at', 'is_edited', 'ip_address', 'user_agent']
    raw_id_fields = ['reply_to']
    inlines = [MessageAttachmentInline, MessageReactionInline]
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('thread', 'sender', 'message_type', 'content')
        }),
        ('回覆設定', {
            'fields': ('reply_to',),
            'classes': ('collapse',)
        }),
        ('重要性標記', {
            'fields': ('is_urgent', 'is_important', 'requires_response', 'response_deadline')
        }),
        ('狀態資訊', {
            'fields': ('is_edited', 'is_deleted'),
            'classes': ('collapse',)
        }),
        ('時間資訊', {
            'fields': ('sent_at', 'edited_at'),
            'classes': ('collapse',)
        }),
        ('安全資訊', {
            'fields': ('ip_address', 'user_agent', 'is_encrypted'),
            'classes': ('collapse',)
        }),
        ('系統資訊', {
            'fields': ('id',),
            'classes': ('collapse',)
        })
    )
    
    def content_preview(self, obj):
        content = obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
        if obj.is_urgent:
            return format_html('<span style="color: red; font-weight: bold;">{}</span>', content)
        elif obj.is_important:
            return format_html('<span style="color: orange; font-weight: bold;">{}</span>', content)
        return content
    content_preview.short_description = '內容預覽'
    content_preview.admin_order_field = 'content'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('sender', 'thread', 'thread__channel')


@admin.register(MessageAttachment)
class MessageAttachmentAdmin(admin.ModelAdmin):
    list_display = ['original_filename', 'message_info', 'attachment_type', 'file_size_display', 'is_safe', 'uploaded_at']
    list_filter = ['attachment_type', 'is_safe', 'is_scanned', 'uploaded_at']
    search_fields = ['original_filename', 'message__content', 'message__sender__username']
    readonly_fields = ['id', 'file_size', 'uploaded_at', 'scan_result']
    
    def message_info(self, obj):
        return f"{obj.message.sender.username}: {obj.message.content[:30]}..."
    message_info.short_description = '所屬訊息'
    
    def file_size_display(self, obj):
        if obj.file_size:
            if obj.file_size < 1024:
                return f"{obj.file_size} B"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size / 1024:.1f} KB"
            else:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
        return "-"
    file_size_display.short_description = '檔案大小'
    file_size_display.admin_order_field = 'file_size'


@admin.register(MessageParticipant)
class MessageParticipantAdmin(admin.ModelAdmin):
    list_display = ['user', 'channel', 'role', 'status', 'joined_at', 'last_read_at']
    list_filter = ['role', 'status', 'notification_enabled', 'joined_at']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'channel__name']
    readonly_fields = ['id', 'joined_at']
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('channel', 'user', 'role', 'status')
        }),
        ('權限設定', {
            'fields': ('can_send_messages', 'can_upload_files', 'can_invite_users', 'can_moderate')
        }),
        ('通知設定', {
            'fields': ('notification_enabled',)
        }),
        ('時間資訊', {
            'fields': ('joined_at', 'last_read_at'),
            'classes': ('collapse',)
        }),
        ('系統資訊', {
            'fields': ('id',),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'channel')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'recipient', 'notification_type', 'priority', 'is_read', 'is_sent', 'created_at']
    list_filter = ['notification_type', 'priority', 'is_read', 'is_sent', 'send_email', 'send_sms', 'created_at']
    search_fields = ['title', 'content', 'recipient__username']
    readonly_fields = ['id', 'created_at', 'read_at', 'sent_at']
    raw_id_fields = ['message', 'thread', 'channel']
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('recipient', 'notification_type', 'title', 'content', 'priority')
        }),
        ('關聯物件', {
            'fields': ('message', 'thread', 'channel'),
            'classes': ('collapse',)
        }),
        ('發送設定', {
            'fields': ('send_email', 'send_sms', 'send_push')
        }),
        ('狀態資訊', {
            'fields': ('is_read', 'is_sent'),
            'classes': ('collapse',)
        }),
        ('時間資訊', {
            'fields': ('created_at', 'read_at', 'sent_at'),
            'classes': ('collapse',)
        }),
        ('系統資訊', {
            'fields': ('id',),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('recipient')


class BulkMessageRecipientInline(admin.TabularInline):
    model = BulkMessageRecipient
    fields = ['recipient', 'app_status', 'email_status', 'sms_status', 'sent_at', 'read_at']
    readonly_fields = ['sent_at', 'read_at']
    extra = 0
    max_num = 10


@admin.register(BulkMessage)
class BulkMessageAdmin(admin.ModelAdmin):
    list_display = ['title', 'sender', 'recipient_type', 'status', 'total_recipients', 'delivery_rate', 'created_at']
    list_filter = ['recipient_type', 'status', 'send_via_app', 'send_via_email', 'send_via_sms', 'created_at']
    search_fields = ['title', 'content', 'sender__username']
    readonly_fields = ['id', 'created_at', 'sent_at', 'total_recipients', 'sent_count', 'delivered_count', 'read_count', 'failed_count']
    inlines = [BulkMessageRecipientInline]
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('title', 'content', 'sender', 'recipient_type')
        }),
        ('接收者設定', {
            'fields': ('recipient_filter',),
            'classes': ('collapse',)
        }),
        ('發送設定', {
            'fields': ('send_via_app', 'send_via_email', 'send_via_sms', 'scheduled_at')
        }),
        ('狀態資訊', {
            'fields': ('status',)
        }),
        ('統計資訊', {
            'fields': ('total_recipients', 'sent_count', 'delivered_count', 'read_count', 'failed_count'),
            'classes': ('collapse',)
        }),
        ('時間資訊', {
            'fields': ('created_at', 'sent_at'),
            'classes': ('collapse',)
        }),
        ('系統資訊', {
            'fields': ('id',),
            'classes': ('collapse',)
        })
    )
    
    def delivery_rate(self, obj):
        if obj.total_recipients > 0:
            rate = (obj.delivered_count / obj.total_recipients) * 100
            color = 'green' if rate >= 90 else 'orange' if rate >= 70 else 'red'
            return format_html(
                '<span style="color: {};">{:.1f}%</span>',
                color,
                rate
            )
        return "-"
    delivery_rate.short_description = '送達率'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('sender')


@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'template_type', 'created_by', 'is_active', 'usage_count', 'last_used_at']
    list_filter = ['template_type', 'is_active', 'is_system_template', 'created_at']
    search_fields = ['name', 'description', 'subject_template', 'content_template']
    readonly_fields = ['id', 'created_at', 'updated_at', 'usage_count', 'last_used_at']
    
    fieldsets = (
        ('基本資訊', {
            'fields': ('name', 'description', 'template_type', 'created_by')
        }),
        ('模板內容', {
            'fields': ('subject_template', 'content_template')
        }),
        ('狀態設定', {
            'fields': ('is_active', 'is_system_template')
        }),
        ('使用統計', {
            'fields': ('usage_count', 'last_used_at'),
            'classes': ('collapse',)
        }),
        ('時間資訊', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('系統資訊', {
            'fields': ('id',),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')


# 註冊其他簡單模型
@admin.register(MessageReaction)
class MessageReactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'message_preview', 'reaction_type', 'created_at']
    list_filter = ['reaction_type', 'created_at']
    search_fields = ['user__username', 'message__content']
    readonly_fields = ['created_at']
    
    def message_preview(self, obj):
        return f"{obj.message.content[:30]}..."
    message_preview.short_description = '訊息預覽'


@admin.register(MessageReadReceipt)
class MessageReadReceiptAdmin(admin.ModelAdmin):
    list_display = ['user', 'message_preview', 'read_at']
    list_filter = ['read_at']
    search_fields = ['user__username', 'message__content']
    readonly_fields = ['read_at']
    
    def message_preview(self, obj):
        return f"{obj.message.content[:30]}..."
    message_preview.short_description = '訊息預覽'


# 自訂管理介面標題
admin.site.site_header = "MedicalCare System - 通訊系統管理"
admin.site.site_title = "通訊系統"
admin.site.index_title = "通訊系統管理介面"
