"""
測試權限管理系統的Django管理命令
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from administration.auth_models import Role, UserRole, APIKey, SessionLog
from administration.auth_serializers import RoleSerializer, UserRoleSerializer


class Command(BaseCommand):
    help = '測試權限管理系統功能'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-type',
            type=str,
            default='all',
            help='測試類型: all, roles, users, api_keys'
        )

    def handle(self, *args, **options):
        test_type = options['test_type']
        
        self.stdout.write(
            self.style.SUCCESS('🔐 開始測試權限管理系統')
        )
        
        if test_type in ['all', 'roles']:
            self.test_roles()
            
        if test_type in ['all', 'users']:
            self.test_user_roles()
            
        if test_type in ['all', 'api_keys']:
            self.test_api_keys()
            
        if test_type in ['all', 'sessions']:
            self.test_sessions()
        
        self.stdout.write(
            self.style.SUCCESS('✅ 權限管理系統測試完成')
        )

    def test_roles(self):
        """測試角色管理"""
        self.stdout.write('\n🎭 測試角色管理')
        self.stdout.write('-' * 30)
        
        # 檢查預設角色
        roles = Role.objects.all()
        self.stdout.write(f'📊 總共有 {roles.count()} 個角色:')
        
        for role in roles:
            permissions_count = role.permissions.count()
            status = '✅ 活躍' if role.is_active else '❌ 停用'
            access_info = []
            if role.can_access_patients:
                access_info.append('病患')
            if role.can_access_appointments:
                access_info.append('預約')
            if role.can_access_medical_records:
                access_info.append('病歷')
            if role.can_access_billing:
                access_info.append('計費')
            
            access_str = ', '.join(access_info) if access_info else '無模組存取權'
            self.stdout.write(f'  • {role.display_name}: {permissions_count} 個權限, 存取: {access_str} - {status}')
        
        # 測試角色序列化器
        serializer = RoleSerializer(roles, many=True)
        self.stdout.write(f'✅ 角色序列化器測試通過，返回 {len(serializer.data)} 筆資料')
        
        # 創建測試角色
        test_role, created = Role.objects.get_or_create(
            name='test_role',
            defaults={
                'display_name': '測試角色',
                'description': '這是一個測試角色',
                'can_access_patients': True,
                'can_access_appointments': True,
                'is_active': True
            }
        )
        
        if created:
            self.stdout.write('✅ 測試角色創建成功')
        else:
            self.stdout.write('ℹ️ 測試角色已存在')

    def test_user_roles(self):
        """測試用戶角色"""
        self.stdout.write('\n👥 測試用戶角色管理')
        self.stdout.write('-' * 30)
        
        # 檢查用戶角色
        user_roles = UserRole.objects.all()
        self.stdout.write(f'📊 總共有 {user_roles.count()} 個用戶角色分配')
        
        # 獲取管理員用戶
        try:
            admin_user = User.objects.get(username='hukuanting')
            admin_roles = UserRole.objects.filter(user=admin_user)
            
            self.stdout.write(f'👤 管理員 {admin_user.username} 的角色:')
            for user_role in admin_roles:
                status = '✅ 活躍' if user_role.is_active else '❌ 停用'
                self.stdout.write(f'  • {user_role.role.name} - {status}')
            
            # 如果管理員沒有角色，分配超級管理員角色
            if not admin_roles.exists():
                super_admin_role = Role.objects.filter(name='超級管理員').first()
                if super_admin_role:
                    UserRole.objects.create(
                        user=admin_user,
                        role=super_admin_role,
                        assigned_by=admin_user,
                        is_active=True
                    )
                    self.stdout.write('✅ 為管理員分配超級管理員角色')
                
        except User.DoesNotExist:
            self.stdout.write('❌ 找不到管理員用戶')

    def test_api_keys(self):
        """測試API金鑰"""
        self.stdout.write('\n🗝️ 測試API金鑰管理')
        self.stdout.write('-' * 30)
        
        api_keys = APIKey.objects.all()
        self.stdout.write(f'📊 總共有 {api_keys.count()} 個API金鑰')
        
        for api_key in api_keys:
            status = '✅ 活躍' if api_key.is_active else '❌ 停用'
            self.stdout.write(f'  • {api_key.name}: {api_key.key[:10]}... - {status}')

    def test_sessions(self):
        """測試會話記錄"""
        self.stdout.write('\n📋 測試會話記錄')
        self.stdout.write('-' * 30)
        
        sessions = SessionLog.objects.all()
        self.stdout.write(f'📊 總共有 {sessions.count()} 個會話記錄')
        
        active_sessions = sessions.filter(status='active')
        self.stdout.write(f'🟢 活躍會話: {active_sessions.count()} 個')
        
        suspicious_sessions = sessions.filter(is_suspicious=True)
        self.stdout.write(f'⚠️ 可疑會話: {suspicious_sessions.count()} 個')
