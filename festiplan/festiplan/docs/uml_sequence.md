# Diagramme de Séquence UML — Déplacement d'un Concert (RescheduleConcert)

Ce diagramme illustre le cas d'utilisation `RescheduleConcert`, qui implique
la vérification des règles de programmation, la persistance et une notification
best-effort. Il représente la correction des 3 défauts initiaux.

---

## Scénario nominal — Déplacement réussi

```mermaid
sequenceDiagram
    actor Client
    participant HTTP as concerts.py<br/>(Contrôleur HTTP)
    participant UC as RescheduleConcertUseCase
    participant Domain as concert_domain.py<br/>(Logique pure)
    participant ConcertRepo as ConcertRepository<br/>(Port sortant)
    participant FestivalRepo as FestivalRepository<br/>(Port sortant)
    participant Notif as EmailNotificationAdapter<br/>(Port sortant)

    Client->>HTTP: PATCH /concerts/42/reschedule<br/>{start_time, end_time}

    HTTP->>UC: execute(42, payload)

    Note over UC: 1. Vérification existence
    UC->>ConcertRepo: get(42)
    ConcertRepo-->>UC: concert (festival_id=1, artist_id=10, stage_id=1)

    Note over UC: 2. Vérification état festival (Défaut 3)
    UC->>FestivalRepo: get(1)
    FestivalRepo-->>UC: festival (status="preparation")
    UC->>UC: festival.status != PUBLISHED ✓

    Note over UC: 3. Validation de l'intervalle
    UC->>Domain: validate_time_range(start, end)
    Domain-->>UC: ✓ valide

    Note over UC: 4. Vérification dans la période festival
    UC->>Domain: validate_within_festival(start, end, fstart, fend)
    Domain-->>UC: ✓ dans la période

    Note over UC: 5. Vérification des conflits (Défaut 1)
    UC->>ConcertRepo: list_for_festival(1)
    ConcertRepo-->>UC: [concert_A, concert_B, ...]
    UC->>Domain: check_schedule_conflicts(concerts, artist_id, stage_id, start, end, exclude_id=42)
    Domain-->>UC: ✓ aucun conflit

    Note over UC: 6. Persistance
    UC->>UC: concert.start_time = new_start<br/>concert.end_time = new_end
    UC->>ConcertRepo: save(concert)
    ConcertRepo-->>UC: concert mis à jour

    Note over UC: 7. Notification best-effort (Défaut 2)
    UC->>Notif: notify("Concert #42 déplacé", "...")
    Notif-->>UC: (succès silencieux)

    UC-->>HTTP: concert mis à jour
    HTTP-->>Client: 200 OK {concert}
```

---

## Scénario — Conflit de scène (Défaut 1 — refus)

```mermaid
sequenceDiagram
    actor Client
    participant HTTP as concerts.py
    participant UC as RescheduleConcertUseCase
    participant Domain as concert_domain.py
    participant ConcertRepo as ConcertRepository

    Client->>HTTP: PATCH /concerts/42/reschedule<br/>{start: 14h, end: 16h}

    HTTP->>UC: execute(42, payload)
    UC->>ConcertRepo: get(42)
    ConcertRepo-->>UC: concert
    UC->>ConcertRepo: list_for_festival(1)
    ConcertRepo-->>UC: [concert_42, concert_B(stage=1, 14h-16h)]

    UC->>Domain: check_schedule_conflicts(...)
    Note over Domain: concert_B chevauche et est sur la même scène !
    Domain-->>UC: raise ConflictError("scène déjà occupée")

    UC-->>HTTP: raise ConflictError
    HTTP-->>Client: 409 Conflict<br/>{"detail": "Conflit : la scène est déjà occupée"}
```

---

## Scénario — Festival publié (Défaut 3 — refus)

```mermaid
sequenceDiagram
    actor Client
    participant HTTP as concerts.py
    participant UC as RescheduleConcertUseCase
    participant FestivalRepo as FestivalRepository

    Client->>HTTP: PATCH /concerts/42/reschedule

    HTTP->>UC: execute(42, payload)
    UC->>UC: get concert (ok)
    UC->>FestivalRepo: get(1)
    FestivalRepo-->>UC: festival (status="published")

    Note over UC: festival.status == PUBLISHED → interdit
    UC-->>HTTP: raise FestivalLockedError
    HTTP-->>Client: 409 Conflict<br/>{"detail": "Le festival est publié..."}
```

---

## Scénario — Panne de notification (Défaut 2 — succès métier maintenu)

```mermaid
sequenceDiagram
    actor Client
    participant HTTP as concerts.py
    participant UC as RescheduleConcertUseCase
    participant ConcertRepo as ConcertRepository
    participant Notif as EmailNotificationAdapter
    participant Log as Logger

    Client->>HTTP: PATCH /concerts/42/reschedule

    HTTP->>UC: execute(42, payload)
    Note over UC: Toutes les vérifications passent ✓
    UC->>ConcertRepo: save(concert)
    ConcertRepo-->>UC: concert persisté ✓

    UC->>Notif: notify(...)
    Note over Notif: send_email() → RuntimeError
    Notif->>Log: logger.warning("Échec notification...")
    Notif-->>UC: (exception avalée — best-effort)

    UC-->>HTTP: concert mis à jour ✓
    HTTP-->>Client: 200 OK {concert}
    Note over Client: La modification est réussie.<br/>Le client n'est pas trompé par un faux 500.
```
