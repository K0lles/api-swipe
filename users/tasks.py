from django.template.loader import render_to_string
from django.utils import timezone
from django.core.mail import EmailMessage

from dateutil.relativedelta import relativedelta

from api_swipe.celery import app
from users.models import UserSubscription


@app.task
def carry_on_activation():
    expired_subscriptions = UserSubscription.objects.filter(expire_date__lt=timezone.now(), auto_pay=True)
    expired_subscriptions.update(expire_date=timezone.now() + relativedelta(months=1))


@app.task
def deactivate_subscription():
    expired_subscriptions = UserSubscription.objects.filter(expire_date__lt=timezone.now(), auto_pay=False)
    email_list = [subscription.user.email for subscription in expired_subscriptions]

    html_message = render_to_string('account/email/subscription_expired.html', {})
    email = EmailMessage(subject='Термін підписки вийшов.', body=html_message, to=email_list)
    email.content_subtype = 'html'
    email.send()

    expired_subscriptions.delete()
