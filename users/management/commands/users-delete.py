from django.core.management.base import BaseCommand
from users.models import *


class Command(BaseCommand):

    def handle(self, *args, **options):
        try:
            SavedFilter.objects.all().delete()
            Message.objects.all().delete()
            UserSubscription.objects.all().delete()
            Subscription.objects.all().delete()
            Notary.objects.all().delete()
            User.objects.all().delete()
        except:
            pass
