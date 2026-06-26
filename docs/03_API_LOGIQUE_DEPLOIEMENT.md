# RAPPORT DE STAGE — Partie 3 : API REST, Logique Métier et Déploiement

---

## 7. Documentation Complète de l'API REST

### 7.1 Configuration globale de l'API

**Fichier** : `Gestion_Suivi_Documentaire/settings.py` (section REST_FRAMEWORK)

```python
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'core.authentication.CsrfExemptSessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',),
}
```

- **Authentification par défaut** : session Django (cookies) avec exemption CSRF pour le cross-domain.
- **Permission par défaut** : `IsAuthenticated` — toute requête non authentifiée reçoit un `403 Forbidden`.
- **Filtrage par défaut** : `DjangoFilterBackend` pour le filtrage via paramètres URL.

### 7.2 Routage des URLs

**Fichier** : `Gestion_Suivi_Documentaire/urls.py`

```
/                              → Page d'accueil HTML (core.views.index)
/admin/                        → Interface admin Django
/api/settings/                 → CRUD paramètres (core.views_api.AppSettingsViewSet)
/api/login/                    → Connexion (users.views.login_view)
/api/logout/                   → Déconnexion (users.views.logout_view)
/api/me/                       → Profil courant (users.views.me_view)
/api/users/                    → Liste/Création utilisateurs (users.views)
/api/users/unlock/             → Déblocage de compte (users.views)
/api/transit/bex/              → CRUD BEX (transit.views.BEXViewSet)
/api/transit/adi/              → CRUD ADI (transit.views.ADIViewSet)
/api/transit/ccpq/             → CRUD CCPQ (transit.views.CCPQViewSet)
/api/analytics/dashboard-data/ → KPIs du dashboard (analytics.views)
/api/analytics/powerbi-embed/  → Config Power BI (analytics.views)
/api/analytics/export-excel/   → Export rapport Excel (analytics.views)
```

### 7.3 Endpoints d'authentification

#### `POST /api/login/`

Authentifie un utilisateur et crée une session Django.

**Corps de la requête** :
```json
{
    "username": "agent1",
    "password": "agent123"
}
```

**Réponse succès (200)** :
```json
{
    "status": "success",
    "user": {
        "username": "agent1",
        "role": "AGENT",
        "full_name": "Jean Transit"
    }
}
```

**Réponses d'erreur** :
- `401` : Identifiants invalides
- `403` : Compte bloqué (5 échecs de connexion)

#### `POST /api/logout/`

Détruit la session de l'utilisateur connecté. Requiert l'authentification.

#### `GET /api/me/`

Retourne le profil de l'utilisateur actuellement connecté.

**Réponse** :
```json
{
    "username": "agent1",
    "email": "",
    "role": "AGENT",
    "role_display": "Transit",
    "first_name": "Jean",
    "last_name": "Transit"
}
```

#### `GET /api/users/` (Admin uniquement)

Liste tous les utilisateurs du système.

#### `POST /api/users/` (Admin uniquement)

Crée un nouvel utilisateur.

```json
{
    "username": "agent2",
    "password": "motdepasse",
    "first_name": "Paul",
    "last_name": "Dupont",
    "role": "AGENT"
}
```

#### `POST /api/users/unlock/` (Admin uniquement)

Débloque un compte verrouillé.

```json
{ "user_id": 5 }
```

### 7.4 Endpoints Transit — BEX

#### `GET /api/transit/bex/`

Liste les dossiers BEX. Filtrage automatique par rôle (un AGENT ne voit que ses BEX).

**Filtres disponibles** :
- `?type_bex=MARITIME` — Filtre par type d'acheminement
- `?statut=EN_ATTENTE` — Filtre par statut
- `?search=SANOFI` — Recherche dans numero_bex et fournisseur

#### `POST /api/transit/bex/`

Crée un nouveau BEX avec ses items (sérialisation imbriquée).

```json
{
    "numero_bex": "BEX-2026-010",
    "type_bex": "MARITIME",
    "fournisseur": "SANOFI France",
    "date_enlevement_prevue": "2026-07-15",
    "items": [
        {
            "numero_conteneur": "CONT-100",
            "designation_produit": "Amoxicilline 500mg",
            "quantite": 5000,
            "facture_fcfa": 3250000.00
        }
    ]
}
```

Le sérialiseur `BEXSerializer` surcharge la méthode `create()` pour gérer la création imbriquée : il crée d'abord le BEX, puis itère sur les items pour créer les `BEXItem` et les `Conteneur` associés.

#### `GET /api/transit/bex/{id}/dossier-complet/`

Vue complète d'un dossier BEX avec toutes ses relations (items, conteneurs, ADIs, CCPQs, documents). Utilise le sérialiseur `BEXDossierCompletSerializer` qui agrège toutes les relations via `related_name`.

