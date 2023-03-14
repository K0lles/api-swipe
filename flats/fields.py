from django.db.models import Min, Max
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


class FlatSquarePriceField(Field):

    def to_representation(self, value: ResidentialComplex):
        queryset = value.flat_set.all()
        flat_info = queryset \
            .values('square', 'price') \
            .aggregate(max_square=Max('square'),
                       min_square=Min('square'),
                       min_price=Min('price'))

        return {
            'maximal_square': flat_info.get('max_square', None),
            'minimal_square': flat_info.get('min_square', None),
            'minimal_price': flat_info.get('min_price', None)
        }

    def to_internal_value(self, data):
        pass


class DisplayField(Field):
    model = None

    def to_internal_value(self, data):
        try:
            return self.model.objects.get(pk=data)
        except self.model.DoesNotExist:
            raise ValidationError({'detail': self.default_error_messages})

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


# class SectionDisplayField(DisplayField):
#     model = Section
#     default_error_messages = _('Вказаної секції не існує.')
#
#
# class FloorDisplayField(DisplayField):
#     model = Floor
#     default_error_messages = _('Вказаного поверху не існує.')
#
#
# class CorpsDisplayField(DisplayField):
#     model = Corps
#     default_error_messages = _('Вказаного корпусу не існує.')
