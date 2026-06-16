"""
Django management command to initialize billing data
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from datetime import datetime, timedelta
import uuid

from billing.models import (
    InsuranceProvider, PatientInsurance, Invoice, InvoiceLineItem,
    Payment, InsuranceClaim, BillingCode, FeeSchedule
)
from patients.models import Patient
from administration.models import Provider


class Command(BaseCommand):
    help = '初始化帳務系統測試數據'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clean',
            action='store_true',
            help='清除現有數據後重新初始化',
        )

    def handle(self, *args, **options):
        if options['clean']:
            self.stdout.write('清除現有帳務數據...')
            self.clean_data()

        try:
            with transaction.atomic():
                self.stdout.write('開始初始化帳務數據...')
                
                # 創建保險提供商
                insurance_providers = self.create_insurance_providers()
                self.stdout.write(f'✓ 已創建 {len(insurance_providers)} 個保險提供商')
                
                # 創建帳務代碼
                billing_codes = self.create_billing_codes()
                self.stdout.write(f'✓ 已創建 {len(billing_codes)} 個帳務代碼')
                
                # 創建費用表
                fee_schedule = self.create_fee_schedule(billing_codes)
                self.stdout.write(f'✓ 已創建 {len(fee_schedule)} 個費用項目')
                
                # 獲取患者和醫師
                patients = self.get_or_create_patients()
                providers = self.get_or_create_providers()
                
                # 創建患者保險
                patient_insurances = self.create_patient_insurances(patients, insurance_providers)
                self.stdout.write(f'✓ 已創建 {len(patient_insurances)} 個患者保險記錄')
                
                # 創建發票
                invoices = self.create_invoices(patients, providers, billing_codes, fee_schedule)
                self.stdout.write(f'✓ 已創建 {len(invoices)} 張發票')
                
                # 創建付款記錄
                payments = self.create_payments(invoices)
                self.stdout.write(f'✓ 已創建 {len(payments)} 筆付款記錄')
                
                # 創建保險申請
                claims = self.create_insurance_claims(invoices, insurance_providers)
                self.stdout.write(f'✓ 已創建 {len(claims)} 筆保險申請')
                
                self.stdout.write(
                    self.style.SUCCESS('✅ 帳務系統初始化完成！')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 初始化失敗: {str(e)}')
            )
            raise

    def clean_data(self):
        """清除現有數據"""
        InsuranceClaim.objects.all().delete()
        Payment.objects.all().delete()
        InvoiceLineItem.objects.all().delete()
        Invoice.objects.all().delete()
        PatientInsurance.objects.all().delete()
        FeeSchedule.objects.all().delete()
        BillingCode.objects.all().delete()
        InsuranceProvider.objects.all().delete()

    def create_insurance_providers(self):
        """創建保險提供商"""
        providers_data = [
            {
                'name': '中央健康保險署',
                'type': 'medicaid',
                'phone': '0800-030-598',
                'email': 'service@nhi.gov.tw',
                'address': '台北市中正區中山南路1號',
                'electronic_payer_id': 'NHI-001',
                'is_active': True,
            },
            {
                'name': '國泰人壽保險股份有限公司',
                'type': 'commercial',
                'phone': '0800-036-599',
                'email': 'service@cathaylife.com.tw',
                'address': '台北市大安區敦化南路二段39號',
                'electronic_payer_id': 'CTL-002',
                'is_active': True,
            },
            {
                'name': '富邦人壽保險股份有限公司',
                'type': 'commercial',
                'phone': '0800-009-888',
                'email': 'service@fubon.com',
                'address': '台北市松山區敦化南路一段108號',
                'electronic_payer_id': 'FBL-003',
                'is_active': True,
            },
            {
                'name': '新光人壽保險股份有限公司',
                'type': 'commercial',
                'phone': '0800-031-115',
                'email': 'service@skl.com.tw',
                'address': '台北市信義區松仁路36號',
                'electronic_payer_id': 'SKL-004',
                'is_active': True,
            },
        ]
        
        providers = []
        for data in providers_data:
            provider, created = InsuranceProvider.objects.get_or_create(
                electronic_payer_id=data['electronic_payer_id'],
                defaults=data
            )
            providers.append(provider)
        
        return providers

    def create_billing_codes(self):
        """創建帳務代碼"""
        codes_data = [
            {'code': '99213', 'code_type': 'cpt', 'description': '門診診察費(中等複雜度)', 'category': 'consultation', 'default_fee': Decimal('300.00')},
            {'code': '99214', 'code_type': 'cpt', 'description': '門診診察費(高複雜度)', 'category': 'consultation', 'default_fee': Decimal('450.00')},
            {'code': '99215', 'code_type': 'cpt', 'description': '門診診察費(極高複雜度)', 'category': 'consultation', 'default_fee': Decimal('600.00')},
            {'code': '85025', 'code_type': 'cpt', 'description': '血液常規檢查(CBC)', 'category': 'laboratory', 'default_fee': Decimal('150.00')},
            {'code': '80053', 'code_type': 'cpt', 'description': '基本代謝功能檢查', 'category': 'laboratory', 'default_fee': Decimal('200.00')},
            {'code': '80061', 'code_type': 'cpt', 'description': '脂質檢查', 'category': 'laboratory', 'default_fee': Decimal('180.00')},
            {'code': '85610', 'code_type': 'cpt', 'description': '凝血酶原時間檢查', 'category': 'laboratory', 'default_fee': Decimal('120.00')},
            {'code': '71020', 'code_type': 'cpt', 'description': '胸部X光檢查', 'category': 'radiology', 'default_fee': Decimal('250.00')},
            {'code': '73060', 'code_type': 'cpt', 'description': '膝關節X光檢查', 'category': 'radiology', 'default_fee': Decimal('200.00')},
            {'code': '76700', 'code_type': 'cpt', 'description': '腹部超音波檢查', 'category': 'radiology', 'default_fee': Decimal('350.00')},
            {'code': 'J7050', 'code_type': 'hcpcs', 'description': '一般藥品費用', 'category': 'medication', 'default_fee': Decimal('100.00')},
            {'code': 'J7060', 'code_type': 'hcpcs', 'description': '抗生素藥品費用', 'category': 'medication', 'default_fee': Decimal('250.00')},
            {'code': '90471', 'code_type': 'cpt', 'description': '疫苗注射費', 'category': 'immunization', 'default_fee': Decimal('50.00')},
            {'code': '90715', 'code_type': 'cpt', 'description': '流感疫苗', 'category': 'immunization', 'default_fee': Decimal('800.00')},
        ]
        
        codes = []
        for data in codes_data:
            code, created = BillingCode.objects.get_or_create(
                code=data['code'],
                defaults=data
            )
            codes.append(code)
        
        return codes

    def create_fee_schedule(self, billing_codes):
        """創建費用表"""
        fee_data = {
            '99213': Decimal('300.00'),
            '99214': Decimal('450.00'),
            '99215': Decimal('600.00'),
            '85025': Decimal('150.00'),
            '80053': Decimal('200.00'),
            '80061': Decimal('180.00'),
            '85610': Decimal('120.00'),
            '71020': Decimal('250.00'),
            '73060': Decimal('200.00'),
            '76700': Decimal('350.00'),
            'J7050': Decimal('100.00'),
            'J7060': Decimal('250.00'),
            '90471': Decimal('50.00'),
            '90715': Decimal('800.00'),
        }
        
        schedules = []
        # 為每個保險提供商創建費用表
        insurance_providers = InsuranceProvider.objects.all()
        for provider in insurance_providers:
            for code in billing_codes:
                if code.code in fee_data:
                    schedule, created = FeeSchedule.objects.get_or_create(
                        insurance_provider=provider,
                        billing_code=code,
                        effective_date=datetime.now().date(),
                        defaults={
                            'fee_amount': fee_data[code.code],
                        }
                    )
                    schedules.append(schedule)
        
        return schedules

    def get_or_create_patients(self):
        """獲取或創建患者"""
        patients_data = [
            {
                'first_name': '小明',
                'last_name': '王',
                'date_of_birth': datetime(1990, 5, 15).date(),
                'gender': 'M',
                'phone_home': '0912-345-678',
                'email': 'wang@example.com',
                'street_address': '台北市中正區中山南路1號',
                'city': '台北市',
                'state': '台北',
                'zip_code': '10048',
                'emergency_contact_name': '王媽媽',
                'emergency_contact_phone': '0987-654-321',
                'medical_record_number': 'MR001001',
            },
            {
                'first_name': '美麗',
                'last_name': '李',
                'date_of_birth': datetime(1985, 8, 22).date(),
                'gender': 'F',
                'phone_home': '0923-456-789',
                'email': 'li@example.com',
                'street_address': '台北市大安區敦化南路100號',
                'city': '台北市',
                'state': '台北',
                'zip_code': '10692',
                'emergency_contact_name': '李先生',
                'emergency_contact_phone': '0976-543-210',
                'medical_record_number': 'MR001002',
            },
            {
                'first_name': '志明',
                'last_name': '陳',
                'date_of_birth': datetime(1978, 12, 8).date(),
                'gender': 'M',
                'phone_home': '0934-567-890',
                'email': 'chen@example.com',
                'street_address': '台北市信義區松仁路50號',
                'city': '台北市',
                'state': '台北',
                'zip_code': '11051',
                'emergency_contact_name': '陳太太',
                'emergency_contact_phone': '0965-432-109',
                'medical_record_number': 'MR001003',
            },
        ]
        
        patients = []
        for data in patients_data:
            patient, created = Patient.objects.get_or_create(
                medical_record_number=data['medical_record_number'],
                defaults=data
            )
            patients.append(patient)
            if created:
                self.stdout.write(f"已創建患者: {patient.first_name} {patient.last_name}")
        
        return patients

    def get_or_create_providers(self):
        """獲取或創建醫師"""
        from django.contrib.auth.models import User
        
        providers_data = [
            {
                'username': 'dr_li',
                'first_name': '建國',
                'last_name': '李',
                'email': 'dr.li@hospital.com',
                'license_number': 'MD001234',
                'npi_number': '1234567890',
                'primary_specialty': '內科',
                'provider_type': 'physician',
                'phone': '02-1234-5678',
                'is_accepting_patients': True,
            },
            {
                'username': 'dr_wang',
                'first_name': '淑芬',
                'last_name': '王',
                'email': 'dr.wang@hospital.com',
                'license_number': 'MD002345',
                'npi_number': '2345678901',
                'primary_specialty': '小兒科',
                'provider_type': 'physician',
                'phone': '02-2345-6789',
                'is_accepting_patients': True,
            },
            {
                'username': 'dr_chen',
                'first_name': '志宏',
                'last_name': '陳',
                'email': 'dr.chen@hospital.com',
                'license_number': 'MD003456',
                'npi_number': '3456789012',
                'primary_specialty': '外科',
                'provider_type': 'physician',
                'phone': '02-3456-7890',
                'is_accepting_patients': True,
            },
        ]
        
        providers = []
        for data in providers_data:
            # 先創建或獲取用戶
            user, created = User.objects.get_or_create(
                username=data['username'],
                defaults={
                    'first_name': data['first_name'],
                    'last_name': data['last_name'],
                    'email': data['email'],
                    'is_staff': True,
                }
            )
            
            # 然後創建或獲取醫師資料
            provider, created = Provider.objects.get_or_create(
                license_number=data['license_number'],
                defaults={
                    'user': user,
                    'npi_number': data['npi_number'],
                    'primary_specialty': data['primary_specialty'],
                    'provider_type': data['provider_type'],
                    'phone': data['phone'],
                    'email': data['email'],
                    'is_accepting_patients': data['is_accepting_patients'],
                }
            )
            providers.append(provider)
            if created:
                self.stdout.write(f"已創建醫師: {provider.full_name}")
        
        return providers

    def create_patient_insurances(self, patients, insurance_providers):
        """創建患者保險記錄"""
        insurances = []
        
        # 所有患者都有健保
        nhi_provider = next(p for p in insurance_providers if p.electronic_payer_id == 'NHI-001')
        for patient in patients:
            insurance, created = PatientInsurance.objects.get_or_create(
                patient=patient,
                insurance_provider=nhi_provider,
                coverage_type='primary',
                defaults={
                    'policy_number': f'NHI{str(patient.id)[:8]}',
                    'group_number': 'GROUP001',
                    'is_active': True,
                    'effective_date': datetime.now().date() - timedelta(days=365),
                }
            )
            insurances.append(insurance)
        
        # 部分患者有額外保險
        if len(patients) > 1 and len(insurance_providers) > 1:
            cathay_provider = next(p for p in insurance_providers if p.electronic_payer_id == 'CTL-002')
            insurance, created = PatientInsurance.objects.get_or_create(
                patient=patients[1],
                insurance_provider=cathay_provider,
                coverage_type='secondary',
                defaults={
                    'policy_number': 'CTL2024001234',
                    'group_number': 'GRP001',
                    'is_active': True,
                    'effective_date': datetime.now().date() - timedelta(days=200),
                    'expiration_date': datetime.now().date() + timedelta(days=365),
                }
            )
            insurances.append(insurance)
        
        return insurances

    def create_invoices(self, patients, providers, billing_codes, fee_schedule):
        """創建發票"""
        invoices = []
        
        # 發票數據
        invoice_data = [
            {
                'patient': patients[0],
                'invoice_date': datetime.now().date() - timedelta(days=10),
                'due_date': datetime.now().date() + timedelta(days=20),
                'status': 'sent',
                'line_items': [
                    {'code': '99213', 'quantity': 1, 'description': '門診診察'},
                    {'code': '85025', 'quantity': 1, 'description': '血液檢查'},
                    {'code': 'J7050', 'quantity': 1, 'description': '一般藥品'},
                ]
            },
            {
                'patient': patients[1],
                'invoice_date': datetime.now().date() - timedelta(days=5),
                'due_date': datetime.now().date() + timedelta(days=25),
                'status': 'paid',
                'line_items': [
                    {'code': '99214', 'quantity': 1, 'description': '門診診察(複雜)'},
                    {'code': '71020', 'quantity': 1, 'description': '胸部X光'},
                ]
            },
            {
                'patient': patients[2],
                'invoice_date': datetime.now().date() - timedelta(days=45),
                'due_date': datetime.now().date() - timedelta(days=15),
                'status': 'overdue',
                'line_items': [
                    {'code': '99215', 'quantity': 1, 'description': '門診診察(高複雜)'},
                    {'code': '76700', 'quantity': 1, 'description': '腹部超音波'},
                    {'code': '80053', 'quantity': 1, 'description': '代謝功能檢查'},
                ]
            },
        ]
        
        # 從BillingCode獲取費用
        code_fees = {bc.code: bc.default_fee for bc in billing_codes if bc.default_fee}
        
        for idx, data in enumerate(invoice_data):
            # 生成發票號碼
            invoice_number = f"INV-2024-{str(idx + 1).zfill(3)}"
            
            # 創建發票
            invoice = Invoice.objects.create(
                patient=data['patient'],
                invoice_number=invoice_number,
                invoice_date=data['invoice_date'],
                due_date=data['due_date'],
                status=data['status'],
                notes=f"Generated by init command for {data['patient'].first_name}",
            )
            
            # 創建發票明細
            total_amount = Decimal('0.00')
            for item in data['line_items']:
                if item['code'] in code_fees:
                    unit_price = code_fees[item['code']]
                    quantity = item['quantity']
                    line_total = unit_price * quantity
                    
                    InvoiceLineItem.objects.create(
                        invoice=invoice,
                        service_code=item['code'],
                        service_description=item['description'],
                        service_date=data['invoice_date'],
                        quantity=quantity,
                        unit_price=unit_price,
                        total_amount=line_total,
                    )
                    total_amount += line_total
            
            # 更新發票總額
            invoice.subtotal = total_amount
            invoice.tax_amount = total_amount * Decimal('0.05')  # 5% 稅
            invoice.total_amount = invoice.subtotal + invoice.tax_amount
            invoice.balance_due = invoice.total_amount
            invoice.save()
            
            invoices.append(invoice)
        
        return invoices

    def create_payments(self, invoices):
        """創建付款記錄"""
        payments = []
        
        payment_data = [
            {
                'invoice': invoices[0],
                'amount': Decimal('500.00'),
                'payment_method': 'cash',
                'payment_date': datetime.now().date() - timedelta(days=5),
                'status': 'completed',
                'notes': '部分付款 - 現金',
            },
            {
                'invoice': invoices[1],
                'amount': invoices[1].total_amount,
                'payment_method': 'credit_card',
                'payment_date': datetime.now().date() - timedelta(days=3),
                'status': 'completed',
                'notes': '全額付清 - 信用卡',
            },
        ]
        
        for data in payment_data:
            # 添加患者信息
            data['patient'] = data['invoice'].patient
            payment = Payment.objects.create(**data)
            payments.append(payment)
            
            # 更新發票已付金額
            invoice = data['invoice']
            invoice.paid_amount += data['amount']
            invoice.balance_amount = invoice.total_amount - invoice.paid_amount
            if invoice.balance_amount <= 0:
                invoice.status = 'paid'
            invoice.save()
        
        return payments

    def create_insurance_claims(self, invoices, insurance_providers):
        """創建保險申請"""
        claims = []
        
        # 為有保險的發票創建申請
        nhi_provider = next(p for p in insurance_providers if p.electronic_payer_id == 'NHI-001')
        
        claim_data = [
            {
                'invoice': invoices[0],
                'patient': invoices[0].patient,
                'insurance_provider': nhi_provider,
                'claim_number': 'NHI-2024-001',
                'billed_amount': invoices[0].total_amount,
                'allowed_amount': invoices[0].total_amount * Decimal('0.7'),  # 70% 理賠
                'service_date_from': datetime.now().date() - timedelta(days=10),
                'service_date_to': datetime.now().date() - timedelta(days=10),
                'place_of_service': '11',  # Office
                'status': 'submitted',
                'submission_date': datetime.now() - timedelta(days=8),
            },
            {
                'invoice': invoices[1],
                'patient': invoices[1].patient,
                'insurance_provider': nhi_provider,
                'claim_number': 'NHI-2024-002',
                'billed_amount': invoices[1].total_amount,
                'allowed_amount': invoices[1].total_amount * Decimal('0.8'),  # 80% 理賠
                'paid_amount': invoices[1].total_amount * Decimal('0.8'),
                'service_date_from': datetime.now().date() - timedelta(days=7),
                'service_date_to': datetime.now().date() - timedelta(days=7),
                'place_of_service': '11',  # Office
                'status': 'paid',
                'submission_date': datetime.now() - timedelta(days=4),
                'response_date': datetime.now() - timedelta(days=1),
            },
        ]
        
        for data in claim_data:
            claim = InsuranceClaim.objects.create(**data)
            claims.append(claim)
        
        return claims
