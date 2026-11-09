# Diagnostic de l'Architecture Initiale — FestiPlan

## Résumé

L'application FestiPlan est fonctionnelle mais son architecture présente des défauts structurels significatifs, à la fois au niveau des règles métier et de l'organisation des responsabilités. Ce document identifie et localise chacun de ces défauts avant la refactorisation.

---

## Défauts métier intentionnels

### Défaut 1 — Conflits non vérifiés lors du déplacement d'un concert

**Localisation** : `app/services/scheduling_service.py` lignes 44–55

```python
# DÉFAUT INTENTIONNEL 1 : les conflits, équipements, dates du festival
# et statut publié ne sont pas contrôlés ici.
concert.start_time = payload.start_time
concert.end_time = payload.end_time
```

**Impact** : La méthode `reschedule_concert()` modifie les dates d'un concert sans vérifier :
- Si la scène est déjà occupée sur le nouveau créneau
- Si l'artiste est déjà programmé sur ce créneau (sur une autre scène)
- Si les nouvelles dates sortent de la période du festival
- Si les équipements requis sont toujours disponibles

Résultat possible : deux concerts sur la même scène au même moment, ou un artiste présent en deux endroits simultanément.

---

### Défaut 2 — Notification envoyée après commit, avec propagation de l'exception

**Localisation** : `app/services/scheduling_service.py` lignes 52–54

```python
self.db.commit(); self.db.refresh(concert)
# DÉFAUT INTENTIONNEL 2 : notification après commit ;
# une panne produit une réponse 500 après persistance.
self.notifications.notify_schedule_change(...)
```

**Impact** : Si `notify_schedule_change()` lève une `RuntimeError` (par exemple quand `FESTIPLAN_FAIL_NOTIFICATIONS=true`), la modification est déjà persistée en base, mais l'API retourne une erreur HTTP 500. Le client interprète cette réponse comme un échec de l'opération, alors que la modification a bel et bien eu lieu.

Résultat : état incohérent entre ce que la base contient et ce que le client croit s'être passé.

---

### Défaut 3 — Publication sans garde-fous, état non respecté

**Localisation** : `app/services/publication_service.py` ligne 12

```python
# Contrôle métier incomplet intentionnel : conflits et contraintes
# non vérifiés avant publication.
festival.status = "published"
```

Et dans `app/services/scheduling_service.py` lignes 57–61 :

```python
def cancel_concert(self, concert_id):
    concert = self.repo.get(concert_id)
    # Aucune vérification de l'état du festival
    concert.status = "cancelled"
```

**Impact** :
- Un festival peut être publié sans avoir aucun concert planifié
- Un festival publié peut voir ses concerts annulés ou déplacés librement
- L'état `published` n'a aucune signification fonctionnelle protégée

---

## Défauts architecturaux

### A — Accès direct à SQLAlchemy depuis les contrôleurs HTTP

**Localisation** : `app/api/concerts.py` lignes 17–18 et 32–33

```python
# Accès direct à SQLAlchemy depuis le contrôleur : défaut architectural.
c = db.query(Concert).filter(Concert.id == concert_id).first()
```

**Impact** : Le contrôleur HTTP (adaptateur entrant) dépend directement de SQLAlchemy (adaptateur sortant). La couche HTTP n'est plus isolable et la logique de récupération des données n'est pas testable sans base de données.

---

### B — Logique métier absente dans `incidents.py`

**Localisation** : `app/api/incidents.py` (entier)

```python
row = Incident(concert_id=payload.concert_id, ...)
db.add(row); db.commit(); db.refresh(row); return row
```

**Impact** : Le contrôleur crée directement une instance `Incident` et la persiste. Il n'existe aucun service ni cas d'utilisation pour la gestion des incidents. Toute règle métier future devrait être ajoutée dans le contrôleur.

---

### C — Absence de ports (interfaces abstraites)

**Impact** : Les services dépendent directement des classes concrètes `ConcertRepository`, `NotificationService`, etc. Il est impossible de substituer une implémentation (par exemple un repository en mémoire pour les tests) sans modifier le code de production.

Les cas d'utilisation ne peuvent pas être testés isolément.

---

### D — Duplication de logique de publication

**Localisation** : `services/festival_service.py:17–21` **et** `services/publication_service.py:8–15`

Deux services proposent une méthode `publish()`. L'une (dans `FestivalService`) ne notifie pas, l'autre (dans `PublicationService`) notifie mais ne gère pas l'erreur. Les deux accèdent directement à la DB sans passer par un port.

---

### E — État `published` représenté par une chaîne libre

**Localisation** : `models.py:13`

```python
status: Mapped[str] = mapped_column(String(30), default="preparation", nullable=False)
```

La valeur `"published"` est une chaîne non contrainte. Une faute de frappe comme `"publied"` passerait silencieusement. L'absence d'un value object ou d'un enum rend les transitions d'état impossibles à auditer statiquement.

---

### F — `SchedulingService` trop couplé

Le service `SchedulingService` cumule les responsabilités :
- Liste des concerts
- Vérification des conflits
- Création d'un concert
- Déplacement d'un concert
- Annulation d'un concert
- Notification

Chaque opération mélange orchestration, règles métier et accès à la persistance.

---

## Tableau récapitulatif

| # | Type | Localisation | Gravité |
|---|------|-------------|---------|
| 1 | Métier | `scheduling_service.py:50` | 🔴 Critique |
| 2 | Métier | `scheduling_service.py:53–54` | 🔴 Critique |
| 3 | Métier | `publication_service.py:12` | 🔴 Critique |
| A | Architecture | `api/concerts.py:17,32` | 🟠 Majeur |
| B | Architecture | `api/incidents.py` (entier) | 🟠 Majeur |
| C | Architecture | Toute la codebase | 🟠 Majeur |
| D | Architecture | `festival_service.py` + `publication_service.py` | 🟡 Mineur |
| E | Architecture | `models.py:13` | 🟡 Mineur |
| F | Architecture | `scheduling_service.py` | 🟡 Mineur |
