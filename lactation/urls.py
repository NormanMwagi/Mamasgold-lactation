
from django.contrib import admin
from django.urls import path, include
from . import views
from django.conf.urls.static import static
from django.conf import settings
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    
    path('create-admin/', views.create_admin, name='create_admin'),
    path('store/', include('store.urls')),
    path('cart/', include('carts.urls')),
    path('accounts/', include('accounts.urls')),
    path('payments/', include('payments.urls')),
    path('run-migrations/', views.run_migrations, name='run_migrations'),
    # path('orders/', include('orders.urls')),
] + static(settings.MEDIA_URL , document_root= settings.MEDIA_ROOT)