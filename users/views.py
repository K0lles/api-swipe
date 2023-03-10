from django.views.generic.base import TemplateResponseMixin, View
from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.generics import ListCreateAPIView, DestroyAPIView
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated

from drf_spectacular.utils import extend_schema

from drf_psq import PsqMixin, Rule

from .models import User
from .serializers import UserSerializer, UserAdminSerializer
from flats.permissions import IsAdminPermission, IsManagerPermission


class ConfirmationCongratulationView(TemplateResponseMixin, View):
    template_name = 'account/email/congratulations.html'

    def get(self, request, *args, **kwargs):
        return self.render_to_response({})


class UserAPIViewSet(PsqMixin,
                     ListCreateAPIView,
                     DestroyAPIView,
                     GenericViewSet):

    serializer_class = UserSerializer
    permission_classes = [IsAdminPermission]

    psq_rules = {
        ('list', 'block'): [Rule([IsManagerPermission | IsAdminPermission], UserAdminSerializer)],
        ('retrieve_self', 'delete_own_account', 'partial_update_self'): [Rule([IsAuthenticated], UserSerializer)],
        'create': [Rule([IsAdminPermission], UserAdminSerializer)]
    }

    def get_queryset(self):
        return User.objects.all()

    def get_object(self, *args, **kwargs):
        try:
            return User.objects.get(pk=self.kwargs.get('pk'))
        except User.DoesNotExist:
            raise ValidationError({'detail': _('Такого користувача не існує.')})

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

    @extend_schema(tags=['update-yourself-account'])
    @action(methods=['PUT'], detail=False, url_path='me/update', url_name='partial-update-user')
    def partial_update_self(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, instance=self.request.user, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(tags=['delete-user'])
    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
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
        user.delete()
        try:
            response = Response(data={'detail': _('Your account successfully deleted')}, status=status.HTTP_200_OK)
            response.delete_cookie('access_token')
            response.delete_cookie('refresh_token')
        except Exception as e:
            return Response(data={'detail': _('Щось пішло не так.')}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return response
