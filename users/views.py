from django.views.generic.base import TemplateResponseMixin, View
from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.generics import ListCreateAPIView
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated

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
                     GenericViewSet):

    serializer_class = UserSerializer
    permission_classes = [IsAdminPermission]

    psq_rules = {
        ('list', 'add_to_blacklist'): [Rule([IsManagerPermission | IsAdminPermission], UserAdminSerializer)],
        ('retrieve_self', 'delete_own_account', 'partial_update_self'): [Rule([IsAuthenticated], UserSerializer)],
        'create': [Rule([IsAdminPermission], UserAdminSerializer)]
    }

    def get_queryset(self):
        return User.objects.all()

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.get_queryset(), many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    @action(methods=['get'], detail=False, url_path='me', url_name='get-self')
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
        serializer = self.get_serializer(data=request.data, instance=self.request.user, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['POST'], url_name='block_user', url_path='block/<int:user_pk>/')
    def add_to_blacklist(self, request, *args, **kwargs):
        try:
            user = User.objects.select_related('role').get(pk=kwargs.get('user_pk'))
        except User.DoesNotExist:
            return Response(data={'detail': _('User does not exist')}, status=status.HTTP_400_BAD_REQUEST)
        if user.is_blocked:
            return Response(data={'detail': _('User is already blocked')}, status=status.HTTP_400_BAD_REQUEST)
        if user.role.role == 'admin':
            return Response(data={'detail': _('You cannot block admin')}, status=status.HTTP_403_FORBIDDEN)
        user.is_blocked = True
        user.save()
        return Response(data={'detail': _('User is successfully blocked')}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['DELETE'], url_path='me/delete', url_name='delete-own-account')
    def delete_own_account(self, request, *args, **kwargs):
        user = request.user
        user.delete()
        try:
            response = Response(data={'detail': _('Your account successfully deleted')}, status=status.HTTP_200_OK)
            response.delete_cookie('access_token')
            response.delete_cookie('refresh_token')
        except Exception as e:
            return Response(data={'detail': _('Something went wrong')}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return response
