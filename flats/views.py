from django.db.models import ProtectedError
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListAPIView, \
    ListCreateAPIView, \
    RetrieveAPIView, \
    RetrieveUpdateAPIView, \
    DestroyAPIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from drf_spectacular.utils import extend_schema, OpenApiParameter

from django.utils.translation import gettext_lazy as _

from drf_psq import Rule, PsqMixin

from .paginators import CustomPageNumberPagination
from .permissions import *
from .serializers import *


@extend_schema(tags=['Corps'], description='Creation, deletion and updating corps')
class CorpsAPIViewSet(PsqMixin,
                      ListAPIView,
                      DestroyAPIView,
                      GenericViewSet):

    serializer_class = CorpsSerializer
    http_method_names = ['get', 'post', 'put', 'delete']
    pagination_class = CustomPageNumberPagination

    psq_rules = {
        ('list', 'destroy'): [
            Rule([IsAdminPermission]),
            Rule([IsManagerPermission])
        ],
        ('corps', 'corps_create'): [
            Rule([IsBuilderPermission])
        ],
        'corps_delete': [
            Rule([IsBuilderPermission, IsOwnerPermission])
        ],
        'retrieve':
            [Rule([CustomIsAuthenticated])]
    }

    def get_object(self, *args, **kwargs):
        try:
            return Corps.objects\
                .select_related('residential_complex', 'residential_complex__owner')\
                .get(pk=self.kwargs.get(self.lookup_field))
        except Corps.DoesNotExist:
            raise ValidationError({'detail': _('Такого корпусу не існує.')})

    def get_queryset(self):
        queryset = Corps.objects.select_related('residential_complex').all().order_by('name')
        return self.paginate_queryset(queryset)

    def destroy_object(self, obj: Corps):
        try:
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            return Response(
                data={
                    'detail': 'Ви не можете видалити корпус, оскільки до нього прив`язані квартири.'
                },
                status=status.HTTP_409_CONFLICT
            )

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.get_queryset(), many=True)
        return self.get_paginated_response(data=serializer.data)

    @extend_schema(
        parameters=[
            OpenApiParameter(name='page_size', location=OpenApiParameter.QUERY,
                             description='Size of the queryset that will be returned', required=False, type=int),
            OpenApiParameter(name='page', location=OpenApiParameter.QUERY,
                             description='Number of the page of the queryset that will be returned', required=False, type=int)
        ]
    )
    @action(methods=['GET'], detail=False, url_path='my')
    def corps(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=
                                         self.paginate_queryset(Corps.objects
                                                                .select_related('residential_complex')
                                                                .filter(residential_complex__owner=request.user)
                                                                .order_by('name')
                                                                ),
                                         many=True)
        return self.get_paginated_response(data=serializer.data)

    @action(methods=['POST'], detail=False, url_path='my/create')
    def corps_create(self, request, *args, **kwargs):
        residential_complex = ResidentialComplex.objects\
            .prefetch_related('corps_set')\
            .get(owner=request.user)
        Corps.objects.create(
            name=f'Корпус {residential_complex.corps_set.all().count() + 1}',
            residential_complex=residential_complex
        )
        serializer = self.get_serializer(instance=self.paginate_queryset(Corps.objects.filter(residential_complex=residential_complex)),
                                         many=True)
        return self.get_paginated_response(data=serializer.data)

    @action(methods=['DELETE'], detail=True, url_path='my/delete')
    def corps_delete(self, request, *args, **kwargs):
        corps_to_delete = self.get_object()
        return self.destroy_object(corps_to_delete)

    def destroy(self, request, *args, **kwargs):
        corps_to_delete = self.get_object()
        return self.destroy_object(corps_to_delete)


