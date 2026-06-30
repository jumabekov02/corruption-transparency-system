"""ML anomaly detection — third-party service (T1) via scikit-learn IsolationForest.

We do NOT implement the algorithm. We engineer features, run them through a
ready-made pipeline (StandardScaler -> IsolationForest), and expose a per-contract
anomaly score in [0,1] (1 = most anomalous) that the risk fusion (C3) consumes.
"""
from __future__ import annotations

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

MIN_ROWS_TO_FIT = 10  # below this, "normal" can't be learned meaningfully


def build_feature_row(ctx) -> list[float]:
    """Turn one contract's risk context into a numeric feature vector."""
    if ctx.final_cost is not None and ctx.awarded_value:
        overrun = (ctx.final_cost - ctx.awarded_value) / ctx.awarded_value
    else:
        overrun = 0.0
    delay = (ctx.actual_end - ctx.planned_end).days if (ctx.actual_end and ctx.planned_end) else 0
    bidders = ctx.admitted_bid_count if ctx.admitted_bid_count else 1
    return [float(ctx.awarded_value), float(overrun), float(delay), float(bidders)]


def fit_and_score(feature_rows: list[list[float]]) -> list[float]:
    """Fit the model on all rows and return an anomaly score in [0,1] for each
    (1 = most anomalous). Returns zeros if there are too few rows to learn from."""
    n = len(feature_rows)
    if n < MIN_ROWS_TO_FIT:
        return [0.0] * n

    X = np.asarray(feature_rows, dtype=float)
    # Standardize so no single feature (e.g. the large awarded_value) dominates.
    X = StandardScaler().fit_transform(X)

    model = IsolationForest(n_estimators=200, contamination="auto", random_state=42)
    model.fit(X)

    # score_samples: higher = more normal. We invert + min-max to [0,1] (1 = anomalous).
    raw = model.score_samples(X)
    lo, hi = float(raw.min()), float(raw.max())
    if hi == lo:
        return [0.0] * n
    return [float((hi - r) / (hi - lo)) for r in raw]
