"""Technical analysis: pivot points, VWAP proxy, ATR, RSI, DMAs for Nifty and BankNifty."""

from __future__ import annotations

import pandas as pd
import numpy as np
from loguru import logger

from features.models import TechnicalLevels


def _ohlcv_to_df(ohlcv_rows: list[dict]) -> pd.DataFrame:
    """Convert list of OHLCV dicts to a DataFrame with expected columns."""
    if not ohlcv_rows:
        return pd.DataFrame()
    df = pd.DataFrame(ohlcv_rows)
    for col in ("Open", "High", "Low", "Close", "Volume"):
        if col not in df.columns:
            # Try lowercase
            lc = col.lower()
            if lc in df.columns:
                df.rename(columns={lc: col}, inplace=True)
            else:
                df[col] = 0.0
    df = df.sort_index()
    return df


def _pivot_points(high: float, low: float, close: float) -> dict:
    """Classic floor pivot points from previous session H/L/C."""
    pivot = (high + low + close) / 3.0
    r1 = 2 * pivot - low
    s1 = 2 * pivot - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)
    r3 = high + 2 * (pivot - low)
    s3 = low - 2 * (high - pivot)
    return {"pivot": pivot, "r1": r1, "r2": r2, "r3": r3, "s1": s1, "s2": s2, "s3": s3}


def _vwap_proxy(df: pd.DataFrame, periods: int = 5) -> float:
    """Volume-weighted typical price over last N sessions (NOT true intraday VWAP)."""
    if df.empty or len(df) < 1:
        return 0.0
    tail = df.tail(periods).copy()
    typical = (tail["High"] + tail["Low"] + tail["Close"]) / 3.0
    vol = tail["Volume"].astype(float)
    total_vol = vol.sum()
    if total_vol == 0:
        return float(typical.iloc[-1])
    return float((typical * vol).sum() / total_vol)


def _atr(df: pd.DataFrame, period: int = 14) -> float:
    """Average True Range over last *period* sessions."""
    if df.empty or len(df) < 2:
        return 0.0
    high = df["High"]
    low = df["Low"]
    prev_close = df["Close"].shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr_series = tr.rolling(window=period, min_periods=1).mean()
    return float(atr_series.iloc[-1])


def _rsi(df: pd.DataFrame, period: int = 14) -> float:
    """Relative Strength Index using Wilder smoothing."""
    if df.empty or len(df) < period + 1:
        return 50.0
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_val = 100.0 - (100.0 / (1.0 + rs))
    val = rsi_val.iloc[-1]
    return float(val) if not np.isnan(val) else 50.0


def _dma(df: pd.DataFrame, period: int) -> float:
    """Simple moving average of Close over *period* sessions."""
    if df.empty or len(df) < 1:
        return 0.0
    sma = df["Close"].rolling(window=period, min_periods=1).mean()
    return float(sma.iloc[-1])


def compute_technical_levels(
    ohlcv_rows: list[dict],
    expected_open: float,
) -> TechnicalLevels:
    """Compute full technical levels for a single index (Nifty or BankNifty).

    Parameters
    ----------
    ohlcv_rows : list[dict]
        Historical OHLCV data — most recent row is previous trading session.
    expected_open : float
        Expected open from SGX / macro regression.
    """
    df = _ohlcv_to_df(ohlcv_rows)
    if df.empty:
        logger.warning("No OHLCV data provided — returning default TechnicalLevels")
        return TechnicalLevels(expected_open=expected_open)

    prev = df.iloc[-1]
    prev_h, prev_l, prev_c = float(prev["High"]), float(prev["Low"]), float(prev["Close"])

    pivots = _pivot_points(prev_h, prev_l, prev_c)

    return TechnicalLevels(
        prev_close=prev_c,
        expected_open=expected_open,
        pivot=round(pivots["pivot"], 2),
        r1=round(pivots["r1"], 2),
        r2=round(pivots["r2"], 2),
        r3=round(pivots["r3"], 2),
        s1=round(pivots["s1"], 2),
        s2=round(pivots["s2"], 2),
        s3=round(pivots["s3"], 2),
        vwap=round(_vwap_proxy(df, 5), 2),
        atr=round(_atr(df, 14), 2),
        rsi=round(_rsi(df, 14), 1),
        dma_20=round(_dma(df, 20), 2),
        dma_50=round(_dma(df, 50), 2),
        dma_200=round(_dma(df, 200), 2),
    )


def compute_all_technical(
    nifty_ohlcv: list[dict],
    banknifty_ohlcv: list[dict],
    expected_nifty_open: float,
    expected_banknifty_open: float,
) -> tuple[TechnicalLevels, TechnicalLevels]:
    """Compute technical levels for both Nifty and BankNifty."""
    logger.info("Computing technical levels for Nifty and BankNifty")
    nifty = compute_technical_levels(nifty_ohlcv, expected_nifty_open)
    banknifty = compute_technical_levels(banknifty_ohlcv, expected_banknifty_open)
    return nifty, banknifty
