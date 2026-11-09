from sqlalchemy.orm import Session
from typing import Optional
from app.models import Incident
from app.ports.repositories import IIncidentRepository


class IncidentRepository(IIncidentRepository):
    """Adaptateur SQLAlchemy pour la persistance des incidents."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, item: Incident) -> Incident:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def list(self, concert_id: Optional[int] = None) -> list:
        q = self.db.query(Incident)
        if concert_id is not None:
            q = q.filter(Incident.concert_id == concert_id)
        return q.order_by(Incident.occurred_at.desc()).all()
