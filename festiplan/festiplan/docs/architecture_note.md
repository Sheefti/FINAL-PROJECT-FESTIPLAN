# Note d'Architecture — FestiPlan

## 1. Défauts identifiés dans l'architecture initiale

### Défauts métier

**Défaut 1** : `reschedule_concert()` ne vérifiait ni les conflits de scène/artiste, ni les dates hors festival. Résultat : il était possible de créer deux concerts sur la même scène au même moment.

**Défaut 2** : La notification était envoyée _après_ le `db.commit()`. Si elle levait une `RuntimeError`, l'API retournait HTTP 500 alors que la modification était déjà persistée. Le client était trompé sur l'état réel de la base.

**Défaut 3** : Un festival pouvait être publié sans concert planifié. L'état `published` n'avait aucun effet protecteur : reschedule et annulation continuaient à fonctionner librement sur un festival publié.

### Défauts architecturaux

- Accès direct à SQLAlchemy depuis les contrôleurs HTTP (`concerts.py`)
- Absence totale de couche service pour les incidents (`incidents.py`)
- Aucun port (interface abstraite) : tests isolés impossibles
- `SchedulingService` = classe fourre-tout mêlant orchestration, règles métier et persistance
- État `published` représenté par une chaîne de caractères libre

---

## 2. Responsabilités de chaque couche

### Domaine (`app/domain/`)

Contient la logique métier pure, sans aucune dépendance externe.

- `errors.py` : exceptions typées (`ConflictError`, `FestivalLockedError`, `ValidationError`…)
- `value_objects.py` : `FestivalStatus` et `ConcertStatus` comme enums stricts — plus de chaînes libres
- `concert_domain.py` : fonctions pures (`overlaps`, `check_schedule_conflicts`, `validate_time_range`, `validate_within_festival`)

Règle : ce package ne dépend d'aucun autre package de l'application.

### Ports (`app/ports/`)

Définit les _contrats_ dont les cas d'utilisation ont besoin.

- `repositories.py` : ABCs pour chaque repository (`IConcertRepository`, etc.)
- `notifications.py` : `INotificationPort` avec la contrainte contractuelle que `notify()` ne propage jamais d'exception

Règle : les ports ne dépendent que du domaine.

### Cas d'utilisation (`app/use_cases/`)

Orchestre les objets métier et délègue à la persistance via les ports.

- `ScheduleConcertUseCase` : vérifie toutes les règles, puis persiste
- `RescheduleConcertUseCase` : corrige les 3 défauts (conflits + notification + verrou festival)
- `CancelConcertUseCase` : vérifie l'état du festival avant annulation
- `PublishFestivalUseCase` : exige au moins un concert avant publication
- `ReportIncidentUseCase` : extrait la logique incidents du contrôleur

Règle : les cas d'utilisation dépendent du domaine et des ports, jamais des adaptateurs.

### Adaptateurs sortants (`app/repositories/`, `app/services/`)

Implémentent les ports avec des technologies concrètes.

- Repositories SQLAlchemy : implémentent les interfaces `IXxxRepository`
- `EmailNotificationAdapter` : implémente `INotificationPort`, avale les exceptions en interne (best-effort)

Règle : un adaptateur peut dépendre de n'importe quel outil technique, mais ne contient aucune logique métier.

### Adaptateurs entrants (`app/api/`)

Contrôleurs FastAPI qui traduisent les requêtes HTTP en appels aux cas d'utilisation.

Règle : un contrôleur ne contient aucune logique métier ni accès direct à SQLAlchemy.

---

## 3. Ports et adaptateurs créés

| Port | Implémentation | Utilité |
|------|---------------|---------|
| `IConcertRepository` | `ConcertRepository` | Rend les cas d'utilisation testables sans DB |
| `IFestivalRepository` | `FestivalRepository` | Idem |
| `IStageRepository` | `StageRepository` | Idem |
| `IArtistRepository` | `ArtistRepository` | Idem |
| `IIncidentRepository` | `IncidentRepository` | Idem |
| `INotificationPort` | `EmailNotificationAdapter` | Permet de tester sans envoyer d'email |

