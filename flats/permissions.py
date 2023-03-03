from rest_framework.permissions import BasePermission, IsAuthenticated

from django.utils.translation import gettext_lazy as _

from flats.models import ResidentialComplex


class CustomIsAuthenticated(IsAuthenticated):
    message = _('You do not have permission.')

    def has_permission(self, request, view):
        print('customer autheticated')
        return super().has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        print('customed isauthenticated object')
        return super().has_object_permission(request, view, obj)


class IsBuilderPermission(BasePermission):
    message = _('You do not have permission.')

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role.role == 'builder'

    def has_object_permission(self, request, view, obj):
        print('inside obj builder perm')
        if isinstance(obj, ResidentialComplex):
            return request.user == obj.owner
        return True


class IsAdminPermission(BasePermission):
    message = _('You do not have permission.')

    def has_permission(self, request, view):
        print('admin_permission')
        return request.user.is_authenticated and request.user.role.role == 'admin'


class IsManagerPermission(BasePermission):
    message = _('You do not have permission.')

    def has_permission(self, request, view):
        print('manager_permission')
        return request.user.is_authenticated and request.user.role.role == 'manager'


class IsOwnerPermission(BasePermission):
    message = _('You do not have permission.')

    def has_object_permission(self, request, view, obj):
        return request.user == obj.owner
