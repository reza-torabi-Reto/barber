# account/urls.py
from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from .views import *

app_name = 'account'
urlpatterns = [
    path('signup/manager/', manager_signup, name='manager_signup'),
    path('signup/customer/', customer_signup, name='customer_signup'),
    path('login/', LoginView.as_view(template_name='account/login.html'), name='login'),  # اضافه کردن URL ورود
    path('profile-manager/', profile_manager, name='profile_manager'),  # URL پروفایل
    path('customer-profile/', customer_profile, name='customer_profile'),
    path('customer-profile/', customer_profile, name='customer_profile'),
    path('join-shop/<int:shop_id>/', join_shop, name='join_shop'),
    path('leave-shop/<int:shop_id>/', leave_shop, name='leave_shop'),
    
    path('logout/', LogoutView.as_view(next_page='account:login'), name='logout'),  # ویوی خروج
    path('error/', error, name='error'),
]