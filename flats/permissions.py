from rest_framework.permissions import BasePermission, IsAuthenticated

from django.utils.translation import gettext_lazy as _

from flats.models import ResidentialComplex, Flat, Section, Floor, Corps


class CustomIsAuthenticated(IsAuthenticated):
    message = _('You do not have permission.')

    def has_permission(self, request, view):
        return super().has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        return super().has_object_permission(request, view, obj)


class IsBuilderPermission(BasePermission):
    message = _('You do not have permission.')

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role.role == 'builder'

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, ResidentialComplex):
            return request.user == obj.owner
        return True


class IsAdminPermission(BasePermission):
    message = _('You do not have permission.')

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role.role == 'admin'


class IsManagerPermission(BasePermission):
    message = _('You do not have permission.')

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role.role == 'manager'


class IsOwnerPermission(BasePermission):
    message = _('You do not have permission.')

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, ResidentialComplex):
            return request.user == obj.owner
        elif isinstance(obj, (Flat, Section, Floor, Corps)):
            return request.user == obj.residential_complex.owner


class IsUserPermission(BasePermission):
    message = _('You do not have permission.')

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role.role == 'user'
