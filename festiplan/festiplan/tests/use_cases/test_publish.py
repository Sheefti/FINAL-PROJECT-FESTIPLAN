"""
Tests des cas d'utilisation PublishFestival.

Vérifie la correction du Défaut 3 : publication avec garde-fous.
"""
from datetime import datetime
from dataclasses import dataclass

import pytest

from app.domain.errors import NotFoundError, ValidationError
from app.domain.value_objects import FestivalStatus, ConcertStatus
from app.use_cases.publish_festival import PublishFestivalUseCase


# ---------------------------------------------------------------------------
# Doubles de test
# ---------------------------------------------------------------------------

@dataclass
class FakeFestival:
    id: int
    name: str
    start_date: datetime
    end_date: datetime
    status: str = FestivalStatus.PREPARATION


@dataclass
class FakeConcert:
    id: int
    festival_id: int
    artist_id: int
    stage_id: int
    start_time: datetime
    end_time: datetime
    status: str = ConcertStatus.SCHEDULED


class FakeFestivalRepo:
    def __init__(self, festivals):
        self._data = {f.id: f for f in festivals}

    def get(self, fid): return self._data.get(fid)
    def list(self): return list(self._data.values())
    def create(self, f): self._data[f.id] = f; return f
    def save(self, f): self._data[f.id] = f; return f


class FakeConcertRepo:
    def __init__(self, concerts):
        self._data = {c.id: c for c in concerts}

    def get(self, cid): return self._data.get(cid)
    def list_for_festival(self, fid):
        return [c for c in self._data.values() if c.festival_id == fid and c.status != "cancelled"]
    def create(self, c): self._data[c.id] = c; return c
    def save(self, c): self._data[c.id] = c; return c


class FakeNotificationPort:
    called = False
    def notify(self, subject, message): self.called = True


class FailingNotificationPort:
    called = False
    def notify(self, subject, message):
        self.called = True
        raise RuntimeError("Panne notification")


FESTIVAL_START = datetime(2027, 6, 20)
FESTIVAL_END = datetime(2027, 6, 22, 23, 59)
DT = lambda d, h: datetime(2027, 6, d, h)


def _festival(status=FestivalStatus.PREPARATION):
    return FakeFestival(id=1, name="Hellfest",
                        start_date=FESTIVAL_START, end_date=FESTIVAL_END,
                        status=status)


def _concert():
    return FakeConcert(id=1, festival_id=1, artist_id=10, stage_id=1,
                       start_time=DT(20, 10), end_time=DT(20, 12))


def _make_uc(festival_list, concert_list, notif=None):
    return PublishFestivalUseCase(
        festival_repo=FakeFestivalRepo(festival_list),
        concert_repo=FakeConcertRepo(concert_list),
        notification_port=notif or FakeNotificationPort(),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPublishFestivalDefaut3:
    """Défaut 3 — la publication doit avoir des garde-fous."""

    def test_publish_with_concerts_succeeds(self):
        f = _festival()
        uc = _make_uc([f], [_concert()])
        result = uc.execute(1)
        assert result.status == FestivalStatus.PUBLISHED

    def test_publish_empty_festival_raises(self):
        """Un festival sans concert ne peut pas être publié."""
        uc = _make_uc([_festival()], [])
        with pytest.raises(ValidationError, match="sans concerts"):
            uc.execute(1)

    def test_publish_already_published_raises(self):
        """Publier un festival déjà publié lève une erreur."""
        uc = _make_uc([_festival(FestivalStatus.PUBLISHED)], [_concert()])
        with pytest.raises(ValidationError, match="déjà publié"):
            uc.execute(1)

    def test_publish_unknown_festival_raises(self):
        uc = _make_uc([], [])
        with pytest.raises(NotFoundError):
            uc.execute(999)


class TestPublishNotificationDefaut2:
    """Défaut 2 — l'échec de la notification ne doit pas annuler la publication."""

    def test_notification_failure_does_not_rollback(self):
        failing = FailingNotificationPort()
        uc = _make_uc([_festival()], [_concert()], notif=failing)
        result = uc.execute(1)
        # La publication est réussie malgré la panne de notification
        assert result.status == FestivalStatus.PUBLISHED
        assert failing.called is True

    def test_notification_called_on_success(self):
        notif = FakeNotificationPort()
        uc = _make_uc([_festival()], [_concert()], notif=notif)
        uc.execute(1)
        assert notif.called is True
