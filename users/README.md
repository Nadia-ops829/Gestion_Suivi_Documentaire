# Application Users - Système d'Authentification & Gestion des Rôles

Cette application gère l'authentification personnalisée, la sécurité des comptes et les permissions basées sur les rôles pour le projet **Gestion Suivi Documentaire (Laborex-Burkina)**.

## 🚀 Fonctionnalités Implémentées

### 1. Custom User Model
- **Modèle** : `User` (hérite de `AbstractUser`).
- **Rôles (Choices)** :
  - `AGENT` (Transit) : Accès restreint à ses propres données.
  - `CHEF_SERVICE` (Validation) : Vue globale.
  - `ADMIN` (RSI) : Gestion totale et déblocage de comptes.
- **Champ `failed_login_attempts`** : Suit le nombre d'échecs de connexion.

### 2. Sécurité & Authentification
- **Blocage de compte** : Verrouillage automatique (`is_active = False`) après **5 tentatives** de connexion infructueuses (géré via Django Signals).
- **Session** : Expiration automatique après **30 minutes d'inactivité** (`SESSION_COOKIE_AGE = 1800`).
- **Chiffrement** : Utilisation du standard Django PBKDF2.

### 3. Gestion des Permissions
- **`RoleRequiredMixin`** : Mixin pour restreindre l'accès aux vues selon le rôle de l'utilisateur.
- **Règle métier (Visibilité)** : Les `AGENT` ne peuvent voir que les objets dont ils sont le "créateur". Implémenté via la fonction helper `get_visible_objects`.

## 🛠 Configuration & Installation

### Migrations
En cas de réinitialisation de la base de données, l'ordre des migrations est crucial :
```bash
python manage.py makemigrations users
python manage.py migrate
```

### Création d'un Super Admin (RSI)
La commande `createsuperuser` crée un compte avec le rôle par défaut. Pour lui assigner le rôle `ADMIN` :
1. Créer le superuser : `python manage.py createsuperuser`
2. Assigner le rôle via le shell :
```bash
python manage.py shell
```
```python
from users.models import User
u = User.objects.get(username='votre_username')
u.role = User.Role.ADMIN
u.save()
```

## 📡 Endpoints API

| Méthode | Endpoint | Description | Accès |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/login/` | Authentification et création de session | Public |
| `POST` | `/api/logout/` | Fermeture de la session | Connecté |
| `GET` | `/api/me/` | Récupère les infos de l'utilisateur connecté | Connecté |
| `POST` | `/api/users/unlock/` | Débloque un compte (`is_active=True`) | Admin uniquement |

## 📁 Structure des Fichiers
- `models.py` : Définition du modèle `User` et des rôles.
- `signals.py` : Logique de blocage/déblocage automatique.
- `permissions.py` : Mixins et logique de filtrage des données.
- `views.py` : Logique des endpoints API (JsonResponse).
- `urls.py` : Routage des endpoints `/api/`.
