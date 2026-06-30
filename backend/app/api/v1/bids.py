import random

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin, require_contractor
from app.db.session import get_db
from app.models.bid import Bid
from app.models.contractor import Contractor
from app.models.enums import BidStatus, TenderStatus
from app.models.tender import Tender
from app.models.user import User
from app.schemas.bid import BidCreate, BidRead

# No prefix: the paths differ (some are under /tenders/{id}/bids, one under /bids/{id}).
router = APIRouter(tags=["bids"])


@router.post(
    "/tenders/{tender_id}/bids",
    response_model=BidRead,
    status_code=status.HTTP_201_CREATED,
)
def submit_bid(
    tender_id: int,
    payload: BidCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_contractor),
):
    tender = db.get(Tender, tender_id)
    if tender is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tender not found")
    if tender.status != TenderStatus.open:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Tender is not open for bids"
        )
    if user.contractor_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your account is not linked to a contractor company",
        )
    bid = Bid(
        tender_id=tender_id,
        contractor_id=user.contractor_id,  # tie the bid to the logged-in contractor
        price=payload.price,
        delivery_days=payload.delivery_days,
        quality_score=payload.quality_score,
        status=BidStatus.submitted,
    )
    db.add(bid)
    db.commit()
    db.refresh(bid)
    return bid


def _ensure_contractors(db: Session, n: int) -> list[Contractor]:
    """Make sure at least n contractor companies exist (creates 'SIM' ones if needed)."""
    contractors = db.scalars(select(Contractor).order_by(Contractor.id)).all()
    next_index = db.scalar(select(func.count()).select_from(Contractor)) or 0
    while len(contractors) < n:
        next_index += 1
        sim = Contractor(name=f"Sim Bidder {next_index}", vat_id=f"SIM{next_index:08d}", country="IT")
        db.add(sim)
        db.flush()
        contractors.append(sim)
    return contractors[:n]


@router.post(
    "/tenders/{tender_id}/simulate-bids",
    response_model=list[BidRead],
    status_code=status.HTTP_201_CREATED,
)
def simulate_bids(
    tender_id: int,
    count: int = 6,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """DEMO helper: drop `count` plausible bids onto an open tender, including one
    deliberately abnormally-low 'scandal' bid so C2 has something to catch."""
    tender = db.get(Tender, tender_id)
    if tender is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tender not found")
    if tender.status != TenderStatus.open:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tender is not open for bids")

    estimated = float(tender.estimated_value)
    contractors = _ensure_contractors(db, count)
    created: list[Bid] = []
    for i in range(count):
        if i == count - 1:
            price = estimated * 0.60  # the planted abnormally-low bid (40% discount)
        else:
            price = estimated * (1 - random.uniform(0.02, 0.05))  # honest 2-5% discounts
        bid = Bid(
            tender_id=tender.id,
            contractor_id=contractors[i].id,
            price=round(price, 2),
            delivery_days=random.randint(250, 400),
            quality_score=random.randint(60, 95),
            status=BidStatus.submitted,
        )
        db.add(bid)
        created.append(bid)
    db.commit()
    for b in created:
        db.refresh(b)
    return created


@router.get("/tenders/{tender_id}/bids", response_model=list[BidRead])
def list_bids(tender_id: int, db: Session = Depends(get_db)):
    # NOTE: sealed-bid visibility (hiding bids until closing) is a future refinement.
    tender = db.get(Tender, tender_id)
    if tender is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tender not found")
    return db.scalars(select(Bid).where(Bid.tender_id == tender_id).order_by(Bid.id)).all()


@router.delete("/bids/{bid_id}", status_code=status.HTTP_204_NO_CONTENT)
def withdraw_bid(
    bid_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_contractor),
):
    bid = db.get(Bid, bid_id)
    if bid is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bid not found")
    if bid.contractor_id != user.contractor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You can only withdraw your own bids"
        )
    tender = db.get(Tender, bid.tender_id)
    if tender.status != TenderStatus.open:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot withdraw a bid after the tender has closed",
        )
    db.delete(bid)
    db.commit()
