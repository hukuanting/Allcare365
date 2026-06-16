from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, ValidationError

from .permissions import normalized_user_roles


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    product_role = serializers.SerializerMethodField()
    legacy_role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'role', 'roles', 'product_role', 'legacy_role')

    def get_role(self, obj):
        return self.get_product_role(obj) or self.get_legacy_role(obj) or 'patient'

    def get_roles(self, obj):
        roles = sorted(normalized_user_roles(obj))
        return roles or [self.get_role(obj)]

    def get_product_role(self, obj):
        try:
            product_user = getattr(obj, 'product_user', None)
        except ObjectDoesNotExist:
            product_user = None
        if product_user is not None and getattr(product_user, 'status', 'active') == 'active':
            return getattr(product_user, 'role', '') or ''
        return ''

    def get_legacy_role(self, obj):
        try:
            auth_profile = getattr(obj, 'auth_profile', None)
        except ObjectDoesNotExist:
            auth_profile = None
        if auth_profile is not None:
            return getattr(auth_profile, 'role', '') or ''
        return ''

class RegisterSerializer(serializers.ModelSerializer):
    """
    ?冽閮餃?摨??嚗??怠?蝣潮?霅??冽?萄遣
    """
    password2 = serializers.CharField(style={'input_type': 'password'}, write_only=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2', 'first_name', 'last_name')
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate(self, attrs):
        """
        撽?撖Ⅳ?臬?寥?
        """
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        
        # 撽?撖Ⅳ撘瑕漲
        try:
            validate_password(attrs['password'])
        except ValidationError as e:
            raise serializers.ValidationError({'password': list(e.messages)})
            
        return attrs

    def create(self, validated_data):
        """
        ?萄遣?啁??        """
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

class LoginSerializer(serializers.Serializer):
    """

    ?餃摨??嚗?潮?霅?亥?瘙?頛詨
    """
    username = serializers.CharField()
    password = serializers.CharField()

