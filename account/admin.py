# account/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import UserProfile, Manager, Barber, Customer

# ادمین برای UserProfile (نمایش همه کاربران)
@admin.register(UserProfile)
class UserProfileAdmin(UserAdmin):
    list_display = ('username', 'phone', 'role', 'status', 'is_active')
    list_filter = ('role', 'status', 'is_active')
    search_fields = ('username', 'phone')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('اطلاعات شخصی', {'fields': ('nickname', 'phone', 'email', 'avatar', 'about')}),
        ('نقش و وضعیت', {'fields': ('role', 'status', 'shop')}),
        ('دسترسی‌ها', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )

# ادمین برای Manager
@admin.register(Manager)
class ManagerAdmin(UserProfileAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(role='manager')

    def save_model(self, request, obj, form, change):
        obj.role = 'manager'
        super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['role'].disabled = True  # غیرفعال کردن فیلد role
        return form

# ادمین برای Barber
@admin.register(Barber)
class BarberAdmin(UserProfileAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(role='barber')

    def save_model(self, request, obj, form, change):
        obj.role = 'barber'
        super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['role'].disabled = True  # غیرفعال کردن فیلد role
        return form

# ادمین برای Customer
@admin.register(Customer)
class CustomerAdmin(UserProfileAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(role='customer')

    def save_model(self, request, obj, form, change):
        obj.role = 'customer'
        super().save_model(request, obj, form, change)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['role'].disabled = True  # غیرفعال کردن فیلد role
        return form