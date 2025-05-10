from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings

from account.views import home

urlpatterns = [
    path('', home, name='home'), 
    path('admin/', admin.site.urls),
    path('account/', include('account.urls', namespace='account')),  # namespace باید اینجا باشه
    path('salon/', include('salon.urls', namespace='salon')),

]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)