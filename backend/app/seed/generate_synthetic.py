"""Generate a synthetic but realistic procurement dataset with PLANTED scandals,
then score every contract. Lets us demo detection against known ground truth.

Run:  docker compose exec backend python -m app.seed.generate_synthetic

Reproducible (fixed random seed). Wipes prior tenders/bids/contracts first, but
keeps users, departments and contractors.
"""
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select, update

from app.db.session import SessionLocal
from app.models.bid import Bid
from app.models.contract import Contract
from app.models.contractor import Contractor
from app.models.department import Department
from app.models.enums import BidStatus, ContractStatus, TenderStatus
from app.models.indicator import Indicator
from app.models.risk_score import RiskScore
from app.models.tender import Tender
from app.services.risk_engine_db import recompute_all

random.seed(42)  # reproducible dataset

DEPARTMENTS = [
    ("Comune di Messina", "Sicilia"),
    ("Comune di Catania", "Sicilia"),
    ("Comune di Palermo", "Sicilia"),
    ("Regione Siciliana", "Sicilia"),
]
CONTRACTOR_NAMES = [
    "Acme", "Beta Costruzioni", "Gamma Infrastrutture", "Delta Lavori", "Epsilon",
    "Zeta Group", "Eta Edilizia", "Theta Opere", "Iota Cantieri", "Kappa Build",
    "Lambda Strade", "Mu Restauri",
]


def _wipe(db):
    """Clear transactional data in FK-safe order (keep users/departments/contractors)."""
    db.execute(delete(RiskScore))
    db.execute(delete(Indicator))
    db.execute(delete(Contract))
    db.execute(update(Tender).values(winning_bid_id=None))  # break the circular FK
    db.execute(delete(Bid))
    db.execute(delete(Tender))
    db.commit()


def _ensure_departments(db):
    out = []
    for name, region in DEPARTMENTS:
        d = db.scalar(select(Department).where(Department.name == name))
        if d is None:
            d = Department(name=name, region=region)
            db.add(d)
            db.flush()
        out.append(d)
    return out


def _ensure_contractors(db):
    out = []
    for i, name in enumerate(CONTRACTOR_NAMES, start=1):
        vat = f"ITSYN{i:06d}"
        c = db.scalar(select(Contractor).where(Contractor.vat_id == vat))
        if c is None:
            c = Contractor(name=f"{name} S.p.A.", vat_id=vat, country="IT")
            db.add(c)
            db.flush()
        out.append(c)
    return out


def _create(db, dept, suffix, awarded_at, estimated, bids_spec, winner_con,
            delivery_days, overrun_pct, delay_days, title):
    """Create one awarded + completed contract with its tender and bids.

    bids_spec: list of (contractor, price). winner_con must be one of them.
    """
    tender = Tender(
        external_id=f"SYN-{dept.id}-{suffix}",
        department_id=dept.id,
        title=title,
        estimated_value=round(estimated, 2),
        published_at=awarded_at - timedelta(days=40),
        closing_at=awarded_at - timedelta(days=10),
        status=TenderStatus.awarded,
        awarded_at=awarded_at,
        w_price=60, w_time=20, w_quality=20,
    )
    db.add(tender)
    db.flush()

    winner_bid = None
    for con, price in bids_spec:
        bid = Bid(
            tender_id=tender.id,
            contractor_id=con.id,
            price=round(price, 2),
            delivery_days=delivery_days,
            quality_score=random.randint(70, 95),
            status=BidStatus.admitted,
            submitted_at=awarded_at - timedelta(days=15),
        )
        db.add(bid)
        db.flush()
        if con is winner_con:
            winner_bid = bid
    tender.winning_bid_id = winner_bid.id

    start = awarded_at.date() + timedelta(days=5)
    planned_end = start + timedelta(days=delivery_days)
    awarded_value = float(winner_bid.price)
    contract = Contract(
        tender_id=tender.id,
        contractor_id=winner_con.id,
        awarded_value=winner_bid.price,
        final_cost=round(awarded_value * (1 + overrun_pct), 2),
        start_date=start,
        planned_end=planned_end,
        actual_end=planned_end + timedelta(days=delay_days),
        status=ContractStatus.completed,
    )
    db.add(contract)
    db.flush()


def run():
    db = SessionLocal()
    try:
        _wipe(db)
        depts = _ensure_departments(db)
        contractors = _ensure_contractors(db)
        base = datetime.now(timezone.utc) - timedelta(days=420)

        # --- normal contracts: ~12 per department (gives >=5 peers each) ---
        for dept in depts:
            for k in range(12):
                awarded_at = base + timedelta(days=random.randint(0, 380))
                estimated = random.uniform(200_000, 1_200_000)
                bidders = random.sample(contractors, random.randint(3, 6))
                bids_spec = [(c, estimated * (1 - random.uniform(0.02, 0.06))) for c in bidders]
                winner = min(bids_spec, key=lambda cp: cp[1])[0]  # lowest price (simplified)
                _create(
                    db, dept, f"{k:03d}", awarded_at, estimated, bids_spec, winner,
                    delivery_days=random.randint(250, 400),
                    overrun_pct=random.uniform(-0.03, 0.08),
                    delay_days=random.randint(-20, 45),
                    title=f"Public works #{k} — {dept.name}",
                )

        # ============ PLANTED SCANDALS (ground truth) ============
        # A) Single bidder + 45% overrun + 210-day delay  (Messina)
        con_a = random.choice(contractors)
        _create(
            db, depts[0], "SCANDAL-A", base + timedelta(days=200), 600_000,
            [(con_a, 588_000)], con_a,
            delivery_days=300, overrun_pct=0.45, delay_days=210,
            title="Emergency road repair (single bidder)",
        )

        # B) Repeated winner who also overruns + delays (a protected favourite): the
        #    same contractor wins 7 tenders in Catania, with cost/time problems.
        repeat_con = contractors[0]
        for m in range(7):
            others = random.sample([c for c in contractors if c is not repeat_con], 3)
            bids_spec = [(repeat_con, 380_000)] + [
                (c, 400_000 + random.uniform(0, 30_000)) for c in others
            ]
            _create(
                db, depts[1], f"SCANDAL-B{m}", base + timedelta(days=30 * m + 15), 420_000,
                bids_spec, repeat_con,
                delivery_days=300, overrun_pct=0.30, delay_days=100,
                title=f"Maintenance lot #{m} (repeat winner)",
            )

        # C) Price outlier + single bidder + overrun (Palermo): awarded value ~5x the
        #    department's typical contracts, only one bidder, big overrun.
        con_c = random.choice(contractors)
        _create(
            db, depts[2], "SCANDAL-C", base + timedelta(days=150), 5_200_000,
            [(con_c, 4_900_000)], con_c,
            delivery_days=300, overrun_pct=0.30, delay_days=100,
            title="Stadium refurbishment (single bidder, price outlier)",
        )

        # A medium-risk cohort: single-bidder tenders with moderate overrun + delay.
        for j in range(6):
            dept = depts[j % len(depts)]
            con = random.choice(contractors)
            awarded_at = base + timedelta(days=random.randint(0, 380))
            est = random.uniform(300_000, 900_000)
            _create(
                db, dept, f"MED-{j:02d}", awarded_at, est, [(con, est * 0.97)], con,
                delivery_days=300, overrun_pct=0.18, delay_days=70,
                title=f"Limited-competition tender #{j}",
            )

        db.commit()
        n = recompute_all(db)
        print(f"Synthetic dataset generated and scored: {n} contracts.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
