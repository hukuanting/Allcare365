from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '設置初始用戶群組和權限'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-admin',
            action='store_true',
            help='創建預設管理員帳戶',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('開始設置用戶群組和權限...'))
        
        # 創建用戶群組
        self.create_user_groups()
        
        # 設置群組權限
        self.set_group_permissions()
        
        # 創建管理員帳戶（如果指定）
        if options['create_admin']:
            self.create_admin_user()
        
        self.stdout.write(self.style.SUCCESS('用戶群組和權限設置完成！'))

    def create_user_groups(self):
        """創建用戶群組"""
        groups = {
            'admin': '系統管理員',
            'doctor': '醫師',
            'nurse': '護理師',
            'staff': '行政人員',
            'patient': '病患'
        }
        
        for group_name, description in groups.items():
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(f'創建群組: {group_name} ({description})')
                logger.info(f'Created group: {group_name}')
            else:
                self.stdout.write(f'群組已存在: {group_name}')

    def set_group_permissions(self):
        """設置群組權限"""
        # 獲取所有群組
        admin_group = Group.objects.get(name='admin')
        doctor_group = Group.objects.get(name='doctor')
        nurse_group = Group.objects.get(name='nurse')
        staff_group = Group.objects.get(name='staff')
        patient_group = Group.objects.get(name='patient')
        
        # 管理員群組 - 所有權限
        admin_permissions = Permission.objects.all()
        admin_group.permissions.set(admin_permissions)
        self.stdout.write('設置管理員權限: 所有權限')
        
        # 醫師群組權限
        doctor_permissions = self.get_permissions_by_codename([
            'view_patient', 'add_patient', 'change_patient',
            'view_appointment', 'add_appointment', 'change_appointment',
            'view_medicalrecord', 'add_medicalrecord', 'change_medicalrecord',
            'view_encounter', 'add_encounter', 'change_encounter',
            'view_prescription', 'add_prescription', 'change_prescription',
            'view_labtest', 'add_labtest', 'change_labtest',
            'view_immunization', 'add_immunization', 'change_immunization',
        ])
        doctor_group.permissions.set(doctor_permissions)
        self.stdout.write('設置醫師權限')
        
        # 護理師群組權限
        nurse_permissions = self.get_permissions_by_codename([
            'view_patient', 'change_patient',
            'view_appointment', 'add_appointment', 'change_appointment',
            'view_medicalrecord', 'add_medicalrecord', 'change_medicalrecord',
            'view_encounter', 'add_encounter', 'change_encounter',
            'view_prescription',
            'view_labtest', 'add_labtest',
            'view_immunization', 'add_immunization', 'change_immunization',
        ])
        nurse_group.permissions.set(nurse_permissions)
        self.stdout.write('設置護理師權限')
        
        # 行政人員群組權限
        staff_permissions = self.get_permissions_by_codename([
            'view_patient', 'add_patient', 'change_patient',
            'view_appointment', 'add_appointment', 'change_appointment',
            'view_billing', 'add_billing', 'change_billing',
            'view_insurance', 'add_insurance', 'change_insurance',
        ])
        staff_group.permissions.set(staff_permissions)
        self.stdout.write('設置行政人員權限')
        
        # 病患群組權限（僅查看自己的資料）
        patient_permissions = self.get_permissions_by_codename([
            'view_patient',  # 僅限自己的資料
            'view_appointment',  # 僅限自己的預約
            'view_medicalrecord',  # 僅限自己的病歷
        ])
        patient_group.permissions.set(patient_permissions)
        self.stdout.write('設置病患權限')

    def get_permissions_by_codename(self, codenames):
        """根據權限代碼名稱獲取權限對象"""
        permissions = []
        for codename in codenames:
            try:
                # 使用filter而不是get，因為可能有重複的權限
                permission_list = Permission.objects.filter(codename=codename)
                if permission_list.exists():
                    permissions.extend(permission_list)
                else:
                    self.stdout.write(
                        self.style.WARNING(f'權限不存在: {codename}')
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'獲取權限時出錯 {codename}: {str(e)}')
                )
        return permissions

    def create_admin_user(self):
        """創建預設管理員帳戶"""
        username = 'admin'
        email = 'admin@medicalcare.local'
        password = 'admin123'
        
        if not User.objects.filter(username=username).exists():
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                first_name='系統',
                last_name='管理員'
            )
            
            # 添加到管理員群組
            admin_group = Group.objects.get(name='admin')
            user.groups.add(admin_group)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'創建管理員帳戶: {username} (密碼: {password})'
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    '請在生產環境中立即更改預設密碼！'
                )
            )
            
            logger.info(f'Created admin user: {username}')
        else:
            self.stdout.write(f'管理員帳戶已存在: {username}')

    def create_demo_users(self):
        """創建示範用戶（可選）"""
        demo_users = [
            {
                'username': 'doctor1',
                'password': 'doctor123',
                'email': 'doctor1@medicalcare.local',
                'first_name': '張',
                'last_name': '醫師',
                'group': 'doctor'
            },
            {
                'username': 'nurse1',
                'password': 'nurse123',
                'email': 'nurse1@medicalcare.local',
                'first_name': '李',
                'last_name': '護理師',
                'group': 'nurse'
            },
            {
                'username': 'staff1',
                'password': 'staff123',
                'email': 'staff1@medicalcare.local',
                'first_name': '王',
                'last_name': '行政',
                'group': 'staff'
            },
            {
                'username': 'patient1',
                'password': 'patient123',
                'email': 'patient1@medicalcare.local',
                'first_name': '陳',
                'last_name': '病患',
                'group': 'patient'
            }
        ]
        
        for user_data in demo_users:
            username = user_data['username']
            
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=user_data['username'],
                    password=user_data['password'],
                    email=user_data['email'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name']
                )
                
                # 添加到對應群組
                group = Group.objects.get(name=user_data['group'])
                user.groups.add(group)
                
                self.stdout.write(f'創建示範用戶: {username}')
                logger.info(f'Created demo user: {username}')
            else:
                self.stdout.write(f'示範用戶已存在: {username}')
