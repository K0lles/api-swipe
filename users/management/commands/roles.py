from django.core.management.base import BaseCommand

from users.models import Role


class Command(BaseCommand):
    def handle(self, *args, **options):
        if not Role.objects.all().exists():
            Role.objects.create(role='admin')
            Role.objects.create(role='user')
            Role.objects.create(role='manager')
            Role.objects.create(role='builder')
