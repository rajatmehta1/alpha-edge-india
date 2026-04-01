"""
Alpha Edge — Historical Data Backfill Script
Run once to populate SQLite with 2+ years of historical data for pattern matching.

Usage:
    python scripts/backfill_history.py
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from loguru import logger
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn

from config.constants import NIFTY_50_STOCKS, YFINANCE_TICKER_MAP, EXPIRY_DATES_2026
from storage.database import init_db

console = Console()

# Backfill period
START_DATE = "2024-01-01"
END_DATE = datetime.now().strftime("%Y-%m-%d")


def download_stock_data() -> dict:
    """Download OHLCV data for all Nifty 50 stocks."""
    tickers = [f"{t}.NS" for t in NIFTY_50_STOCKS.keys()]
    console.print(f"[cyan]Downloading {len(tickers)} stocks from {START_DATE} to {END_DATE}...[/]")

    try:
        data = yf.download(
            tickers,
            start=START_DATE,
            end=END_DATE,
            group_by="ticker",
            auto_adjust=True,
            threads=True,
        )
        return data
    except Exception as e:
        logger.error(f"Batch download failed: {e}")
        return {}


def download_index_data() -> dict:
    """Download index and macro data."""
    indices = {
        "NIFTY": "^NSEI",
        "BANKNIFTY": "^NSEBANK",
        "INDIA_VIX": "^INDIAVIX",
        "BRENT": "BZ=F",
        "USDINR": "USDINR=X",
        "DOW": "YM=F",
    }

    result = {}
    for name, ticker in indices.items():
        try:
            console.print(f"  Downloading {name} ({ticker})...")
            df = yf.download(ticker, start=START_DATE, end=END_DATE, auto_adjust=True)
            if not df.empty:
                result[name] = df
                console.print(f"    [green]{len(df)} rows[/]")
            else:
                console.print(f"    [yellow]Empty data[/]")
        except Exception as e:
            logger.warning(f"Failed to download {name}: {e}")

    return result


def store_ohlcv_data(stock_data, index_data):
    """Store all OHLCV data in SQLite."""
    import sqlite3
    from config.settings import settings

    conn = sqlite3.connect(settings.DB_PATH)
    cursor = conn.cursor()
    rows_inserted = 0

    # Store stock data
    if hasattr(stock_data, 'columns') and not stock_data.empty if isinstance(stock_data, pd.DataFrame) else stock_data:
        for ticker in NIFTY_50_STOCKS:
            yf_ticker = f"{ticker}.NS"
            try:
                if isinstance(stock_data, pd.DataFrame):
                    if yf_ticker in stock_data.columns.get_level_values(0):
                        df = stock_data[yf_ticker].dropna(how="all")
                    else:
                        continue
                else:
                    continue

                for date, row in df.iterrows():
                    try:
                        date_str = date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date)[:10]
                        cursor.execute(
                            """INSERT OR IGNORE INTO daily_ohlcv
                            (ticker, date, open, high, low, close, volume)
                            VALUES (?, ?, ?, ?, ?, ?, ?)""",
                            (ticker, date_str,
                             float(row.get("Open", 0)), float(row.get("High", 0)),
                             float(row.get("Low", 0)), float(row.get("Close", 0)),
                             int(row.get("Volume", 0))),
                        )
                        rows_inserted += 1
                    except Exception:
                        pass
            except Exception as e:
                logger.debug(f"Skipping {ticker}: {e}")

    # Store index data
    for name, df in index_data.items():
        for date, row in df.iterrows():
            try:
                date_str = date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date)[:10]
                cursor.execute(
                    """INSERT OR IGNORE INTO daily_ohlcv
                    (ticker, date, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (name, date_str,
                     float(row.get("Open", 0)), float(row.get("High", 0)),
                     float(row.get("Low", 0)), float(row.get("Close", 0)),
                     int(row.get("Volume", 0))),
                )
                rows_inserted += 1
            except Exception:
                pass

    conn.commit()
    conn.close()
    return rows_inserted


