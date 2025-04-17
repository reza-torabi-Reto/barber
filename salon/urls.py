# salon/urls.py
from django.urls import path
from . import views

app_name = 'salon'

urlpatterns = [
    path('create/', views.create_shop, name='create_shop'),
    path('list/', views.shop_list, name='shop_list'),
    path('barber/<int:shop_id>', views.create_barber, name='create_barber'),
    path('barbers/<int:shop_id>', views.barber_list, name='barber_list'),
    path('create-service/<int:shop_id>', views.create_service, name='create_service'),
    path('services/<int:shop_id>', views.service_list, name='service_list'),
#     
]