@extend_schema(tags=['Residential Complexes'])
class ResidentialComplexAPIViewSet(PsqMixin,
                                   ListAPIView,
                                   GenericViewSet):

    serializer_class = ResidentialComplexSerializer
    pagination_class = CustomPageNumberPagination
    http_method_names = ['get', 'post', 'put', 'delete']

    psq_rules = {
        ('list',): [
            Rule([CustomIsAuthenticated], ResidentialComplexListSerializer)
        ],
        ('retrieve',): [
            Rule([CustomIsAuthenticated])
        ],
        ('create',): [
            Rule([IsBuilderPermission])
        ],
        ('destroy',): [
            Rule([IsAdminPermission]),
            Rule([IsManagerPermission])
        ],
        ('list_self',): [
            Rule([IsBuilderPermission])
        ],
        ('update_complex', 'delete_self_complex'): [
            Rule([IsBuilderPermission])
        ],
    }

    # TODO: Write 'list' method with filtering fields

    def get_queryset(self):
        queryset = ResidentialComplex.objects\
                        .prefetch_related('gallery__photo_set') \
                        .select_related('owner')\
                        .all()
        return self.paginate_queryset(queryset)

    def get_object(self, *args, **kwargs):
        try:
            return ResidentialComplex.objects \
                .prefetch_related('gallery__photo_set') \
                .select_related('owner', 'gallery') \
                .get(pk=self.kwargs.get(self.lookup_field))
        except ResidentialComplex.DoesNotExist:
            raise ValidationError({'detail': _('Вказаного ЖК не існує.')})

    def get_own_obj(self):
        try:
            return ResidentialComplex.objects \
                .prefetch_related('gallery__photo_set') \
                .select_related('owner') \
                .get(owner=self.request.user)
        except ResidentialComplex.DoesNotExist:
            raise ValidationError({'detail': _('На вас не зареєстровано жодного ЖК.')}, code=status.HTTP_400_BAD_REQUEST)

    def delete_obj(self, obj: ResidentialComplex):
        try:
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            raise ValidationError({'detail': _('Ймовірно до вашого ЖК прив`язані квартири. Видалити не вдалося.')},
                                  code=status.HTTP_409_CONFLICT)

    def retrieve(self, request, *args, **kwargs):
        residential_complex = self.get_object()
        serializer = self.get_serializer(instance=residential_complex)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        if ResidentialComplex.objects.filter(owner=request.user).exists():
            raise ValidationError({'detail': _('Ви можете володіти лише одним ЖК.')})
        serializer = self.get_serializer(data=request.data, context={'user': request.user})
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_204_NO_CONTENT)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        return self.delete_obj(obj)

    @action(methods=['GET'], detail=False, url_name='self-residential-complex', url_path='my')
    def list_self(self, request, *args, **kwargs):
        residential_complexes = self.get_own_obj()
        serializer = self.get_serializer(instance=residential_complexes)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    @action(methods=['PUT'], detail=False, url_name='updating-complex', url_path='my/update')
    def update_complex(self, request, *args, **kwargs):
        residential_complex = self.get_own_obj()
        serializer = self.get_serializer(data=request.data, instance=residential_complex, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['DELETE'], detail=False, url_path='my/delete')
    def delete_self_complex(self, request, *args, **kwargs):
        return self.delete_obj(self.get_own_obj())


