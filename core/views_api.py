from rest_framework import serializers, viewsets, permissions
from .models import AppSettings
from users.models import User

class AppSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppSettings
        fields = '__all__'

class AppSettingsViewSet(viewsets.ModelViewSet):
    queryset = AppSettings.objects.all()
    serializer_class = AppSettingsSerializer
    
    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), permissions.BasePermission()] # Sera affiné pour ADMIN uniquement

    # Restriction stricte à l'ADMIN pour la modification
    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method not in permissions.SAFE_METHODS and request.user.role != User.Role.ADMIN:
            self.permission_denied(request, message="Seul l'Administrateur (RSI) peut modifier les paramètres.")
