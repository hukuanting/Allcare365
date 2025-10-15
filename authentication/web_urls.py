from django.urls import path
from .views import RegisterView
from django.contrib.auth import views as auth_views

app_name = 'authentication_web'

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
]
