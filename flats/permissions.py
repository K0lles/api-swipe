from rest_framework.permissions import BasePermission, IsAuthenticated

from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ObjectDoesNotExist

from flats.models import ResidentialComplex, Flat, Section, Floor, Corps, Document, ChessBoardFlat, AdditionInComplex, \
    Photo, ChessBoard, Favorite
from users.models import SavedFilter


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


class IsAdminPermission(BasePermission):
    message = _('You do not have permission.')

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role.role == 'admin'

    def has_object_permission(self, request, view, obj):
        return True


class IsManagerPermission(BasePermission):
    message = _('You do not have permission.')

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role.role == 'manager'

    def has_object_permission(self, request, view, obj):
        return True


class IsOwnerPermission(BasePermission):
    message = _('You do not have permission.')

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, ResidentialComplex):
            return request.user == obj.owner
        elif isinstance(obj, (AdditionInComplex, Flat, Section, Floor, Corps, Document, ChessBoardFlat, ChessBoard)):
            return request.user == obj.residential_complex.owner
        elif isinstance(obj, (SavedFilter, Favorite)):
            return request.user == obj.user

        return False


class IsCreatorPermission(BasePermission):
    message = _('You do not have permission.')

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, ChessBoardFlat):
            return request.user == obj.creator
        return False


class IsUserPermission(BasePermission):
    message = _('You do not have permission.')

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role.role == 'user'


class IsResidentialComplexOrFlatPhotoOwner(BasePermission):
    message = _('You do not have permission.')

    def has_object_permission(self, request, view, obj: Photo):
        try:
            return request.user == obj.gallery.residentialcomplex.owner
        except ObjectDoesNotExist:
            pass

        try:
            return request.user == obj.gallery.flat.residential_complex.owner
        except ObjectDoesNotExist:
            return False


class IsChessBoardFlatPhotoOwner(BasePermission):
    message = _('You do not have permission.')

    def has_object_permission(self, request, view, obj: Photo):
        return request.user == obj.gallery.chessboardflat.creator \
            or request.user == obj.gallery.chessboardflat.residential_complex.owner
