from django.urls import path

from dj_rest_auth.views import LoginView, LogoutView
from dj_rest_auth.registration.views import RegisterView, VerifyEmailView, ConfirmEmailView

from .views import ConfirmationCongratulationView


urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='account_login'),
    path('auth/logout/', LogoutView.as_view(), name='account_logout'),
    path('auth/registration/', RegisterView.as_view(), name='account_signup'),
    path('auth/confirm-email/<str:key>/', ConfirmEmailView.as_view(), name='account_confirm_email'),
    path('auth/account-confirm-email/', VerifyEmailView.as_view(), name='account_email_verification_sent'),
    path('auth/confirmation-congratulations/', ConfirmationCongratulationView.as_view(), name='confirmation_congratulations'),
]
