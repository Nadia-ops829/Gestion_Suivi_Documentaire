from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import index
from core.views_api import AppSettingsViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'settings', AppSettingsViewSet, basename='settings')

urlpatterns = [
    path('', index, name='home'),
    path('api/', include(router.urls)),
    path('api/', include('users.urls')),
    path('api/transit/', include('transit.urls')),
    path('api/analytics/', include('analytics.urls')),
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
