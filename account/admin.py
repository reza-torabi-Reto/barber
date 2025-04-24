from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, ManagerProfile, BarberProfile, CustomerProfile

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'role', 'phone', 'email', 'is_staff')
    list_filter = ('role', 'is_staff')
    search_fields = ('username', 'phone', 'email')
    ordering = ('username',)

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('اطلاعات شخصی', {'fields': ('first_name', 'last_name', 'email', 'phone')}),
        ('نقش و دسترسی‌ها', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('تاریخ‌ها', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'role', 'phone', 'email'),
        }),
    )

class ManagerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'bio', 'has_avatar')
    list_filter = ('user__role',)
    search_fields = ('user__username', 'bio')

    def has_avatar(self, obj):
        return bool(obj.avatar)
    has_avatar.boolean = True
    has_avatar.short_description = 'آواتار دارد؟'

class BarberProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'shop', 'bio', 'has_avatar')
    list_filter = ('user__role', 'shop')
    search_fields = ('user__username', 'bio')

    def has_avatar(self, obj):
        return bool(obj.avatar)
    has_avatar.boolean = True
    has_avatar.short_description = 'آواتار دارد؟'

class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone')
    list_filter = ('user__role',)
    search_fields = ('user__username', 'user__phone')

    def phone(self, obj):
        return obj.user.phone
    phone.short_description = 'شماره تماس'

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(ManagerProfile, ManagerProfileAdmin)
admin.site.register(BarberProfile, BarberProfileAdmin)
admin.site.register(CustomerProfile, CustomerProfileAdmin)