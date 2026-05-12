from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BEXViewSet, ADIViewSet, CCPQViewSet

router = DefaultRouter()
router.register(r'bex', BEXViewSet, basename='bex')
router.register(r'adi', ADIViewSet, basename='adi')
router.register(r'ccpq', CCPQViewSet, basename='ccpq')

urlpatterns = [
    path('', include(router.urls)),
]
