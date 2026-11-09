"""
Service festival — rétrocompatibilité avec l'ancien service layer.

Les nouvelles fonctionnalités utilisent directement les cas d'utilisation.
"""
from sqlalchemy.orm import Session
from app.models import Festival
from app.repositories.festival_repository import FestivalRepository


class FestivalService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = FestivalRepository(db)

    def list_festivals(self):
        return self.repo.list()

    def create_festival(self, payload):
        if payload.end_date <= payload.start_date:
            raise ValueError("La date de fin doit être postérieure à la date de début")
        return self.repo.create(
            Festival(
                name=payload.name,
                location=payload.location,
                start_date=payload.start_date,
                end_date=payload.end_date,
            )
        )