@extend_schema(tags=['Additions'])
class AdditionAPIViewSet(PsqMixin, ModelViewSet):
    serializer_class = AdditionSerializer
    http_method_names = ['get', 'post', 'put', 'delete']
    pagination_class = CustomPageNumberPagination

    psq_rules = {
        ('list', 'retrieve'): [
            Rule([IsBuilderPermission]),
            Rule([IsAdminPermission]),
            Rule([IsManagerPermission])
        ],
        ('create', 'destroy', 'update'): [
            Rule([IsAdminPermission]),
            Rule([IsManagerPermission])
        ]
    }

    def get_object(self, *args, **kwargs):
        try:
            return Addition.objects.get(pk=self.kwargs.get(self.lookup_field))
        except Addition.DoesNotExist:
            raise ValidationError({'detail': _('Вказаного додатку не існує.')})

    def get_queryset(self):
        queryset = Addition.objects.all()
        return self.paginate_queryset(queryset)

    def get_own_residential_additions_queryset(self):
        queryset = AdditionInComplex.objects.filter(residential_complex__owner=self.request.user)
        return self.paginate_queryset(queryset)

    def get_my_residential_complex(self):
        try:
            return ResidentialComplex.objects.get(owner=self.request.user)
        except ResidentialComplex.DoesNotExist:
            raise ValidationError({'detail': _('На вас не зареєстрованого жодного ЖК.')})

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, instance=self.get_object(), partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Additions in complexes'])
class AdditionInComplexAPIViewSet(PsqMixin,
                                  RetrieveAPIView,
                                  DestroyAPIView,
                                  GenericViewSet):
    serializer_class = AdditionInComplexSerializer
    pagination_class = CustomPageNumberPagination

    psq_rules = {
        ('list', 'destroy'): [
            Rule([IsAdminPermission]),
            Rule([IsManagerPermission])
        ],
        ('retrieve',): [
            Rule([CustomIsAuthenticated])
        ],
        ('residential_additions_list',
         'residential_additions_create'): [
            Rule([IsBuilderPermission])
        ],
        ('residential_addition_update', 'residential_addition_delete'): [
            Rule([IsBuilderPermission, IsOwnerPermission]),
        ]
    }

    def get_queryset(self):
        return self.paginate_queryset(AdditionInComplex.objects.all())

    def get_own_queryset(self):
        return self.paginate_queryset(AdditionInComplex.objects.filter(residential_complex__owner=self.request.user))

    def get_object(self, *args, **kwargs):
        try:
            return AdditionInComplex.objects.get(pk=self.kwargs.get(self.lookup_field))
        except AdditionInComplex.DoesNotExist:
            raise ValidationError({'detail': _('Вказаний додаток не існує.')})

    def get_my_residential_complex(self):
        try:
            return ResidentialComplex.objects.get(owner=self.request.user)
        except ResidentialComplex.DoesNotExist:
            raise ValidationError({'detail': _('На вас не зареєстровано жодного ЖК.')})

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.get_queryset(), many=True)
        return self.get_paginated_response(data=serializer.data)

    @action(methods=['GET'], detail=False, url_path='my')
    def residential_additions_list(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.get_own_queryset(),
                                         many=True)
        return self.get_paginated_response(data=serializer.data)

    @action(methods=['POST'], detail=False, url_path='my/create')
    def residential_additions_create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data,
                                         context={'residential_complex': self.get_my_residential_complex()},
                                         many=True)
        if serializer.is_valid():
            serializer.save()
            return Response(status=status.HTTP_201_CREATED)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['PUT'], detail=True, url_path='my/update')
    def residential_addition_update(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.get_serializer(data=request.data,
                                         instance=obj,
                                         partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['DELETE'], detail=True, url_path='my/delete')
    def residential_addition_delete(self, request, *args, **kwargs):
        addition_to_delete = self.get_object()
        addition_to_delete.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['Documents'])
class DocumentAPIViewSet(PsqMixin,
                         ListCreateAPIView,
                         RetrieveUpdateAPIView,
                         DestroyAPIView,
                         GenericViewSet):

    serializer_class = DocumentSerializer
    http_method_names = ['get', 'post', 'put', 'delete']
    pagination_class = CustomPageNumberPagination

    psq_rules = {
        ('create', 'update', 'destroy'):
            [Rule([IsAdminPermission], DocumentSerializer), Rule([IsManagerPermission], DocumentSerializer)],
        ('list', 'retrieve'):
            [Rule([CustomIsAuthenticated])],
        ('my_documents', 'my_documents_create'):
            [Rule([IsBuilderPermission], DocumentSerializer)],
        ('my_documents_update', 'my_documents_delete'):
            [Rule([IsBuilderPermission]),
             Rule([IsOwnerPermission])]
    }

    def get_queryset(self):
        queryset = Document.objects.all()
        return self.paginate_queryset(queryset)

    def get_own_documents_queryset(self):
        queryset = Document.objects.filter(residential_complex__owner=self.request.user)
        return self.paginate_queryset(queryset)

    def get_object(self):
        try:
            return Document.objects\
                .select_related('residential_complex', 'residential_complex__owner')\
                .get(pk=self.kwargs.get(self.lookup_field))
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
        return self.get_paginated_response(serializer.data)

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

    @extend_schema(
        parameters=[
            OpenApiParameter(name='page_size', location=OpenApiParameter.QUERY,
                             description='Size of the queryset that will be returned', required=False, type=int),
            OpenApiParameter(name='page', location=OpenApiParameter.QUERY,
                             description='Number of the page of the queryset that will be returned', required=False,
                             type=int)
        ],
    )
    @action(methods=['GET'], detail=False, url_path='my')
    def my_documents(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.get_own_documents_queryset(), many=True)
        return self.get_paginated_response(data=serializer.data)

    @action(methods=['POST'], detail=False, url_path='my/create')
    def my_documents_create(self, request, *args, **kwargs):
        residential_complex = self.get_residential_complex()
        serializer = self.get_serializer(data=request.data, context={'residential_complex': residential_complex})
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['PUT'], detail=True, url_path='my/update')
    def my_documents_update(self, request, *args, **kwargs):
        obj: Document = self.get_object()
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


