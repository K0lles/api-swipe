from django.db.models import ProtectedError, Q
from rest_framework.decorators import action
from rest_framework.fields import URLField, FileField, ChoiceField
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListAPIView, \
    ListCreateAPIView, \
    RetrieveAPIView, \
    RetrieveUpdateAPIView, \
    DestroyAPIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer

from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend

from drf_psq import Rule, PsqMixin

from .filters import AnnouncementsFilterSet
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
            return Corps.objects \
                .select_related('residential_complex', 'residential_complex__owner') \
                .get(pk=self.kwargs.get(self.lookup_field))
        except Corps.DoesNotExist:
            raise ValidationError({'detail': _('Такого корпусу не існує.')})

    def get_queryset(self):
        queryset = Corps.objects.select_related('residential_complex').all().order_by('name')
        return queryset

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
        serializer = self.get_serializer(instance=self.paginate_queryset(self.get_queryset()), many=True)
        return self.get_paginated_response(data=serializer.data)

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
        residential_complex = ResidentialComplex.objects \
            .prefetch_related('corps_set') \
            .get(owner=request.user)
        instance = Corps.objects.create(
            name=f'Корпус {residential_complex.corps_set.all().count() + 1}',
            residential_complex=residential_complex
        )
        serializer = self.get_serializer(instance=instance)
        return Response(data=serializer.data, status=status.HTTP_201_CREATED)

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
    http_method_names = ['get', 'post', 'patch', 'delete']

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

    def get_queryset(self):
        queryset = ResidentialComplex.objects \
            .prefetch_related('gallery__photo_set') \
            .select_related('owner') \
            .all()
        return queryset

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
            raise ValidationError({'detail': _('На вас не зареєстровано жодного ЖК.')},
                                  code=status.HTTP_400_BAD_REQUEST)

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

    @action(methods=['PATCH'], detail=False, url_name='updating-complex', url_path='my/update')
    def update_complex(self, request, *args, **kwargs):
        residential_complex = self.get_own_obj()
        serializer = self.get_serializer(data=request.data, instance=residential_complex, partial=True,
                                         context={'request': request})
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
    http_method_names = ['get', 'post', 'patch', 'delete']
    pagination_class = CustomPageNumberPagination

    psq_rules = {
        ('list', 'retrieve'): [
            Rule([IsBuilderPermission]),
            Rule([IsAdminPermission]),
            Rule([IsManagerPermission])
        ],
        ('create', 'destroy', 'partial_update'): [
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
        return queryset

    def get_my_residential_complex(self):
        try:
            return ResidentialComplex.objects.get(owner=self.request.user)
        except ResidentialComplex.DoesNotExist:
            raise ValidationError({'detail': _('На вас не зареєстрованого жодного ЖК.')})

    def partial_update(self, request, *args, **kwargs):
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
        return AdditionInComplex.objects.all()

    def get_own_queryset(self):
        return AdditionInComplex.objects.filter(residential_complex__owner=self.request.user)

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
        serializer = self.get_serializer(instance=self.paginate_queryset(self.get_queryset()), many=True)
        return self.get_paginated_response(data=serializer.data)

    @action(methods=['GET'], detail=False, url_path='my')
    def residential_additions_list(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.paginate_queryset(self.get_own_queryset()),
                                         many=True)
        return self.get_paginated_response(data=serializer.data)

    @extend_schema(
        request=inline_serializer(
            name='Creation Addition in RC',
            fields={
                'addition': IntegerField(),
                'turned_on': BooleanField()
            }
        ),
        responses={
            '201': AdditionInComplexSerializer
        }
    )
    @action(methods=['POST'], detail=False, url_path='my/create')
    def residential_additions_create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data,
                                         context={'residential_complex': self.get_my_residential_complex()})
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_201_CREATED)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['PATCH'], detail=True, url_path='my/update')
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
    http_method_names = ['get', 'post', 'patch', 'delete']
    pagination_class = CustomPageNumberPagination

    psq_rules = {
        ('create', 'partial_update', 'destroy'):
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
        return queryset

    def get_own_documents_queryset(self):
        queryset = Document.objects.filter(residential_complex__owner=self.request.user)
        return queryset

    def get_object(self):
        try:
            return Document.objects \
                .select_related('residential_complex', 'residential_complex__owner') \
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
        queryset = self.paginate_queryset(self.get_queryset())
        serializer = self.get_serializer(instance=queryset, many=True)
        return self.get_paginated_response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer: DocumentSerializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_201_CREATED)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
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
        queryset = self.paginate_queryset(self.get_own_documents_queryset())
        serializer = self.get_serializer(instance=queryset, many=True)
        return self.get_paginated_response(data=serializer.data)

    @extend_schema(
        request=inline_serializer(
            name='Creation Addition in RC',
            fields={
                'name': CharField(),
                'document': FileField()
            }
        )
    )
    @action(methods=['POST'], detail=False, url_path='my/create')
    def my_documents_create(self, request, *args, **kwargs):
        residential_complex = self.get_residential_complex()
        serializer = self.get_serializer(data=request.data, context={'residential_complex': residential_complex})
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_201_CREATED)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['PATCH'], detail=True, url_path='my/update')
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
    http_method_names = ['get', 'post', 'patch', 'delete']
    pagination_class = CustomPageNumberPagination

    psq_rules = {
        ('create', 'partial_update', 'destroy'):
            [Rule([IsAdminPermission]), Rule([IsManagerPermission])],
        ('my_news', 'my_news_create', 'my_news_update', 'my_news_delete'):
            [Rule([IsBuilderPermission])],
        ('list', 'retrieve'):
            [Rule([CustomIsAuthenticated])]
    }

    def get_queryset(self):
        queryset = News.objects.all()
        return queryset

    def get_own_news_queryset(self):
        queryset = News.objects.filter(residential_complex__owner=self.request.user)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.paginate_queryset(self.get_queryset())
        serializer = self.get_serializer(instance=queryset, many=True)
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

    def partial_update(self, request, *args, **kwargs):
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
        queryset = self.paginate_queryset(self.get_own_news_queryset())
        serializer = self.get_serializer(instance=queryset, many=True)
        return self.get_paginated_response(data=serializer.data)

    @action(methods=['POST'], detail=False, url_path='my/create')
    def my_news_create(self, request, *args, **kwargs):
        residential_complex = self.get_residential_complex()
        serializer = self.get_serializer(data=request.data, context={'residential_complex': residential_complex})
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_201_CREATED)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['PATCH'], detail=True, url_path='my/update')
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
    http_method_names = ['get', 'post', 'patch', 'delete']
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
        return queryset

    def get_own_sections_queryset(self):
        queryset = Section.objects.filter(residential_complex__owner=self.request.user)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.paginate_queryset(self.get_queryset())
        serializer = self.get_serializer(instance=queryset, many=True)
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
        queryset = self.paginate_queryset(self.get_own_sections_queryset())
        serializer = self.get_serializer(instance=queryset, many=True)
        return self.get_paginated_response(data=serializer.data)

    @action(methods=['POST'], detail=False, url_path='my/create')
    def sections_create(self, request, *args, **kwargs):
        try:
            residential_complex = ResidentialComplex.objects \
                .prefetch_related('section_set') \
                .get(owner=request.user)
        except ResidentialComplex.DoesNotExist:
            raise ValidationError({'detail': _('На вас не зареєстровано жодного ЖК.')})
        instance = Section.objects.create(
            name=f'Секція {residential_complex.section_set.all().count() + 1}',
            residential_complex=residential_complex
        )
        serializer = self.get_serializer(instance=instance)
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
                                                'gallery__flat') \
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
        return queryset

    def get_own_floors_queryset(self):
        queryset = Floor.objects.filter(residential_complex__owner=self.request.user)
        return queryset

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
        queryset = self.paginate_queryset(self.get_queryset())
        serializer = self.get_serializer(instance=queryset, many=True)
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
        queryset = self.paginate_queryset(self.get_own_floors_queryset())
        serializer = self.get_serializer(instance=queryset, many=True)
        return self.get_paginated_response(data=serializer.data)

    @action(methods=['POST'], detail=False, url_path='my/create')
    def floors_create(self, request, *args, **kwargs):
        try:
            residential_complex = ResidentialComplex.objects \
                .prefetch_related('floor_set') \
                .get(owner=request.user)
        except ResidentialComplex.DoesNotExist:
            raise ValidationError({'detail': _('На вас не зареєстровано жодного ЖК.')})
        instance = Floor.objects.create(
            name=f'Поверх {residential_complex.floor_set.all().count() + 1}',
            residential_complex=residential_complex
        )
        serializer = self.get_serializer(instance=instance)
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
    http_method_names = ['get', 'post', 'patch', 'delete']
    pagination_class = CustomPageNumberPagination

    psq_rules = {
        'list': [
            Rule([CustomIsAuthenticated], FlatListSerializer)
        ],
        'retrieve': [
            Rule([CustomIsAuthenticated])
        ],
        ('partial_update', 'destroy'): [
            Rule([IsAdminPermission]), Rule([IsManagerPermission])
        ],
        'my_flats': [
            Rule([IsBuilderPermission, IsOwnerPermission], FlatListSerializer)
        ],
        ('my_flats_create', 'my_not_bounded_flats', 'my_flats_update', 'my_flats_delete'): [
            Rule([IsBuilderPermission, IsOwnerPermission])
        ]
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
        queryset = Flat.objects\
            .select_related('corps', 'section', 'floor', 'residential_complex', 'gallery')\
            .prefetch_related('gallery__photo_set')\
            .all()
        return queryset

    def get_not_bounded_queryset(self):
        """
        Returns queryset of flats, which are not bounded to any ChessBaord.
        :return:
        """
        queryset = Flat.objects \
            .select_related('chessboardflat', 'corps', 'section', 'floor', 'residential_complex', 'gallery')\
            .prefetch_related('gallery__photo_set') \
            .filter(chessboardflat__isnull=True)
        return queryset

    def get_own_flats_queryset(self):
        queryset = Flat.objects.filter(residential_complex__owner=self.request.user)
        return queryset

    def delete_object(self):
        obj = self.get_object()
        try:
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            return Response(
                data={'detail': _('Вказана квартира ймовірно знаходиться у шахматці. Видалення неможливе.')},
                status=status.HTTP_409_CONFLICT)

    def list(self, request, *args, **kwargs):
        queryset = self.paginate_queryset(self.get_queryset())
        serializer = self.get_serializer(instance=queryset, many=True)
        return self.get_paginated_response(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.get_object())
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
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
        queryset = self.paginate_queryset(self.get_own_flats_queryset())
        serializer = self.get_serializer(instance=queryset, many=True)
        return self.get_paginated_response(data=serializer.data)

    @action(methods=['GET'], detail=False, url_path='not-bounded')
    def my_not_bounded_flats(self, request, *args, **kwargs):
        """
        Return set of flats, which are not bounded to any ChessBoard.
        """
        queryset = self.paginate_queryset(self.get_not_bounded_queryset())
        serializer = self.get_serializer(instance=queryset, many=True)
        return self.get_paginated_response(serializer.data)

    @extend_schema(
        request=inline_serializer(
            name='Flat creation',
            fields={
                'section': IntegerField(default=0),
                'floor': IntegerField(default=0),
                'corps': IntegerField(default=0),
                'scheme': Base64ImageField(),
                'gallery_photos': PhotoSerializer(many=True),
                'district': CharField(),
                'micro_district': CharField(),
                'room_amount': IntegerField(min_value=1, max_value=6),
                'square': IntegerField(min_value=0),
                'price': IntegerField(min_value=0),
                'condition': ChoiceField(choices=['draft', 'living-condition'])
            }
        )
    )
    @action(methods=['POST'], detail=False, url_path='my/create')
    def my_flats_create(self, request, *args, **kwargs):
        residential_complex = self.get_residential_complex()
        serializer = self.get_serializer(data=request.data, context={'residential_complex': residential_complex})
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_201_CREATED)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['PATCH'], detail=True, url_path='my/update')
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


