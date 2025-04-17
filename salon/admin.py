from django.contrib import admin
from .models import *

admin.site.site_header = 'پنل مدیریت'

class ShopAdmin(admin.ModelAdmin):
	list_display = ('manager', 'referral_code','name','status')
	# list_filter = ('article__author', 'status')
	# search_fields = ('content',)
	# ordering = ['-status', '-created']


admin.site.register(Shop, ShopAdmin)

class CustomerShopAdmin(admin.ModelAdmin):
	list_display = ('customer', 'shop','joined_at')
	# list_filter = ('article__author', 'status')
	# search_fields = ('content',)
	# ordering = ['-status', '-created']


admin.site.register(CustomerShop, CustomerShopAdmin)
