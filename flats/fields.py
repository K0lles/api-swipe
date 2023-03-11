from rest_framework.exceptions import ValidationError
from rest_framework.fields import Field

from django.utils.translation import gettext_lazy as _

from flats.models import Addition, ResidentialComplex


class AdditionField(Field):

    def to_internal_value(self, data: int) -> Addition:
        try:
            return Addition.objects.get(pk=data)
        except (Addition.DoesNotExist, TypeError):
            raise ValidationError(detail=_('Вказаного додатку не існує.'))

    def to_representation(self, value: Addition) -> dict:
        return {
            'id': value.id,
            'name': value.name,
            'logo': value.logo.url
        }


class ResidentialComplexDisplayField(Field):

    def to_internal_value(self, data: int) -> ResidentialComplex:
        try:
            return ResidentialComplex.objects.get(pk=data)
        except ResidentialComplex.DoesNotExist:
            raise ValidationError({'detail': _('Вказаного ЖК не існує.')})

    def to_representation(self, value: ResidentialComplex):
        return {
            'id': value.id,
            'name': value.name,
        }
