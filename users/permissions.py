from rest_framework.permissions import IsAuthenticated

from django.utils.translation import gettext_lazy as _


class CustomIsAuthenticated(IsAuthenticated):
    message = _('You are not authenticated.')
