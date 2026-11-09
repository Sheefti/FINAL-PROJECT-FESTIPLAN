"""
Contrôleur HTTP pour les incidents.

Adaptateur entrant : délègue à ReportIncidentUseCase.
Plus d'accès direct à SQLAlchemy depuis le contrôleur.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.domain.errors import NotFoundError
from app.repositories.concert_repository import ConcertRepository
from app.repositories.incident_repository import IncidentRepository
from app.schemas import IncidentCreate, IncidentRead
from app.use_cases.report_incident import ReportIncidentUseCase

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post("", response_model=IncidentRead, status_code=201)
def create_incident(payload: IncidentCreate, db: Session = Depends(get_db)):
    uc = ReportIncidentUseCase(
        concert_repo=ConcertRepository(db),
        incident_repo=IncidentRepository(db),
    )
    try:
        return uc.execute(payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("", response_model=list[IncidentRead])
def list_incidents(concert_id: int | None = None, db: Session = Depends(get_db)):
    return IncidentRepository(db).list(concert_id)
