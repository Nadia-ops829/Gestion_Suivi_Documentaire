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

@login_required
def me_view(request):
    user = request.user
    return JsonResponse({
        'username': user.username,
        'email': user.email,
        'role': user.role,
        'role_display': user.get_role_display(),
        'first_name': user.first_name,
        'last_name': user.last_name,
    })

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