def compute_and_store_fingerprints(index_data):
    """Compute session fingerprints from historical data for pattern matching."""
    import sqlite3
    from config.settings import settings

    conn = sqlite3.connect(settings.DB_PATH)
    cursor = conn.cursor()

    nifty_df = index_data.get("NIFTY")
    vix_df = index_data.get("INDIA_VIX")
    brent_df = index_data.get("BRENT")

    if nifty_df is None or nifty_df.empty:
        logger.warning("No Nifty data — skipping fingerprint computation")
        return 0

    # Flatten multi-index columns if present
    if isinstance(nifty_df.columns, pd.MultiIndex):
        nifty_df.columns = nifty_df.columns.get_level_values(0)
    if vix_df is not None and isinstance(vix_df.columns, pd.MultiIndex):
        vix_df.columns = vix_df.columns.get_level_values(0)
    if brent_df is not None and isinstance(brent_df.columns, pd.MultiIndex):
        brent_df.columns = brent_df.columns.get_level_values(0)

    fingerprints_stored = 0

    # Compute Nifty-level fingerprints
    nifty_close = nifty_df["Close"] if "Close" in nifty_df.columns else nifty_df.iloc[:, 3]

    for i in range(20, len(nifty_df)):
        try:
            date = nifty_df.index[i]
            date_str = date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date)[:10]

            prev_close = float(nifty_close.iloc[i - 1])
            open_price = float(nifty_df.iloc[i].get("Open", nifty_close.iloc[i]))
            close_price = float(nifty_close.iloc[i])
            high_price = float(nifty_df.iloc[i].get("High", close_price))

            gap_pct = ((open_price - prev_close) / prev_close) * 100 if prev_close > 0 else 0

            # VIX
            vix_level = 0.0
            vix_change = 0.0
            if vix_df is not None and date in vix_df.index:
                vix_close = vix_df["Close"] if "Close" in vix_df.columns else vix_df.iloc[:, 3]
                idx = vix_df.index.get_loc(date)
                vix_level = float(vix_close.iloc[idx]) if idx < len(vix_close) else 0
                if idx > 0:
                    prev_vix = float(vix_close.iloc[idx - 1])
                    vix_change = ((vix_level - prev_vix) / prev_vix * 100) if prev_vix > 0 else 0

            # Brent
            crude_change = 0.0
            if brent_df is not None and date in brent_df.index:
                brent_close = brent_df["Close"] if "Close" in brent_df.columns else brent_df.iloc[:, 3]
                idx = brent_df.index.get_loc(date)
                if idx > 0:
                    crude_change = ((float(brent_close.iloc[idx]) - float(brent_close.iloc[idx - 1]))
                                    / float(brent_close.iloc[idx - 1]) * 100) if float(brent_close.iloc[idx - 1]) > 0 else 0

            # RSI proxy
            window = nifty_close.iloc[i - 14:i]
            delta = window.diff().dropna()
            gain = delta.where(delta > 0, 0).mean()
            loss = (-delta.where(delta < 0, 0)).mean()
            rsi = 100 - (100 / (1 + gain / loss)) if loss > 0 else 50

            # 5-day return
            prev_5d = float(nifty_close.iloc[i - 5]) if i >= 5 else prev_close
            prev_5d_ret = ((prev_close - prev_5d) / prev_5d * 100) if prev_5d > 0 else 0

            # Volume ratio
            vol = float(nifty_df.iloc[i].get("Volume", 0))
            avg_vol = float(nifty_df.iloc[i - 20:i]["Volume"].mean()) if "Volume" in nifty_df.columns else 1
            vol_ratio = vol / avg_vol if avg_vol > 0 else 1.0

            # Day of week
            dow = date.weekday() if hasattr(date, "weekday") else 0

            # Expiry week (simplified)
            is_expiry = 0
            days_to_exp = 30

            # Outcome
            closed_above = 1 if close_price > open_price else 0
            intraday_ret = ((close_price - open_price) / open_price * 100) if open_price > 0 else 0
            max_dd = ((open_price - float(nifty_df.iloc[i].get("Low", open_price))) / open_price * 100) if open_price > 0 else 0

            # ATR proxy: (high - low) / close as %
            low_price = float(nifty_df.iloc[i].get("Low", close_price))
            atr_pct = ((high_price - low_price) / prev_close * 100) if prev_close > 0 else 0

            # Outcome
            nifty_close_change = intraday_ret
            nifty_high_change = ((high_price - open_price) / open_price * 100) if open_price > 0 else 0
            nifty_low_change = max_dd

            cursor.execute(
                """INSERT OR IGNORE INTO session_fingerprints
                (date, gap_pct, crude_change, dow_change, usdinr_change,
                 vix, pcr, fii_net, dii_net, max_pain_dist,
                 sector_leader, day_of_week, is_expiry_week,
                 rsi_14, atr_pct, volume_ratio,
                 nifty_close_change, nifty_high_change, nifty_low_change, outcome_filled)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (date_str, gap_pct, crude_change, 0.0, 0.0,
                 vix_level, 1.0, 0.0, 0.0, 0.0,
                 "", dow, is_expiry,
                 rsi, atr_pct, vol_ratio,
                 nifty_close_change, nifty_high_change, nifty_low_change, 1),
            )
            fingerprints_stored += 1
        except Exception as e:
            logger.debug(f"Fingerprint error at index {i}: {e}")

    conn.commit()
    conn.close()
    return fingerprints_stored


async def run_backfill():
    """Main backfill entrypoint."""
    console.print("[bold cyan]Alpha Edge — Historical Data Backfill[/]")
    console.print(f"Period: {START_DATE} to {END_DATE}\n")

    init_db()

    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:

        # Step 1: Download stock data
        task = progress.add_task("Downloading Nifty 50 stocks...", total=3)
        stock_data = await asyncio.to_thread(download_stock_data)
        progress.advance(task)

        # Step 2: Download index data
        progress.update(task, description="Downloading indices & macro...")
        index_data = await asyncio.to_thread(download_index_data)
        progress.advance(task)

        # Step 3: Store everything
        progress.update(task, description="Storing OHLCV data...")
        rows = await asyncio.to_thread(store_ohlcv_data, stock_data, index_data)
        console.print(f"  [green]Stored {rows:,} OHLCV rows[/]")
        progress.advance(task)

    # Step 4: Compute fingerprints
    console.print("\n[cyan]Computing session fingerprints...[/]")
    fp_count = await asyncio.to_thread(compute_and_store_fingerprints, index_data)
    console.print(f"  [green]Stored {fp_count:,} fingerprints[/]")

    console.print("\n[bold green]Backfill complete![/]")


if __name__ == "__main__":
    asyncio.run(run_backfill())
