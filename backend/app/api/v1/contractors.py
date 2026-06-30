from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.contractor import Contractor
from app.models.user import User
from app.schemas.contractor import ContractorCreate, ContractorRead, ContractorUpdate

router = APIRouter(prefix="/contractors", tags=["contractors"])


@router.get("", response_model=list[ContractorRead])
def list_contractors(db: Session = Depends(get_db)):
    return db.scalars(select(Contractor).order_by(Contractor.id)).all()


@router.post("", response_model=ContractorRead, status_code=status.HTTP_201_CREATED)
def create_contractor(
    payload: ContractorCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    contractor = Contractor(**payload.model_dump())
    db.add(contractor)
    try:
        db.commit()
    except IntegrityError:
        # The DB rejected the row (here: duplicate unique vat_id). Undo the
        # half-finished transaction, then report a clean 409 instead of a 500.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A contractor with this vat_id already exists"
        )
    db.refresh(contractor)
    return contractor


@router.get("/{contractor_id}", response_model=ContractorRead)
def get_contractor(contractor_id: int, db: Session = Depends(get_db)):
    contractor = db.get(Contractor, contractor_id)
    if contractor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contractor not found")
    return contractor


@router.patch("/{contractor_id}", response_model=ContractorRead)
def update_contractor(
    contractor_id: int,
    payload: ContractorUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    contractor = db.get(Contractor, contractor_id)
    if contractor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contractor not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(contractor, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A contractor with this vat_id already exists"
        )
    db.refresh(contractor)
    return contractor


@router.delete("/{contractor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contractor(
    contractor_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    contractor = db.get(Contractor, contractor_id)
    if contractor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contractor not found")
    db.delete(contractor)
    db.commit()
