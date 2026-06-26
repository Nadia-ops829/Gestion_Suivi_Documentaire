# RAPPORT DE STAGE — Partie 2 : Conception et Modélisation

---

## 4. Modélisation des Données

### 4.1 Diagramme Entité-Relation

```
┌──────────────────────────────────────────────────────────────────┐
│                           USER                                    │
│  (AbstractUser + role + failed_login_attempts)                    │
│  PK: id │ username │ role │ first_name │ last_name │ is_active   │
└──┬──────┬──────────┬───────────────────────────────────────────┘
   │      │          │
   │ agent_createur  │ pharmacien / rsi
   │      │          │
   ▼      ▼          ▼
┌─────────────────────────────────────────────────────────────────┐
│                           BEX                                    │
│  PK: id │ numero_bex (UNIQUE)                                    │
│  type_bex │ fournisseur │ statut │ statut_douanier               │
│  date_creation │ date_depart │ date_arrivee                      │
│  date_enlevement_prevue │ observations                           │
│  FK: agent_createur → User                                       │
│  FK: pharmacien → User │ FK: rsi → User                          │
│  date_pointage_pharmacien │ date_reception_rsi                   │
└──┬──────┬──────────┬──────────┬──────────────────────────────────┘
   │      │          │          │
   │      │          │          │
   ▼      ▼          ▼          ▼
┌──────┐ ┌────────┐ ┌────────┐ ┌──────────────────┐
│BEXItem│ │Conteneur│ │  ADI   │ │      CCPQ         │
│ (1,N) │ │ (1,N)  │ │ (0,N) │ │     (0,N)         │
└──────┘ └────────┘ └────────┘ └──────────────────┘

                     ┌──────────────────┐
                     │ DocumentTransit   │
                     │ FK: bex → BEX     │
                     │ FK: conteneur     │
                     │ fichier (FileField)│
                     │ type_document     │
                     └──────────────────┘
```

### 4.2 Description détaillée des modèles

#### 4.2.1 Modèle `User` — Utilisateur personnalisé

**Fichier** : `users/models.py`  
**Héritage** : `django.contrib.auth.models.AbstractUser`

Ce modèle étend le modèle utilisateur standard de Django pour ajouter la gestion des rôles métier spécifiques à Laborex.

