# from django.contrib.auth import logout
from django.shortcuts import redirect
from functools import wraps

def role_required(allowed_roles):
    """
    دکوراتور برای بررسی نقش کاربر.
    مثال استفاده:
    @role_required(['manager', 'barber'])
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated and request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            # logout(request)
            return redirect('home')  # یا به صفحه 'login' ریدایرکت کنید
        return _wrapped_view
    return decorator