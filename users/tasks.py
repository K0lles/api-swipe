import datetime

from django.utils import timezone
from dateutil.relativedelta import relativedelta

from api_swipe.celery import app
from users.models import UserSubscription


@app.task
def carry_on_activation():
    expired_subscriptions = UserSubscription.objects.filter(expire_date__lt=timezone.now(), auto_pay=True)
    expired_subscriptions.update(expired_date=timezone.now() + relativedelta(months=1))