#### `POST /api/transit/bex/{id}/upload-document/`

Upload multipart d'un document associé au BEX. Déclenche automatiquement le signal de mise à jour de statut si le type est LIQUIDATION ou REC165.

#### `POST /api/transit/bex/{id}/valider/` (Chef de Service uniquement)

Change le statut du BEX en VALIDE. Protégé par la permission `IsChefService`.

#### `POST /api/transit/bex/import-excel/`

Import Excel intelligent avec détection dynamique des en-têtes. L'algorithme :

1. Lit le fichier sans en-têtes (`header=None`)
2. Scanne les 10 premières lignes à la recherche des métadonnées (numéro BEX, dates)
3. Détecte la ligne d'en-tête du tableau (contenant "NUMERO FACTURE")
4. Crée ou met à jour le BEX avec `get_or_create`
5. Parse chaque ligne du tableau avec mapping dynamique des colonnes
6. Utilise `get_or_create` sur les items pour éviter les doublons lors d'un ré-import
7. Le tout est encapsulé dans `transaction.atomic()` pour garantir la cohérence

### 7.5 Endpoints Transit — ADI et CCPQ

Les ViewSets ADI et CCPQ suivent le même patron que BEX (CRUD + import Excel) avec des particularités :

**Import ADI** : gère les cellules fusionnées Excel via `df.ffill()` (forward fill) et supporte les séparateurs décimaux virgule pour le champ coût.

**Import CCPQ** : détection dynamique de la ligne d'en-tête (cherche "DCQ", "FOB EURO" ou "SYLVIE"), liaison automatique avec un BEX existant si la colonne BEX est présente dans le fichier, et mode upsert (création ou mise à jour).

### 7.6 Endpoints Analytics

#### `GET /api/analytics/dashboard-data/`

Endpoint principal du tableau de bord. Calcule en temps réel tous les indicateurs.

**Paramètres de filtre** :
- `?agent_id=3` — Filtre par agent (ignoré pour les AGENT, forcé sur leur propre ID)
- `?periode=semaine|mois|trimestre` — Filtre temporel (7, 30 ou 90 jours)
- `?type_dossier=BEX|ADI|CCPQ|CONTENEUR` — Filtre par type de dossier

**Structure de la réponse** :
```json
{
    "active_counts": {"BEX": 3, "ADI": 2, "CCPQ": 2, "Conteneur": 3},
    "total_active_dossiers": 7,
    "blocked_count": 4,
    "avg_delays": {"BEX": 8.5, "ADI": 4.0, "CCPQ": 4.0},
    "validation_rate": 66.7,
    "charts": {
        "grouped_bars": [
            {"month": "Janvier 2026", "BEX": 2, "ADI": 3, "CCPQ": 1}
        ],
        "pie_causes": [
            {"label": "Retards ADI", "value": 1},
            {"label": "Retards CCPQ", "value": 1},
            {"label": "Retards Douane", "value": 1},
            {"label": "Autres Causes", "value": 0}
        ],
        "trend_weeks": [
            {"week": "Semaine 22", "avg_days": 10.5}
        ]
    },
    "late_dossiers_table": [
        {
            "id": 4, "numero": "BEX-2026-004", "type": "BEX",
            "statut": "BLOQUE", "date_depot_creation": "2026-05-26",
            "agent_responsable": "agent1", "jours_retard": 20,
            "seuil_limite": 15
        }
    ],
    "filters_metadata": {
        "agents": [{"id": 2, "name": "Jean Transit (agent1)"}],
        "types": ["BEX", "ADI", "CCPQ", "CONTENEUR"],
        "periods": [{"key": "semaine", "label": "Semaine"}]
    }
}
```

#### `GET /api/analytics/powerbi-embed/`

Retourne la configuration d'embedding Power BI. Deux modes :
- **Mode réel** : si les variables Azure sont configurées, effectue le flux OAuth2 Client Credentials pour obtenir un token d'embedding.
- **Mode mock** : retourne une configuration simulée réaliste pour le développement frontend.

#### `GET /api/analytics/export-excel/`

Génère et télécharge un fichier Excel (.xlsx) contenant 3 feuilles :
- **Synthèse KPIs** : tous les indicateurs clés
- **Dossiers en Retard** : tableau des dossiers dépassant les seuils
- **Historique Mensuel** : nombre de dossiers traités par mois et par type

---

## 8. Logique Métier du Dashboard

### 8.1 Fichier `analytics/dashboard_logic.py`

Ce fichier de **481 lignes** contient toute l'intelligence métier du tableau de bord. Il est séparé des vues pour respecter le principe de séparation des préoccupations.

### 8.2 Seuils SLA (Service Level Agreement)

Le système définit des seuils réglementaires de traitement :

