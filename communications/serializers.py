from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    MessageChannel, MessageThread, Message, MessageAttachment,
    MessageParticipant, MessageReaction, MessageReadReceipt,
    Notification, BulkMessage, BulkMessageRecipient, MessageTemplate
)


class UserSerializer(serializers.ModelSerializer):
    """用戶序列化器"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'full_name']
        read_only_fields = ['id']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


class MessageChannelSerializer(serializers.ModelSerializer):
    """訊息頻道序列化器"""
    created_by = UserSerializer(read_only=True)
    participant_count = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = MessageChannel
        fields = [
            'id', 'name', 'description', 'channel_type', 'created_by', 'created_at',
            'updated_at', 'is_active', 'is_archived', 'last_activity',
            'is_encrypted', 'require_approval', 'max_participants',
            'participant_count', 'unread_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_activity']
    
    def get_participant_count(self, obj):
        return obj.participants.filter(status='ACTIVE').count()
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # 計算未讀訊息數量
            participant = obj.participants.filter(user=request.user).first()
            if participant:
                last_read = participant.last_read_at
                if last_read:
                    return obj.threads.filter(last_reply_at__gt=last_read).count()
                return obj.threads.count()
        return 0


class MessageChannelDetailSerializer(MessageChannelSerializer):
    """訊息頻道詳細序列化器"""
    participants = serializers.SerializerMethodField()
    recent_threads = serializers.SerializerMethodField()
    
    class Meta(MessageChannelSerializer.Meta):
        fields = MessageChannelSerializer.Meta.fields + ['participants', 'recent_threads']
    
    def get_participants(self, obj):
        participants = obj.participants.filter(status='ACTIVE').select_related('user')[:10]
        return [UserSerializer(p.user).data for p in participants]
    
    def get_recent_threads(self, obj):
        threads = obj.threads.filter(status='ACTIVE')[:5]
        return MessageThreadSerializer(threads, many=True, context=self.context).data


class MessageThreadSerializer(serializers.ModelSerializer):
    """訊息串序列化器"""
    started_by = UserSerializer(read_only=True)
    channel = MessageChannelSerializer(read_only=True)
    channel_id = serializers.UUIDField(write_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = MessageThread
        fields = [
            'id', 'channel', 'channel_id', 'subject', 'started_by', 'started_at', 'last_reply_at',
            'priority', 'status', 'is_pinned', 'patient', 'appointment', 'medical_record',
            'message_count', 'participant_count', 'last_message', 'unread_count'
        ]
        read_only_fields = ['id', 'started_at', 'last_reply_at', 'message_count', 'participant_count']
    
    def create(self, validated_data):
        channel_id = validated_data.pop('channel_id')
        try:
            channel = MessageChannel.objects.get(id=channel_id)
            validated_data['channel'] = channel
            return super().create(validated_data)
        except MessageChannel.DoesNotExist:
            raise serializers.ValidationError({'channel_id': '指定的頻道不存在'})
    
    def get_last_message(self, obj):
        last_message = obj.messages.filter(is_deleted=False).last()
        if last_message:
            return MessageSerializer(last_message, context=self.context).data
        return None
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # 計算用戶在此訊息串的未讀訊息數
            participant = obj.channel.participants.filter(user=request.user).first()
            if participant and participant.last_read_at:
                return obj.messages.filter(
                    sent_at__gt=participant.last_read_at,
                    is_deleted=False
                ).count()
            return obj.messages.filter(is_deleted=False).count()
        return 0


class MessageAttachmentSerializer(serializers.ModelSerializer):
    """訊息附件序列化器"""
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = MessageAttachment
        fields = [
            'id', 'file', 'file_url', 'original_filename', 'file_size',
            'mime_type', 'attachment_type', 'uploaded_at', 'is_safe'
        ]
        read_only_fields = ['id', 'file_size', 'uploaded_at', 'is_safe']
    
    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class MessageReactionSerializer(serializers.ModelSerializer):
    """訊息回應序列化器"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = MessageReaction
        fields = ['id', 'user', 'reaction_type', 'created_at']
        read_only_fields = ['id', 'created_at']


