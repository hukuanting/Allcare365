"""
Laboratory module data initialization command.
Creates sample laboratory providers, test categories, test types, orders, and results.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from datetime import datetime, timedelta

from laboratory.models import (
    LabProvider, LabTestCategory, LabTestType,
    LabOrder, LabOrderItem, LabResult
)
from patients.models import Patient
from administration.models import Provider


class Command(BaseCommand):
    help = 'Initialize laboratory module with sample data'

    def handle(self, *args, **options):
        try:
            with transaction.atomic():
                self.stdout.write('開始初始化實驗室數據...')
                
                # 創建實驗室提供商
                providers = self.create_lab_providers()
                self.stdout.write(f'✓ 已創建 {len(providers)} 個實驗室提供商')
                
                # 創建檢驗分類
                categories = self.create_test_categories()
                self.stdout.write(f'✓ 已創建 {len(categories)} 個檢驗分類')
                
                # 創建檢驗項目
                test_types = self.create_test_types(categories)
                self.stdout.write(f'✓ 已創建 {len(test_types)} 個檢驗項目')
                
                # 獲取患者和醫師
                patients = self.get_or_create_patients()
                ordering_providers = self.get_or_create_ordering_providers()
                
                # 創建檢驗申請單
                orders = self.create_lab_orders(patients, ordering_providers, providers)
                self.stdout.write(f'✓ 已創建 {len(orders)} 張檢驗申請單')
                
                # 創建檢驗項目明細
                order_items = self.create_lab_order_items(orders, test_types)
                self.stdout.write(f'✓ 已創建 {len(order_items)} 個檢驗項目明細')
                
                # 創建檢驗結果
                results = self.create_lab_results(order_items)
                self.stdout.write(f'✓ 已創建 {len(results)} 個檢驗結果')
                
                self.stdout.write('✅ 實驗室系統初始化完成！')
                
        except Exception as e:
            self.stdout.write(f'❌ 初始化失敗: {str(e)}')
            raise

    def create_lab_providers(self):
        """創建實驗室提供商"""
        providers_data = [
            {
                'name': '台大醫院檢驗醫學部',
                'contact_name': '檢驗科主任',
                'phone': '02-2312-3456',
                'email': 'lab@ntuh.gov.tw',
                'address': '台北市中正區中山南路7號',
                'interface_type': 'hl7',
                'clia_number': 'CLIA-001',
                'average_turnaround_time': 24,
                'is_preferred': True,
            },
            {
                'name': '台北榮總檢驗科',
                'contact_name': '檢驗部主任',
                'phone': '02-2875-7524',
                'email': 'lab@vghtpe.gov.tw',
                'address': '台北市北投區石牌路二段201號',
                'interface_type': 'api',
                'clia_number': 'CLIA-002',
                'average_turnaround_time': 12,
                'is_preferred': True,
            },
            {
                'name': '長庚醫院檢驗醫學科',
                'contact_name': '檢驗醫學科主任',
                'phone': '03-328-1200',
                'email': 'lab@cgmh.org.tw',
                'address': '桃園市龜山區復興街5號',
                'interface_type': 'ftp',
                'clia_number': 'CLIA-003',
                'average_turnaround_time': 18,
                'is_preferred': False,
            },
            {
                'name': '中央研究院分子生物研究所',
                'contact_name': '分生所主任',
                'phone': '02-2782-9000',
                'email': 'lab@sinica.edu.tw',
                'address': '台北市南港區研究院路二段128號',
                'interface_type': 'manual',
                'clia_number': 'CLIA-004',
                'average_turnaround_time': 72,
                'is_preferred': False,
            },
        ]
        
        providers = []
        for data in providers_data:
            provider, created = LabProvider.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            providers.append(provider)
        
        return providers

    def create_test_categories(self):
        """創建檢驗分類"""
        categories_data = [
            {'name': '血液學檢查', 'code': 'HEME', 'description': '血球計數、血色素等血液相關檢查'},
            {'name': '生化學檢查', 'code': 'CHEM', 'description': '肝功能、腎功能、血糖等生化檢查'},
            {'name': '免疫學檢查', 'code': 'IMMU', 'description': '抗體、免疫球蛋白等免疫檢查'},
            {'name': '微生物學檢查', 'code': 'MICR', 'description': '細菌培養、病毒檢測等'},
            {'name': '分子診斷', 'code': 'MOLE', 'description': 'PCR、基因檢測等分子生物學檢查'},
            {'name': '內分泌檢查', 'code': 'ENDO', 'description': '荷爾蒙、甲狀腺功能等'},
            {'name': '腫瘤標記', 'code': 'TUMOR', 'description': '癌症標記物檢查'},
            {'name': '尿液檢查', 'code': 'URIN', 'description': '尿液常規及生化檢查'},
        ]
        
        categories = []
        for i, data in enumerate(categories_data):
            data['sort_order'] = i + 1
            category, created = LabTestCategory.objects.get_or_create(
                code=data['code'],
                defaults=data
            )
            categories.append(category)
        
        return categories

    def create_test_types(self, categories):
        """創建檢驗項目"""
        # 建立分類對應字典
        category_map = {cat.code: cat for cat in categories}
        
        test_types_data = [
            # 血液學檢查
            {
                'name': '全血球計數',
                'short_name': 'CBC',
                'category': 'HEME',
                'loinc_code': '57021-8',
                'cpt_code': '85025',
                'specimen_type': 'blood',
                'units': 'cells/μL',
                'reference_range_male': 'WBC: 4,500-11,000',
                'reference_range_female': 'WBC: 4,500-11,000',
                'result_type': 'numeric',
                'average_tat': 2,
                'cost': Decimal('150.00'),
            },
            {
                'name': '血色素',
                'short_name': 'Hb',
                'category': 'HEME',
                'loinc_code': '718-7',
                'specimen_type': 'blood',
                'units': 'g/dL',
                'reference_range_male': '13.5-17.5',
                'reference_range_female': '12.0-15.5',
                'result_type': 'numeric',
                'average_tat': 1,
                'cost': Decimal('100.00'),
            },
            {
                'name': '血小板計數',
                'short_name': 'PLT',
                'category': 'HEME',
                'specimen_type': 'blood',
                'units': '×10³/μL',
                'reference_range_male': '150-450',
                'reference_range_female': '150-450',
                'critical_low': '50',
                'critical_high': '1000',
                'result_type': 'numeric',
                'average_tat': 2,
                'cost': Decimal('120.00'),
            },
            
            # 生化學檢查
            {
                'name': '空腹血糖',
                'short_name': 'AC Sugar',
                'category': 'CHEM',
                'loinc_code': '1558-6',
                'specimen_type': 'serum',
                'units': 'mg/dL',
                'reference_range_male': '70-100',
                'reference_range_female': '70-100',
                'critical_high': '400',
                'result_type': 'numeric',
                'average_tat': 4,
                'cost': Decimal('80.00'),
                'requires_fasting': True,
            },
            {
                'name': '糖化血色素',
                'short_name': 'HbA1c',
                'category': 'CHEM',
                'loinc_code': '4548-4',
                'specimen_type': 'blood',
                'units': '%',
                'reference_range_male': '<5.7',
                'reference_range_female': '<5.7',
                'result_type': 'numeric',
                'average_tat': 6,
                'cost': Decimal('200.00'),
            },
            {
                'name': '總膽固醇',
                'short_name': 'T-Chol',
                'category': 'CHEM',
                'specimen_type': 'serum',
                'units': 'mg/dL',
                'reference_range_male': '<200',
                'reference_range_female': '<200',
                'result_type': 'numeric',
                'average_tat': 4,
                'cost': Decimal('100.00'),
                'requires_fasting': True,
            },
            {
                'name': '肝功能 - ALT',
                'short_name': 'ALT',
                'category': 'CHEM',
                'loinc_code': '1742-6',
                'specimen_type': 'serum',
                'units': 'U/L',
                'reference_range_male': '7-56',
                'reference_range_female': '7-56',
                'result_type': 'numeric',
                'average_tat': 4,
                'cost': Decimal('90.00'),
            },
            {
                'name': '腎功能 - 肌酸酐',
                'short_name': 'Creatinine',
                'category': 'CHEM',
                'loinc_code': '2160-0',
                'specimen_type': 'serum',
                'units': 'mg/dL',
                'reference_range_male': '0.7-1.3',
                'reference_range_female': '0.6-1.1',
                'result_type': 'numeric',
                'average_tat': 4,
                'cost': Decimal('80.00'),
            },
            
            # 免疫學檢查
            {
                'name': 'C反應蛋白',
                'short_name': 'CRP',
                'category': 'IMMU',
                'loinc_code': '1988-5',
                'specimen_type': 'serum',
                'units': 'mg/L',
                'reference_range_male': '<3.0',
                'reference_range_female': '<3.0',
                'result_type': 'numeric',
                'average_tat': 6,
                'cost': Decimal('150.00'),
            },
            {
                'name': 'B型肝炎表面抗原',
                'short_name': 'HBsAg',
                'category': 'IMMU',
                'specimen_type': 'serum',
                'result_type': 'binary',
                'possible_values': ['陰性', '陽性'],
                'average_tat': 12,
                'cost': Decimal('200.00'),
            },
            
            # 內分泌檢查
            {
                'name': '甲狀腺刺激素',
                'short_name': 'TSH',
                'category': 'ENDO',
                'loinc_code': '3016-3',
                'specimen_type': 'serum',
                'units': 'mIU/L',
                'reference_range_male': '0.27-4.2',
                'reference_range_female': '0.27-4.2',
                'result_type': 'numeric',
                'average_tat': 24,
                'cost': Decimal('300.00'),
            },
            
            # 腫瘤標記
            {
                'name': '癌胚抗原',
                'short_name': 'CEA',
                'category': 'TUMOR',
                'specimen_type': 'serum',
                'units': 'ng/mL',
                'reference_range_male': '<5.0',
                'reference_range_female': '<5.0',
                'result_type': 'numeric',
                'average_tat': 24,
                'cost': Decimal('400.00'),
            },
            
            # 尿液檢查
            {
                'name': '尿液常規檢查',
                'short_name': 'Urinalysis',
                'category': 'URIN',
                'specimen_type': 'urine',
                'result_type': 'text',
                'average_tat': 2,
                'cost': Decimal('100.00'),
            },
        ]
        
        test_types = []
        for data in test_types_data:
            category_code = data.pop('category')
            data['category'] = category_map[category_code]
            
            test_type, created = LabTestType.objects.get_or_create(
                name=data['name'],
                category=data['category'],
                defaults=data
            )
            test_types.append(test_type)
        
        return test_types

    def get_or_create_patients(self):
        """獲取或創建測試患者"""
        patients_data = [
            {
                'first_name': '志明',
                'last_name': '王',
                'date_of_birth': datetime(1985, 5, 15).date(),
                'gender': 'M',
                'phone_home': '0912-345-678',
                'email': 'wang@example.com',
                'medical_record_number': 'LAB001001',
            },
            {
                'first_name': '美華',
                'last_name': '李',
                'date_of_birth': datetime(1990, 8, 22).date(),
                'gender': 'F',
                'phone_home': '0923-456-789',
                'email': 'li@example.com',
                'medical_record_number': 'LAB001002',
            },
            {
                'first_name': '小明',
                'last_name': '陳',
                'date_of_birth': datetime(1978, 12, 8).date(),
                'gender': 'M',
                'phone_home': '0934-567-890',
                'email': 'chen@example.com',
                'medical_record_number': 'LAB001003',
            },
        ]
        
        patients = []
        for data in patients_data:
            patient, created = Patient.objects.get_or_create(
                medical_record_number=data['medical_record_number'],
                defaults=data
            )
            patients.append(patient)
        
        return patients

    def get_or_create_ordering_providers(self):
        """獲取或創建醫師"""
        from django.contrib.auth.models import User
        
        providers_data = [
            {
                'username': 'dr_lab_chen',
                'first_name': '志宏',
                'last_name': '陳',
                'email': 'dr.chen@hospital.com',
                'license_number': 'LAB-MD001',
                'npi_number': '1234567801',
                'primary_specialty': '內科',
                'provider_type': 'physician',
            },
            {
                'username': 'dr_lab_liu',
                'first_name': '淑芬',
                'last_name': '劉',
                'email': 'dr.liu@hospital.com',
                'license_number': 'LAB-MD002',
                'npi_number': '1234567802',
                'primary_specialty': '家醫科',
                'provider_type': 'physician',
            },
        ]
        
        providers = []
        for data in providers_data:
            # 創建或獲取用戶
            user, created = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                    'email': data['email'],
                    'is_staff': True,
                }
            )
            
            # 創建或獲取醫師
            provider, created = Provider.objects.get_or_create(
                license_number=data['license_number'],
                defaults={
                    'user': user,
                    'npi_number': data['npi_number'],
                    'primary_specialty': data['primary_specialty'],
                    'provider_type': data['provider_type'],
                    'email': data['email'],
                }
            )
            providers.append(provider)
        
        return providers

    def create_lab_orders(self, patients, ordering_providers, lab_providers):
        """創建檢驗申請單"""
        orders_data = [
            {
                'patient': patients[0],
                'provider': ordering_providers[0],
                'lab_provider': lab_providers[0],
                'order_number': 'ORD001',
                'order_date': timezone.now() - timedelta(days=3),
                'priority': 'routine',
                'status': 'completed',
                'clinical_info': '年度健康檢查',
                'collection_date': timezone.now() - timedelta(days=2, hours=8),
            },
            {
                'patient': patients[1],
                'provider': ordering_providers[1],
                'lab_provider': lab_providers[1],
                'order_number': 'ORD002',
                'order_date': timezone.now() - timedelta(days=1),
                'priority': 'asap',
                'status': 'in_progress',
                'clinical_info': '懷疑糖尿病，需要確認',
                'collection_date': timezone.now() - timedelta(hours=12),
            },
            {
                'patient': patients[2],
                'provider': ordering_providers[0],
                'lab_provider': lab_providers[0],
                'order_number': 'ORD003',
                'order_date': timezone.now(),
                'priority': 'urgent',
                'status': 'pending',
                'clinical_info': '胸痛患者，排除心肌梗塞',
            },
        ]
        
        orders = []
        for data in orders_data:
            order = LabOrder.objects.create(**data)
            orders.append(order)
        
        return orders

    def create_lab_order_items(self, orders, test_types):
        """創建檢驗項目明細"""
        # 為每個申請單添加檢驗項目
        order_items = []
        
        # 第一個申請單 - 健康檢查套餐
        health_check_tests = ['全血球計數', '血色素', '空腹血糖', '總膽固醇', '肝功能 - ALT', '腎功能 - 肌酸酐']
        for test_name in health_check_tests:
            test_type = next((t for t in test_types if t.name == test_name), None)
            if test_type:
                item = LabOrderItem.objects.create(
                    lab_order=orders[0],
                    test_type=test_type,
                    status='completed',
                    cost=50.00,
                )
                order_items.append(item)
        
        # 第二個申請單 - 糖尿病檢查
        diabetes_tests = ['空腹血糖', '糖化血色素']
        for test_name in diabetes_tests:
            test_type = next((t for t in test_types if t.name == test_name), None)
            if test_type:
                item = LabOrderItem.objects.create(
                    lab_order=orders[1],
                    test_type=test_type,
                    status='in_progress',
                    cost=75.00,
                )
                order_items.append(item)
        
        # 第三個申請單 - 急診檢查
        emergency_tests = ['全血球計數', '肝功能 - ALT', '腎功能 - 肌酸酐', 'C反應蛋白']
        for test_name in emergency_tests:
            test_type = next((t for t in test_types if t.name == test_name), None)
            if test_type:
                item = LabOrderItem.objects.create(
                    lab_order=orders[2],
                    test_type=test_type,
                    status='pending',
                    cost=100.00,
                )
                order_items.append(item)
        
        return order_items

    def create_lab_results(self, order_items):
        """創建檢驗結果"""
        results = []
        
        # 為已完成的項目創建結果
        completed_items = [item for item in order_items if item.status == 'completed']
        
        # 模擬結果數據
        sample_results = {
            '全血球計數': {'value': '8,500', 'abnormal_flag': '', 'status': 'final'},
            '血色素': {'value': '14.2', 'abnormal_flag': '', 'status': 'final'},
            '空腹血糖': {'value': '95', 'abnormal_flag': '', 'status': 'final'},
            '總膽固醇': {'value': '185', 'abnormal_flag': '', 'status': 'final'},
            '肝功能 - ALT': {'value': '25', 'abnormal_flag': '', 'status': 'final'},
            '腎功能 - 肌酸酐': {'value': '0.9', 'abnormal_flag': '', 'status': 'final'},
        }
        
        for item in completed_items:
            test_name = item.test_type.name
            if test_name in sample_results:
                result_data = sample_results[test_name]
                
                result = LabResult.objects.create(
                    order_item=item,
                    result_value=result_data['value'],
                    result_date=timezone.now() - timedelta(hours=2),
                    abnormal_flag=result_data['abnormal_flag'],
                    result_status=result_data['status'],
                    units='mg/dL' if any(x in test_name.lower() for x in ['glucose', 'cholesterol']) else 'count/μL',
                    reference_range='70-99 mg/dL' if 'glucose' in test_name.lower() else 'Normal',
                    pathologist_notes='正常範圍內' if not result_data['abnormal_flag'] else '異常值需要複檢',
                )
                results.append(result)
        
        return results
