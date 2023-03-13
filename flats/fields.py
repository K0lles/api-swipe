from rest_framework.exceptions import ValidationError
from rest_framework.fields import Field

from django.utils.translation import gettext_lazy as _

from flats.models import Addition, ResidentialComplex, Section, Floor, Corps


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


class DisplayField(Field):

    def to_internal_value(self, data):
        """This method must be overwritten in successors"""
        pass

    def to_representation(self, value):
        return {
            'id': value.id,
            'name': value.name
        }


class ResidentialComplexDisplayField(DisplayField):

    def to_internal_value(self, data: int) -> ResidentialComplex:
        try:
            return ResidentialComplex.objects.get(pk=data)
        except ResidentialComplex.DoesNotExist:
            raise ValidationError({'detail': _('Вказаного ЖК не існує.')})


class SectionDisplayField(DisplayField):

    def to_internal_value(self, data) -> Section:
        try:
            return Section.objects.get(pk=data)
        except Section.DoesNotExist:
            raise ValidationError({'detail': _('Вказаної секції не існує.')})


class FloorDisplayField(DisplayField):

    def to_internal_value(self, data) -> Floor:
        try:
            return Floor.objects.get(pk=data)
        except Floor.DoesNotExist:
            raise ValidationError({'detail': _('Вказаної секції не існує.')})


class CorpsDisplayField(DisplayField):

    def to_internal_value(self, data) -> Corps:
        try:
            return Corps.objects.get(pk=data)
        except Corps.DoesNotExist:
            raise ValidationError({'detail': _('Вказаної секції не існує.')})
