# RAPPORT DE STAGE — Partie 1 : Présentation Générale du Projet

## Système de Gestion et Suivi Documentaire — Laborex Burkina Faso

---

## 1. Contexte et Problématique

### 1.1 Présentation de l'entreprise d'accueil

**Laborex Burkina Faso** est une filiale du groupe CFAO Healthcare, leader de la distribution pharmaceutique en Afrique de l'Ouest. L'entreprise assure l'importation, le stockage et la distribution de produits pharmaceutiques sur le territoire burkinabè. Cette activité implique une gestion rigoureuse des processus de transit international, soumis à des réglementations douanières et sanitaires strictes.

### 1.2 Problématique identifiée

Avant la mise en place de ce système, le suivi des dossiers de transit chez Laborex Burkina reposait essentiellement sur des fichiers Excel partagés et des processus manuels. Cette situation engendrait plusieurs problèmes opérationnels critiques :

- **Perte de traçabilité** : il était difficile de retracer l'historique complet d'un dossier de transit, depuis l'expédition jusqu'à la réception en entrepôt.
- **Absence de visibilité en temps réel** : les responsables n'avaient pas de vue d'ensemble sur l'état des dossiers en cours, les retards ou les blocages.
- **Processus de validation non structuré** : les validations par le pharmacien responsable et le RSI (Responsable du Système d'Information) se faisaient de manière informelle, sans audit trail.
- **Gestion documentaire dispersée** : les documents réglementaires (factures, ADI, CCPQ, liquidations douanières) étaient stockés sur différents supports sans lien direct avec les dossiers correspondants.
- **Importation de données fastidieuse** : la saisie manuelle des données à partir des fichiers Excel des fournisseurs et des organismes réglementaires était chronophage et source d'erreurs.
- **Aucun tableau de bord décisionnel** : l'absence d'indicateurs de performance (KPIs) rendait impossible le pilotage opérationnel et la détection proactive des retards.

### 1.3 Objectifs du projet

Le projet **Gestion et Suivi Documentaire** a pour objectif de concevoir et développer une application web complète permettant de :

1. **Centraliser** la gestion de tous les dossiers de transit (BEX, ADI, CCPQ) dans une plateforme unique.
2. **Dématérialiser** le stockage et l'association des documents réglementaires aux dossiers correspondants.
3. **Automatiser** les changements de statut des dossiers selon les événements documentaires (upload de liquidation douanière, etc.).
4. **Structurer** les processus de validation avec un système de rôles et de permissions différenciés.
5. **Faciliter l'importation** de données en masse depuis des fichiers Excel aux formats variés et non standardisés.
6. **Fournir un tableau de bord analytique** avec des KPIs en temps réel, des graphiques de tendances et la détection automatique des dossiers en retard.
7. **Intégrer Power BI** pour des analyses visuelles avancées destinées à la direction.
8. **Permettre l'export** de rapports synthétiques au format Excel pour la communication interne.

### 1.4 Périmètre fonctionnel

Le système couvre l'intégralité du cycle de vie documentaire du transit pharmaceutique :

```
Expédition → Arrivée → Dédouanement → Contrôle Qualité → Réception → Archivage
   (BEX)       (ADI)      (Douane)       (CCPQ)          (RSI)      (Documents)
```

---

## 2. Choix Technologiques et Justifications

### 2.1 Stack technologique

| Couche | Technologie | Version | Justification |
|--------|-------------|---------|---------------|
| **Framework Backend** | Django | ≥ 5.1.1 | Framework Python mature, sécurisé par défaut, avec un ORM puissant et une architecture MVT éprouvée. Idéal pour les applications d'entreprise nécessitant une gestion fine des permissions |
| **API REST** | Django REST Framework (DRF) | Latest | Extension standard de Django pour la construction d'APIs RESTful. Fournit la sérialisation, l'authentification, les permissions et le routage automatique |
| **Filtrage des données** | django-filter | Latest | Permet le filtrage dynamique des querysets via les paramètres URL, essentiel pour les vues de recherche et de filtrage des dossiers |
| **Gestion CORS** | django-cors-headers | Latest | Middleware indispensable pour autoriser les requêtes cross-origin depuis le frontend React hébergé sur un domaine différent (Vercel) |
| **Traitement Excel** | Pandas + openpyxl | Latest | Pandas offre un parsing robuste des fichiers Excel avec gestion des cellules fusionnées, des formats de date variés et des séparateurs décimaux. openpyxl sert de moteur de lecture/écriture .xlsx |
| **Base de données (dev)** | SQLite | 3.x | Base de données fichier, sans configuration, idéale pour le développement local et les tests |
| **Base de données (prod)** | PostgreSQL | 14+ | Base de données relationnelle robuste pour la production, configurée via `DATABASE_URL` sur Render |
| **Serveur WSGI** | Gunicorn | Latest | Serveur HTTP Python performant pour la production, capable de gérer les requêtes concurrentes |
| **Fichiers statiques** | WhiteNoise | Latest | Middleware de service de fichiers statiques optimisé, avec compression et cache busting, éliminant le besoin d'un serveur Nginx séparé |
| **Hébergement Backend** | Render.com | — | Plateforme PaaS (Platform as a Service) offrant un déploiement continu depuis Git, avec SSL automatique et gestion simplifiée de PostgreSQL |
| **Frontend** | React.js | — | Application frontend SPA (Single Page Application) hébergée séparément sur Vercel, communiquant avec le backend via l'API REST |

### 2.2 Architecture logicielle adoptée

Le projet adopte une **architecture découplée (Decoupled Architecture)** de type **API-First** :

```
┌──────────────────────────────────────────────────┐
│           Frontend React (Vercel)                 │
│   • Interface utilisateur SPA                     │
│   • Appels API REST (fetch/axios)                 │
│   • Authentification par cookies de session       │
└──────────────────┬───────────────────────────────┘
                   │ HTTPS (JSON)
                   │ CORS Headers
┌──────────────────▼───────────────────────────────┐
│           Backend Django (Render)                  │
│                                                    │
│  ┌────────┐ ┌─────────┐ ┌──────────┐ ┌─────────┐│
│  │ users  │ │ transit │ │analytics │ │  core   ││
│  │        │ │         │ │          │ │         ││
│  │• Auth  │ │• BEX    │ │• KPIs    │ │• Config ││
│  │• RBAC  │ │• ADI    │ │• Charts  │ │• Auth   ││
│  │• Users │ │• CCPQ   │ │• PowerBI │ │  Helper ││
│  │  Mgmt  │ │• Docs   │ │• Export  │ │         ││
│  │• Lock  │ │• Import │ │  Excel   │ │         ││
│  └────────┘ └─────────┘ └──────────┘ └─────────┘│
│                                                    │
│  ┌────────────────────────────────────────────────┐│
│  │       SQLite (dev) / PostgreSQL (prod)          ││
│  └────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────┘
```

**Justification de cette architecture** :

- **Séparation des préoccupations** : le frontend et le backend évoluent indépendamment. L'équipe frontend peut travailler sans dépendre du backend et vice versa.
- **Scalabilité** : chaque composant peut être mis à l'échelle individuellement.
- **Réutilisabilité** : l'API REST peut servir d'autres clients (application mobile, scripts d'intégration, etc.).
- **Testabilité** : les endpoints API peuvent être testés indépendamment avec des outils comme Postman.

### 2.3 Patron de conception — MVT (Modèle-Vue-Template)

Django utilise le patron **MVT** (Model-View-Template), variante du MVC classique :

| Composant | Rôle dans le projet | Fichiers correspondants |
|-----------|---------------------|------------------------|
| **Model** | Définit la structure des données et les interactions avec la base de données | `models.py` dans chaque app |
| **View** | Contient la logique métier, traite les requêtes HTTP et renvoie les réponses JSON | `views.py`, `views_api.py` |
| **Serializer** | Couche intermédiaire propre à DRF, convertit les objets Python en JSON et valide les données entrantes | `serializers.py` |
| **Template** | Génère les pages HTML côté serveur (utilisé uniquement pour la page d'accueil) | `templates/index.html` |

---

## 3. Organisation du Projet Django

### 3.1 Structure modulaire en applications

Le projet est découpé en **5 applications Django**, chacune responsable d'un domaine fonctionnel précis :

| Application | Domaine | Description |
|-------------|---------|-------------|
| `core` | Configuration | Paramètres globaux de l'application, classe d'authentification personnalisée, page d'accueil |
| `users` | Utilisateurs | Modèle utilisateur personnalisé, authentification, gestion des rôles, verrouillage de compte |
| `transit` | Métier | Gestion des dossiers BEX, ADI, CCPQ, conteneurs, documents. Import Excel. C'est le cœur fonctionnel |
| `analytics` | Décisionnel | Tableau de bord avec KPIs, graphiques, intégration Power BI, export Excel |
| `processing` | Extension | Application réservée pour de futurs traitements automatisés (ex : OCR de documents, notifications) |

### 3.2 Arborescence complète des fichiers

```
Gestion_Suivi_Documentaire/
│
├── manage.py                          # Point d'entrée CLI de Django
├── requirements.txt                   # Liste des dépendances Python
├── build.sh                           # Script de déploiement Render
├── db.sqlite3                         # Base de données SQLite locale
├── .gitignore                         # Exclusions Git
│
├── Gestion_Suivi_Documentaire/        # Package de configuration Django
│   ├── __init__.py                    # Marqueur de package Python
│   ├── settings.py                    # Configuration centrale du projet
│   ├── urls.py                        # Table de routage URL principale
│   ├── wsgi.py                        # Interface WSGI (production sync)
│   └── asgi.py                        # Interface ASGI (production async)
│
├── core/                              # App : Configuration globale
│   ├── models.py                      # Modèle AppSettings
│   ├── views.py                       # Vue page d'accueil
│   ├── views_api.py                   # API CRUD AppSettings
│   ├── authentication.py             # Classe CsrfExemptSessionAuthentication
│   ├── apps.py                        # Configuration de l'application
│   └── templates/index.html           # Template HTML d'accueil
│
├── users/                             # App : Gestion des utilisateurs
│   ├── models.py                      # Modèle User (AbstractUser + rôles)
│   ├── views.py                       # Vues login/logout/me/users/unlock
│   ├── urls.py                        # Routes d'authentification
│   ├── permissions.py                 # Classes de permissions RBAC
│   ├── signals.py                     # Signaux de verrouillage de compte
│   └── apps.py                        # Configuration + chargement signaux
│
├── transit/                           # App : Gestion du transit
│   ├── models.py                      # 6 modèles (BEX, BEXItem, etc.)
│   ├── views.py                       # 3 ViewSets (BEX, ADI, CCPQ)
│   ├── serializers.py                 # 6 sérialiseurs DRF
│   ├── urls.py                        # Router DRF pour les ViewSets
│   ├── signals.py                     # Signal de mise à jour auto des statuts
│   └── apps.py                        # Configuration + chargement signaux
│
├── analytics/                         # App : Tableau de bord
│   ├── views.py                       # 3 APIViews (Dashboard, PowerBI, Excel)
│   ├── dashboard_logic.py            # Logique métier des KPIs (481 lignes)
│   ├── urls.py                        # Routes analytics
│   └── apps.py                        # Configuration
│
├── processing/                        # App : Réservée (extension future)
│
├── media/transit/                     # Stockage des documents uploadés
│
├── populate_dashboard_data.py         # Script de peuplement de données test
├── setup_test_users.py                # Script de création d'utilisateurs test
├── test_views.py                      # Tests d'intégration des APIs
└── Postman_Collection.json            # Collection Postman pour tests manuels
```
