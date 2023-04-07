from django.core.management.base import BaseCommand
from faker import Faker
from users.models import *
from allauth.account.models import EmailAddress


class Command(BaseCommand):
    def handle(self, *args, **options):
        faker = Faker('uk.UA')
        if not Role.objects.all().exists():
            Role.objects.create(role='admin')
            Role.objects.create(role='user')
            Role.objects.create(role='manager')
            Role.objects.create(role='builder')

        if not User.objects.filter(role__role='admin').exists():
            superuser = User.objects.create_superuser(
                            email='superuser@gmail.com',
                            password='123qweasd',
                            name='Super',
                            surname='User',
                        )
            EmailAddress.objects.create(
                user=superuser,
                email=superuser.email,
                verified=True,
                primary=True
            )

        if User.objects.filter(role__role='builder').count() < 5:
            for i in range(0, 5):
                user = User.objects.create_user(
                    name=faker.first_name(),
                    surname=faker.last_name(),
                    email=faker.email(),
                    password='123qweasd',
                    role=Role.objects.get(role='builder')
                )
                EmailAddress.objects.create(
                    user=user,
                    email=user.email,
                    verified=True
                )

        if User.objects.filter(role__role='manager').count() < 5:
            for i in range(0, 5):
                user = User.objects.create_user(
                    name=faker.first_name(),
                    surname=faker.last_name(),
                    email=faker.email(),
                    password='123qweasd',
                    role=Role.objects.get(role='manager')
                )
                EmailAddress.objects.create(
                    user=user,
                    email=user.email,
                    verified=True
                )

        if User.objects.filter(role__role='user').count() < 5:
            for i in range(0, 5):
                user = User.objects.create_user(
                    name=faker.first_name(),
                    surname=faker.last_name(),
                    email=faker.email(),
                    password='123qweasd',
                    role=Role.objects.get(role='user')
                )
                EmailAddress.objects.create(
                    user=user,
                    email=user.email,
                    verified=True
                )

        if Notary.objects.all().count() < 5:
            for i in range(0, 5):
                Notary.objects.create(
                    name=faker.first_name(),
                    surname=faker.last_name(),
                    email=faker.email(),
                    phone=faker.phone_number()
                )

        if not Subscription.objects.all().exists():
            Subscription.objects.create(
                type='common',
                sum=2.99
            )

            Subscription.objects.create(
                type='lux',
                sum=6.99
            )
