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
                      ListCreateAPIView,
                      DestroyAPIView,
                      GenericViewSet):

    serializer_class = CorpsSerializer
    lookup_url_kwarg = 'corps_pk'
    http_method_names = ['get', 'post', 'put', 'delete']
    pagination_class = CustomPageNumberPagination

    psq_rules = {
        ('list', 'destroy'):
            [Rule([IsManagerPermission | IsAdminPermission])],
        ('corps', 'corps_create', 'corps_update', 'corps_delete'):
            [Rule([IsBuilderPermission])],
        'retrieve':
            [Rule([CustomIsAuthenticated])]
    }

    def get_object(self, *args, **kwargs):
        try:
            return Corps.objects\
                .select_related('residential_complex', 'residential_complex__owner')\
                .get(pk=self.kwargs.get('corps_pk'))
        except Corps.DoesNotExist:
            raise ValidationError({'detail': _('Такого корпусу не існує.')})

    def get_queryset(self):
        queryset = Corps.objects.select_related('residential_complex').all().order_by('name')
        return self.paginate_queryset(queryset)

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
        if corps_to_delete.residential_complex.owner != request.user:
            raise ValidationError({'detail': _('Ви можете видалити тільки корпус у власному ЖК.')}, code=status.HTTP_403_FORBIDDEN)

        try:
            corps_to_delete.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            return Response(
                data={
                    'detail': 'Ви не можете видалити корпус, оскільки до нього прив`язані квартири.'
                },
                status=status.HTTP_409_CONFLICT
            )

    def destroy(self, request, *args, **kwargs):
        corps_to_delete = self.get_object()
        try:
            corps_to_delete.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            return Response(data={
                'detail': 'Ви не можете видалити корпус, оскільки до нього прив`язані квартири.'},
                            status=status.HTTP_409_CONFLICT)


