from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.enums import TenderStatus
from app.models.tender import Tender
from app.models.user import User
from app.schemas.tender import TenderCreate, TenderRead, TenderUpdate
from app.services.awarding_db import close_and_award

router = APIRouter(prefix="/tenders", tags=["tenders"])


@router.get("", response_model=list[TenderRead])
def list_tenders(db: Session = Depends(get_db)):
    return db.scalars(select(Tender).order_by(Tender.id)).all()


@router.post("", response_model=TenderRead, status_code=status.HTTP_201_CREATED)
def create_tender(
    payload: TenderCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    tender = Tender(**payload.model_dump())
    db.add(tender)
    try:
        db.commit()
    except IntegrityError:
        # Catches BOTH a duplicate external_id AND an unknown department_id (bad FK).
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate external_id or unknown department_id",
        )
    db.refresh(tender)
    return tender


@router.get("/{tender_id}", response_model=TenderRead)
def get_tender(tender_id: int, db: Session = Depends(get_db)):
    tender = db.get(Tender, tender_id)
    if tender is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tender not found")
    return tender


@router.patch("/{tender_id}", response_model=TenderRead)
def update_tender(
    tender_id: int,
    payload: TenderUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    tender = db.get(Tender, tender_id)
    if tender is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tender not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(tender, field, value)
    db.commit()
    db.refresh(tender)
    return tender


@router.delete("/{tender_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tender(
    tender_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    tender = db.get(Tender, tender_id)
    if tender is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tender not found")
    db.delete(tender)
    db.commit()


@router.post("/{tender_id}/publish", response_model=TenderRead)
def publish_tender(
    tender_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Lifecycle action: move a tender from DRAFT to OPEN so contractors can bid."""
    tender = db.get(Tender, tender_id)
    if tender is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tender not found")
    if tender.status != TenderStatus.draft:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot publish a tender in status '{tender.status.value}'",
        )
    tender.status = TenderStatus.open
    tender.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(tender)
    return tender


@router.post("/{tender_id}/close", response_model=TenderRead)
def close_tender(
    tender_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Lifecycle action: close an OPEN tender, run the awarding engine (C1+C2),
    and create the resulting Contract (or void the tender if no bid qualifies)."""
    tender = db.get(Tender, tender_id)
    if tender is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tender not found")
    if tender.status != TenderStatus.open:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only an open tender can be closed (current status: '{tender.status.value}')",
        )
    return close_and_award(db, tender)
