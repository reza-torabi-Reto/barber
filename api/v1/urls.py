from django.urls import path
from api.v1.views.account import *
from api.v1.views.salon import *
from rest_framework_simplejwt.views import (
    TokenObtainPairView,   # login
    TokenRefreshView,      # refresh
    TokenVerifyView,       # verify
)


# api account:
urlpatterns = [
    path('signup/<str:role>/send-otp/', SendOTPView.as_view()),  # role = 'manager' یا 'customer'
    path("auth/is-auth/", IsAuthView.as_view(), name="is_auth"),
    path('signup/verify-otp/', VerifyOTPView.as_view()),
    path('signup/complete/', CompleteSignupView.as_view()),

    path('login/', CustomTokenObtainPairView.as_view(), name='api_login'),
    path('force-password-change/', api_force_password_change, name='api_force_password_change'),

    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    #for web
    path('manager/profile/', ManagerProfileView.as_view(), name='api_manager_profile'),
    #for mobile
    path('manager/profile/api/', ManagerProfileApi.as_view(), name='api_manager_profile'),
    path('manager/profile/edit/', EditManagerProfileView.as_view(), name='api_edit_manager_profile'),

    path('shops/<int:shop_id>/invite-barber/', CreateBarberOTPApi.as_view(), name='api_invite-barber'),


    path('shops/<int:shop_id>/barbers/<int:barber_id>/toggle-status/', toggle_barber_status_api, name='api_toggle_barber_status'),
    path('shops/<int:shop_id>/barbers/<int:barber_id>/delete/', delete_barber_api, name='api_delete_barberi'),

    path('barber/profile/', BarberProfileAPIView.as_view(), name='api_barber_profile'),
    path('barber/profile/edit/', EditBarberProfileAPIView.as_view(), name='api_edit_barber_profile'),

    path('customer/profile/', CustomerProfileAPIView.as_view(), name='api_customer-profile'),
    path('customer/profile/edit/', EditCustomerProfileAPIView.as_view(), name='api_edit-customer-profile'),

    path('manager/shops/<int:shop_id>/customers/', CustomerListAPIView.as_view(), name='api_customer_list'),
    path('manager/shops/<int:shop_id>/customers/<int:customer_id>/toggle-status/', ToggleCustomerStatusAPIView.as_view(), name='api_toggle_customer_status'),
]

# api salon:
urlpatterns += [
    path('shops/create/', CreateShopAPIView.as_view(), name='api_create_shop'),
    path('shops/<int:shop_id>/dashboard/', DashboardShopAPIView.as_view(), name='api_dashboard_shop'),
    path('shops/<int:shop_id>/edit/', ShopEditAPIView.as_view(), name='api_shop_edit'),
    
    path('shops/<int:shop_id>/barber-schedule/<int:barber_id>/', BarberScheduleAPIView.as_view(), name='api_barber_schedule'),
    
    path('shops/<int:shop_id>/services/', ServiceListCreateAPIView.as_view(), name='api_service_list_create'),
    path('shops/<int:shop_id>/services/<int:service_id>/', ServiceDetailAPIView.as_view(), name='api_service_detail'),

    path('customer/shops/<int:shop_id>/join/', JoinShopAPIView.as_view(), name='api_customer-join-shop'),
    path('customer/shops/<int:shop_id>/leave/', LeaveShopAPIView.as_view(), name='api_customer-leave-shop'),
    path('customer/shops/<int:shop_id>/', ShopDashboardCustomerAPIView.as_view(), name='api_customer-shop-dashboard'),

    path('appointment/<int:shop_id>/barbers/', BookAppointmentAPIView.as_view(), name='api_book_appointment'),
    path('appointment/select-date/', SelectDateTimeAPIView.as_view(), name='api_select_date'),
    path('appointment/available-times/', GetAvailableTimesAPIView.as_view(), name='api_get_available_times'),
    path('appointment/confirm/', ConfirmAppointmentAPIView.as_view(), name='api_appointment_confirm'),

    path('customer/appointments/', CustomerAppointmentsAPIView.as_view(), name='api_customer_appointments'),
    path('customer/appointments/<int:shop_id>/', ShopCustomerAppointmentsAPIView.as_view(), name='api_customer_appointments_shop'),
    path('customer/appointment/<int:id>/detail/', AppointmentDetailCustomerAPIView.as_view(), name='api_customer_appointment_detail'),
    
    path('manager/appointments/', manager_appointments_api, name='manager_appointments_api'),
    path('manager-appointment/<int:id>/', api_appointment_detail_manager, name='api_appointment_detail_manager'),
 
    # ReactNative API:
    path("notifications/has_unread/",has_unread_notifications, name="has_unread_notifications"),
    path("notifications/unread/",get_unread_notifications, name="get_unread_notifications"),
    
    path("get-salons/manager/",get_salons_manager, name="get_salons_manager"),
    
    path("show-salons/manager/",show_salons_manager, name="show_salons_manager"),
    
    path("set-active-salon/manager/<int:shop_id>/",set_active_salon, name="set_active_salon"),
    path("get-active-salon/manager/",get_active_salon, name="get_active_salon"),
    path("get-customers-active-salon/manager/",get_customers_of_active_salon_manager, name="get_customers_of_active_salon_manager"),
]