@extend_schema(tags=['ChessBoards'])
class ChessBoardAPIViewSet(PsqMixin,
                           DestroyAPIView,
                           GenericViewSet):
    """
    ViewSet for getting list of all ChessBoard bounded to certain RC
    """
    serializer_class = ChessBoardSerializer
    pagination_class = CustomPageNumberPagination

    psq_rules = {
        'list_chessboard_by_residential': [
            Rule([CustomIsAuthenticated], ChessBoardListSerializer)
        ],
        'retrieve': [
            Rule([CustomIsAuthenticated])
        ],
        'destroy': [
            Rule([IsAdminPermission]),
            Rule([IsManagerPermission])
        ],
        ('my_list', 'my_create', 'my_destroy'): [
            Rule([IsBuilderPermission, IsOwnerPermission])
        ]
    }

    def get_object(self, *args, **kwargs):
        try:
            return ChessBoard.objects\
                .select_related('residential_complex', 'section', 'corps')\
                .prefetch_related('chessboardflat_set')\
                .get(pk=self.kwargs.get(self.lookup_field))
        except ChessBoard.DoesNotExist:
            raise ValidationError({'detail': _('Вказаної шахматки не існує.')})

    def get_queryset(self):
        queryset = ChessBoard.objects.select_related('corps', 'section')\
            .filter(residential_complex__owner=self.request.user).order_by('-section', 'corps')
        return queryset

    def get_queryset_by_residential(self, residential_complex):
        """
        List of ChessBoards bounded to certain RC, displaying its corps and
        section.
        :return: QuerySet<ChessBoard>
        """
        queryset = ChessBoard.objects.select_related('corps', 'section')\
            .filter(residential_complex_id=self.request.query_params.get('residential_complex', None)).order_by('corps', 'section')
        return queryset

    def _get_residential_complex_by_id(self):
        """
        Get RC by query_param 'residential_complex'
        :return: ResidentialComplex
        """
        try:
            return ResidentialComplex.objects.get(pk=self.request.query_params.get('residential_complex'))
        except ResidentialComplex.DoesNotExist:
            raise ValidationError({'detail': _('Вказаного ЖК не існує.')})

    def _get_residential_complex(self) -> ResidentialComplex:
        """
        Returns ResidentialComplex of authenticated builder
        :return: ResidentialComplex
        """
        try:
            return ResidentialComplex.objects.get(owner=self.request.user)
        except ResidentialComplex.DoesNotExist:
            raise ValidationError({'detail': _('На вас не зареєстровано жодного ЖК.')})

    def delete_object(self, obj: ChessBoard):
        try:
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            raise ValidationError({'detail': _('До цієї шахматки все ще прив`язані оголошення.')})

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        return self.delete_object(obj)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='residential_complex',
                type=int,
                required=True
            )
        ]
    )
    @action(methods=['GET'], detail=False, url_path='by-residential')
    def list_chessboard_by_residential(self, request, *args, **kwargs):
        """
        List all bounded to RC ChessBoards, adding to display their corps and
        section.
        :param request: residential_complex: int
        :param args:
        :param kwargs:
        :return: [ChessBoard]
        """
        queryset = self.paginate_queryset(self.get_queryset_by_residential(residential_complex=self._get_residential_complex_by_id()))
        serializer = self.get_serializer(instance=queryset,
                                         many=True)
        return self.get_paginated_response(serializer.data)

    @extend_schema(
        responses={
            '200': inline_serializer(
                name='Success ChessBoard list',
                fields={
                    "count": IntegerField(),
                    "next": URLField(),
                    "previous": URLField(),
                    "results": ChessBoardSerializer(many=True)
                }
            )
        }
    )
    @action(methods=['GET'], detail=False, url_path='my')
    def my_list(self, request, *args, **kwargs):
        """
        Returns all ChessBoards of authenticated builder
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        queryset = self.paginate_queryset(self.get_queryset())
        serializer = self.get_serializer(instance=queryset, many=True)
        return self.get_paginated_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.get_object())
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        request=inline_serializer(
            name='ChessBoard',
            fields={
                'section': IntegerField(),
                'corps': IntegerField()
            }
        ),
        responses={
            '201': ChessBoardSerializer
        }
    )
    @action(methods=['POST'], detail=False, url_path='my/create')
    def my_create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data,
                                         context={'residential_complex': self._get_residential_complex()})
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_201_CREATED)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['DELETE'], detail=True, url_path='my/delete')
    def my_destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        return self.delete_object(obj)


@extend_schema(tags=['Announcements'])
class ChessBoardFlatAnnouncementAPIViewSet(PsqMixin,
                                           ListAPIView,
                                           RetrieveAPIView,
                                           DestroyAPIView,
                                           GenericViewSet):
    """
    ViewSet for user's part of announcements.
    """

    serializer_class = ChessBoardFlatAnnouncementSerializer
    http_method_names = ['get', 'post', 'patch', 'delete']
    pagination_class = CustomPageNumberPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = AnnouncementsFilterSet

    psq_rules = {
        ('destroy', 'list_all_announcements'): [
            Rule([IsAdminPermission], ChessBoardFlatAnnouncementListSerializer),
            Rule([IsManagerPermission], ChessBoardFlatAnnouncementListSerializer)
        ],
        ('retrieve',): [
            Rule([IsUserPermission], ChessBoardFlatAnnouncementSerializer),
            Rule([IsAdminPermission | IsManagerPermission], ChessBoardFlatAnnouncementSerializer)
        ],
        'list': [
            Rule([IsUserPermission | IsAdminPermission | IsManagerPermission | IsBuilderPermission],
                 ChessBoardFlatAnnouncementListSerializer)
        ],
        'create_announcement': [
            Rule([IsUserPermission])
        ],
        ('list_own_announcements',): [
            Rule([IsUserPermission], ChessBoardFlatAnnouncementListSerializer)
        ],
        ('update_own_announcement', 'destroy_own_announcement'): [
            Rule([IsUserPermission, IsCreatorPermission], ChessBoardFlatAnnouncementSerializer)
        ],
        'call_off_announcement': [
            Rule([IsAdminPermission | IsManagerPermission], CallOffAnnouncementSerializer)
        ]
    }

    def get_queryset(self):
        queryset = ChessBoardFlat.objects\
            .select_related('residential_complex', 'creator', 'promotion__promotion_type')\
            .filter(accepted=True, called_off=False)\
            .order_by('promotion__promotion_type__efficiency', 'created_at')
        return queryset

    def get_object(self, *args, **kwargs):
        try:
            self.obj = ChessBoardFlat.objects \
                .select_related('creator') \
                .prefetch_related('gallery__photo_set') \
                .get(pk=self.kwargs.get(self.lookup_field))
            return self.obj
        except ChessBoardFlat.DoesNotExist:
            raise ValidationError({'detail': _('Вказаної об`яви не існує.')})

    def get_owner_queryset(self):
        queryset = ChessBoardFlat.objects \
            .prefetch_related('gallery__photo_set') \
            .select_related('creator') \
            .filter(creator=self.request.user)
        return queryset

    def get_all_queryset(self):
        queryset = ChessBoardFlat.objects.all().order_by('created_at')
        return queryset

    def destroy_object(self, obj):
        try:
            obj.delete()
        except ProtectedError:
            raise ValidationError({'detail': _('Видалити об`яву не вдалося.')})

    @extend_schema(
        parameters=[
            OpenApiParameter(name='house_status', type=str),
            OpenApiParameter(name='district', type=str),
            OpenApiParameter(name='micro_district', type=str),
            OpenApiParameter(name='room_amount', type=int),
            OpenApiParameter(name='price_from', type=int),
            OpenApiParameter(name='price_to', type=int),
            OpenApiParameter(name='square_from', type=int),
            OpenApiParameter(name='square_to', type=int),
            OpenApiParameter(name='purpose', type=str),
            OpenApiParameter(name='payment_option', type=str),
            OpenApiParameter(name='housing_condition', type=str)
        ]
    )
    def list(self, request, *args, **kwargs):
        filtered_queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(instance=self.paginate_queryset(filtered_queryset),
                                         many=True)
        return self.get_paginated_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve method for all authenticated users.
        :param request:
        :param args:
        :param kwargs: pk: int
        :return: ChessBoardFlat
        """
        serializer = self.get_serializer(instance=self.get_object())
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        self.destroy_object(obj)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['GET'], detail=False, url_path='all')
    def list_all_announcements(self, request, *args, **kwargs):
        queryset = self.paginate_queryset(self.get_all_queryset())
        serializer = self.get_serializer(instance=queryset, many=True)
        return self.get_paginated_response(serializer.data)

    @extend_schema(
        responses={
            '200': ChessBoardFlatAnnouncementListSerializer(many=True)
        }
    )
    @action(methods=['GET'], detail=False, url_path='my')
    def list_own_announcements(self, request, *args, **kwargs):
        queryset = self.paginate_queryset(self.get_owner_queryset())
        serializer = self.get_serializer(instance=queryset, many=True)
        return self.get_paginated_response(serializer.data)

    @action(methods=['POST'], detail=False, url_path='create')
    def create_announcement(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'user': request.user})
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_201_CREATED)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['PATCH'], detail=True, url_path='my/update')
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

    @extend_schema(
        request=inline_serializer(
            name='Call off announcement',
            fields={
                'rejection_reason': CharField(required=False),
                'called_off': BooleanField()
            }
        ),
        responses={
            '200': inline_serializer(
                name='Success',
                fields={
                    'detail': CharField(default=_('Оголошення успішно відхилено.'))
                }
            )
        }
    )
    @action(methods=['PATCH'], detail=True, url_path='call-off')
    def call_off_announcement(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, instance=self.get_object(), partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(data={'detail': _('Оголошення успішно відхилено.')}, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        request=None,
        responses={
            '200': inline_serializer(
                name='Success',
                fields = {
                    'detail': CharField(default=_('Оголошення успішно розблоковано.'))
                }
            )
        }
    )
    @action(methods=['PATCH'], detail=True, url_path='allow')
    def allow_announcement(self, request, *args, **kwargs):
        instance: ChessBoardFlat = self.get_object()
        if instance.called_off:
            instance.called_off = False
            instance.rejection_reason = None
            instance.save()
            return Response(data={'detail': _('Оголошення успішно розблоковано.')}, status=status.HTTP_200_OK)
        return Response(data={'detail': _('Оголошення не є заблокованим.')}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Announcement Approval'])
class ChessBoardFlatApprovingAPIViewSet(PsqMixin,
                                        ListAPIView,
                                        GenericViewSet):
    """
    ViewSet for builder's part of announcements
    """

    serializer_class = AnnouncementApproveSerializer
    gallery_photos = PhotoSerializer
    pagination_class = CustomPageNumberPagination

    psq_rules = {
        ('list', 'requests', 'list_called_off_announcements'): [
            Rule([IsBuilderPermission], AnnouncementListSerializer)
        ],
        ('approve_announcement', 'announcement_detail', 'delete_announcement'): [
            Rule([IsBuilderPermission, IsOwnerPermission])
        ]
    }

    def get_queryset(self):
        queryset = ChessBoardFlat.objects \
            .select_related('residential_complex', 'residential_complex__owner') \
            .filter(residential_complex__owner=self.request.user, accepted=True, called_off=False)
        return queryset

    def get_unaccepted_queryset(self):
        unaccepted_conditions = Q(accepted=False)
        unaccepted_conditions.add(Q(called_off=True), Q.OR)
        queryset = ChessBoardFlat.objects.filter(unaccepted_conditions,
                                                 residential_complex__owner=self.request.user)
        return queryset

    def get_called_off_queryset(self):
        queryset = ChessBoardFlat.objects.filter(residential_complex__owner=self.request.user,
                                                 called_off=True)
        return queryset

    def get_object(self, *args, **kwargs):
        try:
            return ChessBoardFlat.objects.get(residential_complex__owner=self.request.user,
                                              pk=self.kwargs.get(self.lookup_field))
        except ChessBoardFlat.DoesNotExist:
            raise ValidationError({'detail': _('Вказаного оголошення не існує.')})

    @extend_schema(
        parameters=[
            OpenApiParameter(name='page_size', location=OpenApiParameter.QUERY,
                             description='Size of the queryset that will be returned', required=False, type=int),
            OpenApiParameter(name='page', location=OpenApiParameter.QUERY,
                             description='Number of the page of the queryset that will be returned', required=False,
                             type=int)
        ],
        responses={
            '200': inline_serializer(
                name='Success ChessBoardFlat list',
                fields={
                    "count": IntegerField(),
                    "next": URLField(),
                    "previous": URLField(),
                    "results": AnnouncementListSerializer(many=True)
                }
            )
        }
    )
    @action(methods=['GET'], detail=False)
    def requests(self, request, *args, **kwargs):
        queryset = self.paginate_queryset(self.get_unaccepted_queryset())
        serializer = self.get_serializer(instance=queryset, many=True)
        return self.get_paginated_response(data=serializer.data)

    @action(methods=['GET'], detail=False, url_path='called-off')
    def list_called_off_announcements(self, request, *args, **kwargs):
        queryset = self.paginate_queryset(self.get_called_off_queryset())
        serializer = self.get_serializer(instance=queryset, many=True)
        return self.get_paginated_response(serializer.data)

    @action(methods=['GET'], detail=True, url_path='detail')
    def announcement_detail(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.get_object())
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        request=inline_serializer(
            name='Approve of announcement',
            fields={
                "main_photo": Base64ImageField(),
                "flat": IntegerField(default=0),
                "gallery_photos": PhotoSerializer(many=True),
                "accepted": BooleanField(),
                "address": CharField(),
                "purpose": ChoiceField(choices=['apartments']),
                "room_amount": IntegerField(min_value=1, max_value=6),
                "planning": ChoiceField(choices=['studio-bathroom', 'studio']),
                "house_condition": ChoiceField(choices=['repair-required', 'good']),
                "overall_square": IntegerField(min_value=1),
                "kitchen_square": IntegerField(min_value=1),
                "has_balcony": BooleanField(),
                "heating_type": ChoiceField(choices=['gas', 'centralizer']),
                "payment_option": ChoiceField(choices=['parent-capital']),
                "agent_commission": IntegerField(min_value=1),
                "communication_method": ChoiceField(choices=['phone-messages', 'phone', 'messages']),
                "description": CharField(),
                "price": IntegerField(min_value=1)
            }
        )
    )
    @action(methods=['PATCH'], detail=True, url_path='approve')
    def approve_announcement(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, instance=self.get_object(), partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['DELETE'], detail=True, url_path='delete')
    def delete_announcement(self, request, *args, **kwargs):
        obj: ChessBoardFlat = self.get_object()
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['Promotions'])
class PromotionTypeAPIViewSet(PsqMixin,
                              ListCreateAPIView,
                              GenericViewSet):
    serializer_class = PromotionTypeSerializer
    http_method_names = ['get', 'post', 'patch']
    pagination_class = CustomPageNumberPagination

    psq_rules = {
        'list': [
            Rule([CustomIsAuthenticated])
        ],
        ('create', 'update'): [
            Rule([IsAdminPermission]),
            Rule([IsManagerPermission])
        ]
    }

    def get_object(self, *args, **kwargs):
        try:
            return PromotionType.objects.get(pk=self.kwargs.get(self.lookup_field))
        except PromotionType.DoesNotExist:
            raise ValidationError({'detail': _('Такого типу просування не існує.')})

    def get_queryset(self):
        return PromotionType.objects.all()

    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, instance=self.get_object(), partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Announcement Promotion'])
