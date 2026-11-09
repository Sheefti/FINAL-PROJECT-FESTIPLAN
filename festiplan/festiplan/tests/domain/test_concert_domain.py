"""
Tests unitaires du domaine Concert.

Ces tests ne requièrent ni FastAPI ni SQLAlchemy : ils vérifient
la logique pure du domaine (invariants, chevauchements, validations).
"""
from datetime import datetime

import pytest

from app.domain.concert_domain import (
    check_schedule_conflicts,
    overlaps,
    validate_time_range,
    validate_within_festival,
)
from app.domain.errors import ConflictError, ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dt(h: int, m: int = 0):
    """Crée un datetime le 2027-06-20 à l'heure donnée."""
    return datetime(2027, 6, 20, h, m)


class _FakeConcert:
    """Double léger d'un concert pour les tests de conflit."""

    def __init__(self, cid, stage_id, artist_id, start, end, status="scheduled"):
        self.id = cid
        self.stage_id = stage_id
        self.artist_id = artist_id
        self.start_time = start
        self.end_time = end
        self.status = status


# ---------------------------------------------------------------------------
# overlaps()
# ---------------------------------------------------------------------------

class TestOverlaps:
    def test_complete_overlap(self):
        assert overlaps(_dt(10), _dt(12), _dt(10), _dt(12)) is True

    def test_partial_overlap_start(self):
        assert overlaps(_dt(9), _dt(11), _dt(10), _dt(12)) is True

    def test_partial_overlap_end(self):
        assert overlaps(_dt(11), _dt(13), _dt(10), _dt(12)) is True

    def test_contained(self):
        assert overlaps(_dt(10, 30), _dt(11, 30), _dt(10), _dt(12)) is True

    def test_adjacent_no_overlap(self):
        """Deux créneaux adjacents (borne à borne) ne se chevauchent pas."""
        assert overlaps(_dt(10), _dt(12), _dt(12), _dt(14)) is False

    def test_no_overlap_before(self):
        assert overlaps(_dt(8), _dt(10), _dt(10), _dt(12)) is False

    def test_no_overlap_after(self):
        assert overlaps(_dt(12), _dt(14), _dt(10), _dt(12)) is False


# ---------------------------------------------------------------------------
# validate_time_range()
# ---------------------------------------------------------------------------

class TestValidateTimeRange:
    def test_valid_range(self):
        validate_time_range(_dt(10), _dt(12))  # ne lève pas

    def test_equal_times_raises(self):
        with pytest.raises(ValidationError):
            validate_time_range(_dt(10), _dt(10))

    def test_end_before_start_raises(self):
        with pytest.raises(ValidationError):
            validate_time_range(_dt(12), _dt(10))


# ---------------------------------------------------------------------------
# validate_within_festival()
# ---------------------------------------------------------------------------

class TestValidateWithinFestival:
    FESTIVAL_START = datetime(2027, 6, 20, 0, 0)
    FESTIVAL_END = datetime(2027, 6, 22, 23, 59)

    def test_valid_within(self):
        validate_within_festival(_dt(10), _dt(12), self.FESTIVAL_START, self.FESTIVAL_END)

    def test_start_before_festival_raises(self):
        with pytest.raises(ValidationError):
            validate_within_festival(
                datetime(2027, 6, 19, 23, 0), _dt(12),
                self.FESTIVAL_START, self.FESTIVAL_END,
            )

    def test_end_after_festival_raises(self):
        with pytest.raises(ValidationError):
            validate_within_festival(
                _dt(10), datetime(2027, 6, 23, 1, 0),
                self.FESTIVAL_START, self.FESTIVAL_END,
            )


# ---------------------------------------------------------------------------
# check_schedule_conflicts()
# ---------------------------------------------------------------------------

class TestCheckScheduleConflicts:
    """
    Tests de non-régression — Défaut 1 :
    reschedule_concert() ne vérifiait pas les conflits.
    """

    def _concerts(self):
        return [
            _FakeConcert(1, stage_id=1, artist_id=10, start=_dt(10), end=_dt(12)),
            _FakeConcert(2, stage_id=2, artist_id=20, start=_dt(14), end=_dt(16)),
        ]

    def test_no_conflict(self):
        # Créneau libre sur une scène et un artiste différents
        check_schedule_conflicts(self._concerts(), artist_id=99, stage_id=99, start_time=_dt(10), end_time=_dt(12))

    def test_stage_conflict_raises(self):
        """Même scène, créneau qui chevauche."""
        with pytest.raises(ConflictError, match="scène"):
            check_schedule_conflicts(
                self._concerts(), artist_id=99, stage_id=1,
                start_time=_dt(11), end_time=_dt(13),
            )

    def test_artist_conflict_raises(self):
        """Même artiste, créneau qui chevauche."""
        with pytest.raises(ConflictError, match="artiste"):
            check_schedule_conflicts(
                self._concerts(), artist_id=10, stage_id=99,
                start_time=_dt(11), end_time=_dt(13),
            )

    def test_exclude_id_ignores_concert(self):
        """exclude_id permet d'ignorer le concert qu'on est en train de déplacer."""
        check_schedule_conflicts(
            self._concerts(), artist_id=10, stage_id=1,
            start_time=_dt(10), end_time=_dt(12),
            exclude_id=1,  # on exclut le concert 1 lui-même
        )

    def test_adjacent_slot_no_conflict(self):
        """Créneau adjacent (commence à la fin du précédent) : pas de conflit."""
        check_schedule_conflicts(
            self._concerts(), artist_id=99, stage_id=1,
            start_time=_dt(12), end_time=_dt(14),
        )
