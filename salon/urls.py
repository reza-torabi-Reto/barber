# salon/urls.py
from django.urls import path
from . import views

app_name = 'salon'

urlpatterns = [
    path('create/', views.create_shop, name='create_shop'),
    # path('list/', views.shop_list, name='shop_list'),
    path('shop/barber/<int:shop_id>', views.create_barber, name='create_barber'),
    path('shop/barbers/<int:shop_id>', views.list_barber, name='list_barber'),
    path('shop/create-service/<int:shop_id>', views.create_service, name='create_service'),
    path('shop/services/<int:shop_id>', views.service_list, name='service_list'),
    path('shop/<int:shop_id>/manage/', views.manage_shop, name='manage_shop'),
    path('shop/<int:shop_id>/delete-barber/<int:barber_id>/', views.delete_barber, name='delete_barber'),
    path('shop/<int:shop_id>/delete-service/<int:service_id>/', views.delete_service, name='delete_service'),
    path('shop/<int:shop_id>/edit-service/<int:service_id>/', views.edit_service, name='edit_service'),
    path('shop/manage-schedule/<int:shop_id>/', views.manage_schedule, name='manage_schedule'),
    # path('book-appointment/', views.book_appointment, name='book_appointment'),
    path('get_shop_details/', views.get_shop_details, name='get_shop_details'),
    path('customer-appointments/', views.customer_appointments, name='customer_appointments'),
    path('barber-appointments/', views.barber_appointments, name='barber_appointments'),
    path('shop/<int:shop_id>/appointments/', views.manager_appointments, name='manager_appointments'),
    path('book-appointment/<int:shop_id>/', views.book_appointment, name='book_appointment'),
    path('get-shop-details/', views.get_shop_details, name='get_shop_details'),
    path('get-available-times/', views.get_available_times, name='get_available_times'),
]