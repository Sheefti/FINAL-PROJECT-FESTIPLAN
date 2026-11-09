# Diagramme de Composants UML — FestiPlan

Ce diagramme représente l'architecture hexagonale réelle de FestiPlan après refactorisation.

## Vue d'ensemble

```mermaid
graph TB
    subgraph HTTP["🌐 Adaptateurs Entrants (HTTP)"]
        FEST_CTRL["festivals.py<br/>APIRouter"]
        CONC_CTRL["concerts.py<br/>APIRouter"]
        INC_CTRL["incidents.py<br/>APIRouter"]
        ART_CTRL["artists.py<br/>APIRouter"]
        STG_CTRL["stages.py<br/>APIRouter"]
    end

    subgraph APP["⚙️ Application — Cas d'utilisation"]
        UC_SCHED["ScheduleConcertUseCase"]
        UC_RESCH["RescheduleConcertUseCase"]
        UC_CANCEL["CancelConcertUseCase"]
        UC_PUBLISH["PublishFestivalUseCase"]
        UC_INC["ReportIncidentUseCase"]
    end

    subgraph DOMAIN["🏛️ Domaine"]
        ERR["domain/errors.py<br/>DomainError, ConflictError<br/>FestivalLockedError…"]
        VO["domain/value_objects.py<br/>FestivalStatus, ConcertStatus"]
        LOGIC["domain/concert_domain.py<br/>overlaps(), check_conflicts()<br/>validate_time_range()"]
    end

    subgraph PORTS["🔌 Ports (Contrats)"]
        P_CONC["IConcertRepository"]
        P_FEST["IFestivalRepository"]
        P_STG["IStageRepository"]
        P_ART["IArtistRepository"]
        P_INC["IIncidentRepository"]
        P_NOTIF["INotificationPort"]
    end

    subgraph ADAPTERS_OUT["🗄️ Adaptateurs Sortants"]
        subgraph REPOS["Persistance SQLAlchemy"]
            R_CONC["ConcertRepository"]
            R_FEST["FestivalRepository"]
            R_STG["StageRepository"]
            R_ART["ArtistRepository"]
            R_INC["IncidentRepository"]
        end
        subgraph NOTIF["Notification"]
            EMAIL["EmailNotificationAdapter"]
        end
    end

    subgraph INFRA["🏗️ Infrastructure"]
        DB["SQLite / SQLAlchemy<br/>festiplan.db"]
        FAKE_EMAIL["email_sender.py<br/>send_email()"]
    end

    %% Flux HTTP → Use Cases
    FEST_CTRL -->|"publish(id)"| UC_PUBLISH
    CONC_CTRL -->|"create(payload)"| UC_SCHED
    CONC_CTRL -->|"reschedule(id, payload)"| UC_RESCH
    CONC_CTRL -->|"cancel(id)"| UC_CANCEL
    INC_CTRL -->|"report(payload)"| UC_INC

    %% Use Cases → Domaine
    UC_RESCH --> LOGIC
    UC_SCHED --> LOGIC
    UC_RESCH --> VO
    UC_CANCEL --> VO
    UC_PUBLISH --> VO

    %% Use Cases → Ports
    UC_SCHED -->|"utilise"| P_CONC
    UC_SCHED -->|"utilise"| P_FEST
    UC_SCHED -->|"utilise"| P_ART
    UC_SCHED -->|"utilise"| P_STG
    UC_RESCH -->|"utilise"| P_CONC
    UC_RESCH -->|"utilise"| P_FEST
    UC_RESCH -->|"utilise"| P_NOTIF
    UC_CANCEL -->|"utilise"| P_CONC
    UC_CANCEL -->|"utilise"| P_FEST
    UC_PUBLISH -->|"utilise"| P_FEST
    UC_PUBLISH -->|"utilise"| P_CONC
    UC_PUBLISH -->|"utilise"| P_NOTIF
    UC_INC -->|"utilise"| P_CONC
    UC_INC -->|"utilise"| P_INC

    %% Ports → Adaptateurs (implémentation)
    P_CONC -.->|"implémenté par"| R_CONC
    P_FEST -.->|"implémenté par"| R_FEST
    P_STG -.->|"implémenté par"| R_STG
    P_ART -.->|"implémenté par"| R_ART
    P_INC -.->|"implémenté par"| R_INC
    P_NOTIF -.->|"implémenté par"| EMAIL

    %% Adaptateurs → Infrastructure
    R_CONC --> DB
    R_FEST --> DB
    R_STG --> DB
    R_ART --> DB
    R_INC --> DB
    EMAIL --> FAKE_EMAIL
```

---

## Légende des couches

| Couche | Rôle | Dépendances |
|--------|------|-------------|
| **Adaptateurs entrants** | Traduit HTTP → cas d'utilisation | Cas d'utilisation + ports |
| **Cas d'utilisation** | Orchestre les règles métier | Domaine + ports |
| **Domaine** | Logique pure, invariants | Aucune |
| **Ports** | Contrats abstraits | Aucune |
| **Adaptateurs sortants** | Implémentations concrètes | Infrastructure |
| **Infrastructure** | Base de données, email | Externe |

---

## Règle fondamentale

> Le **domaine** et les **cas d'utilisation** ne dépendent jamais des adaptateurs.  
> Toute dépendance est inversée via les ports (Dependency Inversion Principle).

---

## Structure des fichiers

```
app/
├── domain/
│   ├── errors.py           ← Exceptions métier typées
│   ├── value_objects.py    ← FestivalStatus, ConcertStatus (enums)
│   └── concert_domain.py   ← Logique pure (overlaps, conflits, validation)
│
├── ports/
│   ├── repositories.py     ← IConcertRepository, IFestivalRepository…
│   └── notifications.py    ← INotificationPort
│
├── use_cases/
│   ├── schedule_concert.py
│   ├── reschedule_concert.py   ← Défauts 1, 2, 3 corrigés
│   ├── cancel_concert.py
│   ├── publish_festival.py     ← Défaut 3 corrigé
│   └── report_incident.py
│
├── repositories/           ← Adaptateurs SQLAlchemy (implémentent les ports)
│   ├── concert_repository.py
│   ├── festival_repository.py
│   ├── stage_repository.py
│   ├── artist_repository.py
│   └── incident_repository.py
│
├── services/
│   └── notification_service.py ← EmailNotificationAdapter (best-effort)
│
└── api/                    ← Adaptateurs HTTP (contrôleurs FastAPI)
    ├── concerts.py
    ├── festivals.py
    ├── incidents.py
    ├── artists.py
    └── stages.py
```
