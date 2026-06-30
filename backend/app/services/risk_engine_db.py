"""Database glue around the pure risk engine (app/services/risk_engine.py).

Gathers each contract's context from the DB, runs the engine, and writes the
Indicator rows + the RiskScore row. Keeps the algorithm itself pure/testable.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.bid import Bid
from app.models.contract import Contract
from app.models.enums import BidStatus, IndicatorType, RiskBand
from app.models.indicator import Indicator
from app.models.risk_score import RiskScore
from app.models.tender import Tender
from app.services.ml_anomaly import build_feature_row, fit_and_score
from app.services.risk_engine import ContractRiskInput, compute_indicators, fuse

WINDOW_DAYS = 730  # ~24 months for the repeated-winner look-back


def _gather(db: Session, contract: Contract) -> tuple[ContractRiskInput, Tender]:
    tender = db.get(Tender, contract.tender_id)
    dept_id = tender.department_id
    ref_date = tender.awarded_at or datetime.now(timezone.utc)
    window_start = ref_date - timedelta(days=WINDOW_DAYS)

    admitted = db.scalar(
        select(func.count(Bid.id)).where(
            Bid.tender_id == tender.id, Bid.status == BidStatus.admitted
        )
    ) or 0

    win_count = db.scalar(
        select(func.count(Contract.id))
        .join(Tender, Contract.tender_id == Tender.id)
        .where(Contract.contractor_id == contract.contractor_id)
        .where(Tender.department_id == dept_id)
        .where(Tender.awarded_at.is_not(None))
        .where(Tender.awarded_at >= window_start)
        .where(Tender.awarded_at <= ref_date)
    ) or 0

    peers = db.scalars(
        select(Contract.awarded_value)
        .join(Tender, Contract.tender_id == Tender.id)
        .where(Tender.department_id == dept_id)
        .where(Contract.id != contract.id)
    ).all()

    ctx = ContractRiskInput(
        admitted_bid_count=admitted if admitted > 0 else None,
        repeated_win_count=win_count,
        awarded_value=float(contract.awarded_value),
        final_cost=float(contract.final_cost) if contract.final_cost is not None else None,
        planned_end=contract.planned_end,
        actual_end=contract.actual_end,
        peer_awarded_values=[float(v) for v in peers],
    )
    return ctx, tender


def _persist(db: Session, contract: Contract, ctx: ContractRiskInput, tender: Tender,
             ml_anomaly: float | None) -> None:
    """Compute indicators + fuse + write the Indicator rows and RiskScore."""
    indicators = compute_indicators(ctx)

    # Awarding-phase evidence (distinct from the rule signals).
    award_flags = {}
    if tender.award_trace:
        c2 = tender.award_trace.get("c2", {})
        if c2.get("flagged_bid_ids"):
            award_flags["awarded_after_exclusions"] = True

    outcome = fuse(indicators, ml_anomaly=ml_anomaly, award_flags=award_flags)

    # Replace any previous results for this contract.
    db.execute(delete(Indicator).where(Indicator.contract_id == contract.id))
    old = db.get(RiskScore, contract.id)
    if old is not None:
        db.delete(old)
    db.flush()

    for ind in indicators:
        db.add(
            Indicator(
                contract_id=contract.id,
                type=IndicatorType(ind.type),
                score=ind.score,
                explanation=ind.explanation,
            )
        )
    db.add(
        RiskScore(
            contract_id=contract.id,
            total_score=outcome.total_score,
            band=RiskBand(outcome.band),
            components={"breakdown": outcome.components},
            explanation=outcome.explanation,
        )
    )


def score_contract(db: Session, contract: Contract, ml_anomaly: float | None = None) -> None:
    """Score a single contract (used outside the batch path)."""
    ctx, tender = _gather(db, contract)
    _persist(db, contract, ctx, tender, ml_anomaly)


def recompute_all(db: Session) -> int:
    """Re-score every contract. Fits the ML anomaly model once over the whole
    dataset, then fuses each contract's rule scores with its ML score."""
    contracts = db.scalars(select(Contract)).all()

    gathered = []
    feature_rows = []
    for contract in contracts:
        ctx, tender = _gather(db, contract)
        gathered.append((contract, ctx, tender))
        feature_rows.append(build_feature_row(ctx))

    ml_scores = fit_and_score(feature_rows)  # one model fit over all contracts

    for (contract, ctx, tender), ml in zip(gathered, ml_scores):
        _persist(db, contract, ctx, tender, ml)

    db.commit()
    return len(contracts)
