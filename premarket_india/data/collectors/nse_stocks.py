"""Collector for Nifty 50 stock OHLCV data via yfinance batch download."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Dict

import yfinance as yf
from loguru import logger

from data.collectors.base import BaseCollector
from data.models import StockOHLCV
from config.constants import NIFTY_50_STOCKS


class NSEStockCollector(BaseCollector):
    name = "nse_stocks"
    timeout = 60  # Larger timeout — 50 stocks take time

    async def _collect(self) -> List[StockOHLCV]:
        """Batch download Nifty 50 stock data and return previous-day OHLCV."""
        # Build yfinance ticker list (append .NS)
        ticker_map: Dict[str, str] = {}  # yf_ticker -> nse_symbol
        for symbol in NIFTY_50_STOCKS:
            yf_ticker = f"{symbol}.NS"
            ticker_map[yf_ticker] = symbol

        yf_tickers = list(ticker_map.keys())
        symbol_str = " ".join(yf_tickers)

        # Download 30 days for volume average calculation
        logger.info(f"[nse_stocks] Downloading {len(yf_tickers)} stocks (30d)")
        data = await self._run_sync(
            yf.download, symbol_str, period="30d", group_by="ticker", progress=False
        )

        now_str = datetime.now(timezone.utc).isoformat()
        results: List[StockOHLCV] = []

        for yf_ticker, nse_symbol in ticker_map.items():
            try:
                # Extract per-ticker data
                if len(yf_tickers) == 1:
                    stock_df = data.dropna(how="all")
                elif yf_ticker in data.columns.get_level_values(0):
                    stock_df = data[yf_ticker].dropna(how="all")
                else:
                    logger.debug(f"[nse_stocks] No data for {nse_symbol}")
                    continue

                if stock_df.empty or len(stock_df) < 2:
                    continue

                # Previous day = last row
                last = stock_df.iloc[-1]
                vol_col = "Volume"
                close_col = "Close"

                # 20-day volume average
                vol_series = stock_df[vol_col].dropna().tail(20)
                vol_avg_20d = int(vol_series.mean()) if len(vol_series) > 0 else 0
                current_vol = int(last.get(vol_col, 0))
                vol_ratio = round(current_vol / vol_avg_20d, 2) if vol_avg_20d > 0 else 1.0

                info = NIFTY_50_STOCKS[nse_symbol]

                results.append(StockOHLCV(
                    ticker=nse_symbol,
                    name=info["name"],
                    sector=info["sector"],
                    open=round(float(last.get("Open", 0)), 2),
                    high=round(float(last.get("High", 0)), 2),
                    low=round(float(last.get("Low", 0)), 2),
                    close=round(float(last.get(close_col, 0)), 2),
                    volume=current_vol,
                    volume_avg_20d=vol_avg_20d,
                    volume_ratio=vol_ratio,
                ))
            except Exception as exc:
                logger.warning(f"[nse_stocks] Failed to parse {nse_symbol}: {exc}")
                continue

        logger.info(f"[nse_stocks] Parsed {len(results)}/{len(yf_tickers)} stocks")
        return results

    def _default(self) -> List[StockOHLCV]:
        return []
