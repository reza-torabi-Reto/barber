from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from django.contrib.auth.views import LogoutView
from account.views import home, CustomLoginView

urlpatterns = [
    path('', home, name='home'), 
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('admin/', admin.site.urls),
    path('account/', include('account.urls', namespace='account')),  # namespace باید اینجا باشه
    path('shop/', include('salon.urls', namespace='salon')),
    path('api/account/', include('account.api.urls')),
    path('api/shop/', include('salon.api.urls')),


]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)