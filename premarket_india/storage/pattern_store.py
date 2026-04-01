"""Pattern store — session fingerprint storage and retrieval for KNN matching."""

from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd
from loguru import logger

from storage.database import get_connection


# 15 feature columns used for KNN similarity search
FEATURE_COLUMNS = [
    "gap_pct", "crude_change", "dow_change", "usdinr_change",
    "vix", "pcr", "fii_net", "dii_net", "max_pain_dist",
    "sector_leader", "day_of_week", "is_expiry_week",
    "rsi_14", "atr_pct", "volume_ratio",
]

OUTCOME_COLUMNS = [
    "nifty_close_change", "nifty_high_change", "nifty_low_change",
]


def store_fingerprint(
    date: str,
    features: Dict[str, float],
) -> None:
    """Store a single session fingerprint.

    Parameters
    ----------
    date : str
        ISO date string (YYYY-MM-DD).
    features : dict
        Dictionary with keys from ``FEATURE_COLUMNS``.  Missing keys default
        to 0.  The ``sector_leader`` key is stored as text; all others as floats.
    """
    values = {col: features.get(col, 0) for col in FEATURE_COLUMNS}
    values["sector_leader"] = str(features.get("sector_leader", ""))

    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO session_fingerprints
                (date, gap_pct, crude_change, dow_change, usdinr_change,
                 vix, pcr, fii_net, dii_net, max_pain_dist,
                 sector_leader, day_of_week, is_expiry_week,
                 rsi_14, atr_pct, volume_ratio)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                date,
                values["gap_pct"], values["crude_change"], values["dow_change"],
                values["usdinr_change"], values["vix"], values["pcr"],
                values["fii_net"], values["dii_net"], values["max_pain_dist"],
                values["sector_leader"], values["day_of_week"],
                int(values["is_expiry_week"]),
                values["rsi_14"], values["atr_pct"], values["volume_ratio"],
            ),
        )
        conn.commit()
    logger.debug("Stored fingerprint for {}", date)


def get_all_fingerprints() -> pd.DataFrame:
    """Retrieve all fingerprints with filled outcomes as a DataFrame.

    Returns
    -------
    pd.DataFrame
        Columns: ``date`` + all ``FEATURE_COLUMNS`` + all ``OUTCOME_COLUMNS``.
        Only rows where ``outcome_filled = 1`` are included (these are the
        historical sessions with known results that the KNN model trains on).
        Returns an empty DataFrame if no fingerprints exist.
    """
    select_cols = ["date"] + FEATURE_COLUMNS + OUTCOME_COLUMNS

    with get_connection() as conn:
        cursor = conn.execute(
            f"""
            SELECT {', '.join(select_cols)}
            FROM session_fingerprints
            WHERE outcome_filled = 1
            ORDER BY date
            """
        )
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

    if not rows:
        logger.info("No fingerprints with outcomes found in database")
        return pd.DataFrame(columns=select_cols)

    df = pd.DataFrame(rows, columns=columns)
    logger.debug("Retrieved {} fingerprints from database", len(df))
    return df


def store_outcome(
    date: str,
    nifty_close_change: float,
    nifty_high_change: float,
    nifty_low_change: float,
) -> bool:
    """Update a fingerprint row with end-of-day outcome data.

    Parameters
    ----------
    date : str
        ISO date of the session to update.
    nifty_close_change : float
        Nifty percentage change from open to close.
    nifty_high_change : float
        Nifty max upside percentage from open.
    nifty_low_change : float
        Nifty max drawdown percentage from open (typically negative).

    Returns
    -------
    bool
        True if a row was updated, False if no matching date was found.
    """
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE session_fingerprints
            SET nifty_close_change = ?,
                nifty_high_change  = ?,
                nifty_low_change   = ?,
                outcome_filled     = 1
            WHERE date = ?
            """,
            (nifty_close_change, nifty_high_change, nifty_low_change, date),
        )
        conn.commit()
        updated = cursor.rowcount > 0

    if updated:
        logger.debug("Stored outcome for {}: close={:+.2f}%, high={:+.2f}%, low={:+.2f}%",
                      date, nifty_close_change, nifty_high_change, nifty_low_change)
    else:
        logger.warning("No fingerprint found for date {} — outcome not stored", date)

    return updated


def get_fingerprint_count() -> int:
    """Return total number of fingerprints (with and without outcomes)."""
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) FROM session_fingerprints").fetchone()
        return row[0] if row else 0


def get_outcome_count() -> int:
    """Return number of fingerprints with filled outcomes."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM session_fingerprints WHERE outcome_filled = 1"
        ).fetchone()
        return row[0] if row else 0