| Type de dossier | Seuil (jours) | Signification |
|-----------------|:-------------:|---------------|
| BEX | **15** | Un BEX doit être entièrement traité en moins de 15 jours |
| ADI | **5** | Une ADI doit être validée dans les 5 jours suivant le dépôt |
| CCPQ | **7** | Un CCPQ doit recevoir un résultat dans les 7 jours |

### 8.3 Calcul des délais de traitement

Trois fonctions dédiées calculent les durées de traitement :

- **`get_bex_processing_days(bex)`** : pour un BEX terminé, calcule la différence entre la date de complétion (document LIQUIDATION/REC165 uploadé) et la date de création. Pour un BEX actif, utilise la date courante.

- **`get_adi_processing_days(adi)`** : calcule la différence entre `date_reception` (si terminé) ou la date courante (si actif) et `date_depot`. Fallback sur la date de création du BEX parent si `date_depot` est absent.

- **`get_ccpq_processing_days(ccpq)`** : même logique avec `date_resultat` et `date_depot`.

### 8.4 Détection des retards

Le système parcourt tous les dossiers actifs (non terminés) et compare leur durée de traitement aux seuils SLA. Un dossier est considéré "en retard" si :
- **BEX** : durée > 15 jours OU statut = BLOQUE
- **ADI** : durée > 5 jours
- **CCPQ** : durée > 7 jours

### 8.5 Analyse des causes de retards (Graphique Pie)

Pour chaque dossier BEX en retard, le système détermine la cause racine :
1. Si le statut est BLOQUE ou le statut douanier est anormal → **Retard Douane**
2. Si le BEX a des ADI non validées → **Retard ADI**
3. Si le BEX a des CCPQ non approuvées → **Retard CCPQ**
4. Sinon → **Autres Causes**

### 8.6 Taux de validation réglementaire

Le taux de validation mesure le pourcentage de dossiers traités dans les délais SLA sur le mois en cours :

```
Taux = (Dossiers traités dans les délais / Total dossiers traités ce mois) × 100
```

---

## 9. Sécurité de l'Application

### 9.1 Authentification

- **Méthode** : authentification par session Django (cookies `sessionid`)
- **Classe personnalisée** : `CsrfExemptSessionAuthentication` dans `core/authentication.py` — hérite de `SessionAuthentication` mais désactive la vérification CSRF, nécessaire car le frontend React est hébergé sur un domaine différent
- **Fallback** : `BasicAuthentication` (pour les tests via Postman ou curl)

### 9.2 Protection CSRF et cookies cross-domain

Configuration dans `settings.py` :

| Paramètre | Valeur | Justification |
|-----------|--------|---------------|
| `CSRF_COOKIE_SAMESITE` | `'None'` | Permet l'envoi cross-domain des cookies |
| `SESSION_COOKIE_SAMESITE` | `'None'` | Idem pour le cookie de session |
| `CSRF_COOKIE_SECURE` | `True` | Cookie CSRF envoyé uniquement via HTTPS |
| `SESSION_COOKIE_SECURE` | `True` | Cookie de session uniquement via HTTPS |
| `SESSION_COOKIE_HTTPONLY` | `True` | Cookie non accessible en JavaScript (protection XSS) |
| `SESSION_COOKIE_AGE` | `1800` | Expiration après 30 minutes d'inactivité |
| `SESSION_SAVE_EVERY_REQUEST` | `True` | Réinitialise le timeout à chaque requête |

### 9.3 CORS (Cross-Origin Resource Sharing)

```python
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "https://laborex-front-45of.vercel.app",
]
```

### 9.4 Validation des mots de passe

Django applique 4 validateurs : similarité avec l'username, longueur minimale, mots de passe courants, mots de passe entièrement numériques.

---

## 10. Déploiement et Mise en Production

### 10.1 Environnement local

```bash
python -m venv env
source env/bin/activate
pip install -r requirements.txt
python manage.py migrate
python setup_test_users.py
python populate_dashboard_data.py    # Optionnel : données de démonstration
python manage.py runserver
```

### 10.2 Script de build Render (`build.sh`)

```bash
#!/usr/bin/env bash
set -o errexit                          # Arrêt immédiat en cas d'erreur
pip install -r requirements.txt         # Installation des dépendances
python manage.py collectstatic --no-input  # Collecte des fichiers statiques
python manage.py migrate                # Application des migrations
python setup_test_users.py              # Création des utilisateurs par défaut
```

### 10.3 Configuration Render

| Paramètre | Valeur |
|-----------|--------|
| **Build Command** | `./build.sh` |
| **Start Command** | `gunicorn Gestion_Suivi_Documentaire.wsgi` |
| **URL** | `https://gestion-suivi-documentaire.onrender.com` |
| **Base de données** | SQLite par défaut, PostgreSQL si `DATABASE_URL` est définie |

### 10.4 Variables d'environnement

