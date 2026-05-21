from django.urls import path
from .views import DashboardDataAPIView, PowerBIEmbedAPIView, ExportExcelAPIView

app_name = 'analytics'

urlpatterns = [
    path('dashboard-data/', DashboardDataAPIView.as_view(), name='dashboard-data'),
    path('powerbi-embed/', PowerBIEmbedAPIView.as_view(), name='powerbi-embed'),
    path('export-excel/', ExportExcelAPIView.as_view(), name='export-excel'),
]
