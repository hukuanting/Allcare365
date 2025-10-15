from django.core.management.base import BaseCommand
from patients.models import Patient, PatientAllergy, PatientMedication, PatientVitals, PatientNote
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
import random


class Command(BaseCommand):
    help = '創建示例患者數據'

    def handle(self, *args, **options):
        # 獲取或創建一個用戶作為創建者
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={'is_staff': True, 'is_superuser': True}
        )
        
        # 示例患者數據
        patients_data = [
            {
                'first_name': '小明',
                'last_name': '王',
                'date_of_birth': date(1985, 3, 15),
                'gender': 'M',
                'phone_mobile': '0912-345-678',
                'email': 'wang.xiaoming@email.com',
                'address_line1': '台北市信義區信義路五段7號',
                'city': '台北市',
                'state': '台北市',
                'postal_code': '110',
                'occupation': '軟體工程師',
                'marital_status': '已婚',
                'blood_type': 'A+',
                'emergency_contact_name': '王美麗',
                'emergency_contact_phone': '0923-456-789',
                'emergency_contact_relationship': '配偶',
            },
            {
                'first_name': '美麗',
                'last_name': '李',
                'date_of_birth': date(1990, 8, 22),
                'gender': 'F',
                'phone_mobile': '0923-456-789',
                'email': 'li.meili@email.com',
                'address_line1': '新北市板橋區文化路一段188號',
                'city': '新北市',
                'state': '新北市',
                'postal_code': '220',
                'occupation': '護理師',
                'marital_status': '單身',
                'blood_type': 'B+',
                'emergency_contact_name': '李大華',
                'emergency_contact_phone': '0934-567-890',
                'emergency_contact_relationship': '父親',
            },
            {
                'first_name': '志強',
                'last_name': '陳',
                'date_of_birth': date(1978, 12, 5),
                'gender': 'M',
                'phone_mobile': '0934-567-890',
                'email': 'chen.zhiqiang@email.com',
                'address_line1': '高雄市左營區博愛二路777號',
                'city': '高雄市',
                'state': '高雄市',
                'postal_code': '813',
                'occupation': '醫師',
                'marital_status': '已婚',
                'blood_type': 'O+',
                'emergency_contact_name': '陳淑芬',
                'emergency_contact_phone': '0945-678-901',
                'emergency_contact_relationship': '配偶',
            },
            {
                'first_name': '雅婷',
                'last_name': '林',
                'date_of_birth': date(1995, 5, 18),
                'gender': 'F',
                'phone_mobile': '0956-789-012',
                'email': 'lin.yating@email.com',
                'address_line1': '台中市西屯區台灣大道三段99號',
                'city': '台中市',
                'state': '台中市',
                'postal_code': '407',
                'occupation': '教師',
                'marital_status': '單身',
                'blood_type': 'AB+',
                'emergency_contact_name': '林志明',
                'emergency_contact_phone': '0967-890-123',
                'emergency_contact_relationship': '兄長',
            },
            {
                'first_name': '建華',
                'last_name': '張',
                'date_of_birth': date(1972, 9, 30),
                'gender': 'M',
                'phone_mobile': '0978-901-234',
                'email': 'zhang.jianhua@email.com',
                'address_line1': '桃園市中壢區中正路123號',
                'city': '桃園市',
                'state': '桃園市',
                'postal_code': '320',
                'occupation': '企業主管',
                'marital_status': '已婚',
                'blood_type': 'A-',
                'emergency_contact_name': '張淑惠',
                'emergency_contact_phone': '0989-012-345',
                'emergency_contact_relationship': '配偶',
            }
        ]
        
        created_patients = []
        
        for patient_data in patients_data:
            patient, created = Patient.objects.get_or_create(
                first_name=patient_data['first_name'],
                last_name=patient_data['last_name'],
                date_of_birth=patient_data['date_of_birth'],
                defaults={**patient_data, 'created_by': admin_user}
            )
            
            if created:
                created_patients.append(patient)
                self.stdout.write(
                    self.style.SUCCESS(f'創建患者: {patient.full_name}')
                )
                
                # 為每個患者創建一些示例數據
                self._create_sample_data_for_patient(patient, admin_user)
            else:
                self.stdout.write(
                    self.style.WARNING(f'患者已存在: {patient.full_name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'成功創建 {len(created_patients)} 個新患者')
        )

    def _create_sample_data_for_patient(self, patient, admin_user):
        """為患者創建示例數據"""
        
        # 創建過敏資訊
        allergies = [
            {'allergen': '花生', 'reaction': '皮疹', 'severity': '輕微'},
            {'allergen': '海鮮', 'reaction': '腫脹', 'severity': '中等'},
            {'allergen': '塵蟎', 'reaction': '打噴嚏', 'severity': '輕微'},
        ]
        
        # 隨機選擇1-2個過敏
        selected_allergies = random.sample(allergies, random.randint(0, 2))
        for allergy_data in selected_allergies:
            PatientAllergy.objects.create(
                patient=patient,
                **allergy_data,
                created_by=admin_user
            )
        
        # 創建用藥資訊
        medications = [
            {'medication_name': '阿斯匹靈', 'dosage': '100mg', 'frequency': '每日一次'},
            {'medication_name': '維他命D', 'dosage': '1000IU', 'frequency': '每日一次'},
            {'medication_name': '血壓藥', 'dosage': '5mg', 'frequency': '每日兩次'},
        ]
        
        # 隨機選擇1-2個藥物
        selected_medications = random.sample(medications, random.randint(0, 2))
        for med_data in selected_medications:
            PatientMedication.objects.create(
                patient=patient,
                **med_data,
                start_date=timezone.now().date() - timedelta(days=random.randint(30, 365)),
                prescribing_doctor='Dr. Smith',
                created_by=admin_user
            )
        
        # 創建生命體徵記錄
        vitals_data = {
            'height': round(random.uniform(150, 190), 1),
            'weight': round(random.uniform(45, 95), 1),
            'blood_pressure_systolic': random.randint(110, 140),
            'blood_pressure_diastolic': random.randint(70, 90),
            'heart_rate': random.randint(60, 100),
            'temperature': round(random.uniform(36.0, 37.5), 1),
            'respiratory_rate': random.randint(12, 20),
            'oxygen_saturation': random.randint(95, 100),
            'measurement_date': timezone.now() - timedelta(days=random.randint(1, 30)),
        }
        
        PatientVitals.objects.create(
            patient=patient,
            **vitals_data,
            created_by=admin_user
        )
        
        # 創建患者備註
        notes = [
            {'title': '初診記錄', 'content': '患者首次就診，主訴頭痛。', 'note_type': 'general'},
            {'title': '追蹤記錄', 'content': '症狀有所改善，建議繼續觀察。', 'note_type': 'follow_up'},
            {'title': '檢查結果', 'content': '血液檢查結果正常。', 'note_type': 'test_result'},
        ]
        
        # 隨機選擇1-2個備註
        selected_notes = random.sample(notes, random.randint(1, 2))
        for note_data in selected_notes:
            PatientNote.objects.create(
                patient=patient,
                **note_data,
                created_by=admin_user
            )