| Variable | Obligatoire | Description |
|----------|:-----------:|-------------|
| `SECRET_KEY` | Non (défaut fourni) | Clé secrète Django pour le hashage cryptographique |
| `DEBUG` | Non (défaut True) | Mode debug — mettre à `False` en production |
| `DATABASE_URL` | Non | URL PostgreSQL. Si absente, SQLite est utilisée |
| `RENDER_EXTERNAL_HOSTNAME` | Non | Hostname Render ajouté dynamiquement à ALLOWED_HOSTS |
| `POWERBI_CLIENT_ID` | Non | Azure AD Client ID pour l'intégration Power BI |
| `POWERBI_CLIENT_SECRET` | Non | Azure AD Client Secret |
| `POWERBI_TENANT_ID` | Non | Azure AD Tenant ID |
| `POWERBI_WORKSPACE_ID` | Non | ID de l'espace de travail Power BI |
| `POWERBI_REPORT_ID` | Non | ID du rapport Power BI à intégrer |

---

## 11. Outils de Test et Données

### 11.1 Collection Postman

Le fichier `Postman_Collection.json` fournit une collection prête à l'emploi pour tester tous les endpoints de l'API avec la variable `{{base_url}}` configurée sur `http://127.0.0.1:8000`.

### 11.2 Script de test d'intégration (`test_views.py`)

Ce script automatise la vérification de bout en bout :
1. Teste qu'un accès non authentifié retourne `403`
2. S'authentifie en tant qu'`agent1`
3. Vérifie le endpoint dashboard-data (KPIs, graphiques, filtres)
4. Teste les filtres par période et par type de dossier
5. Vérifie le endpoint Power BI (mock)

### 11.3 Script de peuplement (`populate_dashboard_data.py`)

Crée un jeu de données réaliste comprenant :
- **3 utilisateurs** : admin, agent1, chef1
- **7 dossiers BEX** avec différents statuts et durées
- **8 items BEX** et **7 conteneurs**
- **4 documents** de transit (liquidations et REC165)
- **5 dossiers ADI** (mix complétés/actifs/en retard)
- **5 dossiers CCPQ** (mix complétés/actifs/en retard)

### 11.4 Comptes de test par défaut

| Utilisateur | Mot de passe | Rôle | Profil métier |
|-------------|-------------|------|---------------|
| `admin` | `admin123` | ADMIN | Administrateur RSI |
| `agent1` | `agent123` | AGENT | Agent Transit |
| `chef1` | `chef123` | CHEF_SERVICE | Chef de Service / Pharmacien |

---

## 12. Dépendances du Projet

### 12.1 Fichier `requirements.txt`

| Package | Rôle dans le projet |
|---------|---------------------|
| `django>=5.1.1` | Framework web principal |
| `djangorestframework` | Construction de l'API REST |
| `django-filter` | Filtrage dynamique des querysets |
| `django-cors-headers` | Gestion des en-têtes CORS |
| `pandas` | Lecture et parsing des fichiers Excel |
| `openpyxl` | Moteur Excel pour pandas (.xlsx) |
| `psycopg2-binary` | Driver PostgreSQL pour la production |
| `gunicorn` | Serveur WSGI de production |
| `whitenoise` | Service des fichiers statiques en production |
| `dj-database-url` | Parsing automatique de `DATABASE_URL` |
| `python-dotenv` | Chargement des variables d'environnement depuis `.env` |
| `requests` | Appels HTTP vers l'API Azure/Power BI |

---

## 13. Glossaire Métier

| Terme | Signification |
|-------|---------------|
| **BEX** | Bon d'Expédition — Document principal traçant l'envoi de marchandises |
| **ADI** | Autorisation de Dédouanement à l'Importation — Document réglementaire de l'ANRP |
| **CCPQ** | Certificat de Contrôle Pharmaceutique et de Qualité — Résultat du contrôle qualité |
| **ANRP** | Agence Nationale de Régulation Pharmaceutique du Burkina Faso |
| **RSI** | Responsable du Système d'Information |
| **REC165** | Document douanier attestant que la marchandise est prête pour enlèvement |
| **SYLVIE** | Système national d'enregistrement des produits pharmaceutiques |
| **FOB** | Free On Board — Valeur de la marchandise au port d'embarquement |
| **ASI** | Autorisation Sanitaire d'Importation |
| **FCFA** | Franc CFA — Monnaie utilisée en Afrique de l'Ouest (XOF) |
| **SLA** | Service Level Agreement — Délai maximal de traitement défini par la réglementation |
| **RBAC** | Role-Based Access Control — Contrôle d'accès basé sur les rôles |
| **CORS** | Cross-Origin Resource Sharing — Mécanisme de sécurité des navigateurs |
| **CSRF** | Cross-Site Request Forgery — Type d'attaque web |
| **KPI** | Key Performance Indicator — Indicateur clé de performance |
