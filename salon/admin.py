from django.contrib import admin
from .models import Shop, Service, CustomerShop

class ShopAdmin(admin.ModelAdmin):
    list_display = ('name', 'referral_code', 'manager', 'status')
    list_filter = ('status',)
    search_fields = ('name', 'referral_code', 'manager__username')
    ordering = ('name',)

class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'shop', 'duration', 'price')
    list_filter = ('shop',)
    search_fields = ('name', 'shop__name')
    ordering = ('shop', 'name')

class CustomerShopAdmin(admin.ModelAdmin):
    list_display = ('customer', 'shop', 'joined_at')
    list_filter = ('shop',)
    search_fields = ('customer__username', 'shop__name')
    ordering = ('joined_at',)

admin.site.register(Shop, ShopAdmin)
admin.site.register(Service, ServiceAdmin)
admin.site.register(CustomerShop, CustomerShopAdmin)