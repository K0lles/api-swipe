from django.contrib.auth.base_user import BaseUserManager
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.contrib.auth.models import AbstractBaseUser
from django.utils.translation import gettext_lazy as _

from phonenumber_field.modelfields import PhoneNumberField


class Role(models.Model):

    class RoleChoice(models.TextChoices):
        user = ('user', 'Користувач')
        manager = ('manager', 'Менеджер')
        administrator = ('admin', 'Адміністратор')
        builder = ('builder', 'Забудовник')

    role = models.CharField(max_length=55, choices=RoleChoice.choices, unique=True)


class UserManager(BaseUserManager):

    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError(_('The Email must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.is_active = True   # without activating further sending email confirmation is impossible
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_active', True)
        admin_role = Role.objects.get(role='admin')
        extra_fields.setdefault('role', admin_role)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser):
    role = models.ForeignKey(Role, on_delete=models.PROTECT)
    name = models.CharField(max_length=200)
    surname = models.CharField(max_length=200)
    logo = models.ImageField(upload_to='users/logo/', blank=True, null=True)
    phone = PhoneNumberField(blank=True, null=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=500)
    is_active = models.BooleanField(default=False)
    is_blocked = models.BooleanField(default=False)

    class NotificationChoices(models.TextChoices):
        me = 'me'
        me_agent = 'me-agent'
        agent = 'agent'
        disabled = 'disabled'

    notifications = models.CharField(max_length=15, choices=NotificationChoices.choices, default='me')
    turn_calls_to_agent = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['password', 'name', 'surname']

    def __str__(self):
        return self.email

    objects = UserManager()


class Notary(models.Model):
    email = models.EmailField()
    name = models.CharField(max_length=200)
    surname = models.CharField(max_length=200)
    phone = PhoneNumberField()


class Subscription(models.Model):

    class TypeChoice(models.TextChoices):
        common = 'common'
        lux = 'lux'

    type = models.CharField(max_length=25, choices=TypeChoice.choices)
    sum = models.FloatField(validators=[MinValueValidator(0.00, _('Sum cannot be less than 0.00'))])


class UserSubscription(models.Model):
    subscription = models.ForeignKey(Subscription, on_delete=models.PROTECT)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    expire_date = models.DateTimeField()
    auto_pay = models.BooleanField(default=False)


class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='sender', blank=True, null=True)
    receiver = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='receiver', blank=True, null=True)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class SavedFilter(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class HouseType(models.TextChoices):
        all = ('', 'Всі')
        secondary_market = ('secondary-market', 'Вторинний ринок')
        many_floors = ('many-floors', 'Багатоповерхівка')
        cottage = ('cottage', 'Котедж')

    house_type = models.CharField(max_length=40, choices=HouseType.choices)

    class HouseStatus(models.TextChoices):
        rented = ('rented', 'Здана')
        # TODO: ask about other statuses

    house_status = models.CharField(max_length=30, choices=HouseStatus.choices)
    district = models.CharField(max_length=200)
    micro_district = models.CharField(max_length=200)
    room_amount = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(5)], blank=True, null=True)
    price_from = models.IntegerField(validators=[MinValueValidator(0)])
    price_to = models.IntegerField(validators=[MinValueValidator(0)])
    square_from = models.IntegerField(validators=[MinValueValidator(0)])
    square_to = models.IntegerField(validators=[MinValueValidator(0)])
    purpose = models.CharField(max_length=200, blank=True, null=True)

    class PaymentOption(models.TextChoices):
        mortgage = ('mortgage', 'Іпотека')
        parent_capital = ('parent-capital', 'Материнський капітал')

    payment_option = models.CharField(max_length=40, choices=PaymentOption.choices)

    class HouseCondition(models.TextChoices):
        repair_required = ('repair-required', 'Потребує ремонту')
        good = ('good', 'Задовільний')

    housing_condition = models.CharField(max_length=30, choices=HouseCondition.choices)
