"""
權限管理系統測試
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch

from .auth_models import Role, UserRole, SessionLog, LoginAttempt, APIKey, TwoFactorAuth


class RoleModelTest(TestCase):
    """角色模型測試"""
    
    def setUp(self):
        self.role = Role.objects.create(
            name='doctor',
            display_name='醫生',
            description='醫生角色，可以查看和編輯病患資料',
            can_access_patients=True,
            can_access_medical_records=True,
            data_access_level='facility'
        )
    
    def test_role_creation(self):
        """測試角色創建"""
        self.assertEqual(self.role.name, 'doctor')
        self.assertEqual(self.role.display_name, '醫生')
        self.assertTrue(self.role.can_access_patients)
        self.assertEqual(self.role.data_access_level, 'facility')
    
    def test_role_str_method(self):
        """測試角色字符串表示"""
        self.assertEqual(str(self.role), '醫生')


class UserRoleModelTest(TestCase):
    """用戶角色模型測試"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testdoctor',
            email='doctor@test.com',
            password='testpass123'
        )
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True
        )
        self.role = Role.objects.create(
            name='doctor',
            display_name='醫生'
        )
        self.user_role = UserRole.objects.create(
            user=self.user,
            role=self.role,
            assigned_by=self.admin
        )
    
    def test_user_role_creation(self):
        """測試用戶角色創建"""
        self.assertEqual(self.user_role.user, self.user)
        self.assertEqual(self.user_role.role, self.role)
        self.assertEqual(self.user_role.assigned_by, self.admin)
        self.assertTrue(self.user_role.is_active)
    
    def test_user_role_is_valid(self):
        """測試角色有效性檢查"""
        # 當前應該有效
        self.assertTrue(self.user_role.is_valid())
        
        # 設置過期時間為過去
        self.user_role.valid_until = timezone.now() - timezone.timedelta(days=1)
        self.user_role.save()
        self.assertFalse(self.user_role.is_valid())
        
        # 停用角色
        self.user_role.valid_until = None
        self.user_role.is_active = False
        self.user_role.save()
        self.assertFalse(self.user_role.is_valid())


class SessionLogModelTest(TestCase):
    """會話日誌模型測試"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.session = SessionLog.objects.create(
            user=self.user,
            session_key='test_session_key',
            ip_address='127.0.0.1',
            user_agent='Test Browser'
        )
    
    def test_session_creation(self):
        """測試會話創建"""
        self.assertEqual(self.session.user, self.user)
        self.assertEqual(self.session.ip_address, '127.0.0.1')
        self.assertEqual(self.session.status, 'active')
    
    def test_session_str_method(self):
        """測試會話字符串表示"""
        expected = f"{self.user.username} - {self.session.login_time}"
        self.assertEqual(str(self.session), expected)


class APIKeyModelTest(TestCase):
    """API金鑰模型測試"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='apiuser',
            password='testpass123'
        )
        self.api_key = APIKey.objects.create(
            user=self.user,
            name='Test API Key',
            key='test_api_key_123456',
            scopes=['patients:read', 'appointments:read']
        )
    
    def test_api_key_creation(self):
        """測試API金鑰創建"""
        self.assertEqual(self.api_key.user, self.user)
        self.assertEqual(self.api_key.name, 'Test API Key')
        self.assertEqual(self.api_key.scopes, ['patients:read', 'appointments:read'])
        self.assertTrue(self.api_key.is_active)


class RoleAPITest(APITestCase):
    """角色API測試"""
    
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin',
            password='testpass123',
            is_superuser=True
        )
        self.normal_user = User.objects.create_user(
            username='user',
            password='testpass123'
        )
        self.role = Role.objects.create(
            name='nurse',
            display_name='護士',
            can_access_patients=True
        )
    
    def test_list_roles_as_admin(self):
        """測試管理員查看角色列表"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/v1/administration/roles/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_create_role_as_admin(self):
        """測試管理員創建角色"""
        self.client.force_authenticate(user=self.admin_user)
        data = {
            'name': 'receptionist',
            'display_name': '櫃台人員',
            'can_access_patients': True,
            'can_access_appointments': True,
            'data_access_level': 'facility'
        }
        response = self.client.post('/api/v1/administration/roles/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'receptionist')
    
    def test_list_roles_as_normal_user(self):
        """測試一般用戶查看角色列表"""
        self.client.force_authenticate(user=self.normal_user)
        response = self.client.get('/api/v1/administration/roles/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 一般用戶只能看到自己的角色（當前為空）
        self.assertEqual(len(response.data['results']), 0)


class UserRoleAPITest(APITestCase):
    """用戶角色API測試"""
    
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin',
            password='testpass123',
            is_superuser=True
        )
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.role = Role.objects.create(
            name='doctor',
            display_name='醫生'
        )
        self.user_role = UserRole.objects.create(
            user=self.user,
            role=self.role,
            assigned_by=self.admin_user
        )
    
    def test_assign_role_to_user(self):
        """測試給用戶指派角色"""
        self.client.force_authenticate(user=self.admin_user)
        
        new_role = Role.objects.create(
            name='nurse',
            display_name='護士'
        )
        
        data = {
            'user': self.user.id,
            'role': new_role.id
        }
        
        response = self.client.post('/api/v1/administration/user-roles/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user'], self.user.id)
        self.assertEqual(response.data['role'], new_role.id)
    
    def test_my_roles_endpoint(self):
        """測試獲取我的角色端點"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/administration/user-roles/my_roles/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['role'], self.role.id)


