from django.contrib import admin
from django.urls import path, include
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
    path('admin/', admin.site.urls),
]
