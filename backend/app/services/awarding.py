"""Tender awarding engine — complex features C1 (MEAT) + C2 (abnormally-low).

These are PURE functions over bid data: no database, no framework. That keeps the
algorithm unit-testable in isolation and easy to defend. Every decision is written
into a ``trace`` dict, honouring the project principle "no unexplained judgments".

Flow:  award() -> detect_abnormally_low() [C2] -> rank_admitted() [C1] -> winner.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field

# --- Tunable parameters (kept here so the thresholds are inspectable / defensible) ---
MIN_BIDS_FOR_ANOMALY = 5   # below this, statistics aren't meaningful -> skip C2
TRIM_FRACTION = 0.10       # taglio delle ali: drop top & bottom 10% before the stats
ANOMALY_K = 2.0            # threshold = mean + K * stddev of the trimmed discounts


@dataclass
class BidInput:
    """The minimum a bid contributes to the decision."""

    bid_id: int
    price: float
    delivery_days: int
    quality_score: float | None = None
    submitted_order: int = 0  # tie-break helper: lower = submitted earlier


@dataclass
class BidResult:
    """Per-bid outcome of the engine (what we write back to each bid row)."""

    bid_id: int
    discount: float
    is_anomalous_low: bool = False
    excluded: bool = False
    exclusion_reason: str | None = None
    norm_price: float | None = None
    norm_time: float | None = None
    norm_quality: float | None = None
    weighted_total: float | None = None
    rank: int | None = None


@dataclass
class AwardOutcome:
    status: str  # "awarded" or "void"
    winning_bid_id: int | None
    results: list[BidResult]
    trace: dict = field(default_factory=dict)


def _discount(price: float, estimated_value: float) -> float:
    """How far below the estimate a price sits (0.20 => 20% cheaper)."""
    if estimated_value <= 0:
        return 0.0
    return (estimated_value - price) / estimated_value


# ----------------------------- C2 -----------------------------
def detect_abnormally_low(bids: list[BidInput], estimated_value: float):
    """Flag bids whose discount is statistically "too good to be true".

    Returns (set_of_flagged_bid_ids, trace).
    """
    n = len(bids)
    discounts = {b.bid_id: _discount(b.price, estimated_value) for b in bids}

    # Too few bids => the statistics would be meaningless. Skip, and say so.
    if n < MIN_BIDS_FOR_ANOMALY:
        return set(), {
            "applied": False,
            "reason": f"only {n} bid(s) (< {MIN_BIDS_FOR_ANOMALY}); screening skipped",
            "discounts": {k: round(v, 6) for k, v in discounts.items()},
        }

    sorted_discounts = sorted(discounts.values())
    k_trim = math.ceil(TRIM_FRACTION * n)                  # taglio delle ali
    trimmed = sorted_discounts[k_trim: n - k_trim]         # drop the extreme wings

    mean = statistics.fmean(trimmed)
    spread = statistics.pstdev(trimmed)
    threshold = mean + ANOMALY_K * spread

    # A bid is abnormally low if its discount exceeds the threshold (price too low).
    flagged = {bid_id for bid_id, d in discounts.items() if d > threshold}

    return flagged, {
        "applied": True,
        "n": n,
        "k_trim": k_trim,
        "trimmed_count": len(trimmed),
        "mean_discount": round(mean, 6),
        "stddev_discount": round(spread, 6),
        "threshold": round(threshold, 6),
        "anomaly_k": ANOMALY_K,
        "discounts": {k: round(v, 6) for k, v in discounts.items()},
        "flagged_bid_ids": sorted(flagged),
    }


# ----------------------------- C1 -----------------------------
def _normalize_lower_better(value: float, best: float) -> float:
    """Lower-is-better criterion -> best offer scores 100, others proportionally."""
    if value <= 0:
        return 0.0
    return best / value * 100.0


def rank_admitted(admitted: list[BidInput], weights: tuple[int, int, int]):
    """Normalize criteria to 0-100, apply weights, rank. Returns (ordered, trace).

    ordered: list of (bid_id, norm_price, norm_time, norm_quality, weighted_total, rank)
    """
    w_price, w_time, w_quality = weights
    w_sum = (w_price + w_time + w_quality) or 1  # guard against all-zero weights

    best_price = min(b.price for b in admitted)
    best_time = min(b.delivery_days for b in admitted)

    scored = []
    for b in admitted:
        norm_price = _normalize_lower_better(b.price, best_price)
        norm_time = _normalize_lower_better(b.delivery_days, best_time)
        # Quality is already a 0-100 declared score; missing => 0. Clamp to be safe.
        norm_quality = 0.0 if b.quality_score is None else max(0.0, min(100.0, float(b.quality_score)))
        weighted_total = (w_price * norm_price + w_time * norm_time + w_quality * norm_quality) / w_sum
        scored.append((b, norm_price, norm_time, norm_quality, weighted_total))

    # Highest weighted_total wins. Tie-break: lower price, then earlier submission.
    scored.sort(key=lambda s: (-s[4], s[0].price, s[0].submitted_order))

    ordered = [
        (b.bid_id, np_, nt, nq, total, rank)
        for rank, (b, np_, nt, nq, total) in enumerate(scored, start=1)
    ]
    trace = {
        "weights": {"price": w_price, "time": w_time, "quality": w_quality},
        "best_price": best_price,
        "best_time": best_time,
        "ranking": [
            {"bid_id": bid_id, "weighted_total": round(total, 4), "rank": rank}
            for bid_id, _, _, _, total, rank in ordered
        ],
    }
    return ordered, trace


# --------------------------- orchestrator ---------------------------
def award(estimated_value: float, weights: tuple[int, int, int], bids: list[BidInput]) -> AwardOutcome:
    """Run C2 then C1, choose a winner, and return a fully-explained outcome."""
    if not bids:
        return AwardOutcome("void", None, [], {"reason": "no bids submitted"})

    results = {
        b.bid_id: BidResult(bid_id=b.bid_id, discount=_discount(b.price, estimated_value))
        for b in bids
    }

    # C2: screen abnormally-low bids. They stay visible but are excluded from ranking.
    flagged, c2_trace = detect_abnormally_low(bids, estimated_value)
    for bid_id in flagged:
        results[bid_id].is_anomalous_low = True
        results[bid_id].excluded = True
        results[bid_id].exclusion_reason = "abnormally low offer (discount above anomaly threshold)"

    admitted = [b for b in bids if b.bid_id not in flagged]
    if not admitted:
        return AwardOutcome(
            "void", None, list(results.values()),
            {"reason": "all bids excluded as abnormally low", "c2": c2_trace},
        )

    # C1: rank the admitted bids and write their scores back.
    ordered, c1_trace = rank_admitted(admitted, weights)
    for bid_id, np_, nt, nq, total, rank in ordered:
        r = results[bid_id]
        r.norm_price, r.norm_time, r.norm_quality = round(np_, 4), round(nt, 4), round(nq, 4)
        r.weighted_total = round(total, 4)
        r.rank = rank

    winner_id = ordered[0][0]
    return AwardOutcome(
        status="awarded",
        winning_bid_id=winner_id,
        results=list(results.values()),
        trace={
            "winner_bid_id": winner_id,
            "admitted_count": len(admitted),
            # One admitted bid => no real competition => a risk signal downstream.
            "single_admitted_bid": len(admitted) == 1,
            "c2": c2_trace,
            "c1": c1_trace,
        },
    )
