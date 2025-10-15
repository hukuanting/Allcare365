from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.http import HttpResponseForbidden, JsonResponse
from django.contrib.auth.models import Group
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class AuthenticationMiddleware:
    """
    認證中間件 - 保護系統安全
    """
    def __init__(self, get_response):
        self.get_response = get_response
        
        # 不需要認證的路徑
        self.public_paths = [
            '/api/auth/login/',
            '/api/auth/register/',
            '/auth/login/',
            '/auth/register/',
            '/auth/check-username/',
            '/auth/check-email/',
            '/admin/',
            '/static/',
            '/media/',
        ]
        
        # 需要特殊權限的路徑
        self.protected_paths = {
            '/admin/': ['admin'],
            '/api/admin/': ['admin'],
            '/reports/': ['doctor', 'nurse', 'admin'],
            '/billing/': ['staff', 'admin'],
            '/administration/': ['admin'],
        }

    def __call__(self, request):
        # 檢查是否為公開路徑
        if any(request.path.startswith(path) for path in self.public_paths):
            response = self.get_response(request)
            return response
        
        # 檢查用戶是否已登入
        if not request.user.is_authenticated:
            # 對於 API 請求，返回 401 Unauthorized
            if request.path.startswith('/api/'):
                return JsonResponse({'detail': 'Authentication credentials were not provided.'}, status=401)
            
            try:
                login_url = reverse('authentication_web:login')
            except:
                login_url = '/auth/login/'
            if request.path != login_url:
                messages.warning(request, '請先登入以訪問此頁面')
                return redirect('authentication_web:login')
        
        # 檢查特殊權限
        if request.user.is_authenticated:
            if not self.check_permissions(request):
                logger.warning(f'User {request.user.username} tried to access {request.path} without permission')
                messages.error(request, '您沒有權限訪問此頁面')
                return HttpResponseForbidden('您沒有權限訪問此頁面')
        
        response = self.get_response(request)
        return response
    
    def check_permissions(self, request):
        """
        檢查用戶權限
        """
        user = request.user
        path = request.path
        
        # 超級用戶有所有權限
        if user.is_superuser:
            return True
        
        # 檢查特殊路徑權限
        for protected_path, required_groups in self.protected_paths.items():
            if path.startswith(protected_path):
                user_groups = user.groups.values_list('name', flat=True)
                if not any(group in user_groups for group in required_groups):
                    return False
        
        return True

def require_user_type(*allowed_types):
    """
    裝飾器：要求特定用戶類型
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            user_groups = request.user.groups.values_list('name', flat=True)
            
            # 超級用戶有所有權限
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # 檢查用戶類型
            if not any(user_type in user_groups for user_type in allowed_types):
                logger.warning(f'User {request.user.username} tried to access {view_func.__name__} without proper user type')
                messages.error(request, f'此功能僅限{", ".join(allowed_types)}使用')
                return redirect('dashboard')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def require_admin(view_func):
    """
    裝飾器：要求管理員權限
    """
    return require_user_type('admin')(view_func)

def require_medical_staff(view_func):
    """
    裝飾器：要求醫療人員權限
    """
    return require_user_type('doctor', 'nurse', 'admin')(view_func)

def require_staff(view_func):
    """
    裝飾器：要求工作人員權限
    """
    return require_user_type('doctor', 'nurse', 'staff', 'admin')(view_func)

class UserTypeRequiredMixin:
    """
    混入類：要求特定用戶類型的類視圖
    """
    required_user_types = []
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not self.has_permission(request.user):
            messages.error(request, f'此功能僅限{", ".join(self.required_user_types)}使用')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def has_permission(self, user):
        if user.is_superuser:
            return True
        
        user_groups = user.groups.values_list('name', flat=True)
        return any(user_type in user_groups for user_type in self.required_user_types)

class AdminRequiredMixin(UserTypeRequiredMixin):
    """
    混入類：要求管理員權限
    """
    required_user_types = ['admin']

class MedicalStaffRequiredMixin(UserTypeRequiredMixin):
    """
    混入類：要求醫療人員權限
    """
    required_user_types = ['doctor', 'nurse', 'admin']

class StaffRequiredMixin(UserTypeRequiredMixin):
    """
    混入類：要求工作人員權限
    """
    required_user_types = ['doctor', 'nurse', 'staff', 'admin']

def get_user_permissions(user):
    """
    獲取用戶權限
    """
    permissions = {
        'can_view_patients': False,
        'can_edit_patients': False,
        'can_delete_patients': False,
        'can_view_medical_records': False,
        'can_edit_medical_records': False,
        'can_view_reports': False,
        'can_manage_billing': False,
        'can_manage_users': False,
        'can_manage_system': False,
    }
    
    if user.is_superuser:
        # 超級用戶有所有權限
        return {key: True for key in permissions.keys()}
    
    user_groups = user.groups.values_list('name', flat=True)
    
    # 管理員權限
    if 'admin' in user_groups:
        return {key: True for key in permissions.keys()}
    
    # 醫師權限
    if 'doctor' in user_groups:
        permissions.update({
            'can_view_patients': True,
            'can_edit_patients': True,
            'can_view_medical_records': True,
            'can_edit_medical_records': True,
            'can_view_reports': True,
        })
    
    # 護理師權限
    if 'nurse' in user_groups:
        permissions.update({
            'can_view_patients': True,
            'can_edit_patients': True,
            'can_view_medical_records': True,
            'can_edit_medical_records': True,
        })
    
    # 行政人員權限
    if 'staff' in user_groups:
        permissions.update({
            'can_view_patients': True,
            'can_manage_billing': True,
        })
    
    # 病患權限
    if 'patient' in user_groups:
        permissions.update({
            'can_view_patients': False,  # 只能查看自己的資料
        })
    
    return permissions

def check_object_permission(user, obj, action='view'):
    """
    檢查對象權限
    """
    user_groups = user.groups.values_list('name', flat=True)
    
    # 超級用戶和管理員有所有權限
    if user.is_superuser or 'admin' in user_groups:
        return True
    
    # 病患只能查看自己的資料
    if 'patient' in user_groups:
        # 檢查是否為病患自己的資料
        if hasattr(obj, 'patient') and obj.patient.user == user:
            return True
        if hasattr(obj, 'user') and obj.user == user:
            return True
        return False
    
    # 醫療人員可以查看和編輯病患資料
    if action in ['view', 'edit'] and any(group in user_groups for group in ['doctor', 'nurse']):
        return True
    
    # 行政人員可以查看基本資料
    if action == 'view' and 'staff' in user_groups:
        return True
    
    return False

class SecurityAuditMiddleware:
    """
    安全審計中間件
    """
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # 記錄用戶活動
        if request.user.is_authenticated:
            self.log_user_activity(request)
        
        response = self.get_response(request)
        return response
    
    def log_user_activity(self, request):
        """
        記錄用戶活動
        """
        if request.method in ['POST', 'PUT', 'DELETE']:
            logger.info(f'User {request.user.username} performed {request.method} on {request.path}')
        
        # 記錄敏感操作
        sensitive_paths = ['/admin/', '/auth/', '/api/']
        if any(request.path.startswith(path) for path in sensitive_paths):
            logger.info(f'Sensitive access: User {request.user.username} accessed {request.path}')
