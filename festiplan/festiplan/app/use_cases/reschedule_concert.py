"""
Cas d'utilisation : Déplacer un concert (RescheduleConcert).

CORRECTIONS des 3 défauts initiaux :

Défaut 1 — Conflits non vérifiés :
    reschedule_concert() vérifie maintenant les conflits de scène et d'artiste,
    les dates hors festival, et la validité de l'intervalle.

Défaut 2 — Notification après commit :
    La persistance est effectuée en premier. Si la notification échoue,
    l'erreur est loggée mais NON propagée. La réponse HTTP indique le succès
    de l'opération métier (ce qui s'est réellement passé).

Défaut 3 — Festival publié :
    Un concert appartenant à un festival publié ne peut plus être déplacé.
    L'appel lève FestivalLockedError → HTTP 409.
"""
import logging

from app.domain.concert_domain import (
    check_schedule_conflicts,
    validate_time_range,
    validate_within_festival,
)
from app.domain.errors import FestivalLockedError, NotFoundError
from app.domain.value_objects import FestivalStatus
from app.ports.notifications import INotificationPort
from app.ports.repositories import IConcertRepository, IFestivalRepository

logger = logging.getLogger(__name__)


class RescheduleConcertUseCase:
    """
    Déplace un concert existant vers un nouveau créneau.

    Vérifie (dans l'ordre) :
    1. Concert existant
    2. Festival non publié  ← Défaut 3
    3. Intervalle de temps valide
    4. Créneau dans la période du festival
    5. Absence de conflits (scène + artiste) ← Défaut 1
    6. Persiste, puis notifie (best-effort) ← Défaut 2
    """

    def __init__(
        self,
        concert_repo: IConcertRepository,
        festival_repo: IFestivalRepository,
        notification_port: INotificationPort,
    ):
        self.concert_repo = concert_repo
        self.festival_repo = festival_repo
        self.notification_port = notification_port

    def execute(self, concert_id: int, payload) -> object:
        """
        :param concert_id: identifiant du concert à déplacer
        :param payload: objet avec start_time et end_time
        :raises NotFoundError: concert introuvable
        :raises FestivalLockedError: festival déjà publié ← Défaut 3
        :raises ValidationError: dates invalides
        :raises ConflictError: créneau déjà occupé ← Défaut 1
        :return: le concert mis à jour
        """
        # 1. Concert existant
        concert = self.concert_repo.get(concert_id)
        if concert is None:
            raise NotFoundError("Concert introuvable")

        # 2. Festival non publié — Défaut 3
        festival = self.festival_repo.get(concert.festival_id)
        if festival is not None and festival.status == FestivalStatus.PUBLISHED:
            raise FestivalLockedError(
                "Le festival est publié. Dépubliez-le avant de modifier la programmation."
            )

        # 3. Validité de l'intervalle
        validate_time_range(payload.start_time, payload.end_time)

        # 4. Dans la période du festival
        if festival is not None:
            validate_within_festival(
                payload.start_time, payload.end_time,
                festival.start_date, festival.end_date,
            )

        # 5. Vérification des conflits — Défaut 1
        active_concerts = self.concert_repo.list_for_festival(concert.festival_id)
        check_schedule_conflicts(
            active_concerts,
            concert.artist_id,
            concert.stage_id,
            payload.start_time,
            payload.end_time,
            exclude_id=concert_id,
        )

        # 6. Persistance
        concert.start_time = payload.start_time
        concert.end_time = payload.end_time
        updated = self.concert_repo.save(concert)

        # Notification best-effort — Défaut 2
        # Une erreur de notification ne fait PAS échouer l'opération.
        try:
            self.notification_port.notify(
                subject=f"Concert #{concert_id} déplacé",
                message=f"Concert déplacé au {updated.start_time.isoformat()}",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Notification échouée pour le concert %s (modification persistée) : %s",
                concert_id,
                exc,
            )

        return updated
