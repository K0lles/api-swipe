from django.db.models import Q
from django.views.generic.base import TemplateResponseMixin, View
from django.utils.translation import gettext_lazy as _

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.generics import ListCreateAPIView, DestroyAPIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework.permissions import IsAuthenticated

from dj_rest_auth.views import PasswordResetConfirmView

from drf_spectacular.utils import extend_schema

from drf_psq import PsqMixin, Rule

from flats.paginators import CustomPageNumberPagination
from .permissions import CustomIsAuthenticated
from .serializers import *
from flats.permissions import IsAdminPermission, IsManagerPermission, IsUserPermission, IsOwnerPermission


class ConfirmationCongratulationView(TemplateResponseMixin, View):
    template_name = 'account/email/congratulations.html'

    def get(self, request, *args, **kwargs):
        return self.render_to_response({})


class UserResetPasswordConfirmView(PasswordResetConfirmView):

    serializer_class = AuthPasswordResetConfirmSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'uid': self.kwargs.get('uid'),
                                                                     'token': self.kwargs.get('token')})
        if serializer.is_valid():
            serializer.save()
            return Response(data={'detail': _('Пароль змінено успішно.')}, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserAPIViewSet(PsqMixin,
                     ListCreateAPIView,
                     DestroyAPIView,
                     GenericViewSet):
    """
    View for user's part and for blocking users by managers and admins.
    """

    serializer_class = UserSerializer
    permission_classes = [IsAdminPermission]

    psq_rules = {
        ('list', 'block'): [Rule([IsManagerPermission | IsAdminPermission], UserAdminSerializer)],
        ('retrieve_self', 'delete_own_account', 'partial_update_self'): [Rule([IsAuthenticated], UserSerializer)],
        'create': [Rule([IsAdminPermission], UserAdminSerializer)],
        'managers_list': [Rule([CustomIsAuthenticated], AuthRegistrationSerializer)]
    }

    def get_queryset(self):
        return User.objects.all()

    def get_object(self, *args, **kwargs):
        try:
            return User.objects.get(pk=self.kwargs.get('pk'))
        except User.DoesNotExist:
            raise ValidationError({'detail': _('Такого користувача не існує.')})

    def get_managers_queryset(self):
        queryset = User.objects.filter(role__role__in=['admin', 'manager'])
        return self.paginate_queryset(queryset)

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.get_queryset(), many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    @action(methods=['GET'], detail=False, url_path='me', url_name='get-self')
    def retrieve_self(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.request.user)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_201_CREATED)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['PATCH'], detail=False, url_path='me/update', url_name='partial-update-user')
    def partial_update_self(self, request, *args, **kwargs):
        if self.request.user.email == 'superuser@gmail.com' and settings.SECRET_PASSWORD_KEY not in request.data.get('password'):
            return Response(data={'detail': _('Ви не маєте права змінити інформацію адміністратору.')}, status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(data=request.data, instance=self.request.user, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user.email == 'superuser@gmail.com':
            return Response({'detail': _('Ви не можете видалити адміністратора.')}, status=status.HTTP_403_FORBIDDEN)
        try:
            user.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(data={'detail': _('Щось пішло не так.')}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['POST'])
    def block(self, request, *args, **kwargs):
        user = self.get_object()
        if user.is_blocked:
            return Response(data={'detail': _('Користувач вже заблокований.')}, status=status.HTTP_400_BAD_REQUEST)
        if user.role.role == 'admin':
            return Response(data={'detail': _('Ви не можете заблокувати адміністратора.')}, status=status.HTTP_403_FORBIDDEN)
        user.is_blocked = True
        user.save()
        return Response(data={'detail': _('Користувач успішно заблокований.')}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['POST'])
    def unblock(self, request, *args, **kwargs):
        user = self.get_object()
        if not user.is_blocked:
            return Response(data={'detail': _('Користувач не є заблокованим.')}, status=status.HTTP_400_BAD_REQUEST)
        user.is_blocked = False
        user.save()
        return Response({'detail': _('Користувач успішно розблокований.')}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['DELETE'], url_path='me/delete', url_name='delete-own-account')
    def delete_own_account(self, request, *args, **kwargs):
        user = request.user
        if user.email == 'superuser@gmail.com':
            return Response({'detail': _('Ви не можете видалити адміністратора.')}, status=status.HTTP_403_FORBIDDEN)
        try:
            user.delete()
            response = Response(data={'detail': _('Your account successfully deleted')}, status=status.HTTP_200_OK)
            response.delete_cookie('access_token')
            response.delete_cookie('refresh_token')
        except Exception as e:
            return Response(data={'detail': _('Щось пішло не так.')}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return response

    @action(methods=['GET'], detail=False, url_path='managers')
    def managers_list(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.get_managers_queryset(), many=True)
        return self.get_paginated_response(serializer.data)


@extend_schema(tags=['Notaries'])
class NotaryAPIViewSet(PsqMixin, ModelViewSet):
    """
    View for creation notaries.
    """

    serializer_class = NotarySerializer
    http_method_names = ['get', 'post', 'patch', 'delete']
    lookup_url_kwarg = 'notary_pk'

    psq_rules = {
        ('list', 'create', 'retrieve', 'destroy'):
            [Rule([IsAdminPermission]), Rule([IsManagerPermission])],
        ('partial_update',):
            [Rule([IsAdminPermission], NotaryUpdateSerializer), Rule([IsManagerPermission], NotaryUpdateSerializer)]
    }

    def get_queryset(self):
        return Notary.objects.all()

    def get_object(self, *args, **kwargs):
        try:
            return Notary.objects.get(pk=self.kwargs.get(self.lookup_url_kwarg))
        except Notary.DoesNotExist:
            raise ValidationError({'detail': _('Вказаного нотаріуса не існує.')})

    def partial_update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, instance=self.get_object(), partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Subscription'])
class SubscriptionAPIViewSet(PsqMixin,
                             ModelViewSet):
    """
    View for creation types of subscription.
    """

    serializer_class = SubscriptionSerializer
    http_method_names = ['get', 'post', 'patch', 'delete']
    pagination_class = CustomPageNumberPagination

    psq_rules = {
        ('list', 'retrieve'): [
            Rule([CustomIsAuthenticated])
        ],
        ('create', 'partial_update', 'destroy'): [
            Rule([IsAdminPermission]),
            Rule([IsManagerPermission])
        ]
    }

    def get_queryset(self):
        queryset = Subscription.objects.all()
        return self.paginate_queryset(queryset)


@extend_schema(tags=['User subscription'])
class UserSubscriptionAPIViewSet(PsqMixin,
                                 GenericViewSet):

    serializer_class = UserSubscriptionSerializer

    psq_rules = {
        ('list', 'create', 'partial_update', 'destroy'): [
            Rule([IsUserPermission])
        ]
    }

    def get_object(self, *args, **kwargs):
        try:
            return UserSubscription.objects.get(user=self.request.user)
        except UserSubscription.DoesNotExist:
            raise ValidationError({'detail': _('У вас ще немає підписки.')})

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.get_object())
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'user': request.user})
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, instance=self.get_object(), partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        obj_to_delete: UserSubscription = self.get_object()
        obj_to_delete.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['Saved filters'])
