from django_filters import CharFilter, NumberFilter
from django_filters.filterset import FilterSet

from flats.models import ChessBoardFlat


class AnnouncementsFilterSet(FilterSet):
    house_status = CharFilter(field_name='residential_complex__status', lookup_expr='iexact')
    district = CharFilter(field_name='flat__district', lookup_expr='iexact')
    micro_district = CharFilter(field_name='flat__micro_district', lookup_expr='iexact')
    room_amount = NumberFilter(field_name='flat__room_amount')
    price_from = NumberFilter(field_name='price', lookup_expr='gte')
    price_to = NumberFilter(field_name='price', lookup_expr='lte')
    square_from = NumberFilter(field_name='overall_square', lookup_expr='gte')
    square_to = NumberFilter(field_name='overall_square', lookup_expr='lte')
    housing_condition = CharFilter(field_name='house_condition')

    class Meta:
        model = ChessBoardFlat
        fields = ['flat', 'residential_complex__status', 'price', 'overall_square',
                  'purpose', 'payment_option', 'house_condition']
