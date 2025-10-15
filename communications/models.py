from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.utils import timezone
import uuid
import os


class MessageChannel(models.Model):
    """訊息頻道"""
    CHANNEL_TYPES = [
        ('DIRECT', '直接訊息'),
        ('GROUP', '群組訊息'),
        ('BROADCAST', '廣播訊息'),
        ('DEPARTMENT', '部門訊息'),
        ('EMERGENCY', '緊急訊息'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name='頻道名稱')
    description = models.TextField(blank=True, null=True, verbose_name='頻道描述')
    channel_type = models.CharField(max_length=20, choices=CHANNEL_TYPES, default='DIRECT', verbose_name='頻道類型')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_channels', verbose_name='建立者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    is_active = models.BooleanField(default=True, verbose_name='是否啟用')
    is_archived = models.BooleanField(default=False, verbose_name='是否封存')
    last_activity = models.DateTimeField(null=True, blank=True, verbose_name='最後活動時間')
    
    # 安全與權限設定
    is_encrypted = models.BooleanField(default=True, verbose_name='是否加密')
    require_approval = models.BooleanField(default=False, verbose_name='需要審核')
    max_participants = models.PositiveIntegerField(null=True, blank=True, verbose_name='最大參與者數')
    
    class Meta:
        db_table = 'communications_message_channel'
        verbose_name = '訊息頻道'
        verbose_name_plural = '訊息頻道'
        indexes = [
            models.Index(fields=['channel_type', 'is_active']),
            models.Index(fields=['created_by', 'created_at']),
            models.Index(fields=['last_activity']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_channel_type_display()})"


class MessageThread(models.Model):
    """訊息串"""
    PRIORITY_LEVELS = [
        ('LOW', '低'),
        ('NORMAL', '普通'),
        ('HIGH', '高'),
        ('URGENT', '緊急'),
        ('CRITICAL', '危急'),
    ]
    
    STATUS_CHOICES = [
        ('ACTIVE', '進行中'),
        ('RESOLVED', '已解決'),
        ('CLOSED', '已關閉'),
        ('ARCHIVED', '已封存'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    channel = models.ForeignKey(MessageChannel, on_delete=models.CASCADE, related_name='threads', verbose_name='所屬頻道')
    subject = models.CharField(max_length=500, verbose_name='主題')
    started_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='started_threads', verbose_name='發起者')
    started_at = models.DateTimeField(auto_now_add=True, verbose_name='開始時間')
    last_reply_at = models.DateTimeField(null=True, blank=True, verbose_name='最後回覆時間')
    priority = models.CharField(max_length=20, choices=PRIORITY_LEVELS, default='NORMAL', verbose_name='優先級')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE', verbose_name='狀態')
    is_pinned = models.BooleanField(default=False, verbose_name='是否置頂')
    
    # 醫療相關欄位
    patient = models.ForeignKey('patients.Patient', on_delete=models.SET_NULL, null=True, blank=True, 
                               related_name='message_threads', verbose_name='相關患者')
    appointment = models.ForeignKey('appointments.Appointment', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='message_threads', verbose_name='相關預約')
    medical_record = models.ForeignKey('medical_records.MedicalRecord', on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='message_threads', verbose_name='相關醫療記錄')
    
    # 統計欄位
    message_count = models.PositiveIntegerField(default=0, verbose_name='訊息數量')
    participant_count = models.PositiveIntegerField(default=0, verbose_name='參與者數量')
    
    class Meta:
        db_table = 'communications_message_thread'
        verbose_name = '訊息串'
        verbose_name_plural = '訊息串'
        indexes = [
            models.Index(fields=['channel', 'status']),
            models.Index(fields=['started_by', 'started_at']),
            models.Index(fields=['priority', 'status']),
            models.Index(fields=['patient']),
            models.Index(fields=['last_reply_at']),
        ]
        ordering = ['-is_pinned', '-last_reply_at', '-started_at']
    
    def __str__(self):
        return f"{self.subject} - {self.channel.name}"


class Message(models.Model):
    """訊息"""
    MESSAGE_TYPES = [
        ('TEXT', '文字訊息'),
        ('FILE', '檔案訊息'),
        ('IMAGE', '圖片訊息'),
        ('VOICE', '語音訊息'),
        ('VIDEO', '視訊訊息'),
        ('SYSTEM', '系統訊息'),
        ('NOTIFICATION', '通知訊息'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread = models.ForeignKey(MessageThread, on_delete=models.CASCADE, related_name='messages', verbose_name='所屬訊息串')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages', verbose_name='發送者')
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='TEXT', verbose_name='訊息類型')
    content = models.TextField(verbose_name='訊息內容')
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name='發送時間')
    edited_at = models.DateTimeField(null=True, blank=True, verbose_name='編輯時間')
    is_edited = models.BooleanField(default=False, verbose_name='是否已編輯')
    is_deleted = models.BooleanField(default=False, verbose_name='是否已刪除')
    
    # 回覆功能
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, 
                                related_name='replies', verbose_name='回覆訊息')
    
    # 緊急與重要標記
    is_urgent = models.BooleanField(default=False, verbose_name='緊急訊息')
    is_important = models.BooleanField(default=False, verbose_name='重要訊息')
    requires_response = models.BooleanField(default=False, verbose_name='需要回應')
    response_deadline = models.DateTimeField(null=True, blank=True, verbose_name='回應期限')
    
    # 安全與審計
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP位址')
    user_agent = models.TextField(blank=True, null=True, verbose_name='用戶代理')
    is_encrypted = models.BooleanField(default=True, verbose_name='是否加密')
    
    class Meta:
        db_table = 'communications_message'
        verbose_name = '訊息'
        verbose_name_plural = '訊息'
        indexes = [
            models.Index(fields=['thread', 'sent_at']),
            models.Index(fields=['sender', 'sent_at']),
            models.Index(fields=['message_type']),
            models.Index(fields=['is_urgent', 'is_important']),
            models.Index(fields=['requires_response', 'response_deadline']),
        ]
        ordering = ['sent_at']
    
    def save(self, *args, **kwargs):
        """保存訊息並更新相關計數"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # 更新訊息串的訊息數量
            message_count = self.thread.messages.filter(is_deleted=False).count()
            self.thread.message_count = message_count
            self.thread.last_reply_at = timezone.now()
            self.thread.save(update_fields=['message_count', 'last_reply_at'])
            
            # 更新頻道的最後活動時間
            self.thread.channel.last_activity = timezone.now()
            self.thread.channel.save(update_fields=['last_activity'])
    
    def __str__(self):
        content_preview = self.content[:50] + '...' if len(self.content) > 50 else self.content
        return f"{self.sender.username}: {content_preview}"


def message_attachment_path(instance, filename):
    """訊息附件上傳路徑"""
    return f'communications/attachments/{instance.message.thread.id}/{timezone.now().strftime("%Y/%m")}/{filename}'


class MessageAttachment(models.Model):
    """訊息附件"""
    ATTACHMENT_TYPES = [
        ('DOCUMENT', '文件'),
        ('IMAGE', '圖片'),
        ('AUDIO', '音訊'),
        ('VIDEO', '視訊'),
        ('ARCHIVE', '壓縮檔'),
        ('OTHER', '其他'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='attachments', verbose_name='所屬訊息')
    file = models.FileField(upload_to=message_attachment_path, verbose_name='附件檔案',
                           validators=[FileExtensionValidator(allowed_extensions=[
                               'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
                               'jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg',
                               'mp3', 'wav', 'ogg', 'mp4', 'avi', 'mov',
                               'zip', 'rar', '7z', 'txt', 'csv'
                           ])])
    original_filename = models.CharField(max_length=255, verbose_name='原始檔名')
    file_size = models.PositiveIntegerField(verbose_name='檔案大小')
    mime_type = models.CharField(max_length=100, verbose_name='MIME類型')
    attachment_type = models.CharField(max_length=20, choices=ATTACHMENT_TYPES, verbose_name='附件類型')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='上傳時間')
    
    # 安全檢查
    is_scanned = models.BooleanField(default=False, verbose_name='已掃描')
    scan_result = models.CharField(max_length=50, blank=True, null=True, verbose_name='掃描結果')
    is_safe = models.BooleanField(default=True, verbose_name='是否安全')
    
    class Meta:
        db_table = 'communications_message_attachment'
        verbose_name = '訊息附件'
        verbose_name_plural = '訊息附件'
        indexes = [
            models.Index(fields=['message']),
            models.Index(fields=['attachment_type']),
            models.Index(fields=['uploaded_at']),
        ]
    
    def __str__(self):
        return f"{self.original_filename} - {self.message}"
    
    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
            self.original_filename = self.file.name
        super().save(*args, **kwargs)


class MessageParticipant(models.Model):
    """訊息參與者"""
    PARTICIPANT_ROLES = [
        ('MEMBER', '成員'),
        ('MODERATOR', '版主'),
        ('ADMIN', '管理員'),
        ('OBSERVER', '觀察者'),
    ]
    
    PARTICIPANT_STATUS = [
        ('ACTIVE', '活躍'),
        ('INACTIVE', '非活躍'),
        ('MUTED', '靜音'),
        ('BANNED', '封禁'),
        ('LEFT', '已離開'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    channel = models.ForeignKey(MessageChannel, on_delete=models.CASCADE, related_name='participants', verbose_name='所屬頻道')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='channel_participations', verbose_name='用戶')
    role = models.CharField(max_length=20, choices=PARTICIPANT_ROLES, default='MEMBER', verbose_name='角色')
    status = models.CharField(max_length=20, choices=PARTICIPANT_STATUS, default='ACTIVE', verbose_name='狀態')
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name='加入時間')
    last_read_at = models.DateTimeField(null=True, blank=True, verbose_name='最後閱讀時間')
    notification_enabled = models.BooleanField(default=True, verbose_name='啟用通知')
    
    # 權限設定
    can_send_messages = models.BooleanField(default=True, verbose_name='可發送訊息')
    can_upload_files = models.BooleanField(default=True, verbose_name='可上傳檔案')
    can_invite_users = models.BooleanField(default=False, verbose_name='可邀請用戶')
    can_moderate = models.BooleanField(default=False, verbose_name='可管理')
    
    class Meta:
        db_table = 'communications_message_participant'
        verbose_name = '訊息參與者'
        verbose_name_plural = '訊息參與者'
        unique_together = ['channel', 'user']
        indexes = [
            models.Index(fields=['channel', 'status']),
            models.Index(fields=['user', 'joined_at']),
            models.Index(fields=['role']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.channel.name} ({self.get_role_display()})"


class MessageReaction(models.Model):
    """訊息回應"""
    REACTION_TYPES = [
        ('LIKE', '👍'),
        ('LOVE', '❤️'),
        ('LAUGH', '😄'),
        ('SURPRISE', '😮'),
        ('SAD', '😢'),
        ('ANGRY', '😡'),
        ('THUMBS_DOWN', '👎'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions', verbose_name='所屬訊息')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_reactions', verbose_name='用戶')
    reaction_type = models.CharField(max_length=20, choices=REACTION_TYPES, verbose_name='回應類型')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    
    class Meta:
        db_table = 'communications_message_reaction'
        verbose_name = '訊息回應'
        verbose_name_plural = '訊息回應'
        unique_together = ['message', 'user', 'reaction_type']
        indexes = [
            models.Index(fields=['message', 'reaction_type']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_reaction_type_display()} - {self.message}"


class MessageReadReceipt(models.Model):
    """訊息已讀回條"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='read_receipts', verbose_name='所屬訊息')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='read_receipts', verbose_name='用戶')
    read_at = models.DateTimeField(auto_now_add=True, verbose_name='閱讀時間')
    
    class Meta:
        db_table = 'communications_message_read_receipt'
        verbose_name = '訊息已讀回條'
        verbose_name_plural = '訊息已讀回條'
        unique_together = ['message', 'user']
        indexes = [
            models.Index(fields=['message']),
            models.Index(fields=['user', 'read_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.message} - {self.read_at}"


class Notification(models.Model):
    """通知"""
    NOTIFICATION_TYPES = [
        ('MESSAGE', '新訊息'),
        ('MENTION', '提及'),
        ('REPLY', '回覆'),
        ('REACTION', '回應'),
        ('INVITATION', '邀請'),
        ('SYSTEM', '系統通知'),
        ('REMINDER', '提醒'),
    ]
    
    PRIORITY_LEVELS = [
        ('LOW', '低'),
        ('NORMAL', '普通'),
        ('HIGH', '高'),
        ('URGENT', '緊急'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name='接收者')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, verbose_name='通知類型')
    title = models.CharField(max_length=200, verbose_name='通知標題')
    content = models.TextField(verbose_name='通知內容')
    priority = models.CharField(max_length=20, choices=PRIORITY_LEVELS, default='NORMAL', verbose_name='優先級')
    
    # 關聯物件
    message = models.ForeignKey(Message, on_delete=models.CASCADE, null=True, blank=True, 
                               related_name='notifications', verbose_name='相關訊息')
    thread = models.ForeignKey(MessageThread, on_delete=models.CASCADE, null=True, blank=True,
                              related_name='notifications', verbose_name='相關訊息串')
    channel = models.ForeignKey(MessageChannel, on_delete=models.CASCADE, null=True, blank=True,
                               related_name='notifications', verbose_name='相關頻道')
    
    # 狀態與時間
    is_read = models.BooleanField(default=False, verbose_name='是否已讀')
    is_sent = models.BooleanField(default=False, verbose_name='是否已發送')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    read_at = models.DateTimeField(null=True, blank=True, verbose_name='閱讀時間')
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='發送時間')
    
    # 發送設定
    send_email = models.BooleanField(default=False, verbose_name='發送郵件')
    send_sms = models.BooleanField(default=False, verbose_name='發送簡訊')
    send_push = models.BooleanField(default=True, verbose_name='推播通知')
    
    class Meta:
        db_table = 'communications_notification'
        verbose_name = '通知'
        verbose_name_plural = '通知'
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['priority', 'created_at']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.recipient.username}"


class BulkMessage(models.Model):
    """批次訊息"""
    STATUS_CHOICES = [
        ('DRAFT', '草稿'),
        ('SCHEDULED', '已排程'),
        ('SENDING', '發送中'),
        ('SENT', '已發送'),
        ('FAILED', '發送失敗'),
        ('CANCELLED', '已取消'),
    ]
    
    RECIPIENT_TYPES = [
        ('ALL_USERS', '所有用戶'),
        ('DEPARTMENT', '部門'),
        ('ROLE', '角色'),
        ('CUSTOM', '自訂清單'),
        ('PATIENTS', '患者'),
        ('STAFF', '員工'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200, verbose_name='標題')
    content = models.TextField(verbose_name='內容')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bulk_messages', verbose_name='發送者')
    
    # 接收者設定
    recipient_type = models.CharField(max_length=20, choices=RECIPIENT_TYPES, verbose_name='接收者類型')
    recipient_filter = models.JSONField(default=dict, blank=True, verbose_name='接收者篩選條件')
    recipients = models.ManyToManyField(User, through='BulkMessageRecipient', related_name='received_bulk_messages', 
                                       verbose_name='接收者')
    
    # 發送設定
    send_via_app = models.BooleanField(default=True, verbose_name='應用內通知')
    send_via_email = models.BooleanField(default=False, verbose_name='郵件通知')
    send_via_sms = models.BooleanField(default=False, verbose_name='簡訊通知')
    
    # 排程設定
    scheduled_at = models.DateTimeField(null=True, blank=True, verbose_name='排程時間')
    
    # 狀態與統計
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT', verbose_name='狀態')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='發送時間')
    
    # 統計資料
    total_recipients = models.PositiveIntegerField(default=0, verbose_name='總接收者數')
    sent_count = models.PositiveIntegerField(default=0, verbose_name='已發送數')
    delivered_count = models.PositiveIntegerField(default=0, verbose_name='已送達數')
    read_count = models.PositiveIntegerField(default=0, verbose_name='已閱讀數')
    failed_count = models.PositiveIntegerField(default=0, verbose_name='失敗數')
    
    class Meta:
        db_table = 'communications_bulk_message'
        verbose_name = '批次訊息'
        verbose_name_plural = '批次訊息'
        indexes = [
            models.Index(fields=['sender', 'created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['scheduled_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.sender.username}"


class BulkMessageRecipient(models.Model):
    """批次訊息接收者"""
    DELIVERY_STATUS = [
        ('PENDING', '待發送'),
        ('SENDING', '發送中'),
        ('SENT', '已發送'),
        ('DELIVERED', '已送達'),
        ('READ', '已閱讀'),
        ('FAILED', '發送失敗'),
        ('BOUNCED', '退回'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bulk_message = models.ForeignKey(BulkMessage, on_delete=models.CASCADE, verbose_name='批次訊息')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='接收者')
    
    # 發送狀態
    app_status = models.CharField(max_length=20, choices=DELIVERY_STATUS, default='PENDING', verbose_name='應用狀態')
    email_status = models.CharField(max_length=20, choices=DELIVERY_STATUS, default='PENDING', verbose_name='郵件狀態')
    sms_status = models.CharField(max_length=20, choices=DELIVERY_STATUS, default='PENDING', verbose_name='簡訊狀態')
    
    # 發送時間
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='發送時間')
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name='送達時間')
    read_at = models.DateTimeField(null=True, blank=True, verbose_name='閱讀時間')
    
    # 錯誤資訊
    error_message = models.TextField(blank=True, null=True, verbose_name='錯誤訊息')
    retry_count = models.PositiveIntegerField(default=0, verbose_name='重試次數')
    
    class Meta:
        db_table = 'communications_bulk_message_recipient'
        verbose_name = '批次訊息接收者'
        verbose_name_plural = '批次訊息接收者'
        unique_together = ['bulk_message', 'recipient']
        indexes = [
            models.Index(fields=['bulk_message', 'app_status']),
            models.Index(fields=['recipient']),
            models.Index(fields=['sent_at']),
        ]
    
    def __str__(self):
        return f"{self.bulk_message.title} - {self.recipient.username}"


class MessageTemplate(models.Model):
    """訊息模板"""
    TEMPLATE_TYPES = [
        ('WELCOME', '歡迎訊息'),
        ('REMINDER', '提醒訊息'),
        ('NOTIFICATION', '通知訊息'),
        ('APPOINTMENT', '預約訊息'),
        ('BILLING', '帳單訊息'),
        ('EMERGENCY', '緊急訊息'),
        ('CUSTOM', '自訂訊息'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name='模板名稱')
    description = models.TextField(blank=True, null=True, verbose_name='模板描述')
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES, verbose_name='模板類型')
    
    # 模板內容
    subject_template = models.CharField(max_length=500, verbose_name='主題模板')
    content_template = models.TextField(verbose_name='內容模板')
    
    # 創建者與時間
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_templates', verbose_name='建立者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    
    # 狀態
    is_active = models.BooleanField(default=True, verbose_name='是否啟用')
    is_system_template = models.BooleanField(default=False, verbose_name='系統模板')
    
    # 使用統計
    usage_count = models.PositiveIntegerField(default=0, verbose_name='使用次數')
    last_used_at = models.DateTimeField(null=True, blank=True, verbose_name='最後使用時間')
    
    class Meta:
        db_table = 'communications_message_template'
        verbose_name = '訊息模板'
        verbose_name_plural = '訊息模板'
        indexes = [
            models.Index(fields=['template_type', 'is_active']),
            models.Index(fields=['created_by']),
            models.Index(fields=['usage_count']),
        ]
        ordering = ['template_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"
