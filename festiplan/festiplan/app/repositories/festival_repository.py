from sqlalchemy.orm import Session
from app.models import Festival
from app.ports.repositories import IFestivalRepository


class FestivalRepository(IFestivalRepository):
    """Adaptateur SQLAlchemy pour la persistance des festivals."""

    def __init__(self, db: Session):
        self.db = db

    def list(self) -> list:
        return self.db.query(Festival).order_by(Festival.id).all()

    def get(self, item_id: int):
        return self.db.query(Festival).filter(Festival.id == item_id).first()

    def create(self, item: Festival) -> Festival:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def save(self, item: Festival) -> Festival:
        """Persiste les modifications d'un festival existant."""
        self.db.commit()
        self.db.refresh(item)
        return item
