from django.views.generic.base import TemplateResponseMixin, View
from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated

from drf_psq import PsqMixin, Rule, psq

from .models import User
from .serializers import UserSerializer, UserAdminSerializer
from flats.permissions import IsAdminPermission, IsManagerPermission


class ConfirmationCongratulationView(TemplateResponseMixin, View):
    template_name = 'account/email/congratulations.html'

    def get(self, request, *args, **kwargs):
        return self.render_to_response({})


class UserAPIViewSet(PsqMixin, ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    psq_rules = {
        ('list', 'add_to_blacklist'): [Rule([IsManagerPermission | IsAdminPermission], UserAdminSerializer)],
        ('retrieve', 'update', 'delete_own_account'): [Rule([IsAuthenticated])],
        'create': [Rule([IsAdminPermission], UserAdminSerializer)]
    }

    def get_queryset(self):
        return User.objects.all()

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.get_queryset(), many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=request.user)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        print(self.serializer_class)
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_201_CREATED)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, instance=request.user)
        if serializer.is_valid():
            serializer.save()
            return Response(data=serializer.data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # def destroy(self, request, *args, **kwargs):
    #     user_to_destroy = request.user
    #     try:
    #         user_to_destroy.delete()
    #         response = Response(data={'detail': _('User successfully deleted')}, status=status.HTTP_200_OK)
    #         response.delete_cookie('access_token')
    #         response.delete_cookie('refresh_token')
    #         return response
    #     except Exception as e:
    #         return Response(data={'detail': _('Something failed')}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['POST'], url_name='block_user', url_path='block/<int:user_pk>/')
    def add_to_blacklist(self, request, *args, **kwargs):
        try:
            user = User.objects.get(pk=kwargs.get('user_pk'))
        except User.DoesNotExist:
            return Response(data={'detail': _('User does not exist')}, status=status.HTTP_400_BAD_REQUEST)
        if user.is_blocked:
            return Response(data={'detail': _('User is already blocked')}, status=status.HTTP_400_BAD_REQUEST)
        user.is_blocked = True
        user.save()
        return Response(data={'detail': _('User is successfully blocked')}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['delete'], url_path='me', url_name='delete-own-account')
    def delete_own_account(self, request, *args, **kwargs):
        print(request.user)
        print('inside deletion')
        user = request.user
        user.delete()
        try:
            response = Response(data={'detail': _('Your account successfully deleted')}, status=status.HTTP_200_OK)
            response.delete_cookie('access_token')
            response.delete_cookie('refresh_token')
        except Exception as e:
            print(e)
            return Response(data={'detail': _('Something went wrong')}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return response
