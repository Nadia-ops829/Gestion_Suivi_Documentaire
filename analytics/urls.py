from django.urls import path
from .views import DashboardDataAPIView, PowerBIEmbedAPIView

app_name = 'analytics'

urlpatterns = [
    path('dashboard-data/', DashboardDataAPIView.as_view(), name='dashboard-data'),
    path('powerbi-embed/', PowerBIEmbedAPIView.as_view(), name='powerbi-embed'),
]
