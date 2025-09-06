# from django.contrib.auth import logout
from django.shortcuts import redirect
from functools import wraps
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied

# for Views
def role_required(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated and request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            # logout(request)
            return redirect('home')  # یا به صفحه 'login' ریدایرکت کنید
        return _wrapped_view
    return decorator
# for API

class RoleRequired(BasePermission):
    def has_permission(self, request, view):
        allowed_roles = getattr(view, 'allowed_roles', [])

        if not request.user.is_authenticated:
            return False

        if request.user.role in allowed_roles:
            return True

        roles_str = "، ".join(allowed_roles) if allowed_roles else "مجاز"
        raise PermissionDenied(f"فقط کاربران با نقش‌های {roles_str} دسترسی دارند")
