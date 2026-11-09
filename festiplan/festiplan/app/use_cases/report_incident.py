"""
Cas d'utilisation : Enregistrer un incident (ReportIncident).

Extrait la logique qui était directement dans le contrôleur HTTP incidents.py.
"""
from datetime import datetime

from app.domain.errors import NotFoundError
from app.models import Incident
from app.ports.repositories import IConcertRepository, IIncidentRepository


class ReportIncidentUseCase:
    """Enregistre un incident survenu pendant un concert."""

    def __init__(
        self,
        concert_repo: IConcertRepository,
        incident_repo: IIncidentRepository,
    ):
        self.concert_repo = concert_repo
        self.incident_repo = incident_repo

    def execute(self, payload) -> object:
        """
        :param payload: objet avec concert_id, description, occurred_at (optionnel)
        :raises NotFoundError: concert introuvable
        """
        concert = self.concert_repo.get(payload.concert_id)
        if concert is None:
            raise NotFoundError("Concert introuvable")

        incident = Incident(
            concert_id=payload.concert_id,
            description=payload.description,
            occurred_at=payload.occurred_at or datetime.utcnow(),
        )
        return self.incident_repo.create(incident)
