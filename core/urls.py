from django.contrib import admin
from django.urls import path, include
from account.views import home

urlpatterns = [
    path('', home, name='home'), 
    path('admin/', admin.site.urls),
    path('account/', include('account.urls', namespace='account')),  # namespace باید اینجا باشه
    path('salon/', include('salon.urls', namespace='salon')),

]