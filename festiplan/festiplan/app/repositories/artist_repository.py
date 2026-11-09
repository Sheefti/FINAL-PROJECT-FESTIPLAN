from sqlalchemy.orm import Session
from app.models import Artist
from app.ports.repositories import IArtistRepository


class ArtistRepository(IArtistRepository):
    """Adaptateur SQLAlchemy pour la persistance des artistes."""

    def __init__(self, db: Session):
        self.db = db

    def list(self) -> list:
        return self.db.query(Artist).order_by(Artist.name).all()

    def get(self, item_id: int):
        return self.db.query(Artist).filter(Artist.id == item_id).first()

    def create(self, item: Artist) -> Artist:
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item
