from django.urls import path
from salon.api.api_views import *

urlpatterns = [
    path('create/', api_create_shop, name='api-create-shop'),
    path('manage/<int:shop_id>/', api_manage_shop, name='api-manage-shop'),
    path('edit/<int:shop_id>/', api_edit_shop, name='api-edit-shop'),
    
    path('<int:shop_id>/barber/create/', api_create_barber, name='api-create-barber'),
    path('<int:shop_id>/barber/delete/<int:barber_id>/', api_delete_barber, name='api-delete-barber'),
    
    path('<int:shop_id>/service/create/', api_create_service, name='api-create-service'),
    path('<int:shop_id>/service/edit/<int:service_id>/', api_edit_service, name='api-edit-service'),
    path('<int:shop_id>/service/delete/<int:service_id>/', api_delete_service, name='api-delete-service'),

]
