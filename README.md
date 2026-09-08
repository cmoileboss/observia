# Observia

API FastAPI qui agrège et croise les offres d'emploi France Travail, les formations et les codes ROME afin d'exposer des indicateurs sur l'emploi et la formation en France.

## Préalables

- Python 3.x
- Git
- PostgreSQL (une base nommée selon `DATABASE_NAME` doit être accessible)

## Installation

### 1. Cloner le dépôt GIT

```bash
git clone https://github.com/cmoileboss/observia.git
cd observia
```

### 2. Créer et activer l'environnement virtuel

```bash
python -m venv .venv
```

**Windows (PowerShell) :**
```powershell
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS :**
```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

### 3. Configurer les variables d'environnement

Copier le fichier `.env.example` vers `.env` et renseigner les valeurs :

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `CLIENT_ID` | Identifiant client de l'application Francetravail.io |
| `SECRET_ID` | Secret de l'application Francetravail.io |
| `X-INSEE-Api-Key-Integration` | Clé d'intégration de l'API INSEE (Sirene) |
| `DATABASE_NAME` | Nom de la base de données PostgreSQL (défaut : `observia_emploi_db`) |
| `DATABASE_HOST` | Hôte du serveur PostgreSQL (défaut : `localhost`) |
| `DATABASE_PORT` | Port du serveur PostgreSQL (défaut : `5432`) |
| `DATABASE_USER` | Utilisateur PostgreSQL |
| `DATABASE_PASSWORD` | Mot de passe PostgreSQL |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Durée de validité (en minutes) des tokens JWT |
| `SECRET_KEY` | Clé secrète utilisée pour signer les tokens JWT |
| `ALGORITHM` | Algorithme de signature des tokens JWT (ex. `HS256`) |
| `ADMIN_EMAIL` | Email de l'utilisateur admin créé automatiquement au démarrage de l'API |
| `ADMIN_PASSWORD` | Mot de passe de l'utilisateur admin créé automatiquement au démarrage de l'API |

Toutes les variables sans valeur par défaut sont obligatoires : l'API refuse de démarrer si l'une d'entre elles est manquante.

## Lancer l'API

```bash
python main.py
```

L'API est alors accessible sur `http://localhost:8000`.

La documentation interactive est générée automatiquement par FastAPI :
- Swagger UI : `http://localhost:8000/docs`
- ReDoc : `http://localhost:8000/redoc`

### Initialisation des données

Au premier démarrage, la base est créée mais reste vide (à l'exception de l'utilisateur admin). Il faut appeler la route `POST /api/populatedb` (en tant qu'admin) pour lancer le pipeline d'import et d'enrichissement des données.  
Si vous supprimez l'utilisateur admin, il faudra relancer l'API.

## Routes exposées

### Authentification (`/auth`)

| Méthode | Route | Description | Accès |
|---|---|---|---|
| POST | `/auth/register` | Crée un compte utilisateur (rôle `user`) | Public |
| POST | `/auth/login` | Authentifie un utilisateur et dépose le JWT dans un cookie httpOnly | Public |
| POST | `/auth/logout` | Supprime le cookie d'authentification | Public |
| GET | `/auth/me` | Retourne le compte de l'utilisateur connecté | Authentifié |
| DELETE | `/auth/me` | Supprime le compte de l'utilisateur connecté | Authentifié |
| GET | `/auth/` | Liste tous les utilisateurs | Admin |
| GET | `/auth/{user_id}` | Retourne un utilisateur par son identifiant | Admin |

### API métier (`/api`)

| Méthode | Route | Description | Accès |
|---|---|---|---|
| POST | `/api/populatedb` | Lance le pipeline d'initialisation de la base de données | Admin |
| GET | `/api/job/{job_id}/formations` | Retourne les formations pertinentes pour une offre | Authentifié |
| GET | `/api/bestskills` | Retourne les compétences les plus fréquentes dans les offres | Authentifié |
| GET | `/api/formations/historique` | Retourne les indicateurs de formations par région/trimestre (params `region`, `quarter`) | Authentifié |

### Routes CRUD génériques

Les ressources suivantes exposent chacune les routes `GET /<ressource>/` (liste paginée, params `skip`, `limit`) et `GET /<ressource>/{entity_id}` (détail) :

| Ressource | Préfixe |
|---|---|
| Compétences | `/competences` |
| Formations | `/formations` |
| Flux mensuels de formation | `/formation-flux-mensuel` |
| Offres | `/offres` |
| Codes ROME | `/rome-codes` |

Toutes ces routes nécessitent d'être authentifié (cookie `access_token`).

## Limitation de débit

Les routes sont soumises à une limite d'appels (`slowapi`), 30 par minutes sur la plupart des lectures et 5 par minutes sur l'inscription. La limite est appliquée par utilisateur authentifié (via le JWT) ou, à défaut, par adresse IP.

## Logs

Les logs sont écrits à la fois sur la console et dans un fichier tournant `logs/app.log` (5 fichiers de sauvegarde max, 1 Mo chacun). Le niveau de log et le chemin du fichier sont configurables via les variables d'environnement `LOG_LEVEL` (défaut : `INFO`) et `LOG_FILE` (défaut : `logs/app.log`), voir [logging_config.py](logging_config.py).

