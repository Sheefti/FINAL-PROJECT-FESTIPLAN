"""
Cas d'utilisation : Publier un festival (PublishFestival).

CORRECTION Défaut 3 — Publication sans garde-fous :
    Avant de publier, on vérifie qu'il y a au moins un concert planifié.
    La publication verrouille le festival : reschedule et annulation sont
    ensuite refusés.

CORRECTION Défaut 2 — Notification best-effort :
    La notification est envoyée après persistance. Si elle échoue,
    l'erreur est loggée, pas propagée.
"""
import logging

from app.domain.errors import NotFoundError, ValidationError
from app.domain.value_objects import FestivalStatus
from app.ports.notifications import INotificationPort
from app.ports.repositories import IConcertRepository, IFestivalRepository

logger = logging.getLogger(__name__)


class PublishFestivalUseCase:
    """
    Publie un festival.

    Pré-conditions :
    - Festival existe et est en état 'preparation'
    - Au moins un concert actif est planifié
    Post-condition :
    - festival.status = 'published'
    - Notification envoyée (best-effort)
    """

    def __init__(
        self,
        festival_repo: IFestivalRepository,
        concert_repo: IConcertRepository,
        notification_port: INotificationPort,
    ):
        self.festival_repo = festival_repo
        self.concert_repo = concert_repo
        self.notification_port = notification_port

    def execute(self, festival_id: int) -> object:
        """
        :raises NotFoundError: festival introuvable
        :raises ValidationError: festival déjà publié ou sans concerts
        """
        festival = self.festival_repo.get(festival_id)
        if festival is None:
            raise NotFoundError("Festival introuvable")

        if festival.status == FestivalStatus.PUBLISHED:
            raise ValidationError("Le festival est déjà publié")

        concerts = self.concert_repo.list_for_festival(festival_id)
        if not concerts:
            raise ValidationError(
                "Impossible de publier un festival sans concerts planifiés"
            )

        festival.status = FestivalStatus.PUBLISHED
        updated = self.festival_repo.save(festival)

        # Notification best-effort — Défaut 2
        try:
            self.notification_port.notify(
                subject=f"Planning du festival '{festival.name}' publié",
                message=f"Le planning du festival {festival.name} est maintenant disponible.",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Notification échouée pour la publication du festival %s : %s",
                festival_id,
                exc,
            )

        return updated
