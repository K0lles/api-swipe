from allauth.account.models import EmailAddress
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from rest_framework.serializers import CharField

from dj_rest_auth.serializers import LoginSerializer

from users.fields import RoleField
from users.models import User, Role


class AuthLoginSerializer(LoginSerializer):
    username = None
    email = serializers.EmailField()


class AuthRegistrationSerializer(ModelSerializer):
    password = CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['email', 'password', 'name', 'surname']

    def save(self, *args, **kwargs):
        return self.create(self.validated_data)

    def create(self, validated_data):
        return User.objects.create_user(**validated_data, role=Role.objects.get(role='user'))


class UserSerializer(ModelSerializer):
    password = CharField(write_only=True)

    class Meta:
        model = User
        exclude = ['role', 'is_active', 'is_blocked', 'last_login']


class UserAdminSerializer(ModelSerializer):
    password = CharField(write_only=True, required=True)
    role = RoleField(write_only=True)

    class Meta:
        model = User
        fields = '__all__'

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        EmailAddress.objects.create(
            user=user,
            email=user.email,
            verified=True,
            primary=True
        )
        return user
