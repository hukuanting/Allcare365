from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q
from django.utils.dateparse import parse_date
from .models import (
    AppointmentType, Appointment, WaitingList, 
    RecurringAppointment, AppointmentNote
)
from .serializers import (
    AppointmentTypeSerializer, AppointmentSerializer, AppointmentSummarySerializer,
    AppointmentWaitingListSerializer, RecurringAppointmentSerializer,
    AppointmentNoteSerializer, AppointmentDetailSerializer,
    AppointmentCalendarSerializer, AppointmentStatisticsSerializer
)


@login_required
def appointment_list_view(request):
    """預約列表頁面視圖"""
    return render(request, 'appointments/appointment_list.html')


class AppointmentTypeViewSet(viewsets.ModelViewSet):
    """預約類型視圖集"""
    queryset = AppointmentType.objects.all()
    serializer_class = AppointmentTypeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active']
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """獲取活躍的預約類型"""
        active_types = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(active_types, many=True)
        return Response(serializer.data)


class AppointmentViewSet(viewsets.ModelViewSet):
    """預約視圖集"""
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'appointment_type', 'provider', 'patient']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 日期範圍篩選
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(appointment_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(appointment_date__lte=end_date)
        
        return queryset.select_related('patient', 'provider', 'appointment_type', 'facility')
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return AppointmentDetailSerializer
        elif self.action == 'list':
            return AppointmentSummarySerializer
        return AppointmentSerializer
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """今日預約"""
        today = timezone.now().date()
        appointments = self.get_queryset().filter(
            appointment_date=today
        ).order_by('appointment_time')
        
        serializer = AppointmentSummarySerializer(appointments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """即將到來的預約"""
        now = timezone.now()
        upcoming_appointments = self.get_queryset().filter(
            appointment_date__gte=now,
            status__in=['scheduled', 'confirmed']
        ).order_by('appointment_date')[:10]
        
        serializer = AppointmentSummarySerializer(upcoming_appointments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def calendar(self, request):
        """日曆視圖資料"""
        start_date = request.query_params.get('start')
        end_date = request.query_params.get('end')
        
        queryset = self.get_queryset()
        
        if start_date:
            queryset = queryset.filter(appointment_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(appointment_date__lte=end_date)
        
        serializer = AppointmentCalendarSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def check_in(self, request, pk=None):
        """病患報到"""
        appointment = self.get_object()
        
        if appointment.status != 'confirmed':
            return Response(
                {'error': '只有已確認的預約才能報到'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        appointment.status = 'checked_in'
        appointment.check_in_time = timezone.now()
        appointment.check_in_by = request.user
        appointment.save()
        
        return Response({'message': '報到成功'})
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """完成預約"""
        appointment = self.get_object()
        
        if appointment.status not in ['checked_in', 'in_progress']:
            return Response(
                {'error': '只有已報到或進行中的預約才能完成'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        appointment.status = 'completed'
        appointment.save()
        
        return Response({'message': '預約已完成'})
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """取消預約"""
        appointment = self.get_object()
        
        if appointment.status in ['completed', 'cancelled']:
            return Response(
                {'error': '已完成或已取消的預約無法再次取消'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        appointment.status = 'cancelled'
        appointment.cancellation_reason = request.data.get('cancellation_reason', request.data.get('reason', ''))
        appointment.cancelled_by = request.user
        appointment.cancellation_date = timezone.now()
        appointment.save()
        
        return Response({'message': '預約已取消'})
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """預約統計"""
        queryset = self.get_queryset()
        
        # 基本統計
        total_appointments = queryset.count()
        status_counts = queryset.values('status').annotate(count=Count('id'))
        
        # 按預約類型統計
        type_stats = queryset.values('appointment_type__name').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # 按醫師統計
        provider_stats = queryset.values('provider__first_name', 'provider__last_name').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # 每日統計（最近30天）
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        daily_stats = []
        for i in range(31):
            current_date = start_date + timedelta(days=i)
            count = queryset.filter(appointment_date__date=current_date).count()
            daily_stats.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'count': count
            })
        
        # 月度統計（最近12個月）
        monthly_stats = []
        for i in range(12):
            current_date = end_date.replace(day=1) - timedelta(days=i*30)
            count = queryset.filter(
                appointment_date__year=current_date.year,
                appointment_date__month=current_date.month
            ).count()
            monthly_stats.append({
                'month': current_date.strftime('%Y-%m'),
                'count': count
            })
        
        data = {
            'total_appointments': total_appointments,
            'scheduled_appointments': sum(s['count'] for s in status_counts if s['status'] == 'scheduled'),
            'confirmed_appointments': sum(s['count'] for s in status_counts if s['status'] == 'confirmed'),
            'completed_appointments': sum(s['count'] for s in status_counts if s['status'] == 'completed'),
            'cancelled_appointments': sum(s['count'] for s in status_counts if s['status'] == 'cancelled'),
            'no_show_appointments': sum(s['count'] for s in status_counts if s['status'] == 'no_show'),
            'appointment_types': type_stats,
            'providers': provider_stats,
            'daily_stats': daily_stats,
            'monthly_stats': monthly_stats
        }
        
        serializer = AppointmentStatisticsSerializer(data)
        return Response(serializer.data)


class WaitingListViewSet(viewsets.ModelViewSet):
    """候補名單視圖集"""
    queryset = WaitingList.objects.all()
    serializer_class = AppointmentWaitingListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'appointment_type', 'provider', 'patient']
    
    def get_queryset(self):
        return super().get_queryset().select_related('patient', 'provider', 'appointment_type')
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """活躍的候補名單"""
        active_waitlist = self.get_queryset().filter(status='waiting')
        serializer = self.get_serializer(active_waitlist, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def notify(self, request, pk=None):
        """通知候補病患"""
        waitlist_entry = self.get_object()
        
        if waitlist_entry.status != 'waiting':
            return Response(
                {'error': '只能通知等待中的候補病患'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        waitlist_entry.status = 'notified'
        waitlist_entry.save()
        
        return Response({'message': '已通知病患'})


class RecurringAppointmentViewSet(viewsets.ModelViewSet):
    """重複預約視圖集"""
    queryset = RecurringAppointment.objects.all()
    serializer_class = RecurringAppointmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['frequency', 'is_active', 'patient', 'provider']
    
    def get_queryset(self):
        return super().get_queryset().select_related('patient', 'provider', 'appointment_type')
    
    @action(detail=True, methods=['post'])
    def generate_appointments(self, request, pk=None):
        """生成重複預約"""
        recurring_appointment = self.get_object()
        
        if not recurring_appointment.is_active:
            return Response(
                {'error': '只能為活躍的重複預約生成預約'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 生成預約邏輯
        generated_count = 0
        current_date = recurring_appointment.start_date
        
        while current_date <= recurring_appointment.end_date:
            # 檢查是否已存在該日期的預約
            existing_appointment = Appointment.objects.filter(
                patient=recurring_appointment.patient,
                provider=recurring_appointment.provider,
                appointment_date__date=current_date
            ).first()
            
            if not existing_appointment:
                # 創建新預約
                appointment_datetime = datetime.combine(
                    current_date, 
                    recurring_appointment.preferred_time
                )
                
                Appointment.objects.create(
                    patient=recurring_appointment.patient,
                    provider=recurring_appointment.provider,
                    appointment_type=recurring_appointment.appointment_type,
                    facility=recurring_appointment.facility,
                    appointment_date=appointment_datetime,
                    duration=recurring_appointment.duration,
                    status='scheduled',
                    notes=f'自動生成自重複預約 #{recurring_appointment.id}'
                )
                generated_count += 1
            
            # 計算下一個預約日期
            if recurring_appointment.frequency == 'daily':
                current_date += timedelta(days=1)
            elif recurring_appointment.frequency == 'weekly':
                current_date += timedelta(weeks=1)
            elif recurring_appointment.frequency == 'monthly':
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)
            elif recurring_appointment.frequency == 'yearly':
                current_date = current_date.replace(year=current_date.year + 1)
        
        return Response({'message': f'已生成 {generated_count} 個預約'})


class AppointmentNoteViewSet(viewsets.ModelViewSet):
    """預約筆記視圖集"""
    queryset = AppointmentNote.objects.all()
    serializer_class = AppointmentNoteSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['appointment', 'author']
    
    def get_queryset(self):
        return super().get_queryset().select_related('appointment', 'author')
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


# 保留舊的視圖集為了向後兼容
class ScheduleViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response({'message': 'Schedules list'})


class WaitingListViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response({'message': 'Waiting list'})


# Frontend Views
def appointment_management_view(request):
    """預約管理主頁面"""
    return render(request, 'appointments/appointment_management.html', {
        'title': '預約管理'
    })

def modern_appointment_management_view(request):
    """現代化預約管理頁面"""
    from datetime import date
    context = {
        'title': '預約管理',
        'today': date.today(),
        'breadcrumb': [
            {'name': '首頁', 'url': '/'},
            {'name': '預約管理', 'url': ''}
        ]
    }
    return render(request, 'appointments/modern_appointment_management.html', context)

def appointment_calendar_view(request):
    """預約行事曆頁面"""
    return render(request, 'appointments/appointment_calendar.html', {
        'title': '預約行事曆'
    })

def appointment_schedule_view(request):
    """預約排程頁面"""
    return render(request, 'appointments/appointment_schedule.html', {
        'title': '預約排程'
    })

def appointment_detail_view(request, appointment_id):
    """預約詳情頁面"""
    try:
        appointment = Appointment.objects.select_related(
            'patient', 'provider', 'appointment_type', 'facility'
        ).get(id=appointment_id)
        return render(request, 'appointments/appointment_detail.html', {
            'appointment': appointment,
            'title': f'預約詳情 - {appointment.patient}'
        })
    except Appointment.DoesNotExist:
        return render(request, '404.html', status=404)

def appointment_create_view(request):
    """新增預約頁面"""
    return render(request, 'appointments/appointment_create.html', {
        'title': '新增預約'
    })

def appointment_edit_view(request, appointment_id):
    """編輯預約頁面"""
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        return render(request, 'appointments/appointment_edit.html', {
            'appointment': appointment,
            'title': f'編輯預約 - {appointment.patient}'
        })
    except Appointment.DoesNotExist:
        return render(request, '404.html', status=404)

def waitlist_management_view(request):
    """候補名單管理頁面"""
    return render(request, 'appointments/waitlist_management.html', {
        'title': '候補名單管理'
    })

def appointment_reports_view(request):
    """預約報告頁面"""
    return render(request, 'appointments/appointment_reports.html', {
        'title': '預約報告'
    })
