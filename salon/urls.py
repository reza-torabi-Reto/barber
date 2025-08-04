# salon/urls.py
from django.urls import path
from . import views

app_name = 'salon'

urlpatterns = [
    path('create/', views.create_shop, name='create_shop'),
    # path('create-barber/<int:shop_id>/', views.create_barber, name='create_barber'),
    path('create-service/<int:shop_id>/', views.create_service, name='create_service'),
    
    path('shop-manage/<int:shop_id>/', views.manage_shop, name='manage_shop'),
    path('shop-edit/<int:shop_id>/', views.edit_shop, name='edit_shop'),
    path('<int:shop_id>/barber-delete/<int:barber_id>/', views.delete_barber, name='delete_barber'),
    path('<int:shop_id>/service-delete/<int:service_id>/', views.delete_service, name='delete_service'),
    path('<int:shop_id>/service-edit/<int:service_id>/', views.edit_service, name='edit_service'),
    path('shop-manage-schedule/<int:shop_id>/', views.manage_schedule, name='manage_schedule'),
    path('<int:shop_id>/barber-schedule/', views.manage_barber_schedule, name='manage_barber_schedule'),
    path('get-shop-details/', views.get_shop_details, name='get_shop_details'),
    path('<int:shop_id>/manager-appointments/', views.manager_appointments, name='manager_appointments'),
    path('<int:shop_id>/manager-appointments-days/', views.manager_appointments_days, name='manager_appointments_days'),
    path('customer-appointments/', views.customer_appointments, name='customer_appointments'),
    path('<int:shop_id>/customer-appointments/', views.shop_customer_appointments, name='shop_customer_appointments'),
    path('<int:shop_id>/barber-appointments/', views.barber_appointments, name='barber_appointments'),
    path('<int:shop_id>/book-appointment/', views.book_appointment, name='book_appointment'),
    # path('select-date-time/', views.select_date_time, name='select_date_time'),
    path('select-date-time-barber/', views.select_date_time_barber, name='select_date_time_barber'),
    path('get-available-times/', views.get_available_times, name='get_available_times'),
    path('confirm-appointment/', views.confirm_appointment, name='confirm_appointment'),
    path('detail/<int:shop_id>/', views.shop_detail, name='shop_detail'),
    path('appointment-detail-manager/<int:id>/', views.appointment_detail_manager, name='appointment_detail_manager'),
    path('appointment-detail-customer/<int:id>/', views.appointment_detail_customer, name='appointment_detail_customer'),
    path('appointment-detail-barber/<int:id>/', views.appointment_detail_barber, name='appointment_detail_barber'),
    path('complete-appointment-confirm/<int:id>/', views.complete_appointment_confirm, name='complete_appointment_confirm'),
    path('notifications/unread/', views.get_unread_notifications, name='get_unread_notifications'),
    path('notifications/mark-read/', views.mark_as_read, name='mark_notification_read'),
    #-------
# Shop URLs
# path('shops/create/', views.create_shop, name='create_shop'),
# path('shops/<int:shop_id>/', views.manage_shop, name='manage_shop'),
# path('shops/<int:shop_id>/edit/', views.edit_shop, name='edit_shop'),
# path('shops/<int:shop_id>/detail/', views.shop_detail, name='shop_detail'),

# # Barber URLs
# path('shops/<int:shop_id>/barbers/create/', views.create_barber, name='create_barber'),
# path('shops/<int:shop_id>/barbers/<int:barber_id>/delete/', views.delete_barber, name='delete_barber'),

# # Service URLs
# path('shops/<int:shop_id>/services/create/', views.create_service, name='create_service'),
# path('shops/<int:shop_id>/services/<int:service_id>/edit/', views.edit_service, name='edit_service'),
# path('shops/<int:shop_id>/services/<int:service_id>/delete/', views.delete_service, name='delete_service'),

# # Schedule URLs
# path('shops/<int:shop_id>/schedule/', views.manage_schedule, name='manage_schedule'),
# path('shops/<int:shop_id>/barbers/<int:barber_id>/schedule/', views.manage_barber_schedule, name='manage_barber_schedule'),

# # Appointment URLs
# path('shops/<int:shop_id>/appointments/manager/', views.manager_appointments, name='manager_appointments'),
# path('shops/<int:shop_id>/appointments/manager/days/', views.manager_appointments_days, name='manager_appointments_days'),
# path('shops/<int:shop_id>/appointments/customer/', views.shop_customer_appointments, name='shop_customer_appointments'),
# path('shops/<int:shop_id>/barbers/<int:barber_id>/appointments/', views.barber_appointments, name='barber_appointments'),
# path('shops/<int:shop_id>/appointments/book/', views.book_appointment, name='book_appointment'),
# path('appointments/customer/', views.customer_appointments, name='customer_appointments'),
# path('appointments/<int:appointment_id>/manager/', views.appointment_detail_manager, name='appointment_detail_manager'),
# path('appointments/<int:appointment_id>/customer/', views.appointment_detail_customer, name='appointment_detail_customer'),
# path('appointments/<int:appointment_id>/complete/', views.complete_appointment_confirm, name='complete_appointment_confirm'),

# # Booking process
# path('booking/select-date-time/', views.select_date_time, name='select_date_time'),
# path('booking/select-date-time-barber/', views.select_date_time_barber, name='select_date_time_barber'),
# path('booking/available-times/', views.get_available_times, name='get_available_times'),
# path('booking/confirm/', views.confirm_appointment, name='confirm_appointment'),

# # Shop details (API)
# path('api/shop-details/', views.get_shop_details, name='get_shop_details'),

# # Notifications
# path('notifications/unread/', views.get_unread_notifications, name='get_unread_notifications'),
# path('notifications/mark-read/', views.mark_as_read, name='mark_notification_read'),

]