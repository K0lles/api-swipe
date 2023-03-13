from allauth.account.models import EmailAddress
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import ModelSerializer
from rest_framework.serializers import CharField

from django.utils.translation import gettext_lazy as _

from dj_rest_auth.serializers import LoginSerializer

from users.fields import RoleField
from users.models import User, Role, Notary


class AuthLoginSerializer(LoginSerializer):
    username = None
    email = serializers.EmailField()

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if attrs.get('user') and attrs.get('user').is_blocked:
            raise ValidationError({'detail': _('Вас заблоковано. Зв`яжіться із адміністратором.')}, code=status.HTTP_403_FORBIDDEN)
        return attrs


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
    notifications = CharField()

    class Meta:
        model = User
        exclude = ['role', 'is_active', 'is_blocked', 'last_login']

    def validate_notifications(self, value: str):
        if value not in ['me', 'me-agent', 'agent', 'disabled']:
            raise ValidationError(_('Виберіть один із можливих варіант.'))
        return value

    def validate_password(self, value: str):
        if len(value) < 5:
            raise ValidationError(_('Пароль занадто простий.'))
        return value

    def update(self, instance: User, validated_data):
        password = validated_data.pop('password', None)
        for field in validated_data.keys():
            # alter email in EmailAddress for rights to authenticate if email is changed
            if field == 'email' and validated_data.get('email') != instance.email:
                email_address = EmailAddress.objects.get(user=instance)
                email_address.email = validated_data.get('email')
                email_address.save()
            setattr(instance, field, validated_data.get(field))
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class UserAdminSerializer(ModelSerializer):
    password = CharField(write_only=True, required=True)
    role = RoleField()

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


class NotarySerializer(ModelSerializer):

    class Meta:
        model = Notary
        fields = '__all__'

    def create(self, validated_data):
        instance = Notary.objects.create(
            **validated_data
        )
        return instance


class NotaryUpdateSerializer(ModelSerializer):

    class Meta:
        model = Notary
        fields = '__all__'
        extra_kwargs = {'email': {'required': False},
                        'name': {'required': False},
                        'surname': {'required': False},
                        'phone': {'required': False}
                        }

    def update(self, instance, validated_data):
        for field in validated_data:
            setattr(instance, field, validated_data.get(field))
        instance.save()
        return instance
