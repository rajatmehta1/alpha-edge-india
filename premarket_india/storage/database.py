"""SQLite database initialisation and core queries.

Tables
------
- ``daily_ohlcv`` — daily OHLCV bars for Nifty 50 stocks
- ``session_fingerprints`` — 15-dimension feature vectors for pattern matching
- ``fii_dii_flows`` — daily FII/DII net flows
- ``report_log`` — one row per generated report (audit trail)
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, List, Optional, Tuple

from loguru import logger

from config.settings import settings


def _db_path() -> Path:
    """Resolve and ensure the database directory exists."""
    path = Path(settings.DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """Context manager yielding a SQLite connection with WAL mode and foreign keys."""
    conn = sqlite3.connect(str(_db_path()), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ─── Schema ──────────────────────────────────────────────────────────

_SCHEMA_SQL = """
-- Daily OHLCV for Nifty 50 stocks + indices
CREATE TABLE IF NOT EXISTS daily_ohlcv (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker      TEXT    NOT NULL,
    date        TEXT    NOT NULL,   -- ISO format YYYY-MM-DD
    open        REAL    NOT NULL DEFAULT 0,
    high        REAL    NOT NULL DEFAULT 0,
    low         REAL    NOT NULL DEFAULT 0,
    close       REAL    NOT NULL DEFAULT 0,
    volume      INTEGER NOT NULL DEFAULT 0,
    delivery_pct REAL   DEFAULT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE(ticker, date)
);
CREATE INDEX IF NOT EXISTS idx_ohlcv_ticker_date ON daily_ohlcv(ticker, date);
CREATE INDEX IF NOT EXISTS idx_ohlcv_date ON daily_ohlcv(date);

-- Session fingerprints for KNN pattern matching
CREATE TABLE IF NOT EXISTS session_fingerprints (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT    NOT NULL UNIQUE,   -- ISO format
    -- 15-dimension feature vector
    gap_pct         REAL    DEFAULT 0,
    crude_change    REAL    DEFAULT 0,
    dow_change      REAL    DEFAULT 0,
    usdinr_change   REAL    DEFAULT 0,
    vix             REAL    DEFAULT 0,
    pcr             REAL    DEFAULT 0,
    fii_net         REAL    DEFAULT 0,
    dii_net         REAL    DEFAULT 0,
    max_pain_dist   REAL    DEFAULT 0,  -- distance from spot to max pain (%)
    sector_leader   TEXT    DEFAULT '',  -- top sector code
    day_of_week     INTEGER DEFAULT 0,  -- 0=Mon .. 4=Fri
    is_expiry_week  INTEGER DEFAULT 0,  -- boolean 0/1
    rsi_14          REAL    DEFAULT 50,
    atr_pct         REAL    DEFAULT 0,  -- ATR as % of prev close
    volume_ratio    REAL    DEFAULT 1,  -- vs 20d avg
    -- Outcome (filled EOD by store_outcome)
    nifty_close_change  REAL    DEFAULT NULL,  -- % change open→close
    nifty_high_change   REAL    DEFAULT NULL,  -- % max upside from open
    nifty_low_change    REAL    DEFAULT NULL,  -- % max drawdown from open
    outcome_filled      INTEGER DEFAULT 0,     -- boolean
    created_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_fp_date ON session_fingerprints(date);
CREATE INDEX IF NOT EXISTS idx_fp_outcome ON session_fingerprints(outcome_filled);

-- FII/DII daily flows
CREATE TABLE IF NOT EXISTS fii_dii_flows (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    date                TEXT    NOT NULL UNIQUE,
    fii_cash_net        REAL    DEFAULT 0,
    dii_cash_net        REAL    DEFAULT 0,
    fii_futures_net     REAL    DEFAULT 0,
    fii_futures_contracts INTEGER DEFAULT 0,
    fii_options_net     REAL    DEFAULT 0,
    fii_options_contracts INTEGER DEFAULT 0,
    source              TEXT    DEFAULT '',
    created_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_fii_date ON fii_dii_flows(date);

-- Report generation log
CREATE TABLE IF NOT EXISTS report_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT    NOT NULL,
    generated_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    duration_secs   REAL    DEFAULT 0,
    sections_ok     INTEGER DEFAULT 17,
    sections_degraded INTEGER DEFAULT 0,
    confidence_score INTEGER DEFAULT 50,
    output_path     TEXT    DEFAULT '',
    error_message   TEXT    DEFAULT NULL,
    metadata_json   TEXT    DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_report_date ON report_log(date);
"""


def init_db() -> None:
    """Create all tables and indexes if they do not exist."""
    with get_connection() as conn:
        conn.executescript(_SCHEMA_SQL)
        conn.commit()
    logger.info("Database initialised at {}", _db_path())


# ─── Core queries ────────────────────────────────────────────────────

def get_session_count() -> int:
    """Return the number of rows in session_fingerprints."""
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) FROM session_fingerprints").fetchone()
        return row[0] if row else 0


def store_daily_snapshot(
    date: str,
    gap_pct: float = 0.0,
    crude_change: float = 0.0,
    dow_change: float = 0.0,
    usdinr_change: float = 0.0,
    vix: float = 0.0,
    pcr: float = 1.0,
    fii_net: float = 0.0,
    dii_net: float = 0.0,
    max_pain_dist: float = 0.0,
    sector_leader: str = "",
    day_of_week: int = 0,
    is_expiry_week: bool = False,
    rsi_14: float = 50.0,
    atr_pct: float = 0.0,
    volume_ratio: float = 1.0,
) -> None:
    """Store today's session fingerprint (pre-market features, no outcome yet)."""
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
                date, gap_pct, crude_change, dow_change, usdinr_change,
                vix, pcr, fii_net, dii_net, max_pain_dist,
                sector_leader, day_of_week, int(is_expiry_week),
                rsi_14, atr_pct, volume_ratio,
            ),
        )
        conn.commit()
    logger.debug("Stored session fingerprint for {}", date)


def get_historical_fingerprints() -> List[dict]:
    """Retrieve all session fingerprints with filled outcomes for KNN matching.

    Returns a list of dicts, each containing the 15 feature dimensions plus
    outcome columns.
    """
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT date, gap_pct, crude_change, dow_change, usdinr_change,
                   vix, pcr, fii_net, dii_net, max_pain_dist,
                   sector_leader, day_of_week, is_expiry_week,
                   rsi_14, atr_pct, volume_ratio,
                   nifty_close_change, nifty_high_change, nifty_low_change
            FROM session_fingerprints
            WHERE outcome_filled = 1
            ORDER BY date
            """
        )
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def log_report(
    date: str,
    duration_secs: float = 0.0,
    sections_ok: int = 17,
    sections_degraded: int = 0,
    confidence_score: int = 50,
    output_path: str = "",
    error_message: Optional[str] = None,
    metadata_json: str = "{}",
) -> None:
    """Insert a row into the report_log table."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO report_log
                (date, duration_secs, sections_ok, sections_degraded,
                 confidence_score, output_path, error_message, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (date, duration_secs, sections_ok, sections_degraded,
             confidence_score, output_path, error_message, metadata_json),
        )
        conn.commit()
    logger.debug("Logged report generation for {}", date)
