"""
Cas d'utilisation : Programmer un concert (ScheduleConcert).

Orchestre les vérifications métier et délègue la persistance via les ports.
"""
from app.domain.concert_domain import (
    check_schedule_conflicts,
    validate_time_range,
    validate_within_festival,
)
from app.domain.errors import EquipmentError, NotFoundError, ValidationError
from app.ports.repositories import (
    IArtistRepository,
    IConcertRepository,
    IFestivalRepository,
    IStageRepository,
)


class ScheduleConcertUseCase:
    """
    Crée un nouveau concert dans un festival.

    Vérifications :
    - Festival, artiste et scène existent
    - La scène appartient au festival
    - Les dates sont valides et dans la période du festival
    - Pas de conflit de scène ni d'artiste
    - La scène dispose des équipements requis
    """

    def __init__(
        self,
        concert_repo: IConcertRepository,
        festival_repo: IFestivalRepository,
        artist_repo: IArtistRepository,
        stage_repo: IStageRepository,
    ):
        self.concert_repo = concert_repo
        self.festival_repo = festival_repo
        self.artist_repo = artist_repo
        self.stage_repo = stage_repo

    def execute(self, payload):
        """
        :param payload: objet avec festival_id, artist_id, stage_id, start_time, end_time
        :raises NotFoundError: si une entité est introuvable
        :raises ValidationError: si les dates sont invalides
        :raises ConflictError: si un créneau est déjà pris
        :raises EquipmentError: si les équipements sont insuffisants
        """
        festival = self.festival_repo.get(payload.festival_id)
        if festival is None:
            raise NotFoundError("Festival introuvable")

        artist = self.artist_repo.get(payload.artist_id)
        if artist is None:
            raise NotFoundError("Artiste introuvable")

        stage = self.stage_repo.get(payload.stage_id)
        if stage is None:
            raise NotFoundError("Scène introuvable")

        if stage.festival_id != festival.id:
            raise ValidationError("La scène n'appartient pas à ce festival")

        validate_time_range(payload.start_time, payload.end_time)
        validate_within_festival(
            payload.start_time, payload.end_time,
            festival.start_date, festival.end_date,
        )

        active_concerts = self.concert_repo.list_for_festival(payload.festival_id)
        check_schedule_conflicts(
            active_concerts,
            payload.artist_id,
            payload.stage_id,
            payload.start_time,
            payload.end_time,
        )

        # Vérification des équipements
        required = {x.strip() for x in artist.required_equipment.split(",") if x.strip()}
        available = {x.strip() for x in stage.available_equipment.split(",") if x.strip()}
        if not required.issubset(available):
            missing = required - available
            raise EquipmentError(
                f"La scène ne dispose pas des équipements requis : {', '.join(missing)}"
            )

        from app.models import Concert
        return self.concert_repo.create(
            Concert(
                festival_id=payload.festival_id,
                artist_id=payload.artist_id,
                stage_id=payload.stage_id,
                start_time=payload.start_time,
                end_time=payload.end_time,
            )
        )
