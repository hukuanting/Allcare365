"""
初始化預設角色和權限的管理命令
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from administration.auth_models import Role, UserRole, DEFAULT_ROLES


class Command(BaseCommand):
    help = '初始化系統預設角色和權限'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='重置所有角色（警告：會刪除現有角色）'
        )
        
        parser.add_argument(
            '--create-admin',
            action='store_true',
            help='創建預設管理員帳號'
        )
    
    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write('重置所有角色...')
            Role.objects.all().delete()
        
        self.stdout.write('創建預設角色...')
        
        created_count = 0
        updated_count = 0
        
        for role_name, role_config in DEFAULT_ROLES.items():
            role, created = Role.objects.get_or_create(
                name=role_name,
                defaults={
                    'display_name': role_config['display_name'],
                    'description': role_config['description'],
                    'data_access_level': role_config['data_access_level'],
                    **role_config['modules']
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ 創建角色: {role.display_name}')
                )
            else:
                # 更新現有角色
                role.display_name = role_config['display_name']
                role.description = role_config['description']
                role.data_access_level = role_config['data_access_level']
                
                for field, value in role_config['modules'].items():
                    setattr(role, field, value)
                
                role.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'↻ 更新角色: {role.display_name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'完成！創建了 {created_count} 個新角色，更新了 {updated_count} 個角色。'
            )
        )
        
        if options['create_admin']:
            self.create_admin_user()
    
    def create_admin_user(self):
        """創建預設管理員用戶"""
        admin_username = 'admin'
        admin_email = 'admin@medicalcare.local'
        admin_password = 'admin123456'
        
        if User.objects.filter(username=admin_username).exists():
            self.stdout.write(
                self.style.WARNING(f'管理員用戶 {admin_username} 已存在，跳過創建。')
            )
            return
        
        # 創建管理員用戶
        admin_user = User.objects.create_user(
            username=admin_username,
            email=admin_email,
            password=admin_password,
            is_staff=True,
            is_superuser=True,
            first_name='系統',
            last_name='管理員'
        )
        
        # 指派超級管理員角色
        try:
            superadmin_role = Role.objects.get(name='superadmin')
            UserRole.objects.create(
                user=admin_user,
                role=superadmin_role,
                assigned_by=admin_user  # 自己指派
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'✓ 創建管理員用戶: {admin_username}')
            )
            self.stdout.write(
                self.style.WARNING(
                    f'預設密碼: {admin_password} (請立即更改)'
                )
            )
        except Role.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('超級管理員角色不存在，請先運行角色初始化')
            )
