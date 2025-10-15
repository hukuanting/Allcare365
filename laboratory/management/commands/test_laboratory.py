"""
Laboratory 模組自動化測試命令

檢測所有 Laboratory API 端點和前端頁面是否正常運行
執行方式: python manage.py test_laboratory
"""

from django.core.management.base import BaseCommand
from django.test import Client, TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
import json
import requests
from colorama import Fore, Style, init

# 初始化 colorama
init(autoreset=True)

User = get_user_model()

class Command(BaseCommand):
    help = '測試 Laboratory 模組的 API 端點和前端頁面'

    def __init__(self):
        super().__init__()
        self.client = Client()
        self.api_base_url = 'http://127.0.0.1:8000'
        self.success_count = 0
        self.total_count = 0

    def add_arguments(self, parser):
        parser.add_argument(
            '--api-only',
            action='store_true',
            help='只測試 API，不測試前端頁面',
        )
        parser.add_argument(
            '--frontend-only',
            action='store_true',
            help='只測試前端頁面，不測試 API',
        )

    def handle(self, *args, **options):
        self.stdout.write(f"{Fore.CYAN}🧪 開始測試 Laboratory 模組...{Style.RESET_ALL}")
        
        # 登入測試用戶
        self.login_test_user()
        
        if not options['frontend_only']:
            self.test_laboratory_apis()
            
        if not options['api_only']:
            self.test_frontend_pages()
            
        self.show_summary()

    def login_test_user(self):
        """登入測試用戶"""
        try:
            # 創建或獲取測試用戶
            user, created = User.objects.get_or_create(
                username='testuser',
                defaults={
                    'email': 'test@example.com',
                    'first_name': 'Test',
                    'last_name': 'User',
                    'is_staff': True,
                    'is_superuser': True
                }
            )
            if created:
                user.set_password('testpass123')
                user.save()
            
            # 登入
            login_success = self.client.login(username='testuser', password='testpass123')
            if login_success:
                self.stdout.write(f"{Fore.GREEN}✓ 用戶登入成功{Style.RESET_ALL}")
            else:
                self.stdout.write(f"{Fore.RED}❌ 用戶登入失敗{Style.RESET_ALL}")
                
        except Exception as e:
            self.stdout.write(f"{Fore.RED}❌ 登入過程出錯: {e}{Style.RESET_ALL}")

    def test_api_endpoint(self, name, url, method='GET', data=None, expected_status=200):
        """測試單個 API 端點"""
        self.total_count += 1
        try:
            if method == 'GET':
                response = self.client.get(url)
            elif method == 'POST':
                response = self.client.post(url, data=json.dumps(data) if data else {}, 
                                          content_type='application/json')
            elif method == 'PUT':
                response = self.client.put(url, data=json.dumps(data) if data else {}, 
                                         content_type='application/json')
            elif method == 'DELETE':
                response = self.client.delete(url)
            
            if response.status_code == expected_status:
                self.stdout.write(f"{Fore.GREEN}✓ {name} - {method} {url}{Style.RESET_ALL}")
                self.success_count += 1
                return True
            else:
                self.stdout.write(f"{Fore.RED}❌ {name} - {method} {url} (狀態碼: {response.status_code}){Style.RESET_ALL}")
                return False
                
        except Exception as e:
            self.stdout.write(f"{Fore.RED}❌ {name} - {method} {url} (錯誤: {e}){Style.RESET_ALL}")
            return False

    def test_frontend_page(self, name, url, expected_status=200):
        """測試前端頁面"""
        self.total_count += 1
        try:
            response = self.client.get(url)
            
            if response.status_code == expected_status:
                self.stdout.write(f"{Fore.GREEN}✓ {name} - GET {url}{Style.RESET_ALL}")
                self.success_count += 1
                return True
            else:
                self.stdout.write(f"{Fore.RED}❌ {name} - GET {url} (狀態碼: {response.status_code}){Style.RESET_ALL}")
                return False
                
        except Exception as e:
            self.stdout.write(f"{Fore.RED}❌ {name} - GET {url} (錯誤: {e}){Style.RESET_ALL}")
            return False

    def test_laboratory_apis(self):
        """測試 Laboratory API 端點"""
        self.stdout.write(f"\n{Fore.YELLOW}📡 測試 Laboratory API 端點...{Style.RESET_ALL}")
        
        # 基本 API 端點測試
        api_tests = [
            # Lab Providers
            ("Lab Providers List", "/api/v1/laboratory/providers/"),
            
            # Lab Test Categories  
            ("Lab Test Categories List", "/api/v1/laboratory/test-categories/"),
            
            # Lab Test Types
            ("Lab Test Types List", "/api/v1/laboratory/test-types/"),
            
            # Lab Orders
            ("Lab Orders List", "/api/v1/laboratory/orders/"),
            
            # Lab Order Items
            ("Lab Order Items List", "/api/v1/laboratory/order-items/"),
            
            # Lab Results
            ("Lab Results List", "/api/v1/laboratory/results/"),
            
            # Statistics
            ("Lab Statistics", "/api/v1/laboratory/statistics/"),
            
            # HL7 Processing (POST endpoint)
            # ("HL7 Process", "/api/v1/laboratory/hl7/process/", "POST"),
        ]
        
        for name, url in api_tests:
            self.test_api_endpoint(name, url)

    def test_frontend_pages(self):
        """測試前端頁面"""
        self.stdout.write(f"\n{Fore.YELLOW}🌐 測試 Laboratory 前端頁面...{Style.RESET_ALL}")
        
        # 前端頁面測試
        frontend_tests = [
            ("Laboratory Dashboard", "/laboratory/"),
            ("Lab Order List", "/laboratory/orders/"),
            ("Lab Order Create", "/laboratory/orders/create/"),
            ("Lab Results List", "/laboratory/results/"),
            ("Lab Test Management", "/laboratory/tests/"),
        ]
        
        for name, url in frontend_tests:
            self.test_frontend_page(name, url)

    def test_specific_record_pages(self):
        """測試特定記錄的頁面（需要記錄 ID）"""
        self.stdout.write(f"\n{Fore.YELLOW}📄 測試特定記錄頁面...{Style.RESET_ALL}")
        
        # 先獲取一些記錄 ID 進行測試
        try:
            # 獲取第一個 lab order
            response = self.client.get('/api/v1/laboratory/lab-orders/')
            if response.status_code == 200:
                data = response.json()
                if data.get('results') and len(data['results']) > 0:
                    order_id = data['results'][0]['id']
                    
                    # 測試詳情頁面
                    detail_tests = [
                        ("Lab Order Detail", f"/laboratory/orders/{order_id}/"),
                    ]
                    
                    for name, url in detail_tests:
                        self.test_frontend_page(name, url)
                        
        except Exception as e:
            self.stdout.write(f"{Fore.YELLOW}⚠️ 跳過特定記錄測試: {e}{Style.RESET_ALL}")

    def show_summary(self):
        """顯示測試總結"""
        self.stdout.write(f"\n{Fore.CYAN}📊 測試總結{Style.RESET_ALL}")
        self.stdout.write(f"總測試項目: {self.total_count}")
        self.stdout.write(f"{Fore.GREEN}成功: {self.success_count}{Style.RESET_ALL}")
        self.stdout.write(f"{Fore.RED}失敗: {self.total_count - self.success_count}{Style.RESET_ALL}")
        
        success_rate = (self.success_count / self.total_count * 100) if self.total_count > 0 else 0
        
        if success_rate >= 90:
            color = Fore.GREEN
            emoji = "🎉"
        elif success_rate >= 70:
            color = Fore.YELLOW
            emoji = "⚠️"
        else:
            color = Fore.RED
            emoji = "❌"
            
        self.stdout.write(f"{color}{emoji} 成功率: {success_rate:.1f}%{Style.RESET_ALL}")
        
        if success_rate == 100:
            self.stdout.write(f"{Fore.GREEN}🎊 所有測試通過！Laboratory 模組運行正常。{Style.RESET_ALL}")
        elif success_rate >= 90:
            self.stdout.write(f"{Fore.YELLOW}👍 大部分測試通過，Laboratory 模組基本正常。{Style.RESET_ALL}")
        else:
            self.stdout.write(f"{Fore.RED}⚠️ 有較多測試失敗，請檢查 Laboratory 模組配置。{Style.RESET_ALL}")
