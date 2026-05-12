# Application Transit - Moteur Métier & Dossiers Documentaires

Cette application gère les dossiers de transit (BEX), les documents associés et les flux de validation spécifiques à Laborex-Burkina.

## 🚀 Fonctionnalités Implémentées

### 1. Architecture des Dossiers (BEX)
- **Modèle BEX** : Gère les types (Local, Maritime, Aérien, Hors BEX) et les statuts de suivi.
- **Modèles Liés** : `ADI`, `CCPQ`, et `Conteneur` sont liés au BEX via des ForeignKeys.
- **Traçabilité** : Champs dédiés pour le pointage par le Pharmacien et la réception par le RSI.

### 2. Gestion Documentaire Centralisée
- **Modèle DocumentTransit** : Permet l'upload de fichiers (Factures, ADI, REC165, etc.) liés à un BEX ou à un Conteneur.
- **Automatisation (Signals)** : 
  - Upload d'une **Liquidation douanière** -> Statut BEX passe à `Dédouané`.
  - Upload d'un **REC165** -> Statut BEX passe à `Prêt pour réception`.

### 3. Logique Métier & Validation
- **Flux BEX Locaux** : 
  - `création par agent` (Statut: En attente)
  - `pointer-pharmacien` (Statut: Pointé) -> Réservé Chef de Service / Admin.
  - `valider-rsi` (Statut: Réceptionné) -> Réservé Admin (RSI).

## 📡 Endpoints API (DRF)

| Méthode | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/transit/bex/` | Liste filtrable par `type_bex` et `statut`. Recherche par `numero_bex`. |
| `GET` | `/api/transit/bex/{id}/dossier-complet/` | Récupère toutes les données (Conteneurs, ADI, Documents). |
| `POST` | `/api/transit/bex/{id}/upload-document/` | Upload d'un document pour un dossier spécifique. |
| `POST` | `/api/transit/bex/{id}/pointer-pharmacien/` | Action de pointage (Chef Service/Admin). |
| `POST` | `/api/transit/bex/{id}/valider-rsi/` | Action de validation finale (Admin). |

## 🛠 Installation & Setup

1. **Migrations** :
```bash
python manage.py makemigrations transit
python manage.py migrate
```

2. **Configuration Media** :
Les documents sont stockés dans le dossier `/media/transit/documents/`. Assurez-vous que ce dossier est accessible en écriture.
