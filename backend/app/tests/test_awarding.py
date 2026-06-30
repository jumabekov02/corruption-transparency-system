"""Unit tests for the awarding engine (C1 + C2).

Each test is a hand-crafted bid set that pins down one behaviour or edge case.
"""
from app.services.awarding import BidInput, award


def make_bids(prices, days=None, quality=None):
    """Helper: build BidInputs with sensible defaults and stable ids/order."""
    days = days or [300] * len(prices)
    quality = quality or [None] * len(prices)
    return [
        BidInput(
            bid_id=i + 1,
            price=prices[i],
            delivery_days=days[i],
            quality_score=quality[i],
            submitted_order=i,
        )
        for i in range(len(prices))
    ]


def test_no_bids_voids_the_tender():
    out = award(500_000, (60, 20, 20), [])
    assert out.status == "void"
    assert out.winning_bid_id is None


def test_single_bid_is_awarded_and_flagged_as_single():
    out = award(500_000, (60, 20, 20), make_bids([480_000]))
    assert out.status == "awarded"
    assert out.winning_bid_id == 1
    assert out.trace["single_admitted_bid"] is True


def test_fewer_than_five_bids_skips_anomaly_screen():
    # 300k looks very low, but with only 3 bids the statistical screen is skipped.
    out = award(500_000, (60, 20, 20), make_bids([490_000, 300_000, 470_000]))
    assert out.status == "awarded"
    assert all(not r.is_anomalous_low for r in out.results)
    assert out.trace["c2"]["applied"] is False


def test_abnormally_low_bid_is_flagged_excluded_and_cannot_win():
    # Five tightly-clustered bids + one absurdly low (300k on a 500k estimate).
    prices = [490_000, 488_000, 485_000, 487_000, 486_000, 300_000]
    out = award(500_000, (60, 20, 20), make_bids(prices))

    cheat = next(r for r in out.results if r.bid_id == 6)
    assert cheat.is_anomalous_low is True
    assert cheat.excluded is True
    assert out.winning_bid_id != 6           # the suspiciously low bid does not win
    assert out.trace["c2"]["applied"] is True


def test_price_dominant_weights_pick_cheapest():
    # weight = 100% price -> cheapest admitted bid wins.
    out = award(500_000, (100, 0, 0), make_bids([400_000, 450_000, 420_000]))
    assert out.winning_bid_id == 1           # 400k is cheapest


def test_quality_dominant_weights_pick_best_quality():
    out = award(
        500_000, (0, 0, 100),
        make_bids([450_000, 450_000], quality=[70, 95]),
    )
    assert out.winning_bid_id == 2           # quality 95 > 70


def test_tie_break_prefers_lower_price():
    # weight = 100% time, equal delivery -> identical weighted_total (a tie).
    # Tie-break rule: the lower price wins.
    out = award(
        500_000, (0, 100, 0),
        make_bids([450_000, 400_000], days=[300, 300]),
    )
    assert out.winning_bid_id == 2           # 400k < 450k
