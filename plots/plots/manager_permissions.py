from rest_framework.permissions import BasePermission


class IsManager(BasePermission):
    """Allow Urban Nest managers and Django superusers."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or hasattr(user, "manager_profile"))
        )


class IsMainManager(BasePermission):
    """Allow only the explicitly designated main manager or a superuser."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_superuser or getattr(getattr(user, "manager_profile", None), "is_main", False))
        )
