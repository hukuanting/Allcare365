from django.urls import path, include

app_name = 'apps.core.authentication'

urlpatterns = [

    # API URLs

    path('api/', include('authentication.api_urls', namespace='authentication_api')),

    # Web URLs  

    path('', include('authentication.web_urls', namespace='authentication_web')),

]
