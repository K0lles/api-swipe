from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from dj_rest_auth.serializers import LoginSerializer
from users.models import User, Role


class AuthLoginSerializer(LoginSerializer):
    username = None
    email = serializers.EmailField()


class AuthRegistrationSerializer(ModelSerializer):

    class Meta:
        model = User
        fields = ['email', 'password', 'name', 'surname']

    def save(self, *args, **kwargs):
        return self.create(self.validated_data)

    def create(self, validated_data):
        return User.objects.create_user(**validated_data, role=Role.objects.get(role='user'))
