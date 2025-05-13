from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminOrAuthenticated(BasePermission):
    """
    Allows access to admin users or authenticated users.
    """
    def has_permission(self, request, view):
        return request.user and (request.user.is_authenticated or request.user.is_staff)
