"""Risk engine — D4 rule indicators (formulae) + C3 fusion (complex).

Pure standard-library functions over pre-gathered context, so the scoring math is
unit-testable in isolation. The DB layer (risk_engine_db.py) gathers the context
(bid counts, department peers, win counts) and persists the results.

All thresholds live here as constants so they are inspectable / tunable.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import date

# --- D4 thresholds ---
SINGLE_BIDDER_SCORE = 25
MIN_PEERS_FOR_ZSCORE = 5

# --- band edges for the final 0-100 score ---
LOW_MAX = 30
MEDIUM_MAX = 60


@dataclass
class ContractRiskInput:
    """Everything the indicators need, pre-gathered from the database."""

    admitted_bid_count: int | None = None      # for single-bidder
    repeated_win_count: int = 0                 # wins by contractor+dept in last 24 months
    awarded_value: float = 0.0
    final_cost: float | None = None             # None while contract in progress
    planned_end: date | None = None
    actual_end: date | None = None
    peer_awarded_values: list[float] = field(default_factory=list)  # same-dept peers


@dataclass
class IndicatorResult:
    type: str
    score: int
    explanation: str


# ============================ D4 indicators ============================
def indicator_single_bidder(ctx: ContractRiskInput) -> IndicatorResult:
    if ctx.admitted_bid_count is None:
        return IndicatorResult("single_bidder", 0, "Bid count unknown; not assessed.")
    if ctx.admitted_bid_count == 1:
        return IndicatorResult("single_bidder", SINGLE_BIDDER_SCORE,
                               "Only 1 admitted bid — no competitive pressure.")
    return IndicatorResult("single_bidder", 0,
                           f"{ctx.admitted_bid_count} admitted bids — competitive.")


def indicator_repeated_winner(ctx: ContractRiskInput) -> IndicatorResult:
    w = ctx.repeated_win_count
    if w >= 6:
        score = 20
    elif w >= 4:
        score = 14
    elif w >= 2:
        score = 8
    else:
        score = 0
    return IndicatorResult("repeated_winner", score,
                           f"Contractor won {w} contract(s) from this department in the last 24 months.")


def indicator_budget_overrun(ctx: ContractRiskInput) -> IndicatorResult:
    if ctx.final_cost is None:
        return IndicatorResult("budget_overrun", 0, "Contract not yet completed — overrun not assessed.")
    if ctx.awarded_value <= 0:
        return IndicatorResult("budget_overrun", 0, "No awarded value to compare against.")
    overrun = (ctx.final_cost - ctx.awarded_value) / ctx.awarded_value
    if overrun >= 0.50:
        score = 20
    elif overrun >= 0.25:
        score = 15
    elif overrun >= 0.10:
        score = 10
    else:
        score = 0
    return IndicatorResult("budget_overrun", score,
                           f"Final cost is {overrun * 100:.1f}% over the awarded value.")


def indicator_delay(ctx: ContractRiskInput) -> IndicatorResult:
    if ctx.actual_end is None or ctx.planned_end is None:
        return IndicatorResult("delay", 0, "Contract not yet completed — delay not assessed.")
    days = (ctx.actual_end - ctx.planned_end).days
    if days <= 0:
        return IndicatorResult("delay", 0, "Delivered on or before the planned end date.")
    if days > 180:
        score = 15
    elif days >= 90:
        score = 10
    elif days >= 30:
        score = 5
    else:
        score = 0
    return IndicatorResult("delay", score, f"Delivered {days} days after the planned end date.")


def indicator_price_anomaly(ctx: ContractRiskInput) -> IndicatorResult:
    peers = ctx.peer_awarded_values
    if len(peers) < MIN_PEERS_FOR_ZSCORE:
        return IndicatorResult("price_anomaly", 0,
                               f"Only {len(peers)} department peer(s) (< {MIN_PEERS_FOR_ZSCORE}) — not assessed.")
    mu = statistics.fmean(peers)
    sigma = statistics.pstdev(peers)
    if sigma == 0:
        return IndicatorResult("price_anomaly", 0, "No price variation among department peers.")
    z = (ctx.awarded_value - mu) / sigma
    az = abs(z)
    if az > 3:
        score = 20
    elif az >= 2:
        score = 10
    else:
        score = 0
    return IndicatorResult("price_anomaly", score,
                           f"Awarded value is {z:+.1f}σ from the department average "
                           f"(μ={mu:,.0f}, σ={sigma:,.0f}).")


def compute_indicators(ctx: ContractRiskInput) -> list[IndicatorResult]:
    """Run all five D4 indicators."""
    return [
        indicator_single_bidder(ctx),
        indicator_repeated_winner(ctx),
        indicator_budget_overrun(ctx),
        indicator_delay(ctx),
        indicator_price_anomaly(ctx),
    ]


# ============================ C3 fusion ============================
@dataclass
class RiskOutcome:
    total_score: int
    band: str
    components: list[dict]
    explanation: str


def _band(total: int) -> str:
    if total <= LOW_MAX:
        return "low"
    if total <= MEDIUM_MAX:
        return "medium"
    return "high"


def fuse(
    indicators: list[IndicatorResult],
    ml_anomaly: float | None = None,
    award_flags: dict | None = None,
) -> RiskOutcome:
    """Combine rule indicators (a) + ML anomaly (b) + awarding flags (c) into one
    explained 0-100 score. The value is in the orchestration, not any single number."""
    components: list[dict] = []

    # (a) Rule indicators.
    rule_score = 0
    for ind in indicators:
        rule_score += ind.score
        components.append(
            {"source": "rule", "type": ind.type, "score": ind.score, "explanation": ind.explanation}
        )

    # (b) ML anomaly signal (Isolation Forest score in [0,1] -> up to 20 points).
    ml_points = 0
    if ml_anomaly is not None:
        ml_points = round(max(0.0, min(1.0, ml_anomaly)) * 20)
        components.append(
            {"source": "ml", "type": "isolation_forest", "score": ml_points,
             "explanation": f"ML anomaly score {ml_anomaly:.2f} (0 = normal, 1 = anomalous)."}
        )

    # (c) Awarding-phase evidence (distinct from the rule signals).
    award_points = 0
    if award_flags:
        if award_flags.get("awarded_after_exclusions"):
            award_points += 10
            components.append(
                {"source": "award", "type": "awarded_after_exclusions", "score": 10,
                 "explanation": "Awarded in a tender where some bids were excluded as abnormally low."}
            )

    raw = rule_score + ml_points + award_points

    # Dominance rule: with NO rule evidence, ancillary signals may raise concern
    # but cannot push the contract into the "high" band on their own.
    if rule_score == 0:
        raw = min(raw, MEDIUM_MAX)

    total = max(0, min(100, raw))
    band = _band(total)
    explanation = (
        f"Risk {total}/100 ({band}). Rule indicators contributed {rule_score}"
        + (f", ML +{ml_points}" if ml_points else "")
        + (f", awarding-phase +{award_points}" if award_points else "")
        + "."
    )
    return RiskOutcome(total_score=total, band=band, components=components, explanation=explanation)
