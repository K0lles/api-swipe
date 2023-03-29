from datetime import datetime, timedelta

from allauth.account.models import EmailAddress
from django.utils import timezone
from django.utils.encoding import force_str
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import ModelSerializer
from rest_framework.serializers import CharField

from django.utils.translation import gettext_lazy as _

from dj_rest_auth.serializers import LoginSerializer, PasswordResetConfirmSerializer, PasswordChangeSerializer

from users.fields import RoleField
from users.forms import CustomSetPasswordForm
from users.models import User, Role, Notary, Subscription, UserSubscription


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


class AuthPasswordChangeSerializer(PasswordChangeSerializer):
    set_password_form_class = CustomSetPasswordForm


class AuthPasswordResetConfirmSerializer(PasswordResetConfirmSerializer):
    uid = None
    token = None

    set_password_form_class = CustomSetPasswordForm

    def validate(self, attrs):
        from allauth.account.forms import default_token_generator
        from allauth.account.utils import url_str_to_user_pk as uid_decoder

        try:
            uid = force_str(uid_decoder(self.context['uid']))
            self.user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise ValidationError({'uid': [_('Неправильне значення.')]})

        if not default_token_generator.check_token(self.user, self.context['token']):
            raise ValidationError({'token': [_('Неправильне значення')]})

        self.custom_validation(attrs)
        # Construct SetPasswordForm instance
        self.set_password_form = self.set_password_form_class(
            user=self.user, data=attrs,
        )
        if not self.set_password_form.is_valid():
            raise serializers.ValidationError(self.set_password_form.errors)

        return attrs


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


class SubscriptionSerializer(ModelSerializer):

    class Meta:
        model = Subscription
        fields = '__all__'


class UserSubscriptionSerializer(ModelSerializer):
    subscription = SubscriptionSerializer()

    class Meta:
        model = UserSubscription
        exclude = ['user']
        read_only_fields = ['expire_date']

    def to_internal_value(self, data):
        ret = {}
        try:
            ret['subscription'] = Subscription.objects.get(pk=data.get('subscription'))
        except Subscription.DoesNotExist:
            raise ValidationError({'detail': _('Вказаної підписки не існує.')})
        return ret

    def validate(self, attrs):
        if not self.instance and UserSubscription.objects.filter(user=self.context.get('user')).exists():
            raise ValidationError({'user': _('У вас вже є підписка.')})
        return super().validate(attrs)

    def create(self, validated_data):
        subscription = UserSubscription.objects.create(
            user=self.context.get('user'),
            expire_date=timezone.now() + timedelta(days=30),
            **validated_data
        )
        return subscription
