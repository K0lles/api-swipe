from rest_framework.generics import ListCreateAPIView, DestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ModelViewSet

from drf_psq import Rule
from drf_psq.decorator import psq

from .permissions import *
from .serializers import *


class ResidentialComplexAPIViewSet(ModelViewSet):
    serializer_class = ResidentialComplexSerializer

    def create(self, request, *args, **kwargs):
        print(request.data)
        serializer: ModelSerializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            print(serializer.validated_data)
            serializer.save()
            return Response(data=request.data, status=status.HTTP_204_NO_CONTENT)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    psq_rules = {
        ('create',): [
            Rule([IsBuilderPermission], ResidentialComplexSerializer)
        ],
        ('list', 'retrieve'): [
            Rule([IsAuthenticated], ResidentialComplexSerializer)
        ],
        ('update', 'partial_update', 'destroy'): [
            Rule([IsAdminPermission, IsAdminPermission, IsOwnerPermission])
        ]
    }


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


class AdditionListCreateAPIView(ListCreateAPIView):
    serializer_class = AdditionSerializer
    queryset = Addition.objects.all()

    def list(self, request, *args, **kwargs):
        print(request.user)
        return super().list(request, *args, **kwargs)


class AdditionDestroyAPIView(DestroyAPIView):
    lookup_url_kwarg = 'addition_pk'
    queryset = Addition.objects.all()
