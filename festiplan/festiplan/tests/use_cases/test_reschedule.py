"""
Tests des cas d'utilisation RescheduleConcert.

Utilise des repositories en mémoire et un port de notification simulé.
Pas de DB, pas de FastAPI.

Couvre les 3 défauts corrigés :
  - Défaut 1 : conflits vérifiés lors du déplacement
  - Défaut 2 : notification en échec n'empêche pas la réussite
  - Défaut 3 : festival publié bloque le déplacement
"""
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

import pytest

from app.domain.errors import ConflictError, FestivalLockedError, NotFoundError, ValidationError
from app.domain.value_objects import ConcertStatus, FestivalStatus
from app.use_cases.reschedule_concert import RescheduleConcertUseCase


# ---------------------------------------------------------------------------
# Doubles de test (repositories en mémoire)
# ---------------------------------------------------------------------------

@dataclass
class FakeConcert:
    id: int
    festival_id: int
    artist_id: int
    stage_id: int
    start_time: datetime
    end_time: datetime
    status: str = ConcertStatus.SCHEDULED


@dataclass
class FakeFestival:
    id: int
    name: str
    start_date: datetime
    end_date: datetime
    status: str = FestivalStatus.PREPARATION


class FakeConcertRepo:
    def __init__(self, concerts: list):
        self._concerts = {c.id: c for c in concerts}

    def get(self, concert_id: int):
        return self._concerts.get(concert_id)

    def list_for_festival(self, festival_id: int) -> list:
        return [c for c in self._concerts.values() if c.festival_id == festival_id and c.status != "cancelled"]

    def create(self, concert):
        self._concerts[concert.id] = concert
        return concert

    def save(self, concert):
        self._concerts[concert.id] = concert
        return concert


class FakeFestivalRepo:
    def __init__(self, festivals: list):
        self._festivals = {f.id: f for f in festivals}

    def get(self, festival_id: int):
        return self._festivals.get(festival_id)

    def list(self): return list(self._festivals.values())
    def create(self, f): self._festivals[f.id] = f; return f
    def save(self, f): self._festivals[f.id] = f; return f


class FakeNotificationPort:
    """Port de notification silencieux (succès)."""
    called = False

    def notify(self, subject, message):
        self.called = True


class FailingNotificationPort:
    """Port de notification qui lève systématiquement une exception."""
    called = False

    def notify(self, subject, message):
        self.called = True
        raise RuntimeError("Service de notification indisponible")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FESTIVAL_START = datetime(2027, 6, 20, 0, 0)
FESTIVAL_END = datetime(2027, 6, 22, 23, 59)


def _dt(day: int, hour: int):
    return datetime(2027, 6, day, hour, 0)


@pytest.fixture
def festival():
    return FakeFestival(
        id=1, name="Hellfest",
        start_date=FESTIVAL_START, end_date=FESTIVAL_END,
    )


@pytest.fixture
def concert(festival):
    return FakeConcert(id=1, festival_id=festival.id, artist_id=10, stage_id=1,
                       start_time=_dt(20, 10), end_time=_dt(20, 12))


@pytest.fixture
def other_concert(festival):
    """Un autre concert sur la même scène, 14h–16h."""
    return FakeConcert(id=2, festival_id=festival.id, artist_id=20, stage_id=1,
                       start_time=_dt(20, 14), end_time=_dt(20, 16))


@pytest.fixture
def published_festival(festival):
    festival.status = FestivalStatus.PUBLISHED
    return festival


def _make_uc(concert_list, festival, notification_port=None):
    return RescheduleConcertUseCase(
        concert_repo=FakeConcertRepo(concert_list),
        festival_repo=FakeFestivalRepo([festival]),
        notification_port=notification_port or FakeNotificationPort(),
    )


@dataclass
class ReschedulePayload:
    start_time: datetime
    end_time: datetime


# ---------------------------------------------------------------------------
# Tests — Défaut 1 : conflits vérifiés
# ---------------------------------------------------------------------------

