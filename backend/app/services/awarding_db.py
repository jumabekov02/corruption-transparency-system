"""Database glue around the pure awarding engine (app/services/awarding.py).

Keeping this separate from the algorithm means the algorithm stays pure and
unit-testable, while this layer handles loading bids, persisting results, and
creating the Contract.
"""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bid import Bid
from app.models.contract import Contract
from app.models.enums import BidStatus, ContractStatus, TenderStatus
from app.models.tender import Tender
from app.services.awarding import BidInput, award


def close_and_award(db: Session, tender: Tender) -> Tender:
    """Run the engine on an OPEN tender, persist all results, create a Contract."""
    # Load every non-withdrawn bid for this tender.
    bids = db.scalars(
        select(Bid).where(Bid.tender_id == tender.id, Bid.status != BidStatus.withdrawn)
    ).all()

    # Convert DB rows -> plain inputs for the pure engine.
    inputs = [
        BidInput(
            bid_id=b.id,
            price=float(b.price),
            delivery_days=b.delivery_days,
            quality_score=float(b.quality_score) if b.quality_score is not None else None,
            submitted_order=int(b.submitted_at.timestamp()),  # earlier = smaller
        )
        for b in bids
    ]

    outcome = award(
        float(tender.estimated_value),
        (tender.w_price, tender.w_time, tender.w_quality),
        inputs,
    )

    # Write each bid's computed results back to its row.
    by_id = {b.id: b for b in bids}
    for r in outcome.results:
        b = by_id[r.bid_id]
        b.norm_price = r.norm_price
        b.norm_time = r.norm_time
        b.norm_quality = r.norm_quality
        b.weighted_total = r.weighted_total
        b.rank = r.rank
        b.is_anomalous_low = r.is_anomalous_low
        b.exclusion_reason = r.exclusion_reason
        b.status = BidStatus.excluded if r.excluded else BidStatus.admitted

    tender.award_trace = outcome.trace
    tender.awarded_at = datetime.now(timezone.utc)

    if outcome.status == "void":
        tender.status = TenderStatus.void
        tender.winning_bid_id = None
        db.commit()
        db.refresh(tender)
        return tender

    # Awarded: record the winner and create the resulting Contract.
    tender.status = TenderStatus.awarded
    tender.winning_bid_id = outcome.winning_bid_id
    winner = by_id[outcome.winning_bid_id]

    start = date.today()
    contract = Contract(
        tender_id=tender.id,
        contractor_id=winner.contractor_id,
        awarded_value=winner.price,
        start_date=start,
        planned_end=start + timedelta(days=winner.delivery_days),
        status=ContractStatus.in_progress,
    )
    db.add(contract)
    db.commit()
    db.refresh(tender)
    return tender
