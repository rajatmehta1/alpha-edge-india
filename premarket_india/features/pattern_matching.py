"""Sector-filtered KNN pattern matching on historical session fingerprints."""

from __future__ import annotations

import numpy as np
from loguru import logger

try:
    from sklearn.preprocessing import MinMaxScaler
    from sklearn.neighbors import NearestNeighbors
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    logger.warning("scikit-learn not available — pattern matching disabled")

from features.models import PatternMatch


# Feature vector layout (continuous features only — categoricals dropped for KNN)
_FEATURE_NAMES = [
    "gap_pct",
    "crude_change_pct",
    "vix",
    "pcr",
    "fii_net_normalized",
    "dow_change_pct",
    "usdinr_change_pct",
    "rsi",
    "atr_pct",
    "volume_ratio",
]

MIN_SESSIONS_FOR_MATCH = 100
MIN_MATCHES_FOR_CONFIDENCE = 8


def _encode_session(
    gap_pct: float,
    crude_change_pct: float,
    vix: float,
    pcr: float,
    fii_net: float,
    dow_change_pct: float,
    usdinr_change_pct: float,
    rsi: float,
    atr_pct: float,
    volume_ratio: float,
) -> list[float]:
    """Encode a single session into a feature vector."""
    # Normalize FII net to a sensible range (divide by 1000 Cr)
    fii_normalized = fii_net / 1000.0
    return [
        gap_pct, crude_change_pct, vix, pcr, fii_normalized,
        dow_change_pct, usdinr_change_pct, rsi, atr_pct, volume_ratio,
    ]


def compute_pattern_match(
    today_features: dict,
    historical_sessions: list[dict],
    sector_filter: str | None = None,
    n_neighbors: int = 20,
) -> PatternMatch:
    """Find similar historical sessions using KNN with cosine similarity.

    Parameters
    ----------
    today_features : dict
        Keys matching _FEATURE_NAMES plus optional 'sector'.
    historical_sessions : list[dict]
        Each dict has _FEATURE_NAMES keys, plus 'outcome_pct' (next-day return),
        'sector' (optional), and 'date'.
    sector_filter : str | None
        If set, first filter historical sessions to this sector.
    n_neighbors : int
        Number of nearest neighbors to find.
    """
    logger.info("Computing pattern matching")

    if not HAS_SKLEARN:
        return PatternMatch(
            message="Pattern matching unavailable (scikit-learn not installed)",
            confidence="low",
        )

    # Apply sector filter if specified
    if sector_filter:
        historical_sessions = [
            s for s in historical_sessions
            if s.get("sector", "") == sector_filter
        ]

    if len(historical_sessions) < MIN_SESSIONS_FOR_MATCH:
        return PatternMatch(
            total_matches=0,
            message=f"Cold start: only {len(historical_sessions)} sessions available (need {MIN_SESSIONS_FOR_MATCH}+). Pattern matching will improve after backfill.",
            confidence="low",
        )

    # Build feature matrices
    today_vec = _encode_session(
        gap_pct=today_features.get("gap_pct", 0),
        crude_change_pct=today_features.get("crude_change_pct", 0),
        vix=today_features.get("vix", 15),
        pcr=today_features.get("pcr", 1.0),
        fii_net=today_features.get("fii_net", 0),
        dow_change_pct=today_features.get("dow_change_pct", 0),
        usdinr_change_pct=today_features.get("usdinr_change_pct", 0),
        rsi=today_features.get("rsi", 50),
        atr_pct=today_features.get("atr_pct", 1.0),
        volume_ratio=today_features.get("volume_ratio", 1.0),
    )

    hist_vecs = []
    outcomes = []
    for sess in historical_sessions:
        vec = _encode_session(
            gap_pct=sess.get("gap_pct", 0),
            crude_change_pct=sess.get("crude_change_pct", 0),
            vix=sess.get("vix", 15),
            pcr=sess.get("pcr", 1.0),
            fii_net=sess.get("fii_net", 0),
            dow_change_pct=sess.get("dow_change_pct", 0),
            usdinr_change_pct=sess.get("usdinr_change_pct", 0),
            rsi=sess.get("rsi", 50),
            atr_pct=sess.get("atr_pct", 1.0),
            volume_ratio=sess.get("volume_ratio", 1.0),
        )
        hist_vecs.append(vec)
        outcomes.append(sess.get("outcome_pct", 0.0))

    X = np.array(hist_vecs, dtype=np.float64)
    y = np.array(outcomes, dtype=np.float64)
    today_arr = np.array([today_vec], dtype=np.float64)

    # Handle NaN/inf
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    today_arr = np.nan_to_num(today_arr, nan=0.0, posinf=0.0, neginf=0.0)

    # Scale features
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)
    today_scaled = scaler.transform(today_arr)

    # KNN with cosine similarity
    k = min(n_neighbors, len(X_scaled))
    knn = NearestNeighbors(n_neighbors=k, metric="cosine")
    knn.fit(X_scaled)
    distances, indices = knn.kneighbors(today_scaled)

    matched_outcomes = y[indices[0]]
    total_matches = len(matched_outcomes)

    if total_matches < MIN_MATCHES_FOR_CONFIDENCE:
        return PatternMatch(
            total_matches=total_matches,
            message=f"Only {total_matches} similar sessions found — low confidence",
            confidence="low",
        )

    wins = (matched_outcomes > 0).sum()
    win_rate = float(wins / total_matches * 100)
    median_upside = float(np.median(matched_outcomes[matched_outcomes > 0])) if wins > 0 else 0.0
    all_drawdowns = matched_outcomes[matched_outcomes < 0]
    median_drawdown = float(np.median(all_drawdowns)) if len(all_drawdowns) > 0 else 0.0

    # Confidence level
    if total_matches >= 15 and win_rate > 60:
        confidence = "high"
    elif total_matches >= 10:
        confidence = "medium"
    else:
        confidence = "low"

    detail = (
        f"{total_matches} similar sessions found. "
        f"Win rate: {win_rate:.0f}%. "
        f"Median upside: +{median_upside:.2f}%. "
        f"Median drawdown: {median_drawdown:.2f}%."
    )

    return PatternMatch(
        total_matches=total_matches,
        win_rate=round(win_rate, 1),
        median_upside=round(median_upside, 2),
        median_drawdown=round(median_drawdown, 2),
        confidence=confidence,
        message=f"{total_matches} similar events, {win_rate:.0f}% win rate",
        detail_text=detail,
    )
