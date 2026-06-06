from django.urls import path
from api.v1.views.account import *
from api.v1.views.salon import *
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from rest_framework.routers import DefaultRouter
router = DefaultRouter()

router.register(r'shop/services', ServiceViewSet, basename='service')##
urlpatterns = [
    #================ 
    # ACCOUNT
    #================
    #=== core Views ===
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    #=== Views ===
    path('signup/<str:role>/send-otp/', SendOTPView.as_view()),##
    path('signup/verify-otp/', VerifyOTPView.as_view()),##
    path('signup/complete/', CompleteSignupView.as_view()),##
    path('login/', CustomTokenObtainPairView.as_view(), name='api_login'),##
    path("auth/is-auth/", IsAuthView.as_view(), name="is_auth"),##
    path("auth/me/", MeView.as_view(), name="auth_me"),##
    path('auth/force-change-password/',ForceChangePasswordView.as_view(),name='force-change-password'),##
    path('barber/self-assign/', SelfAssignBarberView.as_view(), name='self_assign_barber'),##
    path('barber/self/leave/', SelfLeaveBarber.as_view(), name='self_leave_barber'),
    path('barber/invite/', InviteBarberView.as_view(), name='invite_barber'),##
    path('barber/<int:barber_id>/remove/', RemoveBarberFromShopView.as_view(), name='remove_barber'),##
    path('shops/<int:shop_id>/barber-schedule/<int:barber_id>/', BarberScheduleAPIView.as_view(), name='api_barber_schedule'),##

    #================ 
    # SALON
    #================
    path('manager/profile/change-password/', ChangePasswordView.as_view(), name='change-password'),##
    path('appointments/bulk-update/', bulk_update_appointments, name='appointments-bulk-update'),##
    path("manager/appointment/<int:pk>/change-status/",change_appointment_status, name="change_appointment_status"),
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
    path("shop/provinces/", ProvinceListView.as_view(), name="province-list"),##
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