@extend_schema(tags=['News'])
class NewsAPIViewSet(PsqMixin,
                     ListCreateAPIView,
                     RetrieveUpdateAPIView,
                     DestroyAPIView,
                     GenericViewSet):

    serializer_class = NewsSerializer
    http_method_names = ['get', 'post', 'put', 'delete']
    pagination_class = CustomPageNumberPagination

    psq_rules = {
        ('create', 'update', 'destroy'):
            [Rule([IsAdminPermission]), Rule([IsManagerPermission])],
        ('my_news', 'my_news_create', 'my_news_update', 'my_news_delete'):
            [Rule([IsBuilderPermission])],
        ('list', 'retrieve'):
            [Rule([CustomIsAuthenticated])]
    }

    def get_queryset(self):
        queryset = News.objects.all()
        return self.paginate_queryset(queryset)

    def get_own_news_queryset(self):
        queryset = News.objects.filter(residential_complex__owner=self.request.user)
        return self.paginate_queryset(queryset)

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.get_queryset(), many=True)
        return self.get_paginated_response(data=serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.get_serializer(instance=obj)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.get_serializer(data=request.data, instance=obj, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        parameters=[
            OpenApiParameter(name='page_size', location=OpenApiParameter.QUERY,
                             description='Size of the queryset that will be returned', required=False, type=int),
            OpenApiParameter(name='page', location=OpenApiParameter.QUERY,
                             description='Number of the page of the queryset that will be returned', required=False,
                             type=int)
        ]
    )
    @action(methods=['GET'], detail=False, url_path='my')
    def my_news(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.get_own_news_queryset(), many=True)
        return self.get_paginated_response(data=serializer.data)

    @action(methods=['POST'], detail=False, url_path='my/create')
    def my_news_create(self, request, *args, **kwargs):
        residential_complex = self.get_residential_complex()
        serializer = self.get_serializer(data=request.data, context={'residential_complex': residential_complex})
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['PUT'], detail=True, url_path='my/update')
    def my_news_update(self, request, *args, **kwargs):
        obj: News = self.get_object()
        if obj.residential_complex.owner != request.user:
            raise ValidationError({'detail': _('У вас немає доступу для оновлення вказаної новини.')},
                                  code=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(data=request.data, instance=obj, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['DELETE'], detail=True, url_path='my/delete')
    def my_news_delete(self, request, *args, **kwargs):
        obj: News = self.get_object()
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['Sections'])
class SectionAPIViewSet(PsqMixin,
                        ListAPIView,
                        RetrieveAPIView,
                        DestroyAPIView,
                        GenericViewSet):
    serializer_class = SectionSerializer
    http_method_names = ['get', 'post', 'put', 'delete']
    pagination_class = CustomPageNumberPagination

    psq_rules = {
        ('list', 'destroy'):
            [Rule([IsAdminPermission], SectionSerializer), Rule([IsManagerPermission], SectionSerializer)],
        ('sections_list', 'sections_create', 'sections_delete'):
            [Rule([IsBuilderPermission, IsOwnerPermission], SectionSerializer)],
        'retrieve':
            [Rule([CustomIsAuthenticated], SectionSerializer)]
    }

    def get_object(self, *args, **kwargs):
        try:
            return Section.objects.get(pk=self.kwargs.get(self.lookup_field))
        except Section.DoesNotExist:
            raise ValidationError({'detail': _('Вказаної секції не існує.')})

    def get_queryset(self):
        queryset = Section.objects.all()
        return self.paginate_queryset(queryset)

    def get_own_sections_queryset(self):
        queryset = Section.objects.filter(residential_complex__owner=self.request.user)
        return self.paginate_queryset(queryset)

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.get_queryset(), many=True)
        return self.get_paginated_response(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.get_serializer(instance=obj)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def delete_object(self):
        obj = self.get_object()
        try:
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            return Response(data={
                'detail': 'Ви не можете видалити секцію, оскільки до неї прив`язані квартири.'},
                status=status.HTTP_409_CONFLICT)

    def destroy(self, request, *args, **kwargs):
        return self.delete_object()

    @extend_schema(
        parameters=[
            OpenApiParameter(name='page_size', location=OpenApiParameter.QUERY,
                             description='Size of the queryset that will be returned', required=False, type=int),
            OpenApiParameter(name='page', location=OpenApiParameter.QUERY,
                             description='Number of the page of the queryset that will be returned', required=False,
                             type=int)
        ]
    )
    @action(methods=['GET'], detail=False, url_path='my')
    def sections_list(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.get_own_sections_queryset(), many=True)
        return self.get_paginated_response(data=serializer.data)

    @action(methods=['POST'], detail=False, url_path='my/create')
    def sections_create(self, request, *args, **kwargs):
        try:
            residential_complex = ResidentialComplex.objects \
                .prefetch_related('section_set') \
                .get(owner=request.user)
        except ResidentialComplex.DoesNotExist:
            raise ValidationError({'detail': _('На вас не зареєстровано жодного ЖК.')})
        Section.objects.create(
            name=f'Секція {residential_complex.section_set.all().count() + 1}',
            residential_complex=residential_complex
        )
        serializer = self.get_serializer(instance=Section.objects.filter(residential_complex=residential_complex),
                                         many=True)
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)

    @action(methods=['DELETE'], detail=True, url_path='my/delete')
    def sections_delete(self, request, *args, **kwargs):
        return self.delete_object()


