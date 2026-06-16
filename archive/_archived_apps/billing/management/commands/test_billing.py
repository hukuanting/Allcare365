"""
Django management command to test billing system
"""

from django.core.management.base import BaseCommand
from django.test import Client
from django.contrib.auth.models import User
from django.urls import reverse
import json

from billing.models import (
    InsuranceProvider, PatientInsurance, Invoice, InvoiceLineItem,
    Payment, InsuranceClaim, BillingCode, FeeSchedule
)


class Command(BaseCommand):
    help = '測試帳務系統功能'

    def add_arguments(self, parser):
        parser.add_argument(
            '--api-only',
            action='store_true',
            help='只測試API端點',
        )
        parser.add_argument(
            '--frontend-only',
            action='store_true',
            help='只測試前端頁面',
        )

    def handle(self, *args, **options):
        self.client = Client()
        self.setup_test_user()

        try:
            if options['api_only']:
                self.test_api_endpoints()
            elif options['frontend_only']:
                self.test_frontend_pages()
            else:
                self.test_api_endpoints()
                self.test_frontend_pages()
                
            self.stdout.write(
                self.style.SUCCESS('✅ 帳務系統測試完成！')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 測試失敗: {str(e)}')
            )
            raise

    def setup_test_user(self):
        """設置測試用戶"""
        try:
            self.user = User.objects.get(username='admin')
        except User.DoesNotExist:
            self.user = User.objects.create_user(
                username='admin',
                email='admin@example.com',
                password='admin123'
            )
            self.user.is_superuser = True
            self.user.is_staff = True
            self.user.save()

        # 登入用戶
        login_success = self.client.login(username='admin', password='admin123')
        if not login_success:
            raise Exception("無法登入測試用戶")

    def test_api_endpoints(self):
        """測試API端點"""
        self.stdout.write('🔍 測試API端點...')

        api_tests = [
            # 保險提供商API
            {
                'name': '保險提供商列表',
                'url': '/api/v1/billing/insurance-providers/',
                'method': 'GET',
                'expected_status': 200,
            },
            # 發票API
            {
                'name': '發票列表',
                'url': '/api/v1/billing/invoices/',
                'method': 'GET',
                'expected_status': 200,
            },
            # 付款API
            {
                'name': '付款列表',
                'url': '/api/v1/billing/payments/',
                'method': 'GET',
                'expected_status': 200,
            },
            # 保險申請API
            {
                'name': '保險申請列表',
                'url': '/api/v1/billing/insurance-claims/',
                'method': 'GET',
                'expected_status': 200,
            },
            # 帳務代碼API
            {
                'name': '帳務代碼列表',
                'url': '/api/v1/billing/billing-codes/',
                'method': 'GET',
                'expected_status': 200,
            },
            # 費用表API
            {
                'name': '費用表列表',
                'url': '/api/v1/billing/fee-schedules/',
                'method': 'GET',
                'expected_status': 200,
            },
        ]

        for test in api_tests:
            try:
                if test['method'] == 'GET':
                    response = self.client.get(test['url'])
                elif test['method'] == 'POST':
                    response = self.client.post(
                        test['url'],
                        data=json.dumps(test.get('data', {})),
                        content_type='application/json'
                    )

                if response.status_code == test['expected_status']:
                    self.stdout.write(f'  ✓ {test["name"]}: {response.status_code}')
                    
                    # 檢查響應內容
                    if response.status_code == 200 and 'application/json' in response.get('Content-Type', ''):
                        try:
                            data = response.json()
                            if 'results' in data:
                                self.stdout.write(f'    📊 返回 {len(data["results"])} 項記錄')
                            elif isinstance(data, list):
                                self.stdout.write(f'    📊 返回 {len(data)} 項記錄')
                        except json.JSONDecodeError:
                            pass
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  ⚠ {test["name"]}: 期望 {test["expected_status"]}, 實際 {response.status_code}'
                        )
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ❌ {test["name"]}: {str(e)}')
                )

    def test_frontend_pages(self):
        """測試前端頁面"""
        self.stdout.write('🔍 測試前端頁面...')

        # 測試前端頁面
        frontend_tests = [
            {
                'name': '帳務管理主頁',
                'url': reverse('billing_web:billing_management'),
                'expected_status': 200,
            },
            {
                'name': '發票列表',
                'url': reverse('billing_web:invoice_list'),
                'expected_status': 200,
            },
            {
                'name': '新增發票',
                'url': reverse('billing_web:invoice_create'),
                'expected_status': 200,
            },
            {
                'name': '付款管理',
                'url': reverse('billing_web:payment_list'),
                'expected_status': 200,
            },
            {
                'name': '保險管理',
                'url': reverse('billing_web:insurance_management'),
                'expected_status': 200,
            },
            {
                'name': '帳務報告',
                'url': reverse('billing_web:billing_reports'),
                'expected_status': 200,
            },
        ]

        # 測試有數據的詳情頁面
        if Invoice.objects.exists():
            invoice = Invoice.objects.first()
            frontend_tests.append({
                'name': '發票詳情',
                'url': reverse('billing_web:invoice_detail', kwargs={'invoice_id': invoice.id}),
                'expected_status': 200,
            })

        # 測試患者帳務頁面
        if Invoice.objects.exists():
            invoice = Invoice.objects.first()
            if invoice.patient:
                frontend_tests.append({
                    'name': '患者帳務',
                    'url': reverse('billing_web:patient_billing', kwargs={'patient_id': invoice.patient.id}),
                    'expected_status': 200,
                })

        for test in frontend_tests:
            try:
                response = self.client.get(test['url'])
                
                if response.status_code == test['expected_status']:
                    self.stdout.write(f'  ✓ {test["name"]}: {response.status_code}')
                    
                    # 檢查頁面內容
                    if response.status_code == 200:
                        content = response.content.decode('utf-8')
                        if '<!DOCTYPE html>' in content or '<html' in content:
                            self.stdout.write('    📄 HTML頁面載入成功')
                        else:
                            self.stdout.write('    ⚠ 響應不是標準HTML頁面')
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  ⚠ {test["name"]}: 期望 {test["expected_status"]}, 實際 {response.status_code}'
                        )
                    )
                    if response.status_code == 500:
                        self.stdout.write(f'    📄 錯誤詳情: {response.content.decode("utf-8")[:200]}...')
                        
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ❌ {test["name"]}: {str(e)}')
                )

    def test_model_operations(self):
        """測試模型操作"""
        self.stdout.write('🔍 測試模型操作...')

        # 測試創建和查詢操作
        try:
            # 測試保險提供商
            provider_count = InsuranceProvider.objects.count()
            self.stdout.write(f'  📊 保險提供商數量: {provider_count}')

            # 測試發票
            invoice_count = Invoice.objects.count()
            self.stdout.write(f'  📊 發票數量: {invoice_count}')

            # 測試付款記錄
            payment_count = Payment.objects.count()
            self.stdout.write(f'  📊 付款記錄數量: {payment_count}')

            # 測試保險申請
            claim_count = InsuranceClaim.objects.count()
            self.stdout.write(f'  📊 保險申請數量: {claim_count}')

            # 測試帳務代碼
            billing_code_count = BillingCode.objects.count()
            self.stdout.write(f'  📊 帳務代碼數量: {billing_code_count}')

            # 測試統計查詢
            if Invoice.objects.exists():
                total_invoices = Invoice.objects.count()
                paid_invoices = Invoice.objects.filter(status='paid').count()
                pending_invoices = Invoice.objects.filter(status='pending').count()
                overdue_invoices = Invoice.objects.filter(status='overdue').count()

                self.stdout.write(f'  📈 發票統計:')
                self.stdout.write(f'    - 總計: {total_invoices}')
                self.stdout.write(f'    - 已付款: {paid_invoices}')
                self.stdout.write(f'    - 待付款: {pending_invoices}')
                self.stdout.write(f'    - 逾期: {overdue_invoices}')

            self.stdout.write('  ✓ 模型操作測試完成')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  ❌ 模型操作測試失敗: {str(e)}')
            )

    def test_statistics_api(self):
        """測試統計API"""
        self.stdout.write('🔍 測試統計API...')

        stats_tests = [
            {
                'name': '帳務統計',
                'url': '/api/billing/statistics/',
                'method': 'GET',
                'expected_status': 200,
            },
        ]

        for test in stats_tests:
            try:
                response = self.client.get(test['url'])
                
                if response.status_code == test['expected_status']:
                    self.stdout.write(f'  ✓ {test["name"]}: {response.status_code}')
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            self.stdout.write(f'    📊 統計數據: {list(data.keys())}')
                        except json.JSONDecodeError:
                            self.stdout.write('    ⚠ 響應不是有效的JSON')
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  ⚠ {test["name"]}: 期望 {test["expected_status"]}, 實際 {response.status_code}'
                        )
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ❌ {test["name"]}: {str(e)}')
                )
