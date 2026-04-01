"""Collector for macro market data: Nifty, BankNifty, Dow, Brent, USD/INR, VIX."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Tuple, Dict, List

import yfinance as yf
from loguru import logger

from data.collectors.base import BaseCollector
from data.models import MacroDashboard, MacroDataPoint
from config.constants import EXPECTED_OPEN_COEFFICIENTS


class MarketDataCollector(BaseCollector):
    name = "market_data"

    # Tickers to fetch
    MACRO_TICKERS = {
        "nifty": "^NSEI",
        "banknifty": "^NSEBANK",
        "dow_futures": "YM=F",
        "brent_crude": "BZ=F",
        "usdinr": "USDINR=X",
        "india_vix": "^INDIAVIX",
    }

    async def _collect(self) -> Tuple[MacroDashboard, List[dict], List[dict]]:
        """Collect macro dashboard + 30-day OHLCV for Nifty/BankNifty.

        Returns:
            (MacroDashboard, nifty_ohlcv_rows, banknifty_ohlcv_rows)
        """
        # Fetch all macro tickers in one batch via yfinance (sync, run in thread)
        all_symbols = list(self.MACRO_TICKERS.values())
        symbol_str = " ".join(all_symbols)

        data_30d = await self._run_sync(
            yf.download, symbol_str, period="30d", group_by="ticker", progress=False
        )
        data_5d = await self._run_sync(
            yf.download, symbol_str, period="5d", group_by="ticker", progress=False
        )

        now_str = datetime.now(timezone.utc).isoformat()

        # Helper to extract a MacroDataPoint from downloaded data
        def _make_point(df_30d, df_5d, ticker: str) -> MacroDataPoint:
            try:
                # Handle both multi-ticker and single-ticker dataframes
                if ticker in df_30d.columns.get_level_values(0):
                    closes = df_30d[ticker]["Close"].dropna()
                else:
                    closes = df_30d["Close"].dropna()

                if len(closes) < 2:
                    return MacroDataPoint(source="yfinance", timestamp=now_str, fresh=False)

                last = float(closes.iloc[-1])
                prev = float(closes.iloc[-2])
                change = last - prev
                change_pct = (change / prev) * 100 if prev != 0 else 0.0
                sparkline = closes.tail(10).tolist()
                direction = "up" if change > 0 else ("down" if change < 0 else "flat")

                return MacroDataPoint(
                    value=round(last, 2),
                    change=round(change, 2),
                    change_pct=round(change_pct, 2),
                    sparkline=[round(v, 2) for v in sparkline],
                    source="yfinance",
                    timestamp=now_str,
                    fresh=True,
                    direction=direction,
                )
            except Exception as exc:
                logger.warning(f"[market_data] Failed to parse {ticker}: {exc}")
                return MacroDataPoint(source="yfinance", timestamp=now_str, fresh=False)

        nifty_pt = _make_point(data_30d, data_5d, "^NSEI")
        banknifty_pt = _make_point(data_30d, data_5d, "^NSEBANK")
        dow_pt = _make_point(data_30d, data_5d, "YM=F")
        brent_pt = _make_point(data_30d, data_5d, "BZ=F")
        usdinr_pt = _make_point(data_30d, data_5d, "USDINR=X")
        vix_pt = _make_point(data_30d, data_5d, "^INDIAVIX")

        # Compute expected Nifty open
        nifty_prev_close = nifty_pt.value if nifty_pt.fresh else 0.0
        banknifty_prev_close = banknifty_pt.value if banknifty_pt.fresh else 0.0

        coeff = EXPECTED_OPEN_COEFFICIENTS
        expected_nifty_open = nifty_prev_close * (
            1
            + coeff["dow_weight"] * (dow_pt.change_pct / 100)
            + coeff["brent_weight"] * (brent_pt.change_pct / 100)
            + coeff["usdinr_weight"] * (usdinr_pt.change_pct / 100)
        ) if nifty_prev_close else 0.0

        expected_banknifty_open = banknifty_prev_close * (
            1
            + coeff["dow_weight"] * (dow_pt.change_pct / 100)
            + coeff["brent_weight"] * (brent_pt.change_pct / 100)
            + coeff["usdinr_weight"] * (usdinr_pt.change_pct / 100)
        ) if banknifty_prev_close else 0.0

        # Use Nifty data as SGX proxy (SGX Nifty discontinued; Nifty prev close + global cues is the proxy)
        sgx_pt = MacroDataPoint(
            value=round(expected_nifty_open, 2),
            change=round(expected_nifty_open - nifty_prev_close, 2),
            change_pct=round(
                ((expected_nifty_open - nifty_prev_close) / nifty_prev_close) * 100, 2
            ) if nifty_prev_close else 0.0,
            sparkline=nifty_pt.sparkline,
            source="computed_proxy",
            timestamp=now_str,
            fresh=nifty_pt.fresh,
            direction="up" if expected_nifty_open > nifty_prev_close else (
                "down" if expected_nifty_open < nifty_prev_close else "flat"
            ),
        )

        dashboard = MacroDashboard(
            sgx_nifty=sgx_pt,
            dow_futures=dow_pt,
            brent_crude=brent_pt,
            usdinr=usdinr_pt,
            india_vix=vix_pt,
            # fii_net and dii_net filled later by FIIDIICollector
            nifty_prev_close=round(nifty_prev_close, 2),
            banknifty_prev_close=round(banknifty_prev_close, 2),
            expected_nifty_open=round(expected_nifty_open, 2),
            expected_banknifty_open=round(expected_banknifty_open, 2),
        )

        # Extract 30-day OHLCV rows for Nifty and BankNifty
        nifty_ohlcv = self._extract_ohlcv(data_30d, "^NSEI")
        banknifty_ohlcv = self._extract_ohlcv(data_30d, "^NSEBANK")

        return dashboard, nifty_ohlcv, banknifty_ohlcv

    def _extract_ohlcv(self, df, ticker: str) -> List[dict]:
        """Extract OHLCV rows as list of dicts from a multi-ticker download."""
        try:
            if ticker in df.columns.get_level_values(0):
                sub = df[ticker].dropna(how="all")
            else:
                sub = df.dropna(how="all")

            rows = []
            for idx, row in sub.iterrows():
                rows.append({
                    "date": idx.strftime("%Y-%m-%d"),
                    "open": round(float(row.get("Open", 0)), 2),
                    "high": round(float(row.get("High", 0)), 2),
                    "low": round(float(row.get("Low", 0)), 2),
                    "close": round(float(row.get("Close", 0)), 2),
                    "volume": int(row.get("Volume", 0)),
                })
            return rows
        except Exception as exc:
            logger.warning(f"[market_data] OHLCV extraction failed for {ticker}: {exc}")
            return []

    def _default(self):
        return MacroDashboard(), [], []
