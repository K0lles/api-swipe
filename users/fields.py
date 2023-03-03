from rest_framework.exceptions import ValidationError
from rest_framework.serializers import Field
from django.utils.translation import gettext_lazy as _

from .models import Role


class RoleField(Field):

    def to_internal_value(self, data: str) -> Role:
        print(data)
        try:
            return Role.objects.get(role=data)
        except Role.DoesNotExist:
            raise ValidationError(_('Choose existing type of user'))

    def to_representation(self, value: Role):
        return value.role
