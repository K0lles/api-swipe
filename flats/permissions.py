from rest_framework.permissions import BasePermission


class IsBuilderPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role.role == 'builder'

    def has_object_permission(self, request, view, obj):
        print('inside obj builder perm')
        return True


class IsAdminPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role.role == 'admin'


class IsManagerPermission(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role.role == 'manager'


class IsOwnerPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user == obj.owner
