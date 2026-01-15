# permissions.py
from rest_framework.permissions import BasePermission,SAFE_METHODS


class IsManager(BasePermission):
    message = "شما دسترسی مدیر را ندارید."

    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == "manager"
        )


class ForcePasswordChangePermission(BasePermission):
    """
    اگر کاربر must_change_password=True باشد
    فقط اجازه دسترسی به endpoint تغییر رمز را دارد
    """

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if not user.must_change_password:
            return True

        allowed_views = [
            "CustomTokenObtainPairView",
            "ForceChangePasswordView",
        ]

        return view.__class__.__name__ in allowed_views
