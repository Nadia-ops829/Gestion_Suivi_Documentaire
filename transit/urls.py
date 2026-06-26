from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BEXViewSet, ADIViewSet, CCPQViewSet, FactureProformaViewSet

router = DefaultRouter()
router.register(r'bex', BEXViewSet, basename='bex')
router.register(r'adi', ADIViewSet, basename='adi')
router.register(r'ccpq', CCPQViewSet, basename='ccpq')
router.register(r'factures-proformas', FactureProformaViewSet, basename='facture_proforma')

urlpatterns = [
    path('', include(router.urls)),
]
