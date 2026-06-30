"""Unit tests for the risk engine (D4 indicators + C3 fusion)."""
from datetime import date

from app.services.risk_engine import (
    ContractRiskInput,
    IndicatorResult,
    compute_indicators,
    fuse,
    indicator_budget_overrun,
    indicator_delay,
    indicator_price_anomaly,
    indicator_repeated_winner,
    indicator_single_bidder,
)


# ----------------------- D4 indicators -----------------------
def test_single_bidder_scores_only_when_one_bid():
    assert indicator_single_bidder(ContractRiskInput(admitted_bid_count=1)).score == 25
    assert indicator_single_bidder(ContractRiskInput(admitted_bid_count=3)).score == 0


def test_repeated_winner_bands():
    assert indicator_repeated_winner(ContractRiskInput(repeated_win_count=1)).score == 0
    assert indicator_repeated_winner(ContractRiskInput(repeated_win_count=2)).score == 8
    assert indicator_repeated_winner(ContractRiskInput(repeated_win_count=5)).score == 14
    assert indicator_repeated_winner(ContractRiskInput(repeated_win_count=7)).score == 20


def test_budget_overrun_bands():
    base = dict(awarded_value=100_000)
    assert indicator_budget_overrun(ContractRiskInput(**base, final_cost=None)).score == 0   # in progress
    assert indicator_budget_overrun(ContractRiskInput(**base, final_cost=105_000)).score == 0   # 5%
    assert indicator_budget_overrun(ContractRiskInput(**base, final_cost=115_000)).score == 10  # 15%
    assert indicator_budget_overrun(ContractRiskInput(**base, final_cost=130_000)).score == 15  # 30%
    assert indicator_budget_overrun(ContractRiskInput(**base, final_cost=170_000)).score == 20  # 70%


def test_delay_bands():
    def ctx(actual):
        return ContractRiskInput(planned_end=date(2026, 1, 1), actual_end=actual)
    assert indicator_delay(ctx(None)).score == 0
    assert indicator_delay(ctx(date(2025, 12, 1))).score == 0    # early
    assert indicator_delay(ctx(date(2026, 2, 20))).score == 5    # ~50 days
    assert indicator_delay(ctx(date(2026, 4, 15))).score == 10   # ~104 days
    assert indicator_delay(ctx(date(2026, 8, 1))).score == 15    # >180 days


def test_price_anomaly_needs_enough_peers_and_flags_outliers():
    peers = [100_000, 110_000, 90_000, 105_000, 95_000]  # mu=100k, sigma~7.07k
    assert indicator_price_anomaly(ContractRiskInput(awarded_value=130_000, peer_awarded_values=peers[:4])).score == 0  # <5 peers
    assert indicator_price_anomaly(ContractRiskInput(awarded_value=105_000, peer_awarded_values=peers)).score == 0   # ~0.7σ
    assert indicator_price_anomaly(ContractRiskInput(awarded_value=115_000, peer_awarded_values=peers)).score == 10  # ~2.1σ
    assert indicator_price_anomaly(ContractRiskInput(awarded_value=135_000, peer_awarded_values=peers)).score == 20  # ~4.9σ


# ----------------------- C3 fusion -----------------------
def test_fuse_sums_rules_and_bands():
    inds = [IndicatorResult("single_bidder", 25, ""), IndicatorResult("delay", 15, "")]
    out = fuse(inds)
    assert out.total_score == 40
    assert out.band == "medium"


def test_fuse_high_band():
    inds = [
        IndicatorResult("single_bidder", 25, ""),
        IndicatorResult("repeated_winner", 20, ""),
        IndicatorResult("budget_overrun", 20, ""),
        IndicatorResult("price_anomaly", 10, ""),
    ]
    out = fuse(inds)  # 75
    assert out.band == "high"


def test_ml_alone_cannot_reach_high_without_rule_evidence():
    # No rule score at all, but a maximal ML anomaly. Dominance caps it at medium.
    inds = [IndicatorResult("single_bidder", 0, "")]
    out = fuse(inds, ml_anomaly=1.0, award_flags={"awarded_after_exclusions": True})
    assert out.total_score <= 60
    assert out.band != "high"


def test_awarded_after_exclusions_adds_points():
    inds = [IndicatorResult("delay", 10, "")]
    out = fuse(inds, award_flags={"awarded_after_exclusions": True})
    assert out.total_score == 20  # 10 rule + 10 awarding


def test_compute_indicators_returns_five():
    out = compute_indicators(ContractRiskInput(admitted_bid_count=2))
    assert len(out) == 5
