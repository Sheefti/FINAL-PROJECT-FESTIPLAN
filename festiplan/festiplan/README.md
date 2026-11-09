# FestiPlan — API de Gestion de Festival

API FastAPI de gestion d'un festival de musique fictif, refactorisée selon l'**architecture hexagonale** et les principes **DDD**.

## Prérequis

- Python 3.11+
- Virtualenv disponible dans `../.venv/`

## Installation

```bash
# Depuis la racine du projet (festiplan/)
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

pip install -r festiplan/requirements.txt
```

## Configuration

Copier `.env.example` en `.env` et ajuster si nécessaire :

```env
FESTIPLAN_DATABASE_URL=sqlite:///./festiplan.db
FESTIPLAN_FAIL_NOTIFICATIONS=false
```

## Lancement

```bash
# Depuis festiplan/festiplan/
uvicorn app.main:app --reload
```

L'API est disponible sur http://localhost:8000  
Documentation interactive : http://localhost:8000/docs

## Initialisation des données de test

```bash
python -m app.seed
```

## Tests

```bash
# Depuis festiplan/festiplan/
# Windows :
..\.venv\Scripts\python.exe -m pytest tests/ -v

# Linux/macOS :
../.venv/bin/python -m pytest tests/ -v
```

### Structure des tests

```
tests/
├── domain/           ← Tests unitaires du domaine (sans DB ni FastAPI)
│   └── test_concert_domain.py
├── use_cases/        ← Tests des cas d'utilisation (avec repositories en mémoire)
│   ├── test_reschedule.py     ← Couvre les 3 défauts corrigés
│   └── test_publish.py
├── adapters/         ← Tests d'intégration HTTP (avec SQLite en mémoire)
│   ├── test_concerts_http.py  ← Tests de non-régression
│   └── test_festivals_http.py
└── ...               ← Anciens tests (conservés, toujours verts)
```

## Documentation technique

| Document | Localisation |
|----------|-------------|
| Diagnostic de l'architecture initiale | [`diagnostic.md`](diagnostic.md) |
| Diagramme de composants UML | [`docs/uml_components.md`](docs/uml_components.md) |
| Diagramme de séquence UML | [`docs/uml_sequence.md`](docs/uml_sequence.md) |
| Note d'architecture | [`docs/architecture_note.md`](docs/architecture_note.md) |

## Architecture

```
app/
├── domain/        ← Logique métier pure (sans dépendance)
├── ports/         ← Interfaces abstraites (contrats)
├── use_cases/     ← Cas d'utilisation applicatifs
├── repositories/  ← Adaptateurs SQLAlchemy (implémentent les ports)
├── services/      ← Adaptateurs de notification
└── api/           ← Contrôleurs FastAPI (adaptateurs HTTP)
```

## Défauts corrigés

| Défaut | Description | Correction |
|--------|-------------|------------|
| **Défaut 1** | `reschedule_concert()` ignorait les conflits | `check_schedule_conflicts()` appelé dans `RescheduleConcertUseCase` |
| **Défaut 2** | Panne notification → HTTP 500 après persistance | Notification best-effort dans `EmailNotificationAdapter` |
| **Défaut 3** | Festival publié sans garde-fous | `PublishFestivalUseCase` + verrou `FestivalLockedError` |
