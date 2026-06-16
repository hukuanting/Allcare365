from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponseForbidden
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.db.models import Q, Count, Max
from django.utils import timezone
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from datetime import datetime, timedelta
import json

from .models import (
    MessageChannel, MessageThread, Message, MessageAttachment,
    MessageParticipant, MessageReaction, MessageReadReceipt,
    Notification, BulkMessage, BulkMessageRecipient, MessageTemplate
)
from .serializers import (
    MessageChannelSerializer, MessageChannelDetailSerializer,
    MessageThreadSerializer, MessageSerializer, MessageCreateSerializer,
    MessageParticipantSerializer, NotificationSerializer,
    BulkMessageSerializer, MessageTemplateSerializer,
    MessageSearchSerializer, ChannelStatisticsSerializer
)


# ============================================================================
# API ViewSets
# ============================================================================

class MessageChannelViewSet(viewsets.ModelViewSet):
    """訊息頻道 API"""
    serializer_class = MessageChannelSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # 對於 join 動作，允許查看所有頻道
        if self.action == 'join':
            return MessageChannel.objects.all()
        # 其他動作只顯示用戶參與的頻道
        return MessageChannel.objects.filter(
            participants__user=user,
            participants__status='ACTIVE'
        ).distinct().order_by('-last_activity', '-created_at')
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return MessageChannelDetailSerializer
        return MessageChannelSerializer
    
    def perform_create(self, serializer):
        channel = serializer.save(created_by=self.request.user)
        # 自動將建立者加入為管理員
        MessageParticipant.objects.create(
            channel=channel,
            user=self.request.user,
            role='ADMIN',
            can_send_messages=True,
            can_upload_files=True,
            can_invite_users=True,
            can_moderate=True
        )
    
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """加入頻道"""
        # 直接透過 pk 取得頻道，不受 queryset 限制
        try:
            channel = MessageChannel.objects.get(pk=pk)
        except MessageChannel.DoesNotExist:
            return Response(
                {'error': '頻道不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 檢查是否已經是成員
        participant, created = MessageParticipant.objects.get_or_create(
            channel=channel,
            user=request.user,
            defaults={
                'role': 'MEMBER',
                'status': 'ACTIVE'
            }
        )
        
        if not created and participant.status != 'ACTIVE':
            participant.status = 'ACTIVE'
            participant.save()
        
        return Response({'status': 'joined'})
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """離開頻道"""
        channel = self.get_object()
        
        try:
            participant = MessageParticipant.objects.get(
                channel=channel,
                user=request.user
            )
            participant.status = 'LEFT'
            participant.save()
            return Response({'status': 'left'})
        except MessageParticipant.DoesNotExist:
            return Response(
                {'error': '您不是此頻道的成員'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """頻道統計"""
        channel = self.get_object()
        
        # 基本統計
        total_messages = Message.objects.filter(
            thread__channel=channel,
            is_deleted=False
        ).count()
        
        total_participants = channel.participants.count()
        active_participants = channel.participants.filter(status='ACTIVE').count()
        
        # 時間範圍統計
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        messages_today = Message.objects.filter(
            thread__channel=channel,
            is_deleted=False,
            sent_at__date=today
        ).count()
        
        messages_this_week = Message.objects.filter(
            thread__channel=channel,
            is_deleted=False,
            sent_at__date__gte=week_ago
        ).count()
        
        messages_this_month = Message.objects.filter(
            thread__channel=channel,
            is_deleted=False,
            sent_at__date__gte=month_ago
        ).count()
        
        # 最活躍發送者
        top_senders = Message.objects.filter(
            thread__channel=channel,
            is_deleted=False
        ).values(
            'sender__username', 'sender__first_name', 'sender__last_name'
        ).annotate(
            message_count=Count('id')
        ).order_by('-message_count')[:5]
        
        # 訊息類型分佈
        message_types = Message.objects.filter(
            thread__channel=channel,
            is_deleted=False
        ).values('message_type').annotate(
            count=Count('id')
        )
        
        message_types_distribution = {
            item['message_type']: item['count']
            for item in message_types
        }
        
        data = {
            'total_messages': total_messages,
            'total_participants': total_participants,
            'active_participants': active_participants,
            'messages_today': messages_today,
            'messages_this_week': messages_this_week,
            'messages_this_month': messages_this_month,
            'top_senders': list(top_senders),
            'message_types_distribution': message_types_distribution,
            'activity_timeline': []  # 可以後續實作
        }
        
        serializer = ChannelStatisticsSerializer(data)
        return Response(serializer.data)


class MessageThreadViewSet(viewsets.ModelViewSet):
    """訊息串 API"""
    serializer_class = MessageThreadSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        # 只顯示用戶有權限的訊息串
        return MessageThread.objects.filter(
            channel__participants__user=user,
            channel__participants__status='ACTIVE'
        ).distinct().order_by('-is_pinned', '-last_reply_at', '-started_at')
    
    def perform_create(self, serializer):
        serializer.save(started_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """標記為已讀"""
        thread = self.get_object()
        
        # 更新參與者的最後閱讀時間
        try:
            participant = MessageParticipant.objects.get(
                channel=thread.channel,
                user=request.user
            )
            participant.last_read_at = timezone.now()
            participant.save()
            return Response({'status': 'marked_as_read'})
        except MessageParticipant.DoesNotExist:
            return Response(
                {'error': '您不是此頻道的成員'},
                status=status.HTTP_400_BAD_REQUEST
            )


class MessageViewSet(viewsets.ModelViewSet):
    """訊息 API"""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return MessageCreateSerializer
        return MessageSerializer
    
    def get_queryset(self):
        user = self.request.user
        # 只顯示用戶有權限的訊息
        return Message.objects.filter(
            thread__channel__participants__user=user,
            thread__channel__participants__status='ACTIVE',
            is_deleted=False
        ).distinct().order_by('sent_at')
    
    def perform_create(self, serializer):
        message = serializer.save(sender=self.request.user)
        return message
    
    def create(self, request, *args, **kwargs):
        """重寫 create 方法以確保正確的序列化器回應"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save(sender=request.user)
        
        # 使用 MessageSerializer 來回應
        response_serializer = MessageSerializer(message, context={'request': request})
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    @action(detail=True, methods=['post'])
    def react(self, request, pk=None):
        """對訊息回應"""
        message = self.get_object()
        reaction_type = request.data.get('reaction_type')
        
        if reaction_type not in dict(MessageReaction.REACTION_TYPES):
            return Response(
                {'error': '無效的回應類型'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 切換回應狀態
        reaction, created = MessageReaction.objects.get_or_create(
            message=message,
            user=request.user,
            reaction_type=reaction_type
        )
        
        if not created:
            reaction.delete()
            return Response({'status': 'reaction_removed'})
        
        return Response({'status': 'reaction_added'})
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """標記訊息為已讀"""
        message = self.get_object()
        
        MessageReadReceipt.objects.get_or_create(
            message=message,
            user=request.user
        )
        
        return Response({'status': 'marked_as_read'})
    
    @action(detail=False, methods=['post'])
    def search(self, request):
        """搜尋訊息"""
        serializer = MessageSearchSerializer(data=request.data)
        if serializer.is_valid():
            query = serializer.validated_data['query']
            filters = Q(content__icontains=query)
            
            # 應用其他篩選條件
            if 'channel_id' in serializer.validated_data:
                filters &= Q(thread__channel_id=serializer.validated_data['channel_id'])
            
            if 'thread_id' in serializer.validated_data:
                filters &= Q(thread_id=serializer.validated_data['thread_id'])
            
            if 'sender_id' in serializer.validated_data:
                filters &= Q(sender_id=serializer.validated_data['sender_id'])
            
            if 'message_type' in serializer.validated_data:
                filters &= Q(message_type=serializer.validated_data['message_type'])
            
            if 'date_from' in serializer.validated_data:
                filters &= Q(sent_at__gte=serializer.validated_data['date_from'])
            
            if 'date_to' in serializer.validated_data:
                filters &= Q(sent_at__lte=serializer.validated_data['date_to'])
            
            if 'has_attachments' in serializer.validated_data:
                if serializer.validated_data['has_attachments']:
                    filters &= Q(attachments__isnull=False)
                else:
                    filters &= Q(attachments__isnull=True)
            
            if 'is_urgent' in serializer.validated_data:
                filters &= Q(is_urgent=serializer.validated_data['is_urgent'])
            
            if 'is_important' in serializer.validated_data:
                filters &= Q(is_important=serializer.validated_data['is_important'])
            
            # 執行搜尋
            messages = self.get_queryset().filter(filters).distinct()
            page = self.paginate_queryset(messages)
            
            if page is not None:
                serializer = MessageSerializer(page, many=True, context={'request': request})
                return self.get_paginated_response(serializer.data)
            
            serializer = MessageSerializer(messages, many=True, context={'request': request})
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NotificationViewSet(viewsets.ModelViewSet):
    """通知 API"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user
        ).order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """標記通知為已讀"""
        notification = self.get_object()
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        return Response({'status': 'marked_as_read'})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """標記所有通知為已讀"""
        Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
        return Response({'status': 'all_marked_as_read'})
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """獲取未讀通知數量"""
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        return Response({'unread_count': count})


class BulkMessageViewSet(viewsets.ModelViewSet):
    """批次訊息 API"""
    serializer_class = BulkMessageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return BulkMessage.objects.filter(
            sender=self.request.user
        ).order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)


class MessageTemplateViewSet(viewsets.ModelViewSet):
    """訊息模板 API"""
    serializer_class = MessageTemplateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return MessageTemplate.objects.filter(
            Q(created_by=self.request.user) | Q(is_system_template=True),
            is_active=True
        ).order_by('template_type', 'name')


# ============================================================================
# Web Views
# ============================================================================

class CommunicationsDashboardView(LoginRequiredMixin, ListView):
    """通訊系統主控台"""
    template_name = 'communications/dashboard.html'
    context_object_name = 'channels'
    
    def get_queryset(self):
        return MessageChannel.objects.filter(
            participants__user=self.request.user,
            participants__status='ACTIVE'
        ).distinct().order_by('-last_activity')[:10]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # 未讀通知數量
        context['unread_notifications'] = Notification.objects.filter(
            recipient=user,
            is_read=False
        ).count()
        
        # 最近訊息
        context['recent_messages'] = Message.objects.filter(
            thread__channel__participants__user=user,
            thread__channel__participants__status='ACTIVE',
            is_deleted=False
        ).distinct().order_by('-sent_at')[:5]
        
        # 活躍頻道統計
        context['active_channels_count'] = MessageChannel.objects.filter(
            participants__user=user,
            participants__status='ACTIVE',
            is_active=True
        ).distinct().count()
        
        return context


class ChannelListView(LoginRequiredMixin, ListView):
    """頻道列表"""
    model = MessageChannel
    template_name = 'communications/channel_list.html'
    context_object_name = 'channels'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = MessageChannel.objects.filter(
            participants__user=self.request.user,
            participants__status='ACTIVE'
        ).distinct().order_by('-last_activity')
        
        # 搜尋功能
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        
        # 頻道類型篩選
        channel_type = self.request.GET.get('type')
        if channel_type:
            queryset = queryset.filter(channel_type=channel_type)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['channel_types'] = MessageChannel.CHANNEL_TYPES
        context['current_search'] = self.request.GET.get('search', '')
        context['current_type'] = self.request.GET.get('type', '')
        return context


class ChannelDetailView(LoginRequiredMixin, DetailView):
    """頻道詳細頁面"""
    model = MessageChannel
    template_name = 'communications/channel_detail.html'
    context_object_name = 'channel'
    
    def get_object(self):
        channel = super().get_object()
        # 驗證用戶是否有權限查看此頻道
        if not channel.participants.filter(
            user=self.request.user,
            status='ACTIVE'
        ).exists():
            raise PermissionDenied('您沒有權限查看此頻道')
        return channel
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        channel = self.object
        
        # 獲取訊息串
        context['threads'] = channel.threads.filter(
            status='ACTIVE'
        ).order_by('-is_pinned', '-last_reply_at')[:20]
        
        # 獲取參與者
        context['participants'] = channel.participants.filter(
            status='ACTIVE'
        ).select_related('user')
        
        # 用戶權限
        try:
            participant = channel.participants.get(user=self.request.user)
            context['user_participant'] = participant
            context['can_moderate'] = participant.can_moderate
            context['can_send_messages'] = participant.can_send_messages
        except MessageParticipant.DoesNotExist:
            context['can_moderate'] = False
            context['can_send_messages'] = False
        
        return context


class ThreadDetailView(LoginRequiredMixin, DetailView):
    """訊息串詳細頁面"""
    model = MessageThread
    template_name = 'communications/thread_detail.html'
    context_object_name = 'thread'
    
    def get_object(self):
        thread = super().get_object()
        # 驗證用戶是否有權限查看此訊息串
        if not thread.channel.participants.filter(
            user=self.request.user,
            status='ACTIVE'
        ).exists():
            raise PermissionDenied('您沒有權限查看此訊息串')
        return thread
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        thread = self.object
        
        # 獲取訊息
        messages = thread.messages.filter(
            is_deleted=False
        ).order_by('sent_at')
        
        # 分頁
        paginator = Paginator(messages, 50)
        page_number = self.request.GET.get('page')
        context['messages'] = paginator.get_page(page_number)
        
        # 標記為已讀
        try:
            participant = thread.channel.participants.get(user=self.request.user)
            participant.last_read_at = timezone.now()
            participant.save()
        except MessageParticipant.DoesNotExist:
            pass
        
        return context


@login_required
def notifications_view(request):
    """通知頁面"""
    notifications = Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')
    
    # 分頁
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    notifications = paginator.get_page(page_number)
    
    return render(request, 'communications/notifications.html', {
        'notifications': notifications
    })


# ============================================================================
# AJAX Views
# ============================================================================

@login_required
@require_http_methods(["POST"])
def send_message_ajax(request):
    """AJAX 發送訊息"""
    try:
        data = json.loads(request.body)
        thread_id = data.get('thread_id')
        content = data.get('content')
        reply_to_id = data.get('reply_to')
        
        if not thread_id or not content:
            return JsonResponse({'error': '缺少必要參數'}, status=400)
        
        thread = get_object_or_404(MessageThread, id=thread_id)
        
        # 檢查權限
        participant = thread.channel.participants.filter(
            user=request.user,
            status='ACTIVE',
            can_send_messages=True
        ).first()
        
        if not participant:
            return JsonResponse({'error': '您沒有權限發送訊息'}, status=403)
        
        # 建立訊息
        message_data = {
            'thread': thread,
            'sender': request.user,
            'content': content,
            'message_type': 'TEXT'
        }
        
        if reply_to_id:
            reply_to = get_object_or_404(Message, id=reply_to_id)
            message_data['reply_to'] = reply_to
        
        message = Message.objects.create(**message_data)
        
        # 更新訊息串統計
        thread.message_count += 1
        thread.last_reply_at = timezone.now()
        thread.save()
        
        # 更新頻道活動時間
        thread.channel.last_activity = timezone.now()
        thread.channel.save()
        
        return JsonResponse({
            'success': True,
            'message': {
                'id': str(message.id),
                'content': message.content,
                'sender': message.sender.username,
                'sent_at': message.sent_at.isoformat()
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def mark_notification_read_ajax(request, notification_id):
    """AJAX 標記通知為已讀"""
    try:
        notification = get_object_or_404(
            Notification,
            id=notification_id,
            recipient=request.user
        )
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# API 輔助函數
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_channels(request):
    """獲取用戶頻道"""
    channels = MessageChannel.objects.filter(
        participants__user=request.user,
        participants__status='ACTIVE'
    ).distinct().order_by('-last_activity')
    
    serializer = MessageChannelSerializer(channels, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_unread_counts(request):
    """獲取未讀數量統計"""
    # 通知未讀數
    notification_count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    
    # 訊息未讀數（簡化計算）
    participant_channels = MessageParticipant.objects.filter(
        user=request.user,
        status='ACTIVE'
    ).select_related('channel')
    
    total_unread_messages = 0
    for participant in participant_channels:
        if participant.last_read_at:
            unread = Message.objects.filter(
                thread__channel=participant.channel,
                sent_at__gt=participant.last_read_at,
                is_deleted=False
            ).count()
            total_unread_messages += unread
        else:
            total_unread_messages += Message.objects.filter(
                thread__channel=participant.channel,
                is_deleted=False
            ).count()
    
    return Response({
        'notifications': notification_count,
        'messages': total_unread_messages
    })
