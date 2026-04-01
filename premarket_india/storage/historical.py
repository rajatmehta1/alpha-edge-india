"""Historical data storage — OHLCV and FII/DII flows in SQLite."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from loguru import logger

from storage.database import get_connection


# ─── OHLCV ───────────────────────────────────────────────────────────

def store_ohlcv(rows: List[Dict]) -> int:
    """Bulk-insert daily OHLCV rows.

    Parameters
    ----------
    rows : list of dict
        Each dict must contain keys: ``ticker``, ``date``, ``open``, ``high``,
        ``low``, ``close``, ``volume``.  Optional: ``delivery_pct``.

    Returns
    -------
    int
        Number of rows inserted (duplicates are silently skipped).
    """
    if not rows:
        return 0

    inserted = 0
    with get_connection() as conn:
        for row in rows:
            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO daily_ohlcv
                        (ticker, date, open, high, low, close, volume, delivery_pct)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["ticker"],
                        row["date"],
                        row.get("open", 0),
                        row.get("high", 0),
                        row.get("low", 0),
                        row.get("close", 0),
                        row.get("volume", 0),
                        row.get("delivery_pct"),
                    ),
                )
                inserted += 1
            except Exception as e:
                logger.warning("Skipped OHLCV row {}/{}: {}", row.get("ticker"), row.get("date"), e)
        conn.commit()

    logger.debug("Stored {} OHLCV rows ({} provided)", inserted, len(rows))
    return inserted


def get_ohlcv(
    ticker: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 500,
) -> List[Dict]:
    """Retrieve historical OHLCV data for a ticker.

    Parameters
    ----------
    ticker : str
        Stock ticker (e.g. "RELIANCE.NS" or "^NSEI").
    start_date : str, optional
        ISO date lower bound (inclusive).
    end_date : str, optional
        ISO date upper bound (inclusive).
    limit : int
        Maximum number of rows to return (default 500).

    Returns
    -------
    list of dict
        Rows ordered by date ascending.
    """
    query = "SELECT * FROM daily_ohlcv WHERE ticker = ?"
    params: list = [ticker]

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    query += " ORDER BY date ASC LIMIT ?"
    params.append(limit)

    with get_connection() as conn:
        cursor = conn.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


# ─── FII/DII ─────────────────────────────────────────────────────────

def store_fii_dii(
    date: str,
    fii_cash_net: float = 0.0,
    dii_cash_net: float = 0.0,
    fii_futures_net: float = 0.0,
    fii_futures_contracts: int = 0,
    fii_options_net: float = 0.0,
    fii_options_contracts: int = 0,
    source: str = "",
) -> None:
    """Store a single day's FII/DII flow data.

    Upserts — existing rows for the same date are replaced.
    """
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO fii_dii_flows
                (date, fii_cash_net, dii_cash_net, fii_futures_net,
                 fii_futures_contracts, fii_options_net, fii_options_contracts, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (date, fii_cash_net, dii_cash_net, fii_futures_net,
             fii_futures_contracts, fii_options_net, fii_options_contracts, source),
        )
        conn.commit()
    logger.debug("Stored FII/DII flows for {}", date)


def get_fii_dii_history(days: int = 8) -> List[Dict]:
    """Retrieve the last *days* of FII/DII flow data, ordered by date ascending.

    Parameters
    ----------
    days : int
        Number of most-recent trading days to return (default 8 for the bar chart).

    Returns
    -------
    list of dict
        Each dict has: date, fii_cash_net, dii_cash_net, fii_futures_net, etc.
    """
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT * FROM fii_dii_flows
            ORDER BY date DESC
            LIMIT ?
            """,
            (days,),
        )
        columns = [desc[0] for desc in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    # Reverse so oldest is first (ascending order for charts)
    rows.reverse()
    return rows
