from django.db.models import ProtectedError
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListCreateAPIView, DestroyAPIView, RetrieveUpdateAPIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from drf_spectacular.utils import extend_schema

from django.utils.translation import gettext_lazy as _

from drf_psq import Rule, PsqMixin

from .permissions import *
from .serializers import *


@extend_schema(tags=['corps'])
class CorpsAPIViewSet(
    PsqMixin,
    ListCreateAPIView,
    DestroyAPIView,
    GenericViewSet
):

    serializer_class = CorpsSerializer
    lookup_url_kwarg = 'corps_pk'

    psq_rules = {
        'list': [Rule([IsManagerPermission | IsAdminPermission])],
        ('corps', 'corps_create', 'corps_update'): [Rule([IsBuilderPermission])]
    }

    def get_object(self, *args, **kwargs):
        try:
            return Corps.objects\
                .select_related('residential_complex', 'residential_complex__owner')\
                .get(pk=self.kwargs.get('corps_pk'))
        except Corps.DoesNotExist:
            raise ValidationError({'detail': _('Такого корпусу не існує.')})

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=Corps.objects.all(), many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    @action(methods=['GET'], detail=False, url_path='my')
    def corps(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=Corps.objects.filter(residential_complex__owner=self.request.user),
                                         many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    @action(methods=['POST'], detail=False, url_path='my/create')
    def corps_create(self, request, *args, **kwargs):
        residential_complex = ResidentialComplex.objects\
            .prefetch_related('corps_set')\
            .get(owner=request.user)
        Corps.objects.create(
            name=f'Корпус {residential_complex.corps_set.all().count() + 1}',
            residential_complex=residential_complex
        )
        serializer = self.get_serializer(instance=Corps.objects.filter(residential_complex=residential_complex),
                                         many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    @action(methods=['DELETE'], detail=True, url_path='my/delete/<int:corps_pk>')
    def delete_my_corps(self, request, *args, **kwargs):
        corps_to_delete = self.get_object()
        if corps_to_delete.residential_complex.owner != request.user:
            raise ValidationError({'detail': _('Ви можете видалити тільки корпус у власному ЖК.')}, code=status.HTTP_403_FORBIDDEN)

        try:
            corps_to_delete.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            return Response(data={
                'detail': 'Ви не можете видалити корпус, оскільки до нього прив`язані квартири.'
            },
                status=status.HTTP_409_CONFLICT)

    def destroy(self, request, *args, **kwargs):
        corps_to_delete = self.get_object()
        try:
            corps_to_delete.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            return Response(data={
                'detail': 'Ви не можете видалити корпус, оскільки до нього прив`язані квартири'},
                            status=status.HTTP_409_CONFLICT)


@extend_schema(tags=['residential-complex'])
class ResidentialComplexAPIViewSet(PsqMixin,
                                   ListCreateAPIView,
                                   GenericViewSet):

    serializer_class = ResidentialComplexSerializer
    lookup_url_kwarg = 'residential_complex_pk'

    psq_rules = {
        ('create', 'list_self'): [
            Rule([IsBuilderPermission])
        ],
        'update_complex': [
            Rule([IsBuilderPermission])
        ],
        ('list', 'retrieve'): [
            Rule([CustomIsAuthenticated])
        ]
    }

    def get_queryset(self):
        return ResidentialComplex.objects.all()

    def get_object(self, *args, **kwargs):
        try:
            residential_complex: ResidentialComplex = ResidentialComplex.objects.get(pk=self.kwargs.get('residential_complex_pk'))
            return residential_complex
        except ResidentialComplex.DoesNotExist:
            raise ValidationError({'detail': _('Вказаного ЖК не існує.')})

    def retrieve(self, request, *args, **kwargs):
        residential_complex = self.get_object()
        serializer = self.get_serializer(instance=residential_complex)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    @extend_schema(request=ResidentialComplexSerializer)
    def create(self, request, *args, **kwargs):
        serializer: ModelSerializer = self.get_serializer(data=request.data, context={'user': request.user})
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_204_NO_CONTENT)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(tags=['Get your own RS'])
    @action(methods=['GET'], detail=False, url_name='self-residential-complex', url_path='my')
    def list_self(self, request, *args, **kwargs):
        residential_complexes = ResidentialComplex.objects.filter(owner=request.user)
        serializer = self.get_serializer(instance=residential_complexes, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    @extend_schema(tags=['Update your own RS.'], request=ResidentialComplexSerializer)
    @action(methods=['PUT'], detail=False, url_name='updating-complex', url_path='my/update')
    def update_complex(self, request, *args, **kwargs):
        try:
            residential_complex = ResidentialComplex.objects\
                .prefetch_related('additionincomplex_set',
                                  'additionincomplex_set__addition')\
                .get(owner=request.user)
        except ResidentialComplex.DoesNotExist:
            raise ValidationError({'detail': _('На вас не зареєстровано жодного ЖК.')}, code=status.HTTP_400_BAD_REQUEST)

        if not IsOwnerPermission().has_object_permission(request, self, residential_complex):
            raise ValidationError({'detail': IsOwnerPermission.message}, code=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(data=request.data, instance=residential_complex, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['additions-operation'])
class AdditionAPIViewSet(PsqMixin, ModelViewSet):
    serializer_class = AdditionSerializer
    queryset = Addition.objects.all()
    permission_classes = [IsBuilderPermission | IsAdminPermission | IsManagerPermission]
    lookup_field = 'pk'
    lookup_url_kwarg = 'addition_pk'

    psq_rules = {
        ('residential_additions_delete',): [Rule([IsBuilderPermission])],
        ('list',): [Rule([IsBuilderPermission]), Rule([IsAdminPermission]), Rule([IsManagerPermission])],
        ('create', 'destroy', 'update'): [Rule([IsAdminPermission]), Rule([IsManagerPermission])]
    }

    def get_addition_in_complex_object(self):
        try:
            return AdditionInComplex.objects.get(pk=self.kwargs.get('addition_pk'),
                                                 residential_complex__owner=self.request.user)
        except AdditionInComplex.DoesNotExist:
            raise ValidationError({'detail': _('Додатку не існує.')}, code=status.HTTP_400_BAD_REQUEST)

    @extend_schema(tags=['Delete addition from your RC'], request={'id': int})
    @action(methods=['DELETE'], detail=True)
    def residential_addition_delete(self, request, *args, **kwargs):
        try:
            addition_to_delete = AdditionInComplex.objects\
                .select_related('residential_complex__owner')\
                .get(pk=self.kwargs.get('addition_pk'))
        except AdditionInComplex.DoesNotExist:
            return Response(data={'detail': _('У вашому ЖК не зареєстровано вказаний додаток.')}, status=status.HTTP_400_BAD_REQUEST)
        addition_to_delete.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DocumentAPIViewSet(PsqMixin,
                         ListCreateAPIView,
                         RetrieveUpdateAPIView,
                         DestroyAPIView,
                         GenericViewSet):

    serializer_class = DocumentSerializer
    queryset = Document.objects.all()
    lookup_url_kwarg = 'document_pk'

    psq_rules = {
        ('list', 'retrieve', 'create', 'update', 'destroy'):
            [Rule([IsAdminPermission], DocumentSerializer), Rule([IsManagerPermission], DocumentSerializer)]
    }

    def get_object(self):
        try:
            return Document.objects\
                .select_related('residential_complex', 'residential_complex__owner')\
                .get(pk=self.kwargs.get(self.lookup_url_kwarg))
        except Document.DoesNotExist:
            raise ValidationError({'detail': _('Вказаного документу не існує.')})

    def get_residential_complex(self):
        try:
            return ResidentialComplex.objects.get(owner=self.request.user)
        except ResidentialComplex.DoesNotExist:
            raise ValidationError({'detail': _('У вас немає зареєстрованих ЖК.')})

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.get_serializer(instance=obj)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(instance=queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer: DocumentSerializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.get_serializer(data=request.data, instance=obj, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        document_to_delete = self.get_object()
        document_to_delete.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['GET'], detail=False, url_path='my')
    def my_documents(self, request, *args, **kwargs):
        documents = Document.objects.filter(residential_complex__owner=self.request.user)
        serializer = self.get_serializer(instance=documents, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    @action(methods=['POST'], detail=False, url_path='my/create')
    def my_documents_create(self, request, *args, **kwargs):
        residential_complex = self.get_residential_complex()
        serializer = self.get_serializer(data=request.data, context={'residential_complex': residential_complex})
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['PUT'], detail=True, url_path='/my/update')
    def my_documents_update(self, request, *args, **kwargs):
        obj: Document = self.get_object()
        if obj.residential_complex.owner != request.user:
            raise ValidationError({'detail': _('У вас немає доступу для оновлення вказаного документу.')},
                                  code=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(data=request.data, instance=obj, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['DELETE'], detail=True, url_path='my/delete')
    def my_documents_delete(self, request, *args, **kwargs):
        obj: Document = self.get_object()
        if obj.residential_complex.owner != request.user:
            raise ValidationError({'detail': _('У вас немає доступу для оновлення вказаного документу.')},
                                  code=status.HTTP_403_FORBIDDEN)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
