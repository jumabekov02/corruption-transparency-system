from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.contract import Contract
from app.models.enums import RiskBand
from app.models.risk_score import RiskScore
from app.models.tender import Tender
from app.models.user import User
from app.schemas.contract import ContractDetail, ContractRead
from app.services.risk_engine_db import recompute_all

router = APIRouter(tags=["contracts"])


@router.get("/contracts", response_model=list[ContractRead])
def list_contracts(
    db: Session = Depends(get_db),
    min_risk: int | None = Query(None, ge=0, le=100),
    band: RiskBand | None = None,
    department_id: int | None = None,
    contractor_id: int | None = None,
):
    """Public list of contracts with their risk summary; filterable by risk."""
    stmt = (
        select(Contract)
        .join(RiskScore, RiskScore.contract_id == Contract.id, isouter=True)
        .options(selectinload(Contract.risk_score))
    )
    if min_risk is not None:
        stmt = stmt.where(RiskScore.total_score >= min_risk)
    if band is not None:
        stmt = stmt.where(RiskScore.band == band)
    if contractor_id is not None:
        stmt = stmt.where(Contract.contractor_id == contractor_id)
    if department_id is not None:
        stmt = stmt.join(Tender, Contract.tender_id == Tender.id).where(
            Tender.department_id == department_id
        )
    stmt = stmt.order_by(RiskScore.total_score.desc().nullslast())
    return db.scalars(stmt).all()


@router.get("/contracts/{contract_id}", response_model=ContractDetail)
def get_contract(contract_id: int, db: Session = Depends(get_db)):
    """Public detail: contract + its full risk breakdown (indicators + explanation)."""
    contract = db.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contract not found")
    return contract


@router.post("/admin/risk/recompute")
def recompute(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    """Re-score every contract (admin)."""
    n = recompute_all(db)
    return {"recomputed": n}