---

## 4. Entités, value objects, invariants

### Value Objects

- `FestivalStatus` (enum) : `preparation` → `published` — transition à sens unique
- `ConcertStatus` (enum) : `scheduled` → `cancelled`

### Invariants du domaine (protégés dans `concert_domain.py`)

- `end_time > start_time`
- `start_time >= festival.start_date AND end_time <= festival.end_date`
- Pas de chevauchement de scène : `∀ c ∈ concerts_actifs, ¬overlaps(new, c) OR c.stage_id ≠ stage_id`
- Pas de chevauchement d'artiste : `∀ c ∈ concerts_actifs, ¬overlaps(new, c) OR c.artist_id ≠ artist_id`

### Agrégats implicites

Le modèle ne définit pas d'agrégat DDD formel (trop prescriptif pour ce projet), mais `Festival` joue le rôle de racine d'agrégat : toutes les opérations sur ses concerts vérifient son état.

---

## 5. Correction des trois défauts

### Défaut 1 — Conflits lors du reschedule

`RescheduleConcertUseCase.execute()` appelle `check_schedule_conflicts()` (logique pure du domaine) avant de persister. Les conflits de scène et d'artiste sont vérifiés en excluant le concert en cours de déplacement.

### Défaut 2 — Notification best-effort

Le contrat de `INotificationPort` stipule que `notify()` ne propage jamais d'exception. `EmailNotificationAdapter` attrape toute exception et la logue. `RescheduleConcertUseCase` enveloppe l'appel dans un `try/except` supplémentaire pour garantir ce comportement même avec une implémentation non conforme. La persistance précède toujours la notification.

### Défaut 3 — État publié

`FestivalStatus.PUBLISHED` est un enum strict. `RescheduleConcertUseCase` et `CancelConcertUseCase` vérifient cet état et lèvent `FestivalLockedError` → HTTP 409. `PublishFestivalUseCase` vérifie la présence d'au moins un concert actif avant de changer le statut.

---

## 6. Stratégie de tests

| Niveau | Localisation | Technologie | Description |
|--------|-------------|-------------|-------------|
| Domaine (unitaire) | `tests/domain/` | Python pur | `overlaps`, conflits, validations — aucune dépendance |
| Cas d'utilisation | `tests/use_cases/` | Doubles en mémoire | Repositories en mémoire, `FailingNotificationPort` |
| Adaptateurs (intégration) | `tests/adapters/` | FastAPI TestClient + SQLite | Routes HTTP bout-en-bout |
| Non-régression (anciens) | `tests/` (racine) | FastAPI TestClient | Tests initiaux conservés et toujours verts |

**59 tests passent** — aucune régression introduite.

Les tests du domaine et des cas d'utilisation ne démarrent ni FastAPI ni SQLite.

---

## 7. Limites restantes et compromis

**Pas de dépublication** : La règle "festival publié = verrouillé" a été choisie pour sa simplicité et sa cohérence. Une procédure de dépublication pourrait être ajoutée (nouveau use case `UnpublishFestival`) si le besoin se confirme.

**Pas de gestion asynchrone** : La notification est synchrone et best-effort. Dans un système de production, une file de messages (Celery, Redis Queue) permettrait une meilleure fiabilité. Ce choix est proportionné à l'échelle du projet.

**Models SQLAlchemy partagés** : Les cas d'utilisation importent encore `app.models.Concert` pour créer des instances. Une couche de mapping (data mapper pattern) isolerait complètement le domaine, au prix d'une complexité supplémentaire non justifiée ici.

**Pas de Bounded Context formalisé** : Le projet est trop petit pour bénéficier d'une séparation en contextes. Les concepts DDD appliqués (value objects, invariants, agrégat implicite) sont ceux qui apportent une valeur réelle sans sur-ingénierie.