class AnnouncementPromotionAPIViewSet(PsqMixin,
                                      GenericViewSet):
    serializer_class = PromotionSerializer

    psq_rules = {
        ('create', 'destroy_promotion'): [
            Rule([IsUserPermission, IsCreatorPermission])
        ]
    }

    def get_chessboard_flat_object(self):
        if not self.request.query_params.get('announcement', None):
            raise ValidationError({'detail': _('Не вказане оголошення.')})
        try:
            chessboard_flat = ChessBoardFlat.objects.get(pk=self.request.query_params.get('announcement'))
            if not IsCreatorPermission().has_object_permission(self.request, self, chessboard_flat):
                raise ValidationError({'detail': _('Ви не є власником створеного оголошення.')}, code=status.HTTP_403_FORBIDDEN)
            return chessboard_flat
        except ChessBoardFlat.DoesNotExist:
            raise ValidationError({'detail': _('Вказаного оголошення не існує.')})

    def get_promotion_type(self):
        if not self.request.query_params.get('promotion_type', None):
            raise ValidationError({'detail': _('Не вказаний тип просування.')})
        try:
            return PromotionType.objects.get(pk=self.request.query_params.get('promotion_type'))
        except PromotionType.DoesNotExist:
            raise ValidationError({'detail': _('Вказаного типу просування не існує.')})

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='announcement',
                type=int,
                required=True
            ),
            OpenApiParameter(
                name='promotion_type',
                type=int,
                required=True
            )
        ]
    )
    def create(self, request, *args, **kwargs):
        self.obj = self.get_chessboard_flat_object()
        serializer = self.get_serializer(
            data=request.data,
            context={'chessboard_flat': self.obj,
                     'promotion_type': self.get_promotion_type()}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(status=status.HTTP_201_CREATED)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='announcement',
                type=int
            )
        ]
    )
    @action(methods=['DELETE'], detail=False, url_path='clear')
    def destroy_promotion(self, request, *args, **kwargs):
        chessboard_flat = self.get_chessboard_flat_object()
        chessboard_flat.promotion.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['Favorite Announcements'])
