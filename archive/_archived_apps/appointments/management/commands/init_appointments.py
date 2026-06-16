from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from appointments.models import AppointmentType, Appointment
from patients.models import Patient
from administration.models import Provider
from datetime import datetime, timedelta, time
import random

User = get_user_model()

class Command(BaseCommand):
    help = '初始化預約管理系統的基礎資料'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('開始初始化預約管理系統...'))
        
        # 建立預約類型
        self.create_appointment_types()
        
        # 建立示範預約 (如果有病患和醫護人員的話)
        self.create_sample_appointments()
        
        self.stdout.write(self.style.SUCCESS('預約管理系統初始化完成！'))

    def create_appointment_types(self):
        """建立預約類型"""
        appointment_types = [
            {
                'name': '初診',
                'description': '第一次就診或新病患評估',
                'duration_minutes': 60,
                'color': '#4e73df',
                'is_active': True
            },
            {
                'name': '複診',
                'description': '後續追蹤就診',
                'duration_minutes': 30,
                'color': '#1cc88a',
                'is_active': True
            },
            {
                'name': '急診',
                'description': '緊急就醫',
                'duration_minutes': 45,
                'color': '#e74a3b',
                'is_active': True
            },
            {
                'name': '健康檢查',
                'description': '例行健康檢查',
                'duration_minutes': 90,
                'color': '#36b9cc',
                'is_active': True
            },
            {
                'name': '疫苗接種',
                'description': '各種疫苗注射',
                'duration_minutes': 15,
                'color': '#f6c23e',
                'is_active': True
            },
            {
                'name': '手術諮詢',
                'description': '手術前後諮詢',
                'duration_minutes': 45,
                'color': '#5a5c69',
                'is_active': True
            },
            {
                'name': '物理治療',
                'description': '復健物理治療',
                'duration_minutes': 60,
                'color': '#858796',
                'is_active': True
            },
            {
                'name': '心理諮商',
                'description': '心理健康諮詢',
                'duration_minutes': 50,
                'color': '#5b5c69',
                'is_active': True
            }
        ]

        created_count = 0
        for type_data in appointment_types:
            appointment_type, created = AppointmentType.objects.get_or_create(
                name=type_data['name'],
                defaults=type_data
            )
            if created:
                created_count += 1
                self.stdout.write(f'  ✓ 建立預約類型: {appointment_type.name}')
            else:
                self.stdout.write(f'  - 預約類型已存在: {appointment_type.name}')

        self.stdout.write(self.style.SUCCESS(f'完成建立 {created_count} 個預約類型'))

    def create_sample_appointments(self):
        """建立示範預約資料"""
        # 檢查是否有病患和醫護人員
        patients = Patient.objects.all()[:10]  # 取前10個病患
        providers = Provider.objects.all()[:5]  # 取前5個醫護人員
        
        if not patients:
            self.stdout.write(self.style.WARNING('沒有找到病患資料，跳過建立示範預約'))
            return
            
        if not providers:
            self.stdout.write(self.style.WARNING('沒有找到醫護人員，跳過建立示範預約'))
            return

        appointment_types = AppointmentType.objects.all()
        if not appointment_types:
            self.stdout.write(self.style.WARNING('沒有找到預約類型，跳過建立示範預約'))
            return

        # 建立未來7天的示範預約
        created_count = 0
        for i in range(20):  # 建立20個示範預約
            # 隨機選擇日期（未來7天內）
            appointment_date = datetime.now().date() + timedelta(days=random.randint(0, 7))
            
            # 隨機選擇時間（工作時間 8:00-17:00）
            hours = random.randint(8, 16)
            minutes = random.choice([0, 15, 30, 45])
            appointment_time = time(hours, minutes)
            
            # 隨機選擇狀態
            status = random.choice(['scheduled', 'confirmed', 'completed', 'cancelled'])
            
            # 建立預約
            appointment = Appointment.objects.create(
                patient=random.choice(patients),
                provider=random.choice(providers),
                appointment_type=random.choice(appointment_types),
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                status=status,
                reason_for_visit=f'示範預約 {i+1}',
                special_instructions=f'這是第 {i+1} 個示範預約記錄',
                created_by=providers[0].user if providers and hasattr(providers[0], 'user') else None
            )
            created_count += 1
            
            if i < 5:  # 只顯示前5個
                self.stdout.write(f'  ✓ 建立預約: {appointment.patient} - {appointment.appointment_date} {appointment.appointment_time}')

        self.stdout.write(self.style.SUCCESS(f'完成建立 {created_count} 個示範預約'))
