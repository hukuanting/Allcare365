from django.core.management.base import BaseCommand
from django.test import Client
from django.contrib.auth.models import User
from appointments.models import AppointmentType, Appointment
from patients.models import Patient
from administration.models import Provider
import json

class Command(BaseCommand):
    help = '測試預約管理系統的前端和API功能'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('開始測試預約管理系統...'))
        
        # 設置測試客戶端
        self.client = Client()
        
        # 測試資料驗證
        self.test_data_verification()
        
        # 測試前端頁面
        self.test_frontend_pages()
        
        # 測試API端點
        self.test_api_endpoints()
        
        self.stdout.write(self.style.SUCCESS('預約管理系統測試完成！'))

    def test_data_verification(self):
        """驗證測試資料是否存在"""
        self.stdout.write(self.style.WARNING('驗證測試資料...'))
        
        appointment_types = AppointmentType.objects.count()
        appointments = Appointment.objects.count()
        patients = Patient.objects.count()
        providers = Provider.objects.count()
        
        self.stdout.write(f'  - 預約類型: {appointment_types} 個')
        self.stdout.write(f'  - 預約記錄: {appointments} 個')
        self.stdout.write(f'  - 病患: {patients} 個')
        self.stdout.write(f'  - 醫護人員: {providers} 個')
        
        if appointment_types == 0:
            self.stdout.write(self.style.ERROR('  ❌ 沒有預約類型資料'))
        else:
            self.stdout.write(self.style.SUCCESS('  ✅ 預約類型資料正常'))
            
        if appointments == 0:
            self.stdout.write(self.style.WARNING('  ⚠️  沒有預約記錄'))
        else:
            self.stdout.write(self.style.SUCCESS('  ✅ 預約記錄正常'))

    def test_frontend_pages(self):
        """測試前端頁面"""
        self.stdout.write(self.style.WARNING('測試前端頁面...'))
        
        pages = [
            ('/appointments/', '預約管理'),
            ('/appointments/calendar/', '預約日曆'),
            ('/appointments/schedule/', '預約排程'),
            ('/appointments/reports/', '預約報告'),
        ]
        
        for url, name in pages:
            try:
                response = self.client.get(url)
                if response.status_code == 200:
                    self.stdout.write(f'  ✅ {name} ({url}) - 載入成功')
                else:
                    self.stdout.write(f'  ❌ {name} ({url}) - 狀態碼: {response.status_code}')
            except Exception as e:
                self.stdout.write(f'  ❌ {name} ({url}) - 錯誤: {str(e)}')

    def test_api_endpoints(self):
        """測試API端點"""
        self.stdout.write(self.style.WARNING('測試API端點...'))
        
        api_endpoints = [
            ('/api/v1/appointments/api/appointment-types/', 'GET', '預約類型列表'),
            ('/api/v1/appointments/api/appointments/', 'GET', '預約列表'),
            ('/api/v1/appointments/api/appointment-types/active/', 'GET', '活躍預約類型'),
        ]
        
        for url, method, name in api_endpoints:
            try:
                if method == 'GET':
                    response = self.client.get(url)
                elif method == 'POST':
                    response = self.client.post(url, {}, content_type='application/json')
                
                if response.status_code in [200, 201]:
                    self.stdout.write(f'  ✅ {name} ({method} {url}) - 回應成功')
                    
                    # 嘗試解析JSON回應
                    try:
                        data = response.json()
                        if isinstance(data, list):
                            self.stdout.write(f'    📊 回傳 {len(data)} 筆記錄')
                        elif isinstance(data, dict) and 'results' in data:
                            self.stdout.write(f'    📊 回傳 {len(data["results"])} 筆記錄')
                    except:
                        pass
                        
                else:
                    self.stdout.write(f'  ❌ {name} ({method} {url}) - 狀態碼: {response.status_code}')
                    
            except Exception as e:
                self.stdout.write(f'  ❌ {name} ({method} {url}) - 錯誤: {str(e)}')

    def test_appointment_features(self):
        """測試預約功能"""
        self.stdout.write(self.style.WARNING('測試預約功能...'))
        
        # 測試預約統計
        try:
            response = self.client.get('/api/v1/appointments/api/appointments/statistics/')
            if response.status_code == 200:
                self.stdout.write('  ✅ 預約統計API - 正常')
            else:
                self.stdout.write(f'  ❌ 預約統計API - 狀態碼: {response.status_code}')
        except Exception as e:
            self.stdout.write(f'  ❌ 預約統計API - 錯誤: {str(e)}')