@extend_schema(tags=['Photo deletions'])
class PhotoAPIDeleteViews(PsqMixin,
                          GenericViewSet):

    serializer_class = None
    http_method_names = ['delete']

    psq_rules = {
        'destroy': [
            Rule([IsAdminPermission]),
            Rule([IsManagerPermission])
        ],
        ('residential_photo_delete', 'flat_photo_delete'): [
            Rule([IsResidentialComplexOrFlatPhotoOwner])
        ],
        'chessboard_flat_photo_delete': [
            Rule([IsChessBoardFlatPhotoOwner])
        ]
    }

    def get_object(self, *args, **kwargs):
        try:
            return Photo.objects.select_related('gallery__residentialcomplex',
                                                'gallery__chessboardflat',
                                                'gallery__flat')\
                .get(pk=self.kwargs.get(self.lookup_field))
        except Photo.DoesNotExist:
            raise ValidationError({'detail': _('Вказане фото не існує.')})

    def delete_object(self):
        obj = self.get_object()
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def destroy(self, request, *args, **kwargs):
        return self.delete_object()

    @action(methods=['DELETE'], detail=True, url_path='residential-complex/delete')
    def residential_photo_delete(self, request, *args, **kwargs):
        return self.delete_object()

    @action(methods=['DELETE'], detail=True, url_path='flat/delete')
    def flat_photo_delete(self, request, *args, **kwargs):
        return self.delete_object()

    @action(methods=['DELETE'], detail=True, url_path='chessboard-flat/delete')
    def chessboard_flat_photo_delete(self, request, *args, **kwargs):
        return self.delete_object()


@extend_schema(tags=['Floors'])
class FloorAPIViewSet(PsqMixin,
                      ListAPIView,
                      DestroyAPIView,
                      GenericViewSet):

    serializer_class = FloorSerializer
    pagination_class = CustomPageNumberPagination

    psq_rules = {
        ('list', 'destroy'):
            [Rule([IsAdminPermission], FloorSerializer), Rule([IsManagerPermission], FloorSerializer)],
        ('floors_list', 'floors_create', 'floors_delete'):
            [Rule([IsBuilderPermission, IsOwnerPermission], FloorSerializer)],
        'retrieve':
            [Rule([CustomIsAuthenticated], FloorSerializer)]
    }

    def get_object(self, *args, **kwargs):
        try:
            return Floor.objects.get(pk=self.kwargs.get(self.lookup_field))
        except Floor.DoesNotExist:
            raise ValidationError({'detail': _('Вказаного поверху не існує.')})

    def get_own_floors_object(self):
        try:
            return Floor.objects.get(pk=self.kwargs.get(self.lookup_field),
                                     residential_complex__owner=self.request.user)
        except Floor.DoesNotExist:
            raise ValidationError({'detail': _('Вказаного поверху не існує.')})

    def get_queryset(self):
        queryset = Floor.objects.all()
        return self.paginate_queryset(queryset)

    def get_own_floors_queryset(self):
        queryset = Floor.objects.filter(residential_complex__owner=self.request.user)
        return self.paginate_queryset(queryset)

    def delete_object(self):
        obj = self.get_object()
        try:
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            return Response(data={
                'detail': 'Ви не можете видалити поверх, оскільки до нього прив`язані квартири.'},
                status=status.HTTP_409_CONFLICT)

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.get_queryset(), many=True)
        return self.get_paginated_response(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.get_serializer(instance=obj)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        return self.delete_object()

    @extend_schema(
        parameters=[
            OpenApiParameter(name='page_size', location=OpenApiParameter.QUERY,
                             description='Size of the queryset that will be returned', required=False, type=int),
            OpenApiParameter(name='page', location=OpenApiParameter.QUERY,
                             description='Number of the page of the queryset that will be returned', required=False,
                             type=int)
        ],
    )
    @action(methods=['GET'], detail=False, url_path='my')
    def floors_list(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.get_own_floors_queryset(), many=True)
        return self.get_paginated_response(data=serializer.data)

    @action(methods=['POST'], detail=False, url_path='my/create')
    def floors_create(self, request, *args, **kwargs):
        try:
            residential_complex = ResidentialComplex.objects \
                .prefetch_related('floor_set') \
                .get(owner=request.user)
        except ResidentialComplex.DoesNotExist:
            raise ValidationError({'detail': _('На вас не зареєстровано жодного ЖК.')})
        Floor.objects.create(
            name=f'Поверх {residential_complex.floor_set.all().count() + 1}',
            residential_complex=residential_complex
        )
        serializer = self.get_serializer(instance=Floor.objects.filter(residential_complex=residential_complex),
                                         many=True)
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)

    @action(methods=['DELETE'], detail=True, url_path='my/delete')
    def floors_delete(self, request, *args, **kwargs):
        return self.delete_object()