@extend_schema(tags=['Residential Complexes'])
class ResidentialComplexAPIViewSet(PsqMixin,
                                   ListAPIView,
                                   GenericViewSet):

    serializer_class = ResidentialComplexSerializer
    lookup_url_kwarg = 'residential_complex_pk'
    pagination_class = CustomPageNumberPagination
    http_method_names = ['get', 'post', 'put', 'delete']

    psq_rules = {
        ('list',): [
            Rule([CustomIsAuthenticated], ResidentialComplexListSerializer)
        ],
        ('retrieve',): [
            Rule([CustomIsAuthenticated], ResidentialComplexSerializer)
        ],
        ('create',): [
            Rule([IsBuilderPermission], ResidentialComplexSerializer)
        ],
        ('destroy',): [
            Rule([IsAdminPermission]), Rule([IsManagerPermission])
        ],
        ('list_self',): [
            Rule([IsBuilderPermission], ResidentialComplexSerializer)
        ],
        ('update_complex', 'delete_self_complex'): [
            Rule([IsBuilderPermission], ResidentialComplexSerializer)
        ],
    }

    # TODO: Write 'list' method with filtering fields

    def get_queryset(self):
        return ResidentialComplex.objects\
            .prefetch_related('flat_set',
                              'floor_set',
                              'corps_set',
                              'section_set',
                              'document_set',
                              'gallery__photo_set',
                              'additionincomplex_set',
                              'additionincomplex_set__addition') \
            .select_related('owner')\
            .all()

    def get_object(self, *args, **kwargs):
        try:
            queryset = ResidentialComplex.objects \
                .prefetch_related('flat_set',
                                  'floor_set',
                                  'corps_set',
                                  'corps_set__flat_set',
                                  'section_set',
                                  'document_set',
                                  'gallery__photo_set',
                                  'additionincomplex_set',
                                  'additionincomplex_set__addition') \
                .select_related('owner') \
                .get(pk=self.kwargs.get('residential_complex_pk'))
            return self.paginate_queryset(queryset)
        except ResidentialComplex.DoesNotExist:
            raise ValidationError({'detail': _('Вказаного ЖК не існує.')})

    def get_own_obj(self):
        try:
            return ResidentialComplex.objects \
                .prefetch_related('flat_set',
                                  'floor_set',
                                  'corps_set',
                                  'corps_set__flat_set',
                                  'section_set',
                                  'document_set',
                                  'gallery__photo_set',
                                  'additionincomplex_set',
                                  'additionincomplex_set__addition') \
                .select_related('owner') \
                .get(owner=self.request.user)
        except ResidentialComplex.DoesNotExist:
            raise ValidationError({'detail': _('На вас не зареєстровано жодного ЖК.')}, code=status.HTTP_400_BAD_REQUEST)

    def delete_obj(self, obj: ResidentialComplex):
        try:
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            raise ValidationError({'detail': _('Ймовірно до вашого ЖК прив`язані квартири. Видалення відхилено.')},
                                  code=status.HTTP_409_CONFLICT)

    def retrieve(self, request, *args, **kwargs):
        residential_complex = self.get_object()
        serializer = self.get_serializer(instance=residential_complex)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer: ModelSerializer = self.get_serializer(data=request.data, context={'user': request.user})
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
        if not IsOwnerPermission().has_object_permission(request, self, residential_complex):
            raise ValidationError({'detail': IsOwnerPermission.message}, code=status.HTTP_403_FORBIDDEN)
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
    permission_classes = [IsBuilderPermission | IsAdminPermission | IsManagerPermission]
    http_method_names = ['get', 'post', 'put', 'delete']
    lookup_url_kwarg = 'addition_pk'
    pagination_class = CustomPageNumberPagination

    psq_rules = {
        ('residential_additions_list', 'residential_addition_delete'): [Rule([IsBuilderPermission], AdditionInComplexSerializer)],
        ('list', 'retrieve'): [Rule([IsBuilderPermission]), Rule([IsAdminPermission]), Rule([IsManagerPermission])],
        ('residential_additions_all',): [Rule([IsAdminPermission], AdditionInComplexSerializer), Rule([IsManagerPermission], AdditionInComplexSerializer)],
        ('create', 'destroy', 'update'): [Rule([IsAdminPermission]), Rule([IsManagerPermission])]
    }

    def get_queryset(self):
        queryset = Addition.objects.all()
        return self.paginate_queryset(queryset)

    def get_own_residential_additions_queryset(self):
        queryset = AdditionInComplex.objects.filter(residential_complex__owner=self.request.user)
        return self.paginate_queryset(queryset)

    @action(methods=['GET'], detail=False, url_path='residential')
    def residential_additions_all(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=AdditionInComplex.objects.all(),
                                         many=True)
        return self.get_paginated_response(data=serializer.data)

    @extend_schema(
        parameters=[
            OpenApiParameter(name='page_size', location=OpenApiParameter.QUERY,
                             description='Size of the queryset that will be returned', required=False,
                             type=int),
            OpenApiParameter(name='page', location=OpenApiParameter.QUERY,
                             description='Number of the page of the queryset that will be returned', required=False,
                             type=int)
        ]
    )
    @action(methods=['GET'], detail=False, url_path='my')
    def residential_additions_list(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.get_own_residential_additions_queryset(),
                                         many=True)
        return self.get_paginated_response(data=serializer.data)

    @action(methods=['DELETE'], detail=True, url_path='my/delete')
    def residential_addition_delete(self, request, *args, **kwargs):
        try:
            addition_to_delete = AdditionInComplex.objects\
                .select_related('residential_complex__owner')\
                .get(pk=self.kwargs.get('addition_pk'))
        except AdditionInComplex.DoesNotExist:
            return Response(data={'detail': _('У вашому ЖК не зареєстровано вказаний додаток.')}, status=status.HTTP_400_BAD_REQUEST)
        if not IsOwnerPermission().has_object_permission(request, self, addition_to_delete):
            raise ValidationError({'detail': _('Ви не маєте права видаляти вказаний додаток.')}, code=status.HTTP_403_FORBIDDEN)
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
    lookup_url_kwarg = 'document_pk'
    pagination_class = CustomPageNumberPagination

    psq_rules = {
        ('create', 'update', 'destroy'):
            [Rule([IsAdminPermission], DocumentSerializer), Rule([IsManagerPermission], DocumentSerializer)],
        ('list', 'retrieve'):
            [Rule([CustomIsAuthenticated])]
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


@extend_schema(tags=['News'])
class NewsAPIViewSet(PsqMixin,
                     ListCreateAPIView,
                     RetrieveUpdateAPIView,
                     DestroyAPIView,
                     GenericViewSet):

    serializer_class = NewsSerializer
    http_method_names = ['get', 'post', 'put', 'delete']
    lookup_url_kwarg = 'news_pk'
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

    @action(methods=['PUT'], detail=True, url_path='/my/update')
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
        if obj.residential_complex.owner != request.user:
            raise ValidationError({'detail': _('У вас немає доступу для оновлення вказаної новини.')},
                                  code=status.HTTP_403_FORBIDDEN)
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['Sections'])
class SectionAPIViewSet(PsqMixin,
                        ListAPIView,
                        RetrieveAPIView,
                        DestroyAPIView,
                        GenericViewSet):
    serializer_class = SectionSerializer
    lookup_url_kwarg = 'section_pk'
    http_method_names = ['get', 'post', 'put', 'delete']
    pagination_class = CustomPageNumberPagination

    psq_rules = {
        ('list', 'update', 'destroy'):
            [Rule([IsAdminPermission], SectionSerializer), Rule([IsManagerPermission], SectionSerializer)],
        ('sections_list', 'sections_create', 'sections_delete'):
            [Rule([IsBuilderPermission], SectionSerializer)],
        'retrieve':
            [Rule([CustomIsAuthenticated], SectionSerializer)]
    }

    def get_object(self, *args, **kwargs):
        try:
            return Section.objects.get(pk=self.kwargs.get(self.lookup_url_kwarg))
        except Section.DoesNotExist:
            raise ValidationError({'detail': _('Вказаної секції не існує.')})

    def get_own_sections_object(self):
        try:
            return Section.objects.get(pk=self.kwargs.get(self.lookup_url_kwarg),
                                       residential_complex__owner=self.request.user)
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

    def destroy(self, request, *args, **kwargs):
        obj_to_delete = self.get_object()
        try:
            obj_to_delete.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            return Response(data={
                'detail': 'Ви не можете видалити секцію, оскільки до неї прив`язані квартири.'},
                            status=status.HTTP_409_CONFLICT)

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
        obj_to_delete = self.get_own_sections_object()
        if not IsOwnerPermission().has_object_permission(request, self, obj_to_delete):
            raise ValidationError({'detail': IsOwnerPermission.message}, code=status.HTTP_403_FORBIDDEN)
        try:
            obj_to_delete.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            return Response(data={
                'detail': 'Ви не можете видалити секцію, оскільки до неї прив`язані квартири.'},
                            status=status.HTTP_409_CONFLICT)


