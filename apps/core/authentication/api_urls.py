from django.urls import path
from .views import (
    MFAEnrollAPIView,
    MFAVerifyAPIView,
    RegisterAPIView,
    LoginAPIView,
    LogoutAPIView,
    ProfileAPIView,
    ThrottledTokenObtainPairView,
    ThrottledTokenRefreshView,
)

app_name = 'authentication_api'

urlpatterns = [
    path('register/', RegisterAPIView.as_view(), name='register'),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('logout/', LogoutAPIView.as_view(), name='logout'),
    path('mfa/enroll/', MFAEnrollAPIView.as_view(), name='mfa_enroll'),
    path('mfa/verify/', MFAVerifyAPIView.as_view(), name='mfa_verify'),
    path('profile/', ProfileAPIView.as_view(), name='profile'),
    path('token/', ThrottledTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', ThrottledTokenRefreshView.as_view(), name='token_refresh'),
]