@extend_schema(tags=['Flats'])
class FlatAPIViewSet(PsqMixin,
                     ListCreateAPIView,
                     RetrieveUpdateAPIView,
                     DestroyAPIView,
                     GenericViewSet):

    serializer_class = FlatBuilderSerializer
    http_method_names = ['get', 'post', 'put', 'delete']
    pagination_class = CustomPageNumberPagination

    psq_rules = {
        ('my_flats', 'my_flats_create', 'my_flats_update', 'my_flats_delete'):
            [Rule([IsBuilderPermission, IsOwnerPermission])],
        ('update', 'destroy'):
            [Rule([IsAdminPermission]), Rule([IsManagerPermission])],
        ('list', 'retrieve'):
            [Rule([CustomIsAuthenticated])]
    }

    def get_residential_complex(self):
        try:
            return ResidentialComplex.objects.get(owner=self.request.user)
        except ResidentialComplex.DoesNotExist:
            raise ValidationError({'detail': _('На вас не зареєстровано жодного ЖК.')})

    def get_object(self, *args, **kwargs):
        try:
            return Flat.objects.prefetch_related('gallery__photo_set').get(pk=self.kwargs.get(self.lookup_field))
        except Flat.DoesNotExist:
            raise ValidationError({'detail': _('Такої квартири не існує.')})

    def get_queryset(self):
        queryset = Flat.objects.all()
        return self.paginate_queryset(queryset)

    def get_own_flats_queryset(self):
        queryset = Flat.objects.filter(residential_complex__owner=self.request.user)
        return self.paginate_queryset(queryset)

    def delete_object(self):
        obj = self.get_object()
        try:
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            return Response(data={'detail': _('Вказана квартира ймовірно знаходиться у шахматці. Видалення неможливе.')},
                            status=status.HTTP_409_CONFLICT)

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.get_queryset(), many=True)
        return self.get_paginated_response(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.get_object())
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, instance=self.get_object(), partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        return self.delete_object()

    @extend_schema(
        parameters=[
            OpenApiParameter(name='page_size', location=OpenApiParameter.QUERY,
                             description='Size of the queryset that will be returned', required=False, type=int),
            OpenApiParameter(name='page', location=OpenApiParameter.QUERY,
                             description='Number of the page of the queryset that will be returned', required=False,
                             type=int)
        ],
    )
    @action(methods=['GET'], detail=False, url_path='my')
    def my_flats(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.get_own_flats_queryset(), many=True)
        return self.get_paginated_response(data=serializer.data)

    @action(methods=['POST'], detail=False, url_path='my/create')
    def my_flats_create(self, request, *args, **kwargs):
        residential_complex = self.get_residential_complex()
        serializer = self.get_serializer(data=request.data, context={'residential_complex': residential_complex})
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_201_CREATED)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['PUT'], detail=True, url_path='my/update')
    def my_flats_update(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.get_serializer(data=request.data, instance=obj, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['DELETE'], detail=True, url_path='my/delete')
    def my_flats_delete(self, request, *args, **kwargs):
        return self.delete_object()


@extend_schema(tags=['Announcements'])
class ChessBoardFlatAnnouncementAPIViewSet(PsqMixin,
                                           ListAPIView,
                                           RetrieveAPIView,
                                           DestroyAPIView,
                                           GenericViewSet):

    serializer_class = ChessBoardFlatAnnouncementSerializer
    http_method_names = ['get', 'post', 'put', 'delete']
    pagination_class = CustomPageNumberPagination

    psq_rules = {
        ('list', 'destroy'): [
            Rule([IsAdminPermission], ChessBoardFlatAnnouncementListSerializer),
            Rule([IsManagerPermission], ChessBoardFlatAnnouncementListSerializer)
        ],
        ('retrieve',): [
            Rule([IsUserPermission, IsCreatorPermission], ChessBoardFlatAnnouncementSerializer)
        ],
        ('create_announcement',): [
            Rule([IsUserPermission])
        ],
        ('list_own_announcements', 'update_own_announcement', 'destroy_own_announcement'): [
            Rule([IsBuilderPermission], ChessBoardFlatAnnouncementSerializer)
        ]
    }

    def get_queryset(self):
        queryset = ChessBoardFlat.objects.select_related('residential_complex', 'creator').all().order_by('creator')
        return self.paginate_queryset(queryset)

    def get_object(self, *args, **kwargs):
        try:
            self.obj = ChessBoardFlat.objects \
                .select_related('creator') \
                .prefetch_related('gallery__photo_set')\
                .get(pk=self.kwargs.get(self.lookup_field))
            self.check_object_permissions(self.request, self.obj)
            return self.obj
        except ChessBoardFlat.DoesNotExist:
            raise ValidationError({'detail': _('Вказаної об`яви не існує.')})

    def get_owner_queryset(self):
        queryset = ChessBoardFlat.objects \
            .prefetch_related('gallery__photo_set') \
            .select_related('creator') \
            .filter(creator=self.request.user)
        return self.paginate_queryset(queryset)

    def destroy_object(self, obj):
        try:
            obj.delete()
        except ProtectedError:
            raise ValidationError({'detail': _('Видалити об`яву не вдалося.')})

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.get_object())
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        self.destroy_object(obj)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['GET'], detail=False, url_path='my')
    def list_own_announcements(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.get_owner_queryset(), many=True)
        return self.get_paginated_response(serializer.data)

    @action(methods=['POST'], detail=False, url_path='create')
    def create_announcement(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'user': request.user})
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_201_CREATED)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['PUT'], detail=True, url_path='my/update')
    def update_own_announcement(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, instance=self.get_object(), partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['DELETE'], detail=True, url_path='my/delete')
    def destroy_own_announcement(self, request, *args, **kwargs):
        obj = self.get_object()
        self.destroy_object(obj)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['Promotions'])