class FavoriteChessBoardFlatAPIViewSet(PsqMixin,
                                       ListCreateAPIView,
                                       DestroyAPIView,
                                       GenericViewSet):

    serializer_class = FavoriteChessBoardFlatSerializer
    pagination_class = CustomPageNumberPagination

    psq_rules = {
        ('list', 'create', 'destroy'): [
            Rule([IsUserPermission, IsOwnerPermission])
        ]
    }

    def get_object(self, *args, **kwargs):
        try:
            return Favorite.objects.get(pk=self.kwargs.get(self.lookup_field))
        except Favorite.DoesNotExist:
            raise ValidationError({'detail': _('Вказаного улюбленого оголошення не існує.')})

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user, chessboard_flat__isnull=False)

    @extend_schema(
        request=inline_serializer(
            name='Favorite Announcement request',
            fields={
                'chessboard_flat': IntegerField()
            }
        )
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'user': request.user})
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Favorite Residential Complexes'])
class FavoriteResidentialComplexAPIViewSet(PsqMixin,
                                           ListCreateAPIView,
                                           DestroyAPIView,
                                           GenericViewSet):

    serializer_class = FavoriteResidentialComplexSerializer
    pagination_class = CustomPageNumberPagination

    psq_rules = {
        ('list', 'create', 'destroy') : [
            Rule([IsUserPermission, IsOwnerPermission])
        ]
    }

    def get_object(self, *args, **kwargs):
        try:
            return Favorite.objects.get(pk=self.kwargs.get(self.lookup_field))
        except Favorite.DoesNotExist:
            raise ValidationError({'detail': _('Вказаного улюбленого ЖК не існує.')})

    def get_queryset(self):
        return self.paginate_queryset(Favorite.objects.filter(user=self.request.user, residential_complex__isnull=False))

    @extend_schema(
        request=inline_serializer(
            name='Favorite RS request',
            fields={
                'residential_complex': IntegerField()
            }
        )
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'user': request.user})
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

