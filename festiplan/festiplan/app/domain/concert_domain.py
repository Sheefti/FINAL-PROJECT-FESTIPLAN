"""
Logique métier pure du domaine Concert.
Pas de dépendance à SQLAlchemy ni à FastAPI.
"""
from datetime import datetime

from app.domain.errors import ConflictError, ValidationError


def validate_time_range(start_time: datetime, end_time: datetime) -> None:
    """Vérifie que end_time est strictement postérieur à start_time."""
    if end_time <= start_time:
        raise ValidationError("La date de fin doit être postérieure à la date de début")


def validate_within_festival(
    start_time: datetime,
    end_time: datetime,
    festival_start: datetime,
    festival_end: datetime,
) -> None:
    """Vérifie que le concert se situe entièrement dans la période du festival."""
    if start_time < festival_start or end_time > festival_end:
        raise ValidationError("Le concert doit se dérouler pendant la période du festival")


def overlaps(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    """Renvoie True si les deux créneaux se chevauchent (exclusif aux bornes)."""
    return start_a < end_b and start_b < end_a


def check_schedule_conflicts(
    concerts: list,
    artist_id: int,
    stage_id: int,
    start_time: datetime,
    end_time: datetime,
    exclude_id: int | None = None,
) -> None:
    """
    Vérifie les conflits de programmation parmi une liste de concerts actifs.

    Lève ConflictError si :
    - la scène est déjà occupée sur ce créneau
    - l'artiste est déjà programmé sur ce créneau

    :param concerts: liste d'objets ayant les attributs id, stage_id, artist_id,
                     start_time, end_time (peut être des ORM ou des dataclasses).
    :param exclude_id: identifiant du concert à ignorer (utile pour un reschedule).
    """
    for c in concerts:
        if exclude_id is not None and c.id == exclude_id:
            continue
        if overlaps(start_time, end_time, c.start_time, c.end_time):
            if c.stage_id == stage_id:
                raise ConflictError("Conflit : la scène est déjà occupée sur ce créneau")
            if c.artist_id == artist_id:
                raise ConflictError("Conflit : l'artiste est déjà programmé sur ce créneau")