class APIKeyAPITest(APITestCase):
    """API金鑰API測試"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_create_api_key(self):
        """測試創建API金鑰"""
        self.client.force_authenticate(user=self.user)
        data = {
            'name': 'Test API Key',
            'scopes': '["patients:read"]',  # JSON 字符串格式
            'rate_limit': 1000
        }
        response = self.client.post('/api/v1/administration/api-keys/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Test API Key')
        self.assertEqual(response.data['user'], self.user.id)
    
    def test_regenerate_api_key(self):
        """測試重新生成API金鑰"""
        api_key = APIKey.objects.create(
            user=self.user,
            name='Test Key',
            key='old_key_123'
        )
        
        self.client.force_authenticate(user=self.user)
        response = self.client.post(f'/api/v1/administration/api-keys/{api_key.id}/regenerate/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 驗證金鑰已更改
        api_key.refresh_from_db()
        self.assertNotEqual(api_key.key, 'old_key_123')


class TwoFactorAuthAPITest(APITestCase):
    """雙因子認證API測試"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    @patch('qrcode.make')
    @patch('pyotp.random_base32')
    def test_setup_2fa(self, mock_random_base32, mock_make):
        """測試設置雙因子認證"""
        mock_random_base32.return_value = 'TESTSECRETKEY123'
        
        # 模擬QR碼圖片
        from PIL import Image
        mock_image = Image.new('RGB', (100, 100), color='white')
        mock_make.return_value = mock_image
        
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/v1/administration/two-factor-auth/setup/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('secret', response.data)
        self.assertIn('qr_code', response.data)
        self.assertIn('backup_codes', response.data)
    
    @patch('pyotp.TOTP.verify')
    def test_verify_2fa_token(self, mock_verify):
        """測試驗證2FA令牌"""
        mock_verify.return_value = True
        
        # 先設置2FA
        TwoFactorAuth.objects.create(
            user=self.user,
            secret_key='TESTSECRETKEY123'
        )
        
        self.client.force_authenticate(user=self.user)
        data = {'token': '123456'}
        response = self.client.post('/api/v1/administration/two-factor-auth/verify/', data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('2FA enabled successfully', response.data['status'])


class PermissionCalculationTest(TestCase):
    """權限計算測試"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # 創建兩個不同權限級別的角色
        self.doctor_role = Role.objects.create(
            name='doctor',
            display_name='醫生',
            can_access_patients=True,
            can_access_medical_records=True,
            data_access_level='facility'
        )
        
        self.nurse_role = Role.objects.create(
            name='nurse', 
            display_name='護士',
            can_access_patients=True,
            data_access_level='department'
        )
    
    def test_multiple_role_permissions(self):
        """測試多角色權限合併"""
        # 給用戶指派兩個角色
        UserRole.objects.create(user=self.user, role=self.doctor_role)
        UserRole.objects.create(user=self.user, role=self.nurse_role)
        
        # 導入視圖以使用權限計算方法
        from .auth_views import UserPermissionViewSet
        view = UserPermissionViewSet()
        
        user_roles = UserRole.objects.filter(user=self.user, is_active=True)
        permissions = view._calculate_user_permissions(self.user, user_roles)
        
        # 驗證權限合併結果
        self.assertTrue(permissions['modules']['can_access_patients'])
        self.assertTrue(permissions['modules']['can_access_medical_records'])
        self.assertEqual(permissions['data_access_level'], 'facility')  # 取最高級別
        self.assertEqual(len(permissions['roles']), 2)


class SecurityTest(TestCase):
    """安全功能測試"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_login_attempt_logging(self):
        """測試登入嘗試記錄"""
        LoginAttempt.objects.create(
            username='testuser',
            ip_address='127.0.0.1',
            result='success'
        )
        
        attempt = LoginAttempt.objects.get(username='testuser')
        self.assertEqual(attempt.result, 'success')
        self.assertEqual(attempt.ip_address, '127.0.0.1')
    
    def test_session_logging(self):
        """測試會話記錄"""
        session = SessionLog.objects.create(
            user=self.user,
            session_key='test_session',
            ip_address='127.0.0.1',
            status='active'
        )
        
        self.assertEqual(session.status, 'active')
        self.assertIsNone(session.logout_time)
        
        # 模擬登出
        session.status = 'logged_out'
        session.logout_time = timezone.now()
        session.save()
        
        self.assertEqual(session.status, 'logged_out')
        self.assertIsNotNone(session.logout_time)