| Champ | Type | Description |
|-------|------|-------------|
| `username` | CharField | Identifiant unique de connexion (hérité d'AbstractUser) |
| `first_name` | CharField | Prénom de l'utilisateur |
| `last_name` | CharField | Nom de famille |
| `email` | EmailField | Adresse email |
| `password` | CharField | Mot de passe hashé (Django gère automatiquement le hashage avec PBKDF2) |
| `role` | CharField(choices) | Rôle métier : `AGENT` (Transit), `CHEF_SERVICE` (Validation), `ADMIN` (RSI) |
| `failed_login_attempts` | PositiveIntegerField | Compteur de tentatives de connexion échouées consécutives. À 5, le compte est verrouillé |
| `is_active` | BooleanField | Indique si le compte est actif. Passe à `False` automatiquement après 5 échecs de login |
| `is_staff` | BooleanField | Permet l'accès à l'interface d'administration Django |
| `is_superuser` | BooleanField | Donne tous les droits (réservé au rôle ADMIN) |

**Choix de conception** : l'utilisation de `AbstractUser` plutôt que `AbstractBaseUser` permet de conserver tous les champs et méthodes standards de Django (authentification, groupes, permissions) tout en ajoutant les champs métier nécessaires. Le paramètre `AUTH_USER_MODEL = 'users.User'` dans `settings.py` indique à Django d'utiliser ce modèle personnalisé.

#### 4.2.2 Modèle `BEX` — Bon d'Expédition

**Fichier** : `transit/models.py`

Le BEX est l'entité centrale du système. Il représente un dossier d'expédition de marchandises pharmaceutiques, depuis l'envoi par le fournisseur jusqu'à la réception en entrepôt.

| Champ | Type | Contraintes | Description |
|-------|------|-------------|-------------|
| `numero_bex` | CharField(50) | `unique=True` | Identifiant unique du BEX (ex: `BEX-2026-001`) |
| `type_bex` | CharField(choices) | Défaut: MARITIME | Type d'acheminement : LOCAL, MARITIME, AERIEN, HORS_BEX |
| `fournisseur` | CharField(255) | Obligatoire | Nom du fournisseur (ex: SANOFI France, PFIZER Africa) |
| `date_creation` | DateTimeField | `auto_now_add=True` | Date de création automatique du dossier |
| `statut` | CharField(choices) | Défaut: EN_ATTENTE | Statut courant du dossier (7 valeurs possibles) |
| `date_depart` | DateField | Nullable | Date de départ de la marchandise du pays d'origine |
| `date_arrivee` | DateField | Nullable | Date d'arrivée prévue/effective au Burkina |
| `date_enlevement_prevue` | DateField | Nullable | Date prévue pour l'enlèvement en douane |
| `statut_douanier` | CharField(50) | Défaut: 'En attente' | État du dossier vis-à-vis de la douane |
| `observations` | TextField | Nullable | Notes libres sur le dossier |
| `agent_createur` | ForeignKey→User | `SET_NULL` | Agent transit ayant créé le dossier |
| `pharmacien` | ForeignKey→User | `SET_NULL`, Nullable | Pharmacien ayant effectué le pointage |
| `date_pointage_pharmacien` | DateTimeField | Nullable | Horodatage du pointage pharmacien |
| `rsi` | ForeignKey→User | `SET_NULL`, Nullable | RSI ayant réceptionné le dossier |
| `date_reception_rsi` | DateTimeField | Nullable | Horodatage de la réception par le RSI |

**Les 7 statuts du cycle de vie d'un BEX** :

```
EN_ATTENTE → POINTE → VALIDE → RECEPTIONNE → DEDOUANE → PRET_RECEPTION
                                                    ↑
                                              BLOQUE (état exceptionnel)
```

| Statut | Signification | Déclenché par |
|--------|---------------|---------------|
| `EN_ATTENTE` | Dossier créé, en attente de traitement | Création du BEX par l'agent |
| `POINTE` | Vérifié par le pharmacien | Pointage du pharmacien responsable |
| `VALIDE` | Approuvé par le chef de service | Action de validation (`/valider/`) |
| `RECEPTIONNE` | Réceptionné au niveau du RSI | Réception par l'administrateur RSI |
| `DEDOUANE` | Marchandise dédouanée | Upload automatique d'un document de type LIQUIDATION |
| `PRET_RECEPTION` | Prêt pour enlèvement final | Upload automatique d'un document de type REC165 |
| `BLOQUE` | Bloqué en douane ou pour non-conformité | Changement manuel par un utilisateur habilité |

#### 4.2.3 Modèle `BEXItem` — Ligne de facture d'un BEX

| Champ | Type | Description |
|-------|------|-------------|
| `bex` | ForeignKey→BEX | Dossier BEX parent (CASCADE) |
| `numero_conteneur` | CharField(50) | Numéro du conteneur physique |
| `designation_produit` | TextField | Description du produit pharmaceutique |
| `quantite` | PositiveIntegerField | Quantité de produits |
| `facture_fcfa` | DecimalField(20,2) | Montant de la facture en FCFA |
| `numero_facture` | CharField(100) | Numéro de la facture fournisseur |
| `adi` | CharField(50) | Référence ADI associée |
| `asi` | CharField(50) | Référence ASI associée |
| `numero_sylvie` | CharField(100) | Numéro d'enregistrement SYLVIE (système national) |
| `document` | CharField(100) | Référence du document associé |
| `statut_item` | CharField(100) | Statut individuel de la ligne |

#### 4.2.4 Modèle `Conteneur` — Conteneur physique

| Champ | Type | Description |
|-------|------|-------------|
| `numero_conteneur` | CharField(50) | Identifiant du conteneur (ex: CONT-001) |
| `bex` | ForeignKey→BEX | Dossier BEX parent (CASCADE) |

#### 4.2.5 Modèle `ADI` — Autorisation de Dédouanement à l'Importation

L'ADI est un document réglementaire délivré par l'ANRP (Agence Nationale de Régulation Pharmaceutique) autorisant l'importation de produits pharmaceutiques.

| Champ | Type | Description |
|-------|------|-------------|
| `numero_adi` | CharField(50), unique | Numéro unique de l'ADI |
| `bex` | ForeignKey→BEX | Lien optionnel vers un BEX |
| `fournisseur` | CharField(255) | Fournisseur des produits |
| `factures` | CharField(255) | Références des factures concernées |
| `nb_items` | PositiveIntegerField | Nombre de lignes/items |
| `quantite` | PositiveIntegerField | Quantité totale de produits |
| `asi` | PositiveIntegerField | Nombre d'ASI (Autorisations Sanitaires) |
| `cout` | DecimalField(20,2) | Coût total en FCFA |
| `pays` | CharField(100) | Pays d'origine |
| `date_depot` | DateField | Date de dépôt de la demande |
| `date_reception` | DateField | Date de réception/validation par l'organisme |
| `organisme_emetteur` | CharField, défaut 'ANRP' | Organisme ayant délivré l'ADI |
| `statut` | CharField(choices) | EN_ATTENTE → SOUMIS → VALIDE ou REJETE |

#### 4.2.6 Modèle `CCPQ` — Certificat de Contrôle Pharmaceutique et de Qualité

| Champ | Type | Description |
|-------|------|-------------|
| `numero_ccpq` | CharField(50), unique | Numéro du certificat |
| `bex` | ForeignKey→BEX | Lien optionnel vers un BEX |
| `numero_sylvie` | CharField(100) | Numéro d'enregistrement dans le système SYLVIE |
| `fob_euro` | DecimalField(20,2) | Valeur FOB en Euros |
| `fob_fcfa` | DecimalField(20,2) | Valeur FOB en FCFA |
| `date_depot` | DateField | Date de dépôt de la demande de contrôle |
| `date_resultat` | DateField | Date d'obtention du résultat |
| `resultat` | TextField | Description du résultat du contrôle |
| `motif_rejet` | TextField | Motif de rejet le cas échéant |
| `statut` | CharField(choices) | NON_DEMARRE → EN_ANALYSE → APPROUVE ou REJETE |

#### 4.2.7 Modèle `DocumentTransit` — Document numérisé

| Champ | Type | Description |
|-------|------|-------------|
| `bex` | ForeignKey→BEX | Dossier BEX associé |
| `conteneur` | ForeignKey→Conteneur | Ou conteneur associé |
| `fichier` | FileField | Fichier uploadé (stocké dans `media/transit/documents/`) |
| `type_document` | CharField(choices) | FACTURE, ADI, CCPQ, REC165, LIQUIDATION, AUTRE |
| `format` | CharField(choices) | PHYSIQUE ou NUMERIQUE |
| `date_upload` | DateTimeField | Date d'upload automatique |
| `agent_createur` | ForeignKey→User | Agent ayant uploadé le document |

#### 4.2.8 Modèle `AppSettings` — Paramètres globaux

**Fichier** : `core/models.py`

| Champ | Type | Description |
|-------|------|-------------|
| `key` | CharField(100), unique | Clé du paramètre (ex: `seuil_retard_bex`) |
| `value` | TextField | Valeur du paramètre |
| `description` | CharField(255) | Description lisible du paramètre |
| `updated_at` | DateTimeField | Date de dernière modification (auto) |

---

## 5. Système de Rôles et Permissions (RBAC)

### 5.1 Les trois rôles métier

Le système implémente un contrôle d'accès basé sur les rôles (**RBAC — Role-Based Access Control**) avec trois profils distincts reflétant l'organisation réelle de Laborex :

| Rôle | Code interne | Profil métier | Responsabilités |
|------|-------------|---------------|-----------------|
| **Agent Transit** | `AGENT` | Opérateur terrain | Crée et gère ses propres dossiers BEX, ADI, CCPQ. Uploade les documents. Importe les fichiers Excel. Ne voit que ses propres données |
| **Chef de Service** | `CHEF_SERVICE` | Superviseur / Pharmacien | Voit et modifie tous les dossiers de tous les agents. Valide les dossiers BEX. Accès au dashboard global |
| **Administrateur RSI** | `ADMIN` | Responsable SI | Gestion des utilisateurs (création, déblocage). Configuration des paramètres globaux. Lecture seule sur les dossiers métier. Accès au dashboard global |

### 5.2 Matrice des permissions détaillée

| Action | AGENT | CHEF_SERVICE | ADMIN |
|--------|:-----:|:------------:|:-----:|
| Créer un BEX/ADI/CCPQ | ✅ (les siens) | ✅ (tous) | ❌ |
| Modifier un dossier | ✅ (les siens) | ✅ (tous) | ❌ |
| Supprimer un dossier | ✅ (les siens) | ✅ (tous) | ❌ |
| Lire un dossier | ✅ (les siens) | ✅ (tous) | ✅ (tous, lecture seule) |
| Uploader un document | ✅ | ✅ | ❌ |
| Valider un BEX | ❌ | ✅ | ❌ |
| Importer un fichier Excel | ✅ | ✅ | ❌ |
| Voir le dashboard | ✅ (ses données) | ✅ (global) | ✅ (global) |
| Filtrer par agent (dashboard) | ❌ (forcé sur soi) | ✅ | ✅ |
| Exporter en Excel | ✅ (ses données) | ✅ (global) | ✅ (global) |
| Créer un utilisateur | ❌ | ❌ | ✅ |
| Débloquer un compte | ❌ | ❌ | ✅ |
| Modifier les paramètres | ❌ | ❌ | ✅ |

### 5.3 Implémentation technique des permissions

**Fichier** : `users/permissions.py`

Le système utilise 4 classes de permissions DRF :

**`IsAgentTransit`** : vérifie que l'utilisateur est authentifié ET a le rôle AGENT.

**`IsChefService`** : vérifie que l'utilisateur est authentifié ET a le rôle CHEF_SERVICE. Utilisée pour protéger l'action de validation des BEX.

**`IsAdminRSI`** : vérifie que l'utilisateur est authentifié ET a le rôle ADMIN.

**`CanManageTransit`** : permission composée la plus complexe du système. Elle implémente deux niveaux de contrôle :
- **`has_permission`** (niveau vue) : bloque toute écriture (POST, PUT, DELETE) pour les ADMIN. Autorise la lecture pour tous.
- **`has_object_permission`** (niveau objet) : pour un AGENT, vérifie qu'il est le créateur de l'objet (ou que l'objet est lié à un BEX qu'il a créé). Pour un CHEF_SERVICE, autorise tout. Pour un ADMIN, autorise uniquement la lecture.

**Fonction utilitaire `get_visible_objects`** : filtre automatiquement les querysets. Un AGENT ne voit que ses objets (filtre `agent_createur=user`). Un CHEF_SERVICE ou ADMIN voit tout.

### 5.4 Mécanisme de verrouillage de compte

**Fichier** : `users/signals.py`

Le système implémente un mécanisme de sécurité par **signaux Django** :

1. **Signal `user_login_failed`** : à chaque échec de connexion, le compteur `failed_login_attempts` est incrémenté. Si le compteur atteint **5**, le champ `is_active` est mis à `False`, bloquant ainsi toute connexion future.

2. **Signal `user_logged_in`** : à chaque connexion réussie, le compteur est remis à **0**.

3. **Déblocage** : seul un administrateur (ADMIN) peut débloquer un compte via l'endpoint `/api/users/unlock/`, qui remet `is_active=True` et `failed_login_attempts=0`.

---

## 6. Mécanisme des Signaux Django

### 6.1 Concept des signaux

Les **signaux Django** sont un mécanisme de communication inter-composants basé sur le patron **Observer**. Ils permettent à certaines parties du code de réagir automatiquement à des événements système (création d'un objet, connexion d'un utilisateur, etc.) sans couplage direct.

### 6.2 Signaux implémentés dans le projet

| Signal | Fichier | Événement déclencheur | Action automatique |
|--------|---------|----------------------|-------------------|
| `track_failed_login` | `users/signals.py` | Échec de connexion (`user_login_failed`) | Incrémente le compteur d'échecs, verrouille le compte après 5 tentatives |
| `reset_failed_login` | `users/signals.py` | Connexion réussie (`user_logged_in`) | Remet le compteur d'échecs à 0 |
| `update_bex_status_on_document_upload` | `transit/signals.py` | Création d'un DocumentTransit (`post_save`) | Si le document est de type LIQUIDATION → statut BEX = DEDOUANE. Si type REC165 → statut = PRET_RECEPTION |

### 6.3 Enregistrement des signaux

Les signaux sont enregistrés via la méthode `ready()` de la configuration de chaque application :

```python
# users/apps.py
class UsersConfig(AppConfig):
    name = 'users'
    def ready(self):
        import users.signals  # Enregistre les signaux au démarrage

# transit/apps.py
class TransitConfig(AppConfig):
    name = 'transit'
    def ready(self):
        import transit.signals
```