class FilterAPIViewSet(PsqMixin,
                       ListCreateAPIView,
                       DestroyAPIView,
                       GenericViewSet):

    serializer_class = FilterSerializer
    pagination_class = CustomPageNumberPagination

    psq_rules = {
        ('list', 'create', 'destroy'): [
            Rule([IsUserPermission, IsOwnerPermission])
        ]
    }

    def get_object(self, *args, **kwargs):
        try:
            return SavedFilter.objects.get(pk=self.kwargs.get(self.lookup_field))
        except SavedFilter.DoesNotExist:
            raise ValidationError({'detail': _('Вказаний фільтр не існує.')})

    def get_queryset(self):
        return self.paginate_queryset(SavedFilter.objects.filter(user=self.request.user))

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'user': request.user})
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Messages'])
class MessageAPIViewSet(PsqMixin,
                        GenericViewSet):

    serializer_class = MessageSerializer

    psq_rules = {
        'send_to_manager': [
            Rule([IsUserPermission])
        ],
        'send_to_user': [
            Rule([IsAdminPermission | IsManagerPermission])
        ],
        ('retrieve',): [
            Rule([IsManagerPermission | IsAdminPermission | IsUserPermission], MessageListSerializer)
        ]
    }

    def get_object(self, *args, **kwargs):
        pass

    def get_queryset(self):
        filtering_condition = None

        if self.request.user.role.role in ['admin', 'manager']:
            filtering_condition = Q(receiver=self.request.user, sender=self.get_user_object())
            filtering_condition.add(Q(receiver=self.get_user_object(), sender=self.request.user), Q.OR)

        elif self.request.user.role.role == 'user':
            filtering_condition = Q(receiver=self.request.user, sender=self.get_manager_object())
            filtering_condition.add(Q(receiver=self.get_manager_object(), sender=self.request.user), Q.OR)

        queryset = Message.objects \
            .filter(filtering_condition).order_by('created_at')
        return self.paginate_queryset(queryset)

    def get_manager_object(self):
        try:
            return User.objects.get(pk=self.kwargs.get(self.lookup_field), role__role__in=['manager', 'admin'])
        except User.DoesNotExist:
            raise ValidationError({'detail': _('Менеджера не існує.')})

    def get_user_object(self):
        try:
            return User.objects.get(pk=self.kwargs.get(self.lookup_field), role__role='user')
        except User.DoesNotExist:
            raise ValidationError({'detail': _('Користувача не існує.')})

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.get_queryset(), many=True)
        return self.get_paginated_response(serializer.data)

    def get_message(self):
        try:
            return Message.objects.get(pk=self.kwargs.get(self.lookup_field),
                                       sender=self.request.user)
        except Message.DoesNotExist:
            raise ValidationError({'detail': _('Вказаного повідомлення не існує або ви не маєте права його видалити.')})

    @action(methods=['POST'], detail=True, url_path='send')
    def send_to_manager(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'sender': request.user,
                                                                     'receiver': self.get_manager_object()})
        if serializer.is_valid():
            serializer.save()
            return Response(data={'detail': _('Повідомлення успішно надіслано.')}, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['POST'], detail=True, url_path='manager/send')
    def send_to_user(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'sender': request.user,
                                                                     'receiver': self.get_user_object()})
        if serializer.is_valid():
            serializer.save()
            return Response(data={'detail': _('Повідомлення успішно надіслано.')}, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['DELETE'], detail=True, url_path='delete')
    def delete_message(self, request, *args, **kwargs):
        obj = self.get_message()
        obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