class PromotionTypeAPIViewSet(PsqMixin,
                              ListCreateAPIView,
                              GenericViewSet):
    serializer_class = PromotionTypeSerializer
    http_method_names = ['get', 'post', 'put']
    pagination_class = CustomPageNumberPagination

    psq_rules = {
        'list': [
            Rule([CustomIsAuthenticated])
        ],
        'create': [
            Rule([IsAdminPermission]),
            Rule([IsManagerPermission])
        ]
    }

    def get_queryset(self):
        queryset = PromotionType.objects.all()
        return self.paginate_queryset(queryset)

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, instance=self.get_object(), partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Announcement Approval'])
class ChessBoardFlatApprovingAPIViewSet(PsqMixin,
                                        ListAPIView,
                                        GenericViewSet):

    serializer_class = AnnouncementApproveSerializer
    gallery_photos = PhotoSerializer
    pagination_class = CustomPageNumberPagination

    psq_rules = {
        ('list', 'update'): [
            Rule([IsBuilderPermission, IsOwnerPermission])
        ]
    }

    def get_queryset(self):
        queryset = ChessBoardFlat.objects\
            .select_related('residential_complex', 'residential_complex__owner')\
            .filter(residential_complex__owner=self.request.user)
        return self.paginate_queryset(queryset)

    @action(methods=['PUT'], detail=True, url_path='approve')
    def approve_announcement(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, instance=self.get_object(), partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
