from django.contrib import admin
from .models import Shop, Service, CustomerShop, Appointment, Province, City, District

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


class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('customer', 'shop', 'barber', 'start_time', 'end_time', 'status')
    # list_filter = ('shop',)
    # search_fields = ('customer__username', 'shop__name')
    # ordering = ('joined_at',)


class ProvinceAdmin(admin.ModelAdmin):
    list_display = ('id','name',)
    search_fields = ('name',)

class CityAdmin(admin.ModelAdmin):
    list_display = ('id','name','province')
    search_fields = ('name',)
    
class DistrictAdmin(admin.ModelAdmin):
    list_display = ('id','name', 'city')
    search_fields = ('name',)

admin.site.register(Shop, ShopAdmin)
admin.site.register(Service, ServiceAdmin)
admin.site.register(CustomerShop, CustomerShopAdmin)
admin.site.register(Appointment, AppointmentAdmin)

admin.site.register(Province, ProvinceAdmin)
admin.site.register(City, CityAdmin)
admin.site.register(District, DistrictAdmin)