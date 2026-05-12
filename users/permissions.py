from rest_framework import permissions
from users.models import User

class IsAgentTransit(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.AGENT

class IsChefService(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.CHEF_SERVICE

class IsAdminRSI(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.Role.ADMIN

class CanManageTransit(permissions.BasePermission):
    """
    Seuls les AGENTS (leurs propres dossiers) et les CHEFS DE SERVICE (tout) 
    peuvent créer/modifier. L'ADMIN ne peut PAS créer de dossiers ou documents.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # L'Admin ne peut JAMAIS créer ou modifier des données métier
        if request.user.role == User.Role.ADMIN and request.method not in permissions.SAFE_METHODS:
            return False
            
        return True

    def has_object_permission(self, request, view, obj):
        if request.user.role == User.Role.ADMIN:
            return request.method in permissions.SAFE_METHODS
            
        if request.user.role == User.Role.CHEF_SERVICE:
            return True
            
        if request.user.role == User.Role.AGENT:
            # Vérifie si l'utilisateur est le créateur (pour BEX) ou lié via le BEX (pour documents/items)
            creator = getattr(obj, 'agent_createur', None)
            if creator:
                return creator == request.user
            
            # Pour les objets liés (DocumentTransit, BEXItem), on vérifie le BEX parent
            bex = getattr(obj, 'bex', None)
            if bex:
                return bex.agent_createur == request.user
                
        return False

def get_visible_objects(user, queryset, creator_field='agent_createur'):
    if user.role in [User.Role.ADMIN, User.Role.CHEF_SERVICE]:
        return queryset
    return queryset.filter(**{creator_field: user})
