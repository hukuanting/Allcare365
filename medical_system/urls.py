"""
URL configuration for Allcare365 project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .health_check import health_check
from apps.integration.fhir_integration.smart_config import (
    onc_certification_api_documentation,
    smart_configuration,
)
from apps.integration.fhir_integration.views import FHIRResourceViewSet, smart_launch_test_page
import apps.core.authentication.views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # FHIR 標準入口
    path('fhir/R4/', include('apps.integration.fhir_integration.urls')),
    path('fhir/', include('apps.integration.fhir_integration.urls')),
    
    # SMART on FHIR Discovery (標準路徑)
    path('.well-known/smart-configuration', smart_configuration, name='smart_configuration'),
    path('onc-certification/api-documentation/', onc_certification_api_documentation, name='onc_api_documentation'),
    path('metadata', FHIRResourceViewSet.as_view({'get': 'metadata'}), name='root_metadata'),
    path('smart-launch-test/', smart_launch_test_page, name='smart_launch_test'),
    
    # OAuth2 認證
    path('o/authorize/', auth_views.CustomAuthorizationView.as_view(), name="authorize"),
    path('o/token/', auth_views.CustomTokenView.as_view(), name="token"),
    path('o/revoke/', auth_views.SmartRevocationView.as_view(), name="smart_revoke"),
    path('o/introspect/', auth_views.SmartIntrospectionView.as_view(), name="smart_introspect"),
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    
    # 指向 fhir_integration.urls 會包含整個 router
    # 將根目錄的 FHIR 資源請求全部導向 fhir_integration.urls
    
    path('', include('apps.integration.fhir_integration.urls')),

    # 其他 API
    path('api/health-check/', health_check),
    path('api/auth/', include('apps.core.authentication.api_urls')),
    path('api/patients/', include('apps.clinical.patients.urls')),
    path('api/health-screening/', include('apps.clinical.health_screening.urls')),
    path('auth/', include('apps.core.authentication.web_urls', namespace='authentication_web')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
