"""
Contrôleur HTTP pour les festivals.

Adaptateur entrant : traduit les requêtes HTTP en appels aux cas d'utilisation.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.domain.errors import NotFoundError, ValidationError
from app.repositories.concert_repository import ConcertRepository
from app.repositories.festival_repository import FestivalRepository
from app.schemas import FestivalCreate, FestivalRead
from app.services.festival_service import FestivalService
from app.services.notification_service import EmailNotificationAdapter
from app.use_cases.publish_festival import PublishFestivalUseCase

router = APIRouter(prefix="/festivals", tags=["festivals"])


@router.get("", response_model=list[FestivalRead])
def list_festivals(db: Session = Depends(get_db)):
    return FestivalService(db).list_festivals()


@router.post("", response_model=FestivalRead, status_code=201)
def create_festival(payload: FestivalCreate, db: Session = Depends(get_db)):
    try:
        return FestivalService(db).create_festival(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{festival_id}/publish", response_model=FestivalRead)
def publish_festival(festival_id: int, db: Session = Depends(get_db)):
    """
    Publie un festival.

    Utilise PublishFestivalUseCase qui vérifie qu'au moins un concert
    est planifié avant de changer l'état (Défaut 3 corrigé).
    """
    uc = PublishFestivalUseCase(
        festival_repo=FestivalRepository(db),
        concert_repo=ConcertRepository(db),
        notification_port=EmailNotificationAdapter(),
    )
    try:
        return uc.execute(festival_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
