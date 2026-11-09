from sqlalchemy.orm import Session
from app.models import Concert
from app.ports.repositories import IConcertRepository


class ConcertRepository(IConcertRepository):
    """Adaptateur SQLAlchemy pour la persistance des concerts."""

    def __init__(self, db: Session):
        self.db = db

    def get(self, item_id: int):
        return self.db.query(Concert).filter(Concert.id == item_id).first()

    def list_for_festival(self, festival_id: int) -> list:
        return (
            self.db.query(Concert)
            .filter(Concert.festival_id == festival_id, Concert.status != "cancelled")
            .order_by(Concert.start_time)
            .all()
        )

    def create(self, item: Concert) -> Concert:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def save(self, item: Concert) -> Concert:
        """Persiste les modifications d'un concert existant."""
        self.db.commit()
        self.db.refresh(item)
        return item
