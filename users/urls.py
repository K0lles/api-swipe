from django.urls import path, include

from rest_framework.routers import DefaultRouter

from dj_rest_auth.views import LoginView, LogoutView
from dj_rest_auth.registration.views import RegisterView, VerifyEmailView, ConfirmEmailView, ResendEmailVerificationView

from rest_framework_simplejwt.views import TokenRefreshView

from .views import ConfirmationCongratulationView, UserAPIViewSet


router = DefaultRouter()
router.register('', UserAPIViewSet, basename='users')

urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='account_login'),
    path('auth/logout/', LogoutView.as_view(), name='account_logout'),
    path('auth/registration/', RegisterView.as_view(), name='account_signup'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='refresh_token'),
    path('auth/confirm-email/<str:key>/', ConfirmEmailView.as_view(), name='account_confirm_email'),
    path('auth/resend-email/', ResendEmailVerificationView.as_view(), name='account_resend_email'),
    path('auth/verify-email/', VerifyEmailView.as_view(), name='account_email_verification_sent'),
    path('auth/confirmation-congratulations/', ConfirmationCongratulationView.as_view(), name='confirmation_congratulations'),
    path('', include(router.urls))
]
