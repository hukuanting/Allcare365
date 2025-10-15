from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.contrib import messages
from .serializers import UserSerializer, RegisterSerializer, LoginSerializer

class RegisterAPIView(generics.GenericAPIView):
    """
    用戶註冊 API 視圖
    """
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny] # 允許任何人註冊

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            "user": UserSerializer(user, context=self.get_serializer_context()).data,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)

class LoginAPIView(generics.GenericAPIView):
    """
    用戶登入 API 視圖
    """
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny] # 允許任何人登入

    def post(self, request, *args, **kwargs):
        print(f"Login request data: {request.data}")  # 調試信息
        
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print(f"Serializer errors: {serializer.errors}")  # 調試信息
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        
        print(f"Attempting to authenticate user: {username}")  # 調試信息
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            print(f"Authentication successful for user: {username}")  # 調試信息
            login(request, user) # 登入用戶
            refresh = RefreshToken.for_user(user)
            return Response({
                "user": UserSerializer(user, context={'request': request}).data,
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            })
        else:
            print(f"Authentication failed for user: {username}")  # 調試信息
            return Response({"detail": "無效的憑證。"}, status=status.HTTP_401_UNAUTHORIZED)

class LogoutAPIView(APIView):
    """
    用戶登出 API 視圖
    """
    permission_classes = [permissions.IsAuthenticated] # 只有登入的用戶才能登出

    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                # 由於blacklist被禁用，我們只是返回成功狀態
                # 在生產環境中，應該啟用blacklist功能
                pass
            return Response({"detail": "成功登出"}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            print(f"Logout error: {e}")
            return Response({"detail": "登出過程中發生錯誤"}, status=status.HTTP_400_BAD_REQUEST)

class ProfileAPIView(generics.RetrieveAPIView):
    """
    獲取用戶個人資料的 API 視圖
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class RegisterView(CreateView):
    """
    用戶註冊頁面視圖
    """
    form_class = UserCreationForm
    template_name = 'auth/register.html'
    success_url = reverse_lazy('authentication:login')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, '註冊成功！請登入您的帳號。')
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, '註冊失敗，請檢查輸入的資料。')
        return super().form_invalid(form)
