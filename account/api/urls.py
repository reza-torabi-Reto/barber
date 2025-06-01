
from django.urls import path
from .api_views import CustomLoginAPIView, LogoutAPIView, ManagerSignupAPIView, ManagerProfileAPIView,update_manager_profile

urlpatterns = [
    path('token/', CustomLoginAPIView.as_view(), name='api-token-obtain'),
    path('logout/', LogoutAPIView.as_view(), name='api-logout'),
    path('manager/signup/', ManagerSignupAPIView.as_view(), name='api-manager-signup'),
    path('manager/profile/', ManagerProfileAPIView.as_view(), name='api-manager-profile'),
    path('managerprofile/update/', update_manager_profile, name='api-manager-profile-update'),

]