class TestReschedulDefaut1Conflicts:
    """Les conflits doivent être détectés lors du déplacement."""

    def test_valid_reschedule_accepted(self, concert, festival):
        uc = _make_uc([concert], festival)
        result = uc.execute(1, ReschedulePayload(_dt(20, 13), _dt(20, 15)))
        assert result.start_time == _dt(20, 13)

    def test_stage_conflict_rejected(self, concert, other_concert, festival):
        """Un déplacement qui crée un chevauchement sur la même scène est refusé."""
        uc = _make_uc([concert, other_concert], festival)
        with pytest.raises(ConflictError, match="scène"):
            uc.execute(1, ReschedulePayload(_dt(20, 14, ), _dt(20, 16)))

    def test_artist_conflict_rejected(self, concert, festival):
        """Un artiste ne peut pas jouer simultanément sur deux scènes."""
        artist_elsewhere = FakeConcert(id=3, festival_id=1, artist_id=10, stage_id=2,
                                       start_time=_dt(20, 14), end_time=_dt(20, 16))
        uc = _make_uc([concert, artist_elsewhere], festival)
        with pytest.raises(ConflictError, match="artiste"):
            uc.execute(1, ReschedulePayload(_dt(20, 14), _dt(20, 16)))

    def test_self_overlap_excluded(self, concert, festival):
        """Le concert lui-même est exclu de la vérification de conflit."""
        uc = _make_uc([concert], festival)
        # Déplace au même créneau → pas de conflit avec soi-même
        result = uc.execute(1, ReschedulePayload(_dt(20, 10), _dt(20, 12)))
        assert result.start_time == _dt(20, 10)

    def test_dates_outside_festival_rejected(self, concert, festival):
        with pytest.raises(ValidationError):
            uc = _make_uc([concert], festival)
            uc.execute(1, ReschedulePayload(datetime(2027, 6, 19, 10), datetime(2027, 6, 19, 12)))

    def test_invalid_time_range_rejected(self, concert, festival):
        with pytest.raises(ValidationError):
            _make_uc([concert], festival).execute(
                1, ReschedulePayload(_dt(20, 12), _dt(20, 10))
            )


# ---------------------------------------------------------------------------
# Tests — Défaut 2 : notification en échec
# ---------------------------------------------------------------------------

class TestRescheduleDefaut2Notification:
    """La réussite métier est indépendante du succès de la notification."""

    def test_notification_failure_does_not_raise(self, concert, festival):
        """Si la notification échoue, l'opération réussit quand même."""
        failing = FailingNotificationPort()
        uc = _make_uc([concert], festival, failing)
        result = uc.execute(1, ReschedulePayload(_dt(20, 13), _dt(20, 15)))
        # L'opération a réussi malgré l'échec de la notification
        assert result.start_time == _dt(20, 13)
        assert failing.called is True

    def test_notification_called_on_success(self, concert, festival):
        notif = FakeNotificationPort()
        uc = _make_uc([concert], festival, notif)
        uc.execute(1, ReschedulePayload(_dt(20, 13), _dt(20, 15)))
        assert notif.called is True


# ---------------------------------------------------------------------------
# Tests — Défaut 3 : festival publié
# ---------------------------------------------------------------------------

class TestRescheduleDefaut3Published:
    """Un festival publié verrouille la programmation."""

    def test_reschedule_published_festival_raises(self, concert, published_festival):
        uc = _make_uc([concert], published_festival)
        with pytest.raises(FestivalLockedError):
            uc.execute(1, ReschedulePayload(_dt(20, 13), _dt(20, 15)))

    def test_reschedule_preparation_festival_allowed(self, concert, festival):
        uc = _make_uc([concert], festival)
        result = uc.execute(1, ReschedulePayload(_dt(20, 13), _dt(20, 15)))
        assert result.start_time == _dt(20, 13)


# ---------------------------------------------------------------------------
# Tests — Not Found
# ---------------------------------------------------------------------------

def test_reschedule_unknown_concert_raises(festival):
    uc = _make_uc([], festival)
    with pytest.raises(NotFoundError):
        uc.execute(999, ReschedulePayload(_dt(20, 10), _dt(20, 12)))
