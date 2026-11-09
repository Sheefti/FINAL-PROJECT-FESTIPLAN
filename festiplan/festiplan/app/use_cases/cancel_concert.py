"""
Cas d'utilisation : Annuler un concert (CancelConcert).
"""
from app.domain.errors import FestivalLockedError, NotFoundError
from app.domain.value_objects import FestivalStatus
from app.ports.repositories import IConcertRepository, IFestivalRepository


class CancelConcertUseCase:
    """
    Annule un concert.

    Un concert appartenant à un festival publié ne peut plus être annulé
    directement (Défaut 3 — cohérence de l'état publié).
    """

    def __init__(
        self,
        concert_repo: IConcertRepository,
        festival_repo: IFestivalRepository,
    ):
        self.concert_repo = concert_repo
        self.festival_repo = festival_repo

    def execute(self, concert_id: int) -> object:
        concert = self.concert_repo.get(concert_id)
        if concert is None:
            raise NotFoundError("Concert introuvable")

        festival = self.festival_repo.get(concert.festival_id)
        if festival is not None and festival.status == FestivalStatus.PUBLISHED:
            raise FestivalLockedError(
                "Le festival est publié. Dépubliez-le avant d'annuler un concert."
            )

        concert.status = "cancelled"
        return self.concert_repo.save(concert)