class MessageSerializer(serializers.ModelSerializer):
    """訊息序列化器"""
    sender = UserSerializer(read_only=True)
    attachments = serializers.SerializerMethodField()
    reactions = MessageReactionSerializer(many=True, read_only=True)
    reply_to = serializers.SerializerMethodField()
    reaction_summary = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'thread', 'sender', 'message_type', 'content', 'sent_at',
            'edited_at', 'is_edited', 'is_deleted', 'reply_to', 'is_urgent',
            'is_important', 'requires_response', 'response_deadline',
            'attachments', 'reactions', 'reaction_summary', 'is_read'
        ]
        read_only_fields = ['id', 'sent_at', 'edited_at', 'is_edited']
    
    def get_attachments(self, obj):
        """取得附件列表"""
        attachments = obj.attachments.all()
        return MessageAttachmentSerializer(attachments, many=True, context=self.context).data
    
    def get_reply_to(self, obj):
        if obj.reply_to:
            return {
                'id': obj.reply_to.id,
                'sender': UserSerializer(obj.reply_to.sender).data,
                'content': obj.reply_to.content[:100],
                'sent_at': obj.reply_to.sent_at
            }
        return None
    
    def get_reaction_summary(self, obj):
        reactions = obj.reactions.all()
        summary = {}
        for reaction in reactions:
            reaction_type = reaction.reaction_type
            if reaction_type not in summary:
                summary[reaction_type] = {'count': 0, 'users': []}
            summary[reaction_type]['count'] += 1
            summary[reaction_type]['users'].append(reaction.user.username)
        return summary
    
    def get_is_read(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.read_receipts.filter(user=request.user).exists()
        return False


class MessageParticipantSerializer(serializers.ModelSerializer):
    """訊息參與者序列化器"""
    user = UserSerializer(read_only=True)
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = MessageParticipant
        fields = [
            'id', 'user', 'role', 'status', 'joined_at', 'last_read_at',
            'notification_enabled', 'can_send_messages', 'can_upload_files',
            'can_invite_users', 'can_moderate', 'unread_count'
        ]
        read_only_fields = ['id', 'joined_at']
    
    def get_unread_count(self, obj):
        if obj.last_read_at:
            return obj.channel.threads.filter(
                last_reply_at__gt=obj.last_read_at
            ).count()
        return obj.channel.threads.count()


class NotificationSerializer(serializers.ModelSerializer):
    """通知序列化器"""
    message = MessageSerializer(read_only=True)
    thread = MessageThreadSerializer(read_only=True)
    channel = MessageChannelSerializer(read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'content', 'priority',
            'message', 'thread', 'channel', 'is_read', 'is_sent',
            'created_at', 'read_at', 'sent_at', 'send_email', 'send_sms', 'send_push'
        ]
        read_only_fields = ['id', 'created_at', 'read_at', 'sent_at', 'is_sent']


class BulkMessageRecipientSerializer(serializers.ModelSerializer):
    """批次訊息接收者序列化器"""
    recipient = UserSerializer(read_only=True)
    
    class Meta:
        model = BulkMessageRecipient
        fields = [
            'id', 'recipient', 'app_status', 'email_status', 'sms_status',
            'sent_at', 'delivered_at', 'read_at', 'error_message', 'retry_count'
        ]
        read_only_fields = ['id', 'sent_at', 'delivered_at', 'read_at', 'retry_count']


class BulkMessageSerializer(serializers.ModelSerializer):
    """批次訊息序列化器"""
    sender = UserSerializer(read_only=True)
    recipients_detail = BulkMessageRecipientSerializer(
        source='bulkmessagerecipient_set', many=True, read_only=True
    )
    
    class Meta:
        model = BulkMessage
        fields = [
            'id', 'title', 'content', 'sender', 'recipient_type',
            'recipient_filter', 'send_via_app', 'send_via_email', 'send_via_sms',
            'scheduled_at', 'status', 'created_at', 'sent_at', 'total_recipients',
            'sent_count', 'delivered_count', 'read_count', 'failed_count',
            'recipients_detail'
        ]
        read_only_fields = [
            'id', 'created_at', 'sent_at', 'total_recipients',
            'sent_count', 'delivered_count', 'read_count', 'failed_count'
        ]


class MessageTemplateSerializer(serializers.ModelSerializer):
    """訊息模板序列化器"""
    created_by = UserSerializer(read_only=True)
    
    class Meta:
        model = MessageTemplate
        fields = [
            'id', 'name', 'description', 'template_type', 'subject_template',
            'content_template', 'created_by', 'created_at', 'updated_at',
            'is_active', 'is_system_template', 'usage_count', 'last_used_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'usage_count', 'last_used_at']


# 建立訊息的序列化器
class MessageCreateSerializer(serializers.ModelSerializer):
    """建立訊息的序列化器"""
    attachments = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        allow_empty=True
    )
    
    class Meta:
        model = Message
        fields = [
            'thread', 'message_type', 'content', 'reply_to', 'is_urgent',
            'is_important', 'requires_response', 'response_deadline', 'attachments'
        ]
    
    def create(self, validated_data):
        attachments = validated_data.pop('attachments', [])
        
        # 使用標準方法建立訊息，但確保調用 save 方法
        message = Message.objects.create(**validated_data)
        
        # 處理附件
        for attachment_file in attachments:
            MessageAttachment.objects.create(
                message=message,
                file=attachment_file,
                original_filename=attachment_file.name,
                file_size=attachment_file.size,
                mime_type=attachment_file.content_type,
                attachment_type=self._get_attachment_type(attachment_file.content_type)
            )
        
        return message
    
    def _get_attachment_type(self, mime_type):
        """根據 MIME 類型判斷附件類型"""
        if mime_type.startswith('image/'):
            return 'IMAGE'
        elif mime_type.startswith('audio/'):
            return 'AUDIO'
        elif mime_type.startswith('video/'):
            return 'VIDEO'
        elif mime_type in ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
            return 'DOCUMENT'
        elif mime_type in ['application/zip', 'application/x-rar-compressed', 'application/x-7z-compressed']:
            return 'ARCHIVE'
        else:
            return 'OTHER'


# 搜尋相關序列化器
class MessageSearchSerializer(serializers.Serializer):
    """訊息搜尋序列化器"""
    query = serializers.CharField(required=True, max_length=200)
    channel_id = serializers.UUIDField(required=False)
    thread_id = serializers.UUIDField(required=False)
    sender_id = serializers.IntegerField(required=False)
    message_type = serializers.ChoiceField(
        choices=Message.MESSAGE_TYPES,
        required=False
    )
    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)
    has_attachments = serializers.BooleanField(required=False)
    is_urgent = serializers.BooleanField(required=False)
    is_important = serializers.BooleanField(required=False)


class ChannelStatisticsSerializer(serializers.Serializer):
    """頻道統計序列化器"""
    total_messages = serializers.IntegerField()
    total_participants = serializers.IntegerField()
    active_participants = serializers.IntegerField()
    messages_today = serializers.IntegerField()
    messages_this_week = serializers.IntegerField()
    messages_this_month = serializers.IntegerField()
    top_senders = serializers.ListField()
    message_types_distribution = serializers.DictField()
    activity_timeline = serializers.ListField()
