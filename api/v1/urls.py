from django.urls import path
from api.v1.views.account import *
from api.v1.views.salon import *
from rest_framework_simplejwt.views import (
    TokenObtainPairView,   # login
    TokenRefreshView,      # refresh
    TokenVerifyView,       # verify
)
from rest_framework.routers import DefaultRouter
router = DefaultRouter()

urlpatterns = [
    path("notifications/unread/",get_unread_notifications, name="get_unread_notifications"),    
    path("get-active-salon/manager/",get_active_salon, name="get_active_salon"),
    # path('manamanager/profile/change-password/ger/appointments/', manager_appointments_api, name='manager_appointments_api'),
    path("shop/provinces/", ProvinceListView.as_view(), name="province-list"),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('manager/profile/', ManagerProfileView.as_view(), name='manager_profile'),
    path('manager/profile/edit/', EditManagerProfileView.as_view(), name='edit_manager_profile'),
    path('shops/<int:shop_id>/invite-barber/', CreateBarberOTPApi.as_view(), name='api_invite-barber'),
    path('shops/<int:shop_id>/barbers/<int:barber_id>/toggle-status/', toggle_barber_status_api, name='api_toggle_barber_status'),
    path('shops/<int:shop_id>/barbers/<int:barber_id>/delete/', delete_barber_api, name='api_delete_barberi'),
    path('barber/profile/', BarberProfileAPIView.as_view(), name='api_barber_profile'),
    path('barber/profile/edit/', EditBarberProfileAPIView.as_view(), name='api_edit_barber_profile'),
    path('customer/profile/', CustomerProfileAPIView.as_view(), name='api_customer-profile'),
    path('customer/profile/edit/', EditCustomerProfileAPIView.as_view(), name='api_edit-customer-profile'),
    path('manager/shops/<int:shop_id>/customers/', CustomerListAPIView.as_view(), name='api_customer_list'),
    path('manager/shops/<int:shop_id>/customers/<int:customer_id>/toggle-status/', ToggleCustomerStatusAPIView.as_view(), name='api_toggle_customer_status'),
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
]
#-------------------------------------------------------
# Mobile Roots:
router.register(r'shop/services', ServiceViewSet, basename='service')##
urlpatterns += [
    # account:
    path('signup/<str:role>/send-otp/', SendOTPView.as_view()),##
    path('signup/verify-otp/', VerifyOTPView.as_view()),##
    path('signup/complete/', CompleteSignupView.as_view()),##
    path('barber/self-assign/', SelfAssignBarberView.as_view(), name='self_assign_barber'),##
    path('barber/self/leave/', SelfLeaveBarber.as_view(), name='self_leave_barber'),
    path('barber/invite/', InviteBarberView.as_view(), name='invite_barber'),##
    path('barber/<int:barber_id>/remove/', RemoveBarberFromShopView.as_view(), name='remove_barber'),##
    path('auth/force-change-password/',ForceChangePasswordView.as_view(),name='force-change-password'),##
    path('login/', CustomTokenObtainPairView.as_view(), name='api_login'),##
    path("auth/is-auth/", IsAuthView.as_view(), name="is_auth"),##
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),##
    path("auth/me/", MeView.as_view(), name="auth_me"),##
    # salon:
    path('manager/profile/change-password/', ChangePasswordView.as_view(), name='change-password'),##
    path('appointments/bulk-update/', bulk_update_appointments, name='appointments-bulk-update'),##
    path("notifications/has_unread/",has_unread_notifications, name="has_unread_notifications"),##    
    path("get-customers-active-salon/manager/",get_customers_of_active_salon_manager, name="get_customers_of_active_salon_manager"),##
    path('customers/bulk-update/', bulk_update_customers_status, name='bulk_update_customers_status'),##
    path('customer/<int:customer_id>/update-status/', update_customer_status, name='bulk_update_customer_status'),##
    path('manager/profile/api/', ManagerProfileApi.as_view(), name='api_manager_profile'),##
    path("manager/profile/update/", ManagerProfileUpdateApi.as_view(), name="manager_profile_update"),##
    path("manager/profile/avatar/update/", ManagerAvatarUpdateApi.as_view(), name="manager_avatar_update"),##
    path("shops/customers/<int:pk>/detail/", CustomerProfileDetailView.as_view(), name="customer-detail"),##
    path('manager/appointments/', manager_appointments_api, name='appointments'),##
    path('manager/appointment/<int:pk>/', AppointmentDetailAPIView.as_view(), name='appointment-detail'),##
    path('shop/barbers/modal/', manager_barbers_api, name='manager_barbers'),##
    path("shop/provinces/<int:province_id>/cities/", CityListView.as_view(), name="city-list"),##
    path("shop/create/", ShopCreateView.as_view(), name="shop_create"),##
    path('shop/has-active/', HasActiveSalonAPIView.as_view(),name='shop-has-active'), ##
    path('shop/summary/', ShopSummaryAPIView.as_view()),##
    path('shop/detail/', ShopDetailAPIView.as_view()),##
    path('shop/update/', ShopUpdateAPIView.as_view(), name='shop-update'),##
    path('shop/update-logo/', ShopLogoUpdateAPIView.as_view(), name='shop-update-logo'),##
    path('shop/update-image/', UpdateShopImage.as_view(), name='shop-update-image'),
    path('shop/details/', GetShopDetails.as_view(), name='shop-details'),##
    path('shop/barbers/', BarberListAPIView.as_view()),##
    path('shop/barbers/add-service/', BarberListAddServiceAPIView.as_view()),##
    path("manager/barber/<int:barber_id>/schedule/", BarberScheduleAPIView.as_view(), name="barber-schedule"),##
    path("manager/barber/<int:id>/detail/", BarberProfileDetailAPIView.as_view()),##
    path("manager/barber/<int:barber_id>/status/", BarberStatusUpdateAPIView.as_view(), name="barber-status-update"),##
    
] + router.urls
