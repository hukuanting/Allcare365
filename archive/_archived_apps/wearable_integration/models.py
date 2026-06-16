"""
Healthcare 365 穿戴式裝置整合模型
實時數據收集和風險分析
"""

from django.db import models
from django.utils import timezone
from patients.models import BaseModel, Patient
from django.contrib.auth.models import User
import json
import uuid


class WearableDevice(BaseModel):
    """穿戴式裝置管理"""
    
    DEVICE_TYPES = [
        ('continuous_monitor', '連續監護儀'),
        ('wearable_patch', '可穿戴貼片'),
        ('smartwatch', '智能手錶'),
        ('fitness_tracker', '健身追蹤器'),
        ('medical_sensor', '醫療感測器'),
    ]
    
    STATUS_CHOICES = [
        ('active', '使用中'),
        ('inactive', '未使用'),
        ('maintenance', '維護中'),
        ('offline', '離線'),
    ]
    
    device_id = models.CharField(max_length=50, unique=True, verbose_name='裝置ID')
    device_type = models.CharField(max_length=50, choices=DEVICE_TYPES, verbose_name='裝置類型')
    manufacturer = models.CharField(max_length=100, default='Sotera Wireless', verbose_name='製造商')
    model = models.CharField(max_length=100, verbose_name='型號')
    serial_number = models.CharField(max_length=100, unique=True, verbose_name='序號')
    
    # 裝置狀態
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='inactive', verbose_name='狀態')
    last_seen = models.DateTimeField(null=True, blank=True, verbose_name='最後連線時間')
    battery_level = models.IntegerField(null=True, blank=True, verbose_name='電池電量(%)')
    
    # 技術規格
    supported_measurements = models.JSONField(default=list, verbose_name='支援的測量項目')
    sampling_rate = models.IntegerField(default=1, verbose_name='採樣頻率(秒)')
    
    class Meta:
        db_table = 'wearable_devices'
        verbose_name = '穿戴式裝置'
        verbose_name_plural = '穿戴式裝置'
    
    def __str__(self):
        return f"{self.device_id} ({self.get_status_display()})"
    
    def is_online(self):
        """檢查裝置是否在線"""
        if not self.last_seen:
            return False
        return (timezone.now() - self.last_seen).total_seconds() < 60  # 60秒內有數據視為在線


class PatientWearableAssignment(BaseModel):
    """患者穿戴式裝置分配"""
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='wearable_assignments')
    device = models.ForeignKey(WearableDevice, on_delete=models.CASCADE, related_name='patient_assignments')
    
    start_time = models.DateTimeField(verbose_name='開始時間')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='結束時間')
    
    # 住院信息
    care_unit = models.CharField(max_length=100, blank=True, verbose_name='護理單位')
    room = models.CharField(max_length=50, blank=True, verbose_name='房間')
    bed = models.CharField(max_length=50, blank=True, verbose_name='床位')
    
    # 負責人員
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='分配人員')
    
    class Meta:
        db_table = 'patient_wearable_assignments'
        verbose_name = '患者穿戴式裝置分配'
        verbose_name_plural = '患者穿戴式裝置分配'
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.device.device_id}"
    
    @property
    def is_active(self):
        """檢查分配是否仍然有效"""
        now = timezone.now()
        return self.start_time <= now and (self.end_time is None or self.end_time > now)


class RealTimeVitalSigns(BaseModel):
    """實時生命體徵數據"""
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='realtime_vitals')
    device = models.ForeignKey(WearableDevice, on_delete=models.CASCADE, related_name='vital_measurements')
    assignment = models.ForeignKey(PatientWearableAssignment, on_delete=models.CASCADE, null=True)
    
    timestamp = models.DateTimeField(verbose_name='時間戳記', db_index=True)
    
    # 生命體徵數據
    heart_rate = models.FloatField(null=True, blank=True, verbose_name='心率(bpm)')
    systolic_bp = models.IntegerField(null=True, blank=True, verbose_name='收縮壓(mmHg)')
    diastolic_bp = models.IntegerField(null=True, blank=True, verbose_name='舒張壓(mmHg)')
    mean_arterial_pressure = models.IntegerField(null=True, blank=True, verbose_name='平均動脈壓(mmHg)')
    oxygen_saturation = models.FloatField(null=True, blank=True, verbose_name='血氧飽和度(%)')
    respiration_rate = models.FloatField(null=True, blank=True, verbose_name='呼吸率(breaths/min)')
    skin_temperature = models.FloatField(null=True, blank=True, verbose_name='皮膚溫度(°C)')
    
    # 活動和姿態
    posture = models.CharField(max_length=50, null=True, blank=True, verbose_name='姿態')
    activity_level = models.FloatField(null=True, blank=True, verbose_name='活動強度')
    
    # 數據品質
    signal_quality = models.JSONField(default=dict, verbose_name='信號品質')
    data_complete = models.BooleanField(default=True, verbose_name='數據完整性')
    
    class Meta:
        db_table = 'realtime_vital_signs'
        verbose_name = '實時生命體徵'
        verbose_name_plural = '實時生命體徵'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['patient', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"


class RealTimeRiskAnalysis(BaseModel):
    """實時風險分析結果"""
    
    RISK_LEVELS = [
        ('low', '低風險'),
        ('medium_low', '中低風險'),
        ('medium', '中等風險'),
        ('high', '高風險'),
        ('critical', '危急風險'),
    ]
    
    RISK_TYPES = [
        ('cardiovascular', '心血管風險'),
        ('respiratory', '呼吸系統風險'),
        ('fall', '跌倒風險'),
        ('infection', '感染風險'),
        ('arrhythmia', '心律不整風險'),
        ('hypotension', '低血壓風險'),
        ('hypertension', '高血壓風險'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='realtime_risks')
    device = models.ForeignKey(WearableDevice, on_delete=models.CASCADE, related_name='risk_analyses')
    vital_signs = models.ForeignKey(RealTimeVitalSigns, on_delete=models.CASCADE, related_name='risk_analysis')
    
    analysis_timestamp = models.DateTimeField(auto_now_add=True, verbose_name='分析時間')
    
    # 風險分析結果
    risk_type = models.CharField(max_length=20, choices=RISK_TYPES, verbose_name='風險類型')
    risk_level = models.CharField(max_length=20, choices=RISK_LEVELS, verbose_name='風險等級')
    risk_score = models.FloatField(verbose_name='風險分數')
    risk_percentage = models.FloatField(verbose_name='風險百分比')
    
    # 分析詳情
    contributing_factors = models.JSONField(default=list, verbose_name='危險因子')
    recommendations = models.JSONField(default=list, verbose_name='建議')
    alert_triggered = models.BooleanField(default=False, verbose_name='是否觸發警報')
    
    # 趨勢資訊
    trend_direction = models.CharField(max_length=20, choices=[
        ('improving', '改善中'),
        ('stable', '穩定'),
        ('worsening', '惡化中'),
        ('unknown', '未知')
    ], default='unknown', verbose_name='趨勢方向')
    
    confidence_score = models.FloatField(default=0.0, verbose_name='可信度分數')
    
    class Meta:
        db_table = 'realtime_risk_analysis'
        verbose_name = '實時風險分析'
        verbose_name_plural = '實時風險分析'
        ordering = ['-analysis_timestamp']
        indexes = [
            models.Index(fields=['patient', 'risk_type', 'analysis_timestamp']),
            models.Index(fields=['risk_level', 'alert_triggered']),
            models.Index(fields=['analysis_timestamp']),
        ]
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.get_risk_type_display()} ({self.get_risk_level_display()})"


class RealTimeAlert(BaseModel):
    """實時警報"""
    
    ALERT_TYPES = [
        ('critical_vitals', '生命體徵危急'),
        ('device_disconnected', '設備斷線'),
        ('high_risk_detected', '高風險檢測'),
        ('trend_deterioration', '趨勢惡化'),
        ('missing_data', '數據缺失'),
    ]
    
    ALERT_PRIORITIES = [
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('critical', '危急'),
    ]
    
    ALERT_STATUS = [
        ('active', '活躍'),
        ('acknowledged', '已確認'),
        ('resolved', '已解決'),
        ('dismissed', '已忽略'),
    ]
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='realtime_alerts')
    device = models.ForeignKey(WearableDevice, on_delete=models.CASCADE, null=True, related_name='alerts')
    risk_analysis = models.ForeignKey(RealTimeRiskAnalysis, on_delete=models.CASCADE, null=True, related_name='alerts')
    
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES, verbose_name='警報類型')
    priority = models.CharField(max_length=20, choices=ALERT_PRIORITIES, verbose_name='優先級')
    status = models.CharField(max_length=20, choices=ALERT_STATUS, default='active', verbose_name='狀態')
    
    # 時間資訊
    triggered_at = models.DateTimeField(auto_now_add=True, verbose_name='觸發時間')
    acknowledged_at = models.DateTimeField(null=True, blank=True, verbose_name='確認時間')
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name='解決時間')
    
    # 警報內容
    title = models.CharField(max_length=200, verbose_name='警報標題')
    message = models.TextField(verbose_name='警報訊息')
    data_snapshot = models.JSONField(default=dict, verbose_name='數據快照')
    
    # 處理人員
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                      related_name='realtime_alerts_acknowledged_by', verbose_name='確認人員')
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='resolved_alerts', verbose_name='解決人員')
    
    class Meta:
        db_table = 'realtime_alerts'
        verbose_name = '實時警報'
        verbose_name_plural = '實時警報'
        ordering = ['-triggered_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['patient', 'triggered_at']),
            models.Index(fields=['triggered_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.patient.full_name} ({self.get_priority_display()})"


class DataStreamSession(BaseModel):
    """數據流會話管理"""
    
    SESSION_STATUS = [
        ('active', '活躍'),
        ('paused', '暫停'),
        ('stopped', '停止'),
        ('error', '錯誤'),
    ]
    
    session_id = models.UUIDField(default=uuid.uuid4, unique=True, verbose_name='會話ID')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='data_sessions')
    device = models.ForeignKey(WearableDevice, on_delete=models.CASCADE, related_name='data_sessions')
    assignment = models.ForeignKey(PatientWearableAssignment, on_delete=models.CASCADE)
    
    status = models.CharField(max_length=20, choices=SESSION_STATUS, default='active', verbose_name='狀態')
    
    # 會話時間
    started_at = models.DateTimeField(auto_now_add=True, verbose_name='開始時間')
    last_data_received = models.DateTimeField(null=True, blank=True, verbose_name='最後接收數據時間')
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name='結束時間')
    
    # 統計信息
    total_data_points = models.IntegerField(default=0, verbose_name='總數據點數')
    data_quality_score = models.FloatField(default=100.0, verbose_name='數據品質分數')
    
    # 配置
    sampling_interval = models.IntegerField(default=1, verbose_name='採樣間隔(秒)')
    risk_analysis_enabled = models.BooleanField(default=True, verbose_name='啟用風險分析')
    
    class Meta:
        db_table = 'data_stream_sessions'
        verbose_name = '數據流會話'
        verbose_name_plural = '數據流會話'
        ordering = ['-started_at']
    
    def __str__(self):
        return f"Session {self.session_id.hex[:8]} - {self.patient.full_name}"
    
    @property
    def duration(self):
        """獲取會話持續時間"""
        end_time = self.ended_at or timezone.now()
        return end_time - self.started_at
    
    @property
    def is_active(self):
        """檢查會話是否活躍"""
        return self.status == 'active' and (
            not self.last_data_received or 
            (timezone.now() - self.last_data_received).total_seconds() < 300
        )  # 5分鐘內有數據視為活躍