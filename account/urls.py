# account/urls.py
from django.urls import path
from django.contrib.auth.views import LogoutView, PasswordResetView,PasswordResetDoneView,PasswordResetConfirmView,PasswordResetCompleteView
from .views import *

app_name = 'account'
urlpatterns = [
    path('logout/', LogoutView.as_view(next_page='account:login'), name='logout'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('change-password/', CustomPasswordChangeView.as_view(), name='change_password'),
    path('change-password/done/', CustomPasswordChangeDoneView.as_view(), name='change_password_done'),

    path('password-reset/', PasswordResetView.as_view(
        template_name='account/password_reset_form.html',
        email_template_name='account/password_reset_email.html',
        subject_template_name='account/password_reset_subject.txt',
        success_url='done/',
    ), name='password_reset'),

    # نمایش پیام ارسال ایمیل موفق
    path('password-reset/done/', PasswordResetDoneView.as_view(
        template_name='account/password_reset_done.html'
    ), name='password_reset_done'),

    # فرم وارد کردن رمز جدید
    path('reset/<uidb64>/<token>/', PasswordResetConfirmView.as_view(
        template_name='account/password_reset_confirm.html',
        success_url='/account/reset/done/'
    ), name='password_reset_confirm'),

    # پیام موفقیت نهایی
    path('reset/done/', PasswordResetCompleteView.as_view(
        template_name='account/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    path('signup/manager/', manager_signup, name='manager_signup'),
    path('signup/customer/', customer_signup, name='customer_signup'),

    path('manager-profile/', profile, name='profile'),  # URL پروفایل
    path('edit-profile/', edit_manager_profile, name='edit_manager_profile'),
    path('barber-profile/', barber_profile, name='barber_profile'),
    path('edit-barber-profile/', edit_barber_profile, name='edit_barber_profile'),
    path('barber/<int:barber_id>/toggle/<int:shop_id>/', toggle_barber_status, name='toggle_barber_status'),
    path('customers/<int:shop_id>/', customer_list, name='customer_list'),
    path('customer-profile/', customer_profile, name='customer_profile'),
    path('edit-customer-profile/', edit_customer_profile, name='edit_customer_profile'),
    path('customer/toggle/<int:customer_id>/<int:shop_id>/', toggle_customer_status, name='toggle_customer_status'),

    path('join-shop/<int:shop_id>/', join_shop, name='join_shop'),
    path('leave-shop/<int:shop_id>/', leave_shop, name='leave_shop'),

]

# API Urls:
from .api.api_views import CustomLoginAPIView, LogoutAPIView, ManagerSignupAPIView, ManagerProfileAPIView,update_manager_profile

urlpatterns += [
    path('api/token/', CustomLoginAPIView.as_view(), name='api-token-obtain'),
    path('api/logout/', LogoutAPIView.as_view(), name='api-logout'),
    path('api/signup/manager/', ManagerSignupAPIView.as_view(), name='api-manager-signup'),
    path('api/manager/profile/', ManagerProfileAPIView.as_view(), name='manager-profile-api'),
    path('api/update/manager/profile/', update_manager_profile, name='manager-profile-update'),

]
