"""
Contrôleur HTTP pour les concerts.

Adaptateur entrant : traduit les requêtes HTTP en appels aux cas d'utilisation.
Le contrôleur ne contient aucune logique métier ni accès direct à SQLAlchemy.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.domain.errors import ConflictError, FestivalLockedError, NotFoundError, ValidationError, EquipmentError
from app.repositories.artist_repository import ArtistRepository
from app.repositories.concert_repository import ConcertRepository
from app.repositories.festival_repository import FestivalRepository
from app.repositories.stage_repository import StageRepository
from app.schemas import ConcertCreate, ConcertRead, ConcertReschedule
from app.services.notification_service import EmailNotificationAdapter
from app.use_cases.cancel_concert import CancelConcertUseCase
from app.use_cases.reschedule_concert import RescheduleConcertUseCase
from app.use_cases.schedule_concert import ScheduleConcertUseCase

router = APIRouter(prefix="/concerts", tags=["concerts"])


def _make_reschedule_uc(db: Session) -> RescheduleConcertUseCase:
    return RescheduleConcertUseCase(
        concert_repo=ConcertRepository(db),
        festival_repo=FestivalRepository(db),
        notification_port=EmailNotificationAdapter(),
    )


def _make_schedule_uc(db: Session) -> ScheduleConcertUseCase:
    return ScheduleConcertUseCase(
        concert_repo=ConcertRepository(db),
        festival_repo=FestivalRepository(db),
        artist_repo=ArtistRepository(db),
        stage_repo=StageRepository(db),
    )


def _make_cancel_uc(db: Session) -> CancelConcertUseCase:
    return CancelConcertUseCase(
        concert_repo=ConcertRepository(db),
        festival_repo=FestivalRepository(db),
    )


@router.get("", response_model=list[ConcertRead])
def list_concerts(festival_id: int, db: Session = Depends(get_db)):
    return ConcertRepository(db).list_for_festival(festival_id)


@router.get("/{concert_id}", response_model=ConcertRead)
def get_concert(concert_id: int, db: Session = Depends(get_db)):
    """Récupère un concert par son identifiant via le repository (sans SQL direct dans le contrôleur)."""
    concert = ConcertRepository(db).get(concert_id)
    if concert is None:
        raise HTTPException(status_code=404, detail="Concert introuvable")
    return concert


@router.post("", response_model=ConcertRead, status_code=201)
def create_concert(payload: ConcertCreate, db: Session = Depends(get_db)):
    try:
        return _make_schedule_uc(db).execute(payload)
    except (NotFoundError, ValidationError, EquipmentError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.patch("/{concert_id}/reschedule", response_model=ConcertRead)
def reschedule_concert(concert_id: int, payload: ConcertReschedule, db: Session = Depends(get_db)):
    try:
        return _make_reschedule_uc(db).execute(concert_id, payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except FestivalLockedError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except (ValidationError, EquipmentError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/{concert_id}/cancel", response_model=ConcertRead)
def cancel_concert(concert_id: int, db: Session = Depends(get_db)):
    try:
        return _make_cancel_uc(db).execute(concert_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except FestivalLockedError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("/schedule/{festival_id}", response_model=list[ConcertRead])
def get_schedule(festival_id: int, db: Session = Depends(get_db)):
    return ConcertRepository(db).list_for_festival(festival_id)
