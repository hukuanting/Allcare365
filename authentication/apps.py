from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'authentication'
    verbose_name = '認證系統'
    
    def ready(self):
        """應用準備就緒時運行"""
        import authentication.signals  # 導入信號處理器
