from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ModelViewSet

from django.utils.translation import gettext_lazy as _

from drf_psq import Rule, PsqMixin

from .permissions import *
from .serializers import *


class ResidentialComplexAPIViewSet(PsqMixin, ModelViewSet):
    serializer_class = ResidentialComplexSerializer
    lookup_url_kwarg = 'residential_complex_pk'

    psq_rules = {
        ('create',): [
            Rule([IsBuilderPermission], ResidentialComplexSerializer)
        ],
        ('list', 'retrieve'): [
            Rule([CustomIsAuthenticated], ResidentialComplexSerializer)
        ],
        ('update', 'partial_update', 'destroy'): [
            Rule([IsAdminPermission, IsAdminPermission, IsOwnerPermission], ResidentialComplexSerializer)
        ]
    }

    def get_queryset(self):
        return ResidentialComplex.objects.filter(owner=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        try:
            residential_complex: ResidentialComplex = ResidentialComplex.objects.get(pk=self.kwargs.get('residential_complex_pk'))
        except ResidentialComplex.DoesNotExist:
            return Response(data={'detail': _('Residential Complex does not exist')}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(instance=residential_complex)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer: ModelSerializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_204_NO_CONTENT)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdditionAPIViewSet(ModelViewSet):
    serializer_class = AdditionSerializer
    queryset = Addition.objects.all()
    permission_classes = [IsBuilderPermission | IsAdminPermission | IsManagerPermission]
    lookup_field = 'pk'
    lookup_url_kwarg = 'addition_pk'

    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    psq_rules = {
        ('list',): [Rule([IsBuilderPermission])],
        ('create', 'destroy', 'update'): [Rule(IsAdminPermission, IsManagerPermission)]
    }