@extend_schema(tags=['Floors'])
class FloorAPIViewSet(PsqMixin,
                      ListAPIView,
                      DestroyAPIView,
                      GenericViewSet):

    serializer_class = FloorSerializer
    lookup_url_kwarg = 'floor_pk'
    pagination_class = CustomPageNumberPagination

    psq_rules = {
        ('list', 'update', 'destroy'):
            [Rule([IsAdminPermission], FloorSerializer), Rule([IsManagerPermission], FloorSerializer)],
        ('floors_list', 'floors_create', 'floors_delete'):
            [Rule([IsBuilderPermission], FloorSerializer)],
        'retrieve':
            [Rule([CustomIsAuthenticated], FloorSerializer)]
    }

    def get_object(self, *args, **kwargs):
        try:
            return Floor.objects.get(pk=self.kwargs.get(self.lookup_url_kwarg))
        except Floor.DoesNotExist:
            raise ValidationError({'detail': _('Вказаного поверху не існує.')})

    def get_own_floors_object(self):
        try:
            return Floor.objects.get(pk=self.kwargs.get(self.lookup_url_kwarg),
                                     residential_complex__owner=self.request.user)
        except Floor.DoesNotExist:
            raise ValidationError({'detail': _('Вказаного поверху не існує.')})

    def get_queryset(self):
        queryset = Floor.objects.all()
        return self.paginate_queryset(queryset)

    def get_own_floors_queryset(self):
        queryset = Floor.objects.filter(residential_complex__owner=self.request.user)
        return self.paginate_queryset(queryset)

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.get_queryset(), many=True)
        return self.get_paginated_response(data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.get_serializer(instance=obj)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        obj_to_delete = self.get_object()
        try:
            obj_to_delete.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            return Response(data={
                'detail': 'Ви не можете видалити поверх, оскільки до нього прив`язані квартири.'},
                status=status.HTTP_409_CONFLICT)

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
        obj_to_delete = self.get_own_floors_object()
        if not IsOwnerPermission().has_object_permission(request, self, obj_to_delete):
            raise ValidationError({'detail': IsOwnerPermission.message}, code=status.HTTP_403_FORBIDDEN)
        try:
            obj_to_delete.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            return Response(data={
                'detail': 'Ви не можете видалити поверх, оскільки до нього прив`язані квартири.'},
                status=status.HTTP_409_CONFLICT)


@extend_schema(tags=['Flats'])
class FlatAPIViewSet(PsqMixin,
                     ListCreateAPIView,
                     RetrieveUpdateAPIView,
                     DestroyAPIView,
                     GenericViewSet):

    serializer_class = FlatBuilderSerializer
    http_method_names = ['get', 'post', 'put', 'delete']
    lookup_url_kwarg = 'flat_pk'
    pagination_class = CustomPageNumberPagination

    psq_rules = {
        ('my_flats', 'my_flats_create', 'my_flats_update', 'my_flats_delete'):
            [Rule([IsBuilderPermission])],
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
            return Flat.objects.get(pk=self.kwargs.get(self.lookup_url_kwarg))
        except Flat.DoesNotExist:
            raise ValidationError({'detail': _('Такої квартири не існує.')})

    def get_queryset(self):
        queryset = Flat.objects.all()
        return self.paginate_queryset(queryset)

    def get_own_flats_queryset(self):
        queryset = Flat.objects.filter(residential_complex__owner=self.request.user)
        return self.paginate_queryset(queryset)

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
        obj = self.get_object()
        try:
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            return Response(data={'detail': _('Вказана квартира ймовірно знаходиться у шахматці. Видалення неможливе.')},
                            status=status.HTTP_409_CONFLICT)

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
        if not IsOwnerPermission().has_object_permission(request, self, obj):
            raise ValidationError({'detail': IsOwnerPermission.message}, code=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(data=request.data, instance=obj, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['DELETE'], detail=True, url_path='my/delete')
    def my_flats_delete(self, request, *args, **kwargs):
        obj = self.get_object()
        if not IsOwnerPermission().has_object_permission(request, self, obj):
            raise ValidationError({'detail': IsOwnerPermission.message}, code=status.HTTP_403_FORBIDDEN)
        try:
            obj.delete()
            Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            return Response(data={'detail': _('Ваша квартира ймовірно знаходиться у шахматці. Видалення неможливе.')},
                            status=status.HTTP_409_CONFLICT)


@extend_schema(tags=['Announcements'])
class ChessBoardFlatAnnouncementAPIViewSet(PsqMixin,
                                           ListAPIView,
                                           GenericViewSet):

    serializer_class = ChessBoardFlatAnnouncementSerializer
    http_method_names = ['get', 'post', 'put', 'delete']
    lookup_url_kwarg = 'announcement_pk'

    def get_queryset(self):
        queryset = ChessBoardFlat.objects.all()
        return self.paginate_queryset(queryset)

    def get_owner_queryset(self):
        return ChessBoardFlat.objects.filter(residential_complex__owner=self.request.user)

    psq_rules = {
        ('list',): [
            Rule([IsAdminPermission]), Rule([IsManagerPermission])
        ],
        ('create_announcement',): [
            Rule([IsUserPermission])
        ]
    }

    @action(methods=['POST'], detail=False, url_path='create')
    def create_announcement(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_201_CREATED)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
