from rest_framework.exceptions import ValidationError
from rest_framework.fields import Field

from django.utils.translation import gettext_lazy as _

from flats.models import Addition


class AdditionField(Field):

    def to_internal_value(self, data: int) -> Addition:
        try:
            return Addition.objects.get(pk=data)
        except Addition.DoesNotExist:
            raise ValidationError(detail=_('There is no such addition.'))

    def to_representation(self, value: Addition) -> dict:
        print('returning representation')
        return {
            'id': value.id,
            'name': value.name,
            'logo': value.logo.url
        }
