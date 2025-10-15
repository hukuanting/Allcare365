"""
Laboratory web views URL configuration for /laboratory/
Includes both web interface and API endpoints
"""

from django.urls import path, include

app_name = 'laboratory'

# Include template URLs for web interface and API endpoints
urlpatterns = [
    # Web interface
    path('', include('laboratory.template_urls')),
    # API endpoints for testing and legacy support
    path('api/', include('laboratory.api_urls')),
]
