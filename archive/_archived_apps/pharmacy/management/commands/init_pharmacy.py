"""
Pharmacy 模組初始化命令

建立藥房管理系統的基礎資料，包括：
- 藥物分類
- 藥物主檔
- 處方籤資料
- 庫存記錄
- 測試患者和醫師資料

執行方式: python manage.py init_pharmacy
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import random

from pharmacy.models import (
    DrugCategory, Drug, Prescription, PrescriptionRefill,
    DrugInventory, InventoryTransaction
)
from patients.models import Patient
from administration.models import Provider, Facility


class Command(BaseCommand):
    help = '初始化 Pharmacy 模組的基礎資料'

    def handle(self, *args, **options):
        self.stdout.write('開始初始化藥房數據...')
        
        try:
            # 創建藥物分類
            categories = self.create_drug_categories()
            self.stdout.write(f'✓ 已創建 {len(categories)} 個藥物分類')
            
            # 創建藥物主檔
            drugs = self.create_drugs(categories)
            self.stdout.write(f'✓ 已創建 {len(drugs)} 個藥物')
            
            # 確保有患者和醫師資料
            patients = self.ensure_patients()
            providers = self.ensure_providers()
            facility = self.ensure_facility()
            self.stdout.write(f'✓ 確認有 {len(patients)} 個患者、{len(providers)} 個醫師和醫療機構')
            
            # 創建處方籤
            prescriptions = self.create_prescriptions(drugs, patients, providers)
            self.stdout.write(f'✓ 已創建 {len(prescriptions)} 張處方籤')
            
            # 創建庫存記錄
            inventories = self.create_inventories(drugs, facility)
            self.stdout.write(f'✓ 已創建 {len(inventories)} 個庫存記錄')
            
            # 創建庫存異動
            transactions = self.create_inventory_transactions(inventories)
            self.stdout.write(f'✓ 已創建 {len(transactions)} 筆庫存異動')
            
            self.stdout.write(self.style.SUCCESS('✅ 藥房系統初始化完成！'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ 初始化失敗: {e}'))
            raise

    def create_drug_categories(self):
        """創建藥物分類"""
        categories_data = [
            {'name': '抗生素類', 'code': 'ANTI', 'description': '用於治療細菌感染的藥物'},
            {'name': '心血管藥物', 'code': 'CARDIO', 'description': '治療心臟和血管疾病的藥物'},
            {'name': '消化系統藥物', 'code': 'GI', 'description': '治療消化系統疾病的藥物'},
            {'name': '呼吸系統藥物', 'code': 'RESP', 'description': '治療呼吸系統疾病的藥物'},
            {'name': '內分泌藥物', 'code': 'ENDO', 'description': '治療內分泌疾病的藥物'},
            {'name': '神經系統藥物', 'code': 'NEURO', 'description': '治療神經系統疾病的藥物'},
            {'name': '止痛藥物', 'code': 'PAIN', 'description': '用於緩解疼痛的藥物'},
            {'name': '維生素和礦物質', 'code': 'VIT', 'description': '維生素和礦物質補充劑'},
        ]
        
        categories = []
        for data in categories_data:
            category, created = DrugCategory.objects.get_or_create(
                code=data['code'],
                defaults=data
            )
            categories.append(category)
        
        return categories

    def create_drugs(self, categories):
        """創建藥物主檔"""
        drugs_data = [
            {
                'name': 'Amoxicillin 500mg',
                'generic_name': 'Amoxicillin',
                'ndc_number': '0093-2264-01',
                'category': categories[0],  # 抗生素類
                'dosage_form': 'capsule',
                'strength': '500mg',
                'unit': 'mg',
                'manufacturer': 'Teva Pharmaceuticals',
                'therapeutic_class': 'Penicillin Antibiotic',
            },
            {
                'name': 'Lisinopril 10mg',
                'generic_name': 'Lisinopril',
                'ndc_number': '0781-1506-01',
                'category': categories[1],  # 心血管藥物
                'dosage_form': 'tablet',
                'strength': '10mg',
                'unit': 'mg',
                'manufacturer': 'Sandoz',
                'therapeutic_class': 'ACE Inhibitor',
            },
            {
                'name': 'Omeprazole 20mg',
                'generic_name': 'Omeprazole',
                'ndc_number': '0615-8006-39',
                'category': categories[2],  # 消化系統藥物
                'dosage_form': 'capsule',
                'strength': '20mg',
                'unit': 'mg',
                'manufacturer': 'Dr. Reddy\'s',
                'therapeutic_class': 'Proton Pump Inhibitor',
            },
            {
                'name': 'Albuterol Inhaler',
                'generic_name': 'Albuterol Sulfate',
                'ndc_number': '0173-0682-20',
                'category': categories[3],  # 呼吸系統藥物
                'dosage_form': 'inhaler',
                'strength': '90mcg',
                'unit': 'mcg',
                'manufacturer': 'Proventil HFA',
                'therapeutic_class': 'Beta-2 Agonist',
            },
            {
                'name': 'Metformin 500mg',
                'generic_name': 'Metformin HCl',
                'ndc_number': '0093-1074-01',
                'category': categories[4],  # 內分泌藥物
                'dosage_form': 'tablet',
                'strength': '500mg',
                'unit': 'mg',
                'manufacturer': 'Teva Pharmaceuticals',
                'therapeutic_class': 'Biguanide',
            },
            {
                'name': 'Ibuprofen 200mg',
                'generic_name': 'Ibuprofen',
                'ndc_number': '0113-0467-78',
                'category': categories[6],  # 止痛藥物
                'dosage_form': 'tablet',
                'strength': '200mg',
                'unit': 'mg',
                'manufacturer': 'Major Pharmaceuticals',
                'therapeutic_class': 'NSAID',
            },
            {
                'name': 'Vitamin D3 1000 IU',
                'generic_name': 'Cholecalciferol',
                'ndc_number': '0904-6809-60',
                'category': categories[7],  # 維生素和礦物質
                'dosage_form': 'tablet',
                'strength': '1000 IU',
                'unit': 'IU',
                'manufacturer': 'Major Pharmaceuticals',
                'therapeutic_class': 'Vitamin D Supplement',
            },
            {
                'name': 'Atorvastatin 20mg',
                'generic_name': 'Atorvastatin Calcium',
                'ndc_number': '0093-7270-01',
                'category': categories[1],  # 心血管藥物
                'dosage_form': 'tablet',
                'strength': '20mg',
                'unit': 'mg',
                'manufacturer': 'Teva Pharmaceuticals',
                'therapeutic_class': 'HMG-CoA Reductase Inhibitor',
            },
            {
                'name': 'Lorazepam 1mg',
                'generic_name': 'Lorazepam',
                'ndc_number': '0904-5881-61',
                'category': categories[5],  # 神經系統藥物
                'dosage_form': 'tablet',
                'strength': '1mg',
                'unit': 'mg',
                'manufacturer': 'Major Pharmaceuticals',
                'therapeutic_class': 'Benzodiazepine',
                'controlled_substance': 'CIV',
            },
            {
                'name': 'Azithromycin 250mg',
                'generic_name': 'Azithromycin',
                'ndc_number': '0093-7146-56',
                'category': categories[0],  # 抗生素類
                'dosage_form': 'tablet',
                'strength': '250mg',
                'unit': 'mg',
                'manufacturer': 'Teva Pharmaceuticals',
                'therapeutic_class': 'Macrolide Antibiotic',
            },
        ]
        
        drugs = []
        for data in drugs_data:
            drug, created = Drug.objects.get_or_create(
                ndc_number=data['ndc_number'],
                defaults=data
            )
            drugs.append(drug)
        
        return drugs

    def ensure_patients(self):
        """確保有患者資料"""
        if Patient.objects.exists():
            return list(Patient.objects.all()[:5])
        
        # 創建測試患者
        patients_data = [
            {
                'first_name': '小明',
                'last_name': '王',
                'date_of_birth': timezone.now().date() - timedelta(days=365*30),
                'phone_home': '02-1234-5678',
            },
            {
                'first_name': '小華',
                'last_name': '李',
                'date_of_birth': timezone.now().date() - timedelta(days=365*45),
                'phone_home': '02-2345-6789',
            },
            {
                'first_name': '小美',
                'last_name': '陳',
                'date_of_birth': timezone.now().date() - timedelta(days=365*35),
                'phone_home': '02-3456-7890',
            },
        ]
        
        patients = []
        for data in patients_data:
            patient = Patient.objects.create(**data)
            patients.append(patient)
        
        return patients

    def ensure_providers(self):
        """確保有醫師資料"""
        if Provider.objects.exists():
            return list(Provider.objects.all()[:3])
        
        # 創建測試醫師
        providers_data = [
            {
                'first_name': '志明',
                'last_name': '張',
                'specialty': '內科',
                'phone': '02-9876-5432',
                'email': 'dr.zhang@example.com',
            },
            {
                'first_name': '美麗',
                'last_name': '林',
                'specialty': '家醫科',
                'phone': '02-8765-4321',
                'email': 'dr.lin@example.com',
            },
            {
                'first_name': '建國',
                'last_name': '黃',
                'specialty': '心臟科',
                'phone': '02-7654-3210',
                'email': 'dr.huang@example.com',
            },
        ]
        
        providers = []
        for data in providers_data:
            provider = Provider.objects.create(**data)
            providers.append(provider)
        
        return providers

    def ensure_facility(self):
        """確保有醫療機構資料"""
        if Facility.objects.exists():
            return Facility.objects.first()
        
        # 創建測試醫療機構
        facility_data = {
            'name': '主要醫療機構',
            'address': '台北市信義區信義路五段7號',
            'phone': '02-2345-6789',
            'facility_type': 'hospital',
        }
        
        facility = Facility.objects.create(**facility_data)
        return facility

    def create_prescriptions(self, drugs, patients, providers):
        """創建處方籤"""
        prescriptions_data = [
            {
                'patient': patients[0],
                'provider': providers[0],
                'drug': drugs[0],  # Amoxicillin
                'dosage_instructions': '500mg twice daily',
                'quantity': 20,
                'refills': 0,
                'unit': 'capsules',
                'frequency': 'BID',
                'duration': '10 days',
                'status': 'completed',
                'prescribed_date': timezone.now().date() - timedelta(days=5),
                'notes': 'Take with food. Complete the full course.',
            },
            {
                'patient': patients[1],
                'provider': providers[1],
                'drug': drugs[1],  # Lisinopril
                'dosage_instructions': '10mg once daily',
                'quantity': 30,
                'refills': 5,
                'unit': 'tablets',
                'frequency': 'QD',
                'duration': '30 days',
                'status': 'active',
                'prescribed_date': timezone.now().date() - timedelta(days=15),
                'notes': 'Take in the morning with water.',
            },
            {
                'patient': patients[2],
                'provider': providers[0],
                'drug': drugs[2],  # Omeprazole
                'dosage_instructions': '20mg once daily',
                'quantity': 30,
                'refills': 3,
                'unit': 'capsules',
                'frequency': 'QD',
                'duration': '30 days',
                'status': 'active',
                'prescribed_date': timezone.now().date() - timedelta(days=2),
                'notes': 'Take 30 minutes before breakfast.',
            },
            {
                'patient': patients[0],
                'provider': providers[2],
                'drug': drugs[4],  # Metformin
                'dosage_instructions': '500mg twice daily',
                'quantity': 60,
                'refills': 5,
                'unit': 'tablets',
                'frequency': 'BID',
                'duration': '30 days',
                'status': 'active',
                'prescribed_date': timezone.now().date() - timedelta(days=20),
                'notes': 'Take with meals to reduce stomach upset.',
            },
            {
                'patient': patients[1],
                'provider': providers[1],
                'drug': drugs[5],  # Ibuprofen
                'dosage_instructions': '200mg as needed',
                'quantity': 50,
                'refills': 2,
                'unit': 'tablets',
                'frequency': 'PRN',
                'duration': '30 days',
                'status': 'active',
                'prescribed_date': timezone.now().date() - timedelta(days=1),
                'notes': 'Take with food. Do not exceed 6 tablets per day.',
            },
        ]
        
        prescriptions = []
        for data in prescriptions_data:
            prescription = Prescription.objects.create(**data)
            prescriptions.append(prescription)
        
        return prescriptions

    def create_inventories(self, drugs, facility):
        """創建庫存記錄"""
        inventories = []
        
        for drug in drugs:
            # 隨機生成庫存數量（有些故意設為低庫存以測試警示功能）
            if random.random() < 0.3:  # 30% 機率設為低庫存
                quantity_on_hand = random.randint(1, 10)
            else:
                quantity_on_hand = random.randint(50, 500)
            
            inventory_data = {
                'drug': drug,
                'facility': facility,
                'warehouse': 'Main',
                'quantity_on_hand': quantity_on_hand,
                'quantity_allocated': 0,
                'unit_cost': Decimal(str(random.uniform(0.5, 50.0))),
                'lot_number': f'LOT{random.randint(1000, 9999)}',
                'expiration_date': timezone.now().date() + timedelta(days=random.randint(180, 730)),
            }
            
            inventory = DrugInventory.objects.create(**inventory_data)
            inventories.append(inventory)
        
        return inventories

    def create_inventory_transactions(self, inventories):
        """創建庫存異動記錄"""
        transactions = []
        
        for inventory in inventories:
            # 為每個庫存項目創建幾筆異動記錄
            transaction_types = ['purchase', 'dispensing', 'adjustment', 'return']
            current_qty = inventory.quantity_on_hand
            
            for i in range(random.randint(2, 5)):
                transaction_type = random.choice(transaction_types)
                
                if transaction_type == 'dispensing':
                    quantity_change = -random.randint(1, 10)
                elif transaction_type == 'return':
                    quantity_change = random.randint(1, 5)
                elif transaction_type == 'adjustment':
                    quantity_change = random.randint(-5, 5)
                else:  # purchase
                    quantity_change = random.randint(10, 100)
                
                quantity_before = current_qty
                quantity_after = current_qty + quantity_change
                current_qty = quantity_after
                
                transaction_data = {
                    'drug_inventory': inventory,
                    'transaction_type': transaction_type,
                    'quantity_before': quantity_before,
                    'quantity_change': quantity_change,
                    'quantity_after': quantity_after,
                    'unit_cost': inventory.unit_cost,
                    'reference_number': f'{transaction_type.upper()}-{random.randint(1000, 9999)}',
                    'reason': f'{transaction_type.title()} transaction for {inventory.drug.name}',
                }
                
                transaction = InventoryTransaction.objects.create(**transaction_data)
                transactions.append(transaction)
        
        return transactions
