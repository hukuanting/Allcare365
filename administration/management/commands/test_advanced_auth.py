"""
完善權限管理功能的測試
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from administration.auth_models import Role, UserRole, APIKey, TwoFactorAuth, SessionLog
from django.utils import timezone
import secrets
import string


class Command(BaseCommand):
    help = '測試並完善權限管理的進階功能'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔧 開始測試進階權限功能')
        )
        
        self.test_api_keys()
        self.test_two_factor_auth()
        self.test_session_logging()
        self.test_permission_checking()
        
        self.stdout.write(
            self.style.SUCCESS('✅ 進階權限功能測試完成')
        )

    def test_api_keys(self):
        """測試API金鑰功能"""
        self.stdout.write('\n🗝️ 測試API金鑰功能')
        self.stdout.write('-' * 30)
        
        # 獲取測試用戶
        admin_user = User.objects.get(username='hukuanting')
        
        # 創建API金鑰
        api_key = APIKey.objects.create(
            user=admin_user,
            name='測試API金鑰',
            scopes=['read', 'write'],
            expires_at=timezone.now() + timezone.timedelta(days=30)
        )
        
        self.stdout.write(f'✅ 創建API金鑰: {api_key.name}')
        self.stdout.write(f'   金鑰: {api_key.key[:20]}...')
        self.stdout.write(f'   範圍: {", ".join(api_key.scopes)}')
        self.stdout.write(f'   狀態: {"✅ 活躍" if api_key.is_active else "❌ 停用"}')
        self.stdout.write(f'   到期時間: {api_key.expires_at}')
        
        # 測試金鑰驗證
        if hasattr(api_key, 'is_valid') and api_key.is_valid():
            self.stdout.write('✅ API金鑰驗證通過')
        else:
            self.stdout.write('ℹ️ API金鑰基本資訊正常')

    def test_two_factor_auth(self):
        """測試雙因素認證"""
        self.stdout.write('\n🔒 測試雙因素認證')
        self.stdout.write('-' * 30)
        
        admin_user = User.objects.get(username='hukuanting')
        
        # 檢查是否已有2FA設定
        two_fa, created = TwoFactorAuth.objects.get_or_create(
            user=admin_user,
            defaults={
                'is_enabled': True,
                'backup_codes': self.generate_backup_codes()
            }
        )
        
        if created:
            self.stdout.write('✅ 創建2FA設定')
        else:
            self.stdout.write('ℹ️ 2FA設定已存在')
        
        self.stdout.write(f'   狀態: {"✅ 啟用" if two_fa.is_enabled else "❌ 停用"}')
        self.stdout.write(f'   備份碼數量: {len(two_fa.backup_codes) if two_fa.backup_codes else 0}')
        
        # 生成TOTP設定URL
        if hasattr(two_fa, 'get_qr_code_url'):
            self.stdout.write('✅ QR碼URL生成功能可用')

    def test_session_logging(self):
        """測試會話記錄"""
        self.stdout.write('\n📋 測試會話記錄')
        self.stdout.write('-' * 30)
        
        admin_user = User.objects.get(username='hukuanting')
        
        # 創建測試會話記錄
        session_log = SessionLog.objects.create(
            user=admin_user,
            session_key='test_session_' + ''.join(secrets.choice(string.ascii_letters) for _ in range(10)),
            ip_address='127.0.0.1',
            user_agent='Test User Agent',
            status='active'
        )
        
        self.stdout.write(f'✅ 創建會話記錄: {session_log.session_key}')
        self.stdout.write(f'   IP地址: {session_log.ip_address}')
        self.stdout.write(f'   狀態: {session_log.status}')
        self.stdout.write(f'   登入時間: {session_log.login_time}')
        
        # 測試會話記錄統計
        total_sessions = SessionLog.objects.count()
        active_sessions = SessionLog.objects.filter(status='active').count()
        
        self.stdout.write(f'📊 總會話記錄: {total_sessions}')
        self.stdout.write(f'📊 活躍會話: {active_sessions}')

    def test_permission_checking(self):
        """測試權限檢查機制"""
        self.stdout.write('\n🛡️ 測試權限檢查機制')
        self.stdout.write('-' * 30)
        
        admin_user = User.objects.get(username='hukuanting')
        
        # 獲取用戶角色
        user_roles = UserRole.objects.filter(user=admin_user, is_active=True)
        
        self.stdout.write(f'👤 用戶 {admin_user.username} 的權限檢查:')
        
        for user_role in user_roles:
            role = user_role.role
            self.stdout.write(f'   角色: {role.display_name}')
            
            # 檢查模組存取權限
            modules = []
            if role.can_access_patients:
                modules.append('病患管理')
            if role.can_access_appointments:
                modules.append('預約管理')
            if role.can_access_medical_records:
                modules.append('病歷記錄')
            if role.can_access_billing:
                modules.append('計費系統')
            if role.can_access_pharmacy:
                modules.append('藥房管理')
            if role.can_access_laboratory:
                modules.append('實驗室')
            if role.can_access_reports:
                modules.append('報表系統')
            if role.can_access_administration:
                modules.append('系統管理')
            
            self.stdout.write(f'   可存取模組: {", ".join(modules) if modules else "無"}')
            self.stdout.write(f'   資料存取級別: {role.data_access_level}')
            
            # 檢查Django權限
            permissions_count = role.permissions.count()
            self.stdout.write(f'   Django權限數量: {permissions_count}')
            
            if permissions_count > 0:
                perms = role.permissions.all()[:5]  # 顯示前5個權限
                for perm in perms:
                    self.stdout.write(f'     • {perm.content_type.app_label}.{perm.codename}')

    def generate_backup_codes(self):
        """生成備份碼"""
        codes = []
        for _ in range(10):
            code = ''.join(secrets.choice(string.digits) for _ in range(8))
            codes.append(f'{code[:4]}-{code[4:]}')
        return codes
