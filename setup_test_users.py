import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gestion_Suivi_Documentaire.settings')
django.setup()

from users.models import User

def create_test_users():
    users_data = [
        ('admin', 'admin123', User.Role.ADMIN, 'Admin', 'RSI'),
        ('agent1', 'agent123', User.Role.AGENT, 'Jean', 'Transit'),
        ('chef1', 'chef123', User.Role.CHEF_SERVICE, 'Marie', 'Validation'),
    ]

    for username, password, role, first, last in users_data:
        if not User.objects.filter(username=username).exists():
            user = User.objects.create_user(
                username=username,
                password=password,
                role=role,
                first_name=first,
                last_name=last,
                is_staff=True,
                is_superuser=(role == User.Role.ADMIN)
            )
            print(f"Utilisateur créé : {username} (Rôle: {role})")
        else:
            print(f"L'utilisateur {username} existe déjà.")

if __name__ == "__main__":
    create_test_users()
