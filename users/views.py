import json
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404
from .models import User

@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return JsonResponse({
                        'status': 'success',
                        'user': {
                            'username': user.username,
                            'role': user.role,
                            'full_name': f"{user.first_name} {user.last_name}".strip()
                        }
                    })
                else:
                    return JsonResponse({'status': 'error', 'message': 'Compte bloqué. Contactez un administrateur.'}, status=403)
            else:
                return JsonResponse({'status': 'error', 'message': 'Identifiants invalides.'}, status=401)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée.'}, status=405)

@csrf_exempt
@login_required
def logout_view(request):
    logout(request)
    return JsonResponse({'status': 'success', 'message': 'Déconnecté avec succès.'})

@csrf_exempt
@login_required
def me_view(request):
    user = request.user
    
    if request.method == 'GET':
        return JsonResponse({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'role_display': user.get_role_display(),
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_active': user.is_active,
            'date_joined': user.date_joined.isoformat() if user.date_joined else None,
            'last_login': user.last_login.isoformat() if user.last_login else None,
        })
        
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
            user.first_name = data.get('first_name', user.first_name)
            user.last_name = data.get('last_name', user.last_name)
            user.email = data.get('email', user.email)
            
            # Modification du mot de passe
            if 'password' in data and data['password']:
                user.set_password(data['password'])
                
            user.save()
            return JsonResponse({'status': 'success', 'message': 'Profil mis à jour avec succès.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            
    return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée.'}, status=405)

@csrf_exempt
@login_required
@user_passes_test(lambda u: u.role == User.Role.ADMIN)
def users_list_create_view(request):
    if request.method == 'GET':
        users = User.objects.all().values('id', 'username', 'first_name', 'last_name', 'role', 'is_active')
        return JsonResponse(list(users), safe=False)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user = User.objects.create_user(
                username=data['username'],
                password=data['password'],
                first_name=data.get('first_name', ''),
                last_name=data.get('last_name', ''),
                role=data.get('role', User.Role.AGENT)
            )
            return JsonResponse({'status': 'success', 'message': 'Utilisateur créé.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée.'}, status=405)

@csrf_exempt
@login_required
@user_passes_test(lambda u: u.role == User.Role.ADMIN)
def unlock_user_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            user_to_unlock = get_object_or_404(User, id=user_id)
            user_to_unlock.is_active = True
            user_to_unlock.failed_login_attempts = 0
            user_to_unlock.save()
            return JsonResponse({'status': 'success', 'message': f'Utilisateur {user_to_unlock.username} débloqué.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée.'}, status=405)

@csrf_exempt
@login_required
def user_profile_view(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    # Lecture du profil
    if request.method == 'GET':
        # Restriction : Un agent normal ne voit que lui-même
        if request.user.role == User.Role.AGENT and request.user.id != user.id:
            return JsonResponse({'status': 'error', 'message': 'Accès non autorisé.'}, status=403)

        return JsonResponse({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'role_display': user.get_role_display(),
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_active': user.is_active,
            'date_joined': user.date_joined.isoformat() if user.date_joined else None,
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'failed_login_attempts': user.failed_login_attempts,
        })
        
    # Mise à jour du profil
    if request.method == 'PUT':
        # Restriction : Seul l'utilisateur lui-même ou l'admin peut modifier
        if request.user.id != user.id and request.user.role != User.Role.ADMIN:
            return JsonResponse({'status': 'error', 'message': 'Accès non autorisé.'}, status=403)
            
        try:
            data = json.loads(request.body)
            user.first_name = data.get('first_name', user.first_name)
            user.last_name = data.get('last_name', user.last_name)
            user.email = data.get('email', user.email)
            
            # Seul l'admin peut modifier le rôle ou le statut
            if request.user.role == User.Role.ADMIN:
                if 'role' in data:
                    user.role = data['role']
                if 'is_active' in data:
                    user.is_active = data['is_active']
            
            # Modification du mot de passe
            if 'password' in data and data['password']:
                user.set_password(data['password'])
                
            user.save()
            return JsonResponse({'status': 'success', 'message': 'Profil mis à jour.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            
    return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée.'}, status=405)
