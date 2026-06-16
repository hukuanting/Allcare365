"""
分配用戶角色的Django管理命令
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from administration.auth_models import Role, UserRole


class Command(BaseCommand):
    help = '為用戶分配角色'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='用戶名')
        parser.add_argument('role_name', type=str, help='角色名稱')
        parser.add_argument(
            '--remove',
            action='store_true',
            help='移除角色而不是分配'
        )

    def handle(self, *args, **options):
        username = options['username']
        role_name = options['role_name']
        remove = options['remove']
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ 找不到用戶: {username}')
            )
            return
        
        try:
            role = Role.objects.get(display_name=role_name)
        except Role.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ 找不到角色: {role_name}')
            )
            self.stdout.write('可用角色:')
            for r in Role.objects.all():
                self.stdout.write(f'  • {r.display_name}')
            return
        
        if remove:
            # 移除角色
            user_role = UserRole.objects.filter(user=user, role=role, is_active=True).first()
            if user_role:
                user_role.is_active = False
                user_role.save()
                self.stdout.write(
                    self.style.SUCCESS(f'✅ 已從 {username} 移除角色 {role_name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠️ 用戶 {username} 並沒有角色 {role_name}')
                )
        else:
            # 分配角色
            user_role, created = UserRole.objects.get_or_create(
                user=user,
                role=role,
                defaults={
                    'assigned_by': user,  # 自我分配，實際應該由管理員分配
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ 已為 {username} 分配角色 {role_name}')
                )
            else:
                if user_role.is_active:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️ 用戶 {username} 已經有角色 {role_name}')
                    )
                else:
                    user_role.is_active = True
                    user_role.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ 已重新啟用 {username} 的角色 {role_name}')
                    )
        
        # 顯示用戶當前的角色
        current_roles = UserRole.objects.filter(user=user, is_active=True)
        self.stdout.write(f'\n👤 {username} 當前的角色:')
        for user_role in current_roles:
            self.stdout.write(f'  • {user_role.role.display_name}')
