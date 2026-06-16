"""
API功能測試的Django管理命令
"""
from django.core.management.base import BaseCommand
from django.test.client import Client
from django.contrib.auth.models import User
from administration.auth_models import Role, UserRole
import json


class Command(BaseCommand):
    help = '測試權限管理API功能'

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔐 開始測試權限管理API')
        )
        
        # 創建測試客戶端
        client = Client()
        
        # 使用現有的管理員用戶登入
        admin_user = User.objects.get(username='hukuanting')
        client.force_login(admin_user)
        
        self.test_roles_api(client)
        self.test_user_roles_api(client)
        
        self.stdout.write(
            self.style.SUCCESS('✅ API測試完成')
        )

    def test_roles_api(self, client):
        """測試角色API"""
        self.stdout.write('\n🎭 測試角色API')
        self.stdout.write('-' * 30)
        
        # 測試獲取角色列表
        response = client.get('/api/v1/administration/roles/')
        self.stdout.write(f'GET /roles/: HTTP {response.status_code}')
        
        if response.status_code == 200:
            try:
                data = response.json()
                results = data.get('results', data) if isinstance(data, dict) else data
                self.stdout.write(f'📊 找到 {len(results)} 個角色')
                
                # 顯示前幾個角色的資訊
                for i, role in enumerate(results[:3]):
                    self.stdout.write(f'  • {role.get("display_name", role.get("name"))}: {role.get("description", "無描述")[:50]}')
            except Exception as e:
                self.stdout.write(f'JSON解析錯誤: {e}')
        
        # 測試可用角色端點
        response = client.get('/api/v1/administration/roles/available_roles/')
        self.stdout.write(f'GET /available_roles/: HTTP {response.status_code}')

    def test_user_roles_api(self, client):
        """測試用戶角色API"""
        self.stdout.write('\n👥 測試用戶角色API')
        self.stdout.write('-' * 30)
        
        # 測試獲取用戶角色列表
        response = client.get('/api/v1/administration/user-roles/')
        self.stdout.write(f'GET /user-roles/: HTTP {response.status_code}')
        
        if response.status_code == 200:
            try:
                data = response.json()
                results = data.get('results', data) if isinstance(data, dict) else data
                self.stdout.write(f'📊 找到 {len(results)} 個用戶角色分配')
                
                for user_role in results:
                    user_info = user_role.get('user', {})
                    role_info = user_role.get('role', {})
                    username = user_info.get('username', 'Unknown') if isinstance(user_info, dict) else str(user_info)
                    role_name = role_info.get('display_name', 'Unknown') if isinstance(role_info, dict) else str(role_info)
                    status = '✅ 活躍' if user_role.get('is_active') else '❌ 停用'
                    self.stdout.write(f'  • {username} -> {role_name} ({status})')
            except Exception as e:
                self.stdout.write(f'JSON解析錯誤: {e}')
        
        # 測試我的角色端點
        response = client.get('/api/v1/administration/user-roles/my_roles/')
        self.stdout.write(f'GET /my_roles/: HTTP {response.status_code}')
        
        if response.status_code == 200:
            try:
                my_roles = response.json()
                self.stdout.write(f'👤 當前用戶有 {len(my_roles)} 個角色')
                for role in my_roles:
                    role_info = role.get('role', {})
                    role_name = role_info.get('display_name', 'Unknown') if isinstance(role_info, dict) else str(role_info)
                    self.stdout.write(f'  • {role_name}')
            except Exception as e:
                self.stdout.write(f'JSON解析錯誤: {e}')
