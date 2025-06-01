from django.urls import path
from salon.api.api_views import create_shop

urlpatterns = [
    path('create/', create_shop, name='create-shop'),